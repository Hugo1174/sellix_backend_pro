from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminOrderViewSet,
    AdminPayoutViewSet,
    AdminProducerViewSet,
    AdminProductViewSet,
    AdminStoreViewSet,
    AdminUserViewSet,
    AuditLogViewSet,
    DashboardView,
)

router = DefaultRouter()
router.register("users", AdminUserViewSet, basename="admin-user")
router.register("stores", AdminStoreViewSet, basename="admin-store")
router.register("producers", AdminProducerViewSet, basename="admin-producer")
router.register("products", AdminProductViewSet, basename="admin-product")
router.register("orders", AdminOrderViewSet, basename="admin-order")
router.register("payouts", AdminPayoutViewSet, basename="admin-payout")
router.register("audit", AuditLogViewSet, basename="admin-audit")

urlpatterns = [
    path("admin-panel/dashboard/", DashboardView.as_view(), name="admin-dashboard"),
    path("admin-panel/", include(router.urls)),
]
