from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.constants import Role
from apps.catalog.models import StoreProduct
from apps.common.permissions import IsBuyer, IsProducer, IsSeller
from apps.tenants.constants import StoreStatus
from apps.tenants.models import Store
from .constants import ActorType, OrderStatus, ShipmentStatus
from .models import Order, Shipment
from .serializers import (
    CheckoutSerializer,
    OrderSerializer,
    OrderTrackingSerializer,
)
from .services import (
    OrderError,
    create_order,
    create_shipment_label,
    mark_assembling,
    quote_delivery,
    transition,
)


class CheckoutQuoteView(APIView):
    """US-32. Предварительный расчёт доставки по адресу (до оплаты)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        slug = request.data.get("store_slug")
        city = (request.data.get("address") or {}).get("city", "")
        items_raw = request.data.get("items", [])
        store = Store.objects.filter(slug=slug, status=StoreStatus.PUBLISHED).first()
        if store is None:
            raise NotFound("Магазин не найден")
        items_by_producer = {}
        goods = 0
        for entry in items_raw:
            sp = StoreProduct.objects.filter(
                id=entry["store_product_id"], store=store, is_visible=True
            ).select_related("product__producer").first()
            if sp is None:
                continue
            qty = int(entry["quantity"])
            items_by_producer.setdefault(sp.product.producer, []).append((sp, qty))
            goods += float(sp.retail_price) * qty
        quotes = quote_delivery(store, items_by_producer, city)
        delivery_total = sum(float(q["fee"]) for q in quotes.values())
        return Response({
            "goods_total": round(goods, 2),
            "delivery_total": round(delivery_total, 2),
            "grand_total": round(goods + delivery_total, 2),
            "delivery_by_producer": [
                {"producer": str(pid), "provider": q["provider"], "fee": str(q["fee"])}
                for pid, q in quotes.items()
            ],
        })


class CheckoutView(APIView):
    """US-31/32/33. Создание заказа покупателем."""

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        # Покупателю роль присваивается автоматически при первом заказе (PRD 6.4)
        if request.user.role is None:
            request.user.role = Role.BUYER
            request.user.save(update_fields=["role", "updated_at"])
        if request.user.role != Role.BUYER:
            raise PermissionDenied("Заказы оформляет только покупатель")

        ser = CheckoutSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        slug = ser.validated_data["store_slug"]
        store = Store.objects.filter(slug=slug, status=StoreStatus.PUBLISHED).first()
        if store is None:
            raise NotFound("Магазин не найден или не опубликован")

        items = []
        entries = ser.validated_data.get("items")
        if not entries:
            from apps.storefront.models import Cart
            cart = Cart.objects.filter(user=request.user, store=store,
                                       is_active=True).first()
            if cart:
                entries = [{"store_product_id": ci.store_product_id,
                            "quantity": ci.quantity} for ci in cart.items.all()]
        if not entries:
            raise ValidationError("Корзина пуста")

        for entry in entries:
            sp = StoreProduct.objects.filter(
                id=entry["store_product_id"], store=store, is_visible=True
            ).select_related("product__producer").first()
            if sp is None:
                raise ValidationError("Один из товаров недоступен")
            items.append((sp, int(entry["quantity"])))

        try:
            order = create_order(buyer=request.user, store=store, items=items,
                                 address=ser.validated_data["address"])
        except OrderError as exc:
            raise ValidationError(str(exc))

        # Инициируем платёж (PRD 6.4)
        from apps.payments.services import initiate_payment
        payment = initiate_payment(order)
        return Response(
            {
                "order": OrderSerializer(order).data,
                "payment": {
                    "id": str(payment.id),
                    "provider": payment.provider,
                    "confirmation_url": payment.confirmation_url,
                    "status": payment.status,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class BuyerOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """US-34. История заказов покупателя across всех магазинов."""

    serializer_class = OrderSerializer
    permission_classes = [IsBuyer]

    def get_queryset(self):
        return (Order.objects.filter(buyer=self.request.user)
                .prefetch_related("items", "shipments", "status_events"))

    @action(detail=True, methods=["get"])
    def tracking(self, request, pk=None):
        order = self.get_object()
        return Response(OrderTrackingSerializer(order).data)

    @action(detail=True, methods=["post"])
    def confirm_delivery(self, request, pk=None):
        """US-53. Покупатель вручную подтверждает получение (PRD 6.8)."""
        order = self.get_object()
        try:
            transition(order, OrderStatus.DELIVERED, actor_type=ActorType.BUYER,
                       actor_id=request.user.id, comment="Подтверждено покупателем")
        except OrderError as exc:
            raise ValidationError(str(exc))
        return Response(OrderTrackingSerializer(order).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """PRD 10.3 #4 — отмена до сборки с возвратом средств."""
        order = self.get_object()
        if order.status not in (OrderStatus.PAID, OrderStatus.SENT_TO_PRODUCER,
                                OrderStatus.CREATED):
            raise ValidationError("Заказ уже в обработке, отмена невозможна")
        try:
            transition(order, OrderStatus.CANCELLED, actor_type=ActorType.BUYER,
                       actor_id=request.user.id, comment="Отменён покупателем")
        except OrderError as exc:
            raise ValidationError(str(exc))
        return Response(OrderSerializer(order).data)


class SellerOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """US-40. Заказы магазина продавца (наблюдатель, без подтверждения)."""

    serializer_class = OrderSerializer
    permission_classes = [IsSeller]
    filterset_fields = ["status"]

    def get_queryset(self):
        store = getattr(self.request.user, "store", None)
        if store is None:
            return Order.objects.none()
        return (Order.objects.filter(store=store)
                .prefetch_related("items", "shipments", "status_events"))


class ProducerShipmentViewSet(viewsets.ReadOnlyModelViewSet):
    """US-41/42/43. Производитель видит только свои отгрузки."""

    permission_classes = [IsProducer]
    filterset_fields = ["status"]

    def get_queryset(self):
        producer = getattr(self.request.user, "producer", None)
        if producer is None:
            return Shipment.objects.none()
        return (Shipment.objects.filter(producer=producer)
                .select_related("order").prefetch_related("order__items"))

    def get_serializer_class(self):
        from .serializers import ShipmentSerializer
        return ShipmentSerializer

    def retrieve(self, request, *args, **kwargs):
        shipment = self.get_object()
        from .serializers import ShipmentSerializer, OrderItemSerializer
        data = ShipmentSerializer(shipment).data
        # Только позиции этого производителя (US-41)
        my_items = shipment.order.items.filter(producer=shipment.producer)
        data["items"] = OrderItemSerializer(my_items, many=True).data
        data["order_number"] = shipment.order.number
        data["ship_city"] = shipment.order.ship_city
        data["ship_address"] = shipment.order.ship_address
        return Response(data)

    @action(detail=True, methods=["post"])
    def assemble(self, request, pk=None):
        shipment = self.get_object()
        mark_assembling(shipment, actor_id=request.user.id)
        from .serializers import ShipmentSerializer
        return Response(ShipmentSerializer(shipment).data)

    @action(detail=True, methods=["post"])
    def ship(self, request, pk=None):
        shipment = self.get_object()
        try:
            create_shipment_label(shipment, actor_id=request.user.id)
        except Exception as exc:  # noqa: BLE001
            raise ValidationError(str(exc))
        from .serializers import ShipmentSerializer
        return Response(ShipmentSerializer(shipment).data)
