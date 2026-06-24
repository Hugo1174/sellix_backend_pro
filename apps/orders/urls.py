from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BuyerOrderViewSet,
    CheckoutQuoteView,
    CheckoutView,
    ProducerShipmentViewSet,
    SellerOrderViewSet,
)

router = DefaultRouter()
router.register("buyer/orders", BuyerOrderViewSet, basename="buyer-order")
router.register("seller/orders", SellerOrderViewSet, basename="seller-order")
router.register("producer/shipments", ProducerShipmentViewSet, basename="producer-shipment")

urlpatterns = [
    path("checkout/quote/", CheckoutQuoteView.as_view(), name="checkout-quote"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("", include(router.urls)),
]
