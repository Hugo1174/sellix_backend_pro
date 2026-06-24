from django.urls import path

from .views import (
    CartView,
    PublicProductDetailView,
    PublicStoreProductsView,
    PublicStoreView,
)

urlpatterns = [
    path("shop/<slug:slug>/", PublicStoreView.as_view(), name="public-store"),
    path("shop/<slug:slug>/products/", PublicStoreProductsView.as_view(),
         name="public-store-products"),
    path("shop/<slug:slug>/products/<uuid:product_id>/",
         PublicProductDetailView.as_view(), name="public-product"),
    path("shop/<slug:slug>/cart/", CartView.as_view(), name="cart"),
]
