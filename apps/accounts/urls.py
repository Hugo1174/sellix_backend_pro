from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AdminLoginView,
    BuyerAddressViewSet,
    LogoutView,
    MeView,
    OAuthLoginView,
    SelectRoleView,
)

router = DefaultRouter()
router.register("addresses", BuyerAddressViewSet, basename="buyer-address")

urlpatterns = [
    path("auth/oauth/", OAuthLoginView.as_view(), name="oauth-login"),
    path("auth/admin/", AdminLoginView.as_view(), name="admin-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("me/role/", SelectRoleView.as_view(), name="select-role"),
    path("", include(router.urls)),
]
