from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    ProducerProductViewSet,
    ProductPoolViewSet,
    StoreProductViewSet,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("producer/products", ProducerProductViewSet, basename="producer-product")
router.register("pool", ProductPoolViewSet, basename="product-pool")
router.register("seller/products", StoreProductViewSet, basename="store-product")

urlpatterns = [path("", include(router.urls))]
