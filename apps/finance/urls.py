from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ProducerPayoutViewSet, SellerPayoutViewSet

router = DefaultRouter()
router.register("seller/payouts", SellerPayoutViewSet, basename="seller-payout")
router.register("producer/payouts", ProducerPayoutViewSet, basename="producer-payout")

urlpatterns = [path("", include(router.urls))]
