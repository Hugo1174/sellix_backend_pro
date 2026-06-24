from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import StoreProduct
from apps.catalog.serializers import PublicStoreProductSerializer
from apps.tenants.constants import StoreStatus
from apps.tenants.models import Store
from .models import Cart, CartItem
from .serializers import (
    AddToCartSerializer,
    CartSerializer,
    PublicStoreSerializer,
)


def _published_store(slug):
    store = Store.objects.filter(slug=slug, status=StoreStatus.PUBLISHED).first()
    if store is None:
        raise NotFound("Магазин не найден или не опубликован")
    return store


class PublicStoreView(RetrieveAPIView):
    """Главная магазина по slug (PRD 6.2)."""

    serializer_class = PublicStoreSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        return _published_store(self.kwargs["slug"])


class PublicStoreProductsView(ListAPIView):
    """Сетка товаров витрины — только видимые (PRD 6.2)."""

    serializer_class = PublicStoreProductSerializer
    permission_classes = [AllowAny]
    search_fields = ["product__name"]

    def get_queryset(self):
        store = _published_store(self.kwargs["slug"])
        qs = (StoreProduct.objects.filter(store=store, is_visible=True)
              .select_related("product", "product__category")
              .prefetch_related("product__images"))
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(product__category_id=category)
        return qs


class PublicProductDetailView(RetrieveAPIView):
    serializer_class = PublicStoreProductSerializer
    permission_classes = [AllowAny]
    lookup_field = "id"
    lookup_url_kwarg = "product_id"

    def get_queryset(self):
        store = _published_store(self.kwargs["slug"])
        return StoreProduct.objects.filter(store=store, is_visible=True)


class CartView(APIView):
    """Серверная корзина для авторизованного покупателя (PRD 6.4)."""

    permission_classes = [IsAuthenticated]

    def _get_cart(self, slug, create=False):
        store = _published_store(slug)
        cart = Cart.objects.filter(user=self.request.user, store=store,
                                   is_active=True).first()
        if cart is None and create:
            cart = Cart.objects.create(user=self.request.user, store=store)
        return cart, store

    def get(self, request, slug):
        cart, _ = self._get_cart(slug)
        if cart is None:
            return Response({"items": [], "subtotal": "0.00", "store": None})
        return Response(CartSerializer(cart).data)

    def post(self, request, slug):
        ser = AddToCartSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        cart, store = self._get_cart(slug, create=True)
        sp = StoreProduct.objects.filter(
            id=ser.validated_data["store_product_id"], store=store, is_visible=True
        ).first()
        if sp is None:
            raise ValidationError("Товар недоступен")
        if not sp.product.is_orderable:
            raise ValidationError("Товара нет в наличии")
        item, created = CartItem.objects.get_or_create(cart=cart, store_product=sp)
        item.quantity = ser.validated_data["quantity"] if created else (
            item.quantity + ser.validated_data["quantity"])
        item.save()
        return Response(CartSerializer(cart).data, status=status.HTTP_201_CREATED)

    def delete(self, request, slug):
        cart, _ = self._get_cart(slug)
        item_id = request.query_params.get("item_id")
        if cart and item_id:
            CartItem.objects.filter(cart=cart, id=item_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
