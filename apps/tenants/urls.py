from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    IntegrationViewSet,
    MyProducerView,
    MyStoreView,
    ProducerProductsPublicView,
    ProducerProfileView,
    SlugCheckView,
    StorePublishView,
)

router = DefaultRouter()
router.register("integrations", IntegrationViewSet, basename="integration")

urlpatterns = [
    path("seller/store/", MyStoreView.as_view(), name="my-store"),
    path("seller/store/publish/", StorePublishView.as_view(), name="store-publish"),
    path("seller/store/slug-check/", SlugCheckView.as_view(), name="slug-check"),
    path("producer/profile/", MyProducerView.as_view(), name="my-producer"),
    # Публичные профили производителей (для просмотра в пуле).
    path("producers/<uuid:producer_id>/", ProducerProfileView.as_view(),
         name="producer-profile"),
    path("producers/<uuid:producer_id>/products/", ProducerProductsPublicView.as_view(),
         name="producer-products-public"),
    path("", include(router.urls)),
]
