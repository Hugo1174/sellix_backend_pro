from decimal import Decimal

from django.db.models import Count, Sum
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.catalog.models import Product
from apps.finance.constants import PayoutStatus
from apps.finance.models import Payout
from apps.finance.services import confirm_payout, mark_payout_processing
from apps.common.permissions import IsPlatformAdmin
from apps.orders.constants import OrderStatus
from apps.orders.models import Order
from apps.orders.serializers import OrderSerializer
from apps.tenants.constants import IntegrationStatus, ProducerStatus, StoreStatus
from apps.tenants.models import Producer, ShopIntegration, Store
from .models import AuditLog, write_audit
from .serializers import (
    AdminOrderSerializer,
    AdminPayoutSerializer,
    AdminProducerSerializer,
    AdminProductSerializer,
    AdminStoreSerializer,
    AdminUserSerializer,
    AuditLogSerializer,
)


class DashboardView(APIView):
    """PRD 9.3 — сводные метрики платформы."""

    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        completed = Order.objects.filter(status=OrderStatus.COMPLETED)
        gmv = completed.aggregate(s=Sum("grand_total"))["s"] or Decimal("0")
        status_funnel = dict(
            Order.objects.values_list("status").annotate(c=Count("id"))
        )
        pending_payouts = Payout.objects.filter(
            status=PayoutStatus.PENDING
        ).aggregate(s=Sum("amount"))["s"] or Decimal("0")
        return Response({
            "gmv_completed": str(gmv),
            "orders_total": Order.objects.count(),
            "orders_by_status": {k: v for k, v in status_funnel.items()},
            "users_total": User.objects.count(),
            "stores_total": Store.objects.count(),
            "stores_published": Store.objects.filter(status=StoreStatus.PUBLISHED).count(),
            "producers_total": Producer.objects.count(),
            "products_total": Product.objects.count(),
            "pending_payouts_sum": str(pending_payouts),
            "integration_errors": ShopIntegration.objects.filter(
                status=IntegrationStatus.ERROR).count(),
        })


class AdminUserViewSet(viewsets.ReadOnlyModelViewSet):
    """PRD 9.1 — управление пользователями + блокировка (US-70)."""

    queryset = User.objects.all().order_by("-created_at")
    serializer_class = AdminUserSerializer
    permission_classes = [IsPlatformAdmin]
    filterset_fields = ["role", "is_blocked"]
    search_fields = ["email", "full_name", "phone"]

    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        user = self.get_object()
        user.is_blocked = True
        user.blocked_reason = request.data.get("reason", "")
        user.save(update_fields=["is_blocked", "blocked_reason", "updated_at"])
        write_audit(request.user, "block", "user", user.id,
                    {"reason": user.blocked_reason})
        return Response(AdminUserSerializer(user).data)

    @action(detail=True, methods=["post"])
    def unblock(self, request, pk=None):
        user = self.get_object()
        user.is_blocked = False
        user.blocked_reason = ""
        user.save(update_fields=["is_blocked", "blocked_reason", "updated_at"])
        write_audit(request.user, "unblock", "user", user.id)
        return Response(AdminUserSerializer(user).data)


class AdminStoreViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Store.objects.all().order_by("-created_at")
    serializer_class = AdminStoreSerializer
    permission_classes = [IsPlatformAdmin]
    filterset_fields = ["status", "niche"]
    search_fields = ["name", "slug"]

    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        store = self.get_object()
        store.status = StoreStatus.BLOCKED
        store.blocked_reason = request.data.get("reason", "")
        store.save(update_fields=["status", "blocked_reason", "updated_at"])
        write_audit(request.user, "block", "store", store.id)
        return Response(AdminStoreSerializer(store).data)

    @action(detail=True, methods=["post"])
    def unblock(self, request, pk=None):
        store = self.get_object()
        store.status = StoreStatus.DRAFT
        store.blocked_reason = ""
        store.save(update_fields=["status", "blocked_reason", "updated_at"])
        write_audit(request.user, "unblock", "store", store.id)
        return Response(AdminStoreSerializer(store).data)


class AdminProducerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Producer.objects.all().order_by("-created_at")
    serializer_class = AdminProducerSerializer
    permission_classes = [IsPlatformAdmin]
    filterset_fields = ["status"]
    search_fields = ["company_name", "inn"]

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        producer = self.get_object()
        producer.status = ProducerStatus.APPROVED
        producer.save(update_fields=["status", "updated_at"])
        write_audit(request.user, "approve", "producer", producer.id)
        return Response(AdminProducerSerializer(producer).data)

    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        producer = self.get_object()
        producer.status = ProducerStatus.BLOCKED
        producer.blocked_reason = request.data.get("reason", "")
        producer.save(update_fields=["status", "blocked_reason", "updated_at"])
        write_audit(request.user, "block", "producer", producer.id)
        return Response(AdminProducerSerializer(producer).data)


class AdminProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all().select_related("producer").order_by("-created_at")
    serializer_class = AdminProductSerializer
    permission_classes = [IsPlatformAdmin]
    filterset_fields = ["status", "category"]
    search_fields = ["name", "sku"]


class AdminOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """PRD 9.4 — список заказов + карточка спора (детальный просмотр)."""

    queryset = Order.objects.all().order_by("-created_at")
    serializer_class = AdminOrderSerializer
    permission_classes = [IsPlatformAdmin]
    filterset_fields = ["status"]
    search_fields = ["number"]

    def retrieve(self, request, *args, **kwargs):
        order = self.get_object()
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["post"])
    def force_status(self, request, pk=None):
        """PRD 9.4 — ручной перевод статуса для разрешения спора."""
        from apps.orders.constants import ActorType
        from apps.orders.services import transition
        order = self.get_object()
        to_status = request.data.get("status")
        transition(order, to_status, actor_type=ActorType.ADMIN,
                   actor_id=request.user.id, force=True,
                   comment=request.data.get("comment", "Ручной перевод (спор)"))
        write_audit(request.user, "force_status", "order", order.id,
                    {"to": to_status})
        return Response(OrderSerializer(order).data)


class AdminPayoutViewSet(viewsets.ReadOnlyModelViewSet):
    """PRD 9.3, US-62 — реестр выплат и подтверждение."""

    queryset = Payout.objects.all().select_related("order").order_by("-created_at")
    serializer_class = AdminPayoutSerializer
    permission_classes = [IsPlatformAdmin]
    filterset_fields = ["status", "payee_type"]

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        payout = self.get_object()
        confirm_payout(payout, note=request.data.get("note", ""))
        write_audit(request.user, "confirm_payout", "payout", payout.id)
        return Response(AdminPayoutSerializer(payout).data)

    @action(detail=True, methods=["post"])
    def processing(self, request, pk=None):
        payout = self.get_object()
        mark_payout_processing(payout)
        return Response(AdminPayoutSerializer(payout).data)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all().select_related("actor")
    serializer_class = AuditLogSerializer
    permission_classes = [IsPlatformAdmin]
    filterset_fields = ["target_entity", "action"]
