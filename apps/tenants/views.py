from django.db import transaction
from django.db.models import Count
from django.utils.text import slugify
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsProducer, IsSeller, IsSellerOrProducer
from .constants import IntegrationKind, IntegrationOwnerType, ProducerStatus, StoreStatus
from .models import Producer, ShopIntegration, Store
from .serializers import (
    IntegrationSerializer,
    ProducerCreateSerializer,
    ProducerPublicSerializer,
    ProducerSerializer,
    SlugCheckSerializer,
    StoreCreateSerializer,
    StoreSerializer,
)
from .services import verify_integration


class MyStoreView(APIView):
    """Создание/получение/обновление магазина продавца. 1 на пользователя."""

    permission_classes = [IsSeller]

    def get(self, request):
        store = getattr(request.user, "store", None)
        if store is None:
            return Response({"detail": "Магазин не создан"}, status=status.HTTP_404_NOT_FOUND)
        return Response(StoreSerializer(store, context={"request": request}).data)

    @transaction.atomic
    def post(self, request):
        if getattr(request.user, "store", None) is not None:
            raise ValidationError("В MVP допускается один магазин на продавца")
        ser = StoreCreateSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        store = ser.save()
        return Response(
            StoreSerializer(store, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def patch(self, request):
        store = getattr(request.user, "store", None)
        if store is None:
            return Response({"detail": "Магазин не создан"}, status=status.HTTP_404_NOT_FOUND)
        ser = StoreSerializer(store, data=request.data, partial=True,
                              context={"request": request})
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class StorePublishView(APIView):
    """Публикация магазина: нужен товар + оплата."""

    permission_classes = [IsSeller]

    def post(self, request):
        store = getattr(request.user, "store", None)
        if store is None:
            return Response({"detail": "Магазин не создан"}, status=status.HTTP_404_NOT_FOUND)
        if not store.can_publish():
            return Response(
                {"detail": "Для публикации нужен минимум один видимый товар "
                           "и активная платёжная интеграция."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        store.status = StoreStatus.PUBLISHED
        store.save(update_fields=["status", "updated_at"])
        return Response(StoreSerializer(store, context={"request": request}).data)


class SlugCheckView(APIView):
    permission_classes = [IsSeller]

    def post(self, request):
        ser = SlugCheckSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        slug = slugify(ser.validated_data["name"], allow_unicode=False)
        available = bool(slug) and not Store.objects.filter(slug=slug).exists()
        return Response({"slug": slug, "available": available})


class MyProducerView(APIView):
    """Создание/получение/обновление профиля производителя."""

    permission_classes = [IsProducer]

    def get(self, request):
        producer = getattr(request.user, "producer", None)
        if producer is None:
            return Response({"detail": "Профиль не создан"}, status=status.HTTP_404_NOT_FOUND)
        return Response(ProducerSerializer(producer).data)

    @transaction.atomic
    def post(self, request):
        if getattr(request.user, "producer", None) is not None:
            raise ValidationError("Профиль производителя уже создан")
        ser = ProducerCreateSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        producer = ser.save()
        return Response(ProducerSerializer(producer).data, status=status.HTTP_201_CREATED)

    def patch(self, request):
        producer = getattr(request.user, "producer", None)
        if producer is None:
            return Response({"detail": "Профиль не создан"}, status=status.HTTP_404_NOT_FOUND)
        ser = ProducerSerializer(producer, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class ProducerProfileView(APIView):
    """Публичный профиль производителя по id.

    Production: продавец может кликнуть на производителя в пуле и просмотреть
    его полный ассортимент.
    """

    permission_classes = [IsSellerOrProducer]

    def get(self, request, producer_id):
        producer = (Producer.objects
                    .filter(id=producer_id, status=ProducerStatus.APPROVED)
                    .annotate(_product_count=Count("products"))
                    .first())
        if producer is None:
            raise NotFound("Производитель не найден")
        return Response(ProducerPublicSerializer(producer).data)


class ProducerProductsPublicView(APIView):
    """Все опубликованные товары конкретного производителя (для продавцов)."""

    permission_classes = [IsSellerOrProducer]

    def get(self, request, producer_id):
        from apps.catalog.constants import ProductStatus
        from apps.catalog.models import Product
        from apps.catalog.serializers import ProductSerializer

        producer = Producer.objects.filter(
            id=producer_id, status=ProducerStatus.APPROVED
        ).first()
        if producer is None:
            raise NotFound("Производитель не найден")

        products = (Product.objects
                    .filter(producer=producer,
                            status__in=[ProductStatus.PUBLISHED, ProductStatus.OUT_OF_STOCK])
                    .select_related("category", "producer")
                    .prefetch_related("images")
                    .annotate(_store_count=Count("store_links")))
        return Response(ProductSerializer(products, many=True).data)


class IntegrationViewSet(viewsets.ModelViewSet):
    """Подключение оплаты/доставки. Для store и producer."""

    serializer_class = IntegrationSerializer
    permission_classes = [IsSellerOrProducer]

    def _owner(self):
        user = self.request.user
        store = getattr(user, "store", None)
        producer = getattr(user, "producer", None)
        return store, producer

    def get_queryset(self):
        store, producer = self._owner()
        qs = ShopIntegration.objects.none()
        if store is not None:
            qs = ShopIntegration.objects.filter(store=store)
        elif producer is not None:
            qs = ShopIntegration.objects.filter(producer=producer)
        return qs.order_by("kind", "provider")

    @transaction.atomic
    def perform_create(self, serializer):
        store, producer = self._owner()
        if store is not None:
            owner_type = IntegrationOwnerType.STORE
            integration = serializer.save(owner_type=owner_type, store=store)
        elif producer is not None:
            owner_type = IntegrationOwnerType.PRODUCER
            integration = serializer.save(owner_type=owner_type, producer=producer)
        else:
            raise PermissionDenied("Нет привязанного магазина/профиля")
        verify_integration(integration)

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        integration = self.get_object()
        verify_integration(integration)
        return Response(IntegrationSerializer(integration).data)
