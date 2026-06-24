from django.db import transaction
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import IsProducer, IsSeller, IsSellerOrProducer, ReadOnly
from .constants import ProductStatus
from .filters import PoolProductFilter
from .models import Category, Product, ProductImage, StoreProduct
from .serializers import (
    AddToStoreSerializer,
    CategorySerializer,
    ProductImageSerializer,
    ProductSerializer,
    ProductWriteSerializer,
    StoreProductSerializer,
)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    pagination_class = None


class ProducerProductViewSet(viewsets.ModelViewSet):
    """Производитель управляет своими товарами в общем пуле."""

    permission_classes = [IsProducer]
    search_fields = ["name", "sku"]

    def get_queryset(self):
        producer = getattr(self.request.user, "producer", None)
        if producer is None:
            return Product.objects.none()
        return (Product.objects.filter(producer=producer)
                .select_related("category", "producer")
                .annotate(_store_count=Count("store_links")))

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ProductWriteSerializer
        return ProductSerializer

    def perform_create(self, serializer):
        producer = getattr(self.request.user, "producer", None)
        if producer is None:
            raise PermissionDenied("Сначала создайте профиль производителя")
        serializer.save(producer=producer)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        product = self.get_object()
        if not product.images.exists():
            raise ValidationError("Добавьте хотя бы одно фото перед публикацией")
        product.status = (ProductStatus.OUT_OF_STOCK if product.stock == 0
                          else ProductStatus.PUBLISHED)
        product.save(update_fields=["status", "updated_at"])
        return Response(ProductSerializer(product).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        product = self.get_object()
        product.status = ProductStatus.ARCHIVED
        product.save(update_fields=["status", "updated_at"])
        return Response(ProductSerializer(product).data)

    @action(detail=True, methods=["post"], url_path="images")
    def add_image(self, request, pk=None):
        product = self.get_object()
        if product.images.count() >= 8:
            raise ValidationError("Максимум 8 изображений")
        ser = ProductImageSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        is_primary = not product.images.filter(is_primary=True).exists()
        ser.save(product=product, is_primary=ser.validated_data.get("is_primary", is_primary))
        return Response(ser.data, status=status.HTTP_201_CREATED)


class ProductPoolViewSet(viewsets.ReadOnlyModelViewSet):
    """Общий пул товаров — для продавцов И производителей.

    Production: производитель тоже получает доступ, чтобы видеть конкурентов.
    """

    serializer_class = ProductSerializer
    permission_classes = [IsSellerOrProducer]
    filterset_class = PoolProductFilter
    search_fields = ["name", "sku"]
    ordering_fields = ["base_price", "created_at"]

    def get_queryset(self):
        return (Product.objects
                .filter(status__in=[ProductStatus.PUBLISHED, ProductStatus.OUT_OF_STOCK])
                .select_related("category", "producer")
                .annotate(_store_count=Count("store_links")))


class StoreProductViewSet(viewsets.ModelViewSet):
    """Товары магазина продавца + наценка + видимость."""

    serializer_class = StoreProductSerializer
    permission_classes = [IsSeller]

    def _store(self):
        store = getattr(self.request.user, "store", None)
        if store is None:
            raise PermissionDenied("Сначала создайте магазин")
        return store

    def get_queryset(self):
        store = getattr(self.request.user, "store", None)
        if store is None:
            return StoreProduct.objects.none()
        return (StoreProduct.objects.filter(store=store)
                .select_related("product", "product__category", "product__producer")
                .prefetch_related("product__images"))

    @action(detail=False, methods=["post"], url_path="add")
    @transaction.atomic
    def add(self, request):
        store = self._store()
        ser = AddToStoreSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        product = Product.objects.filter(
            id=ser.validated_data["product_id"],
            status__in=[ProductStatus.PUBLISHED, ProductStatus.OUT_OF_STOCK],
        ).first()
        if product is None:
            raise ValidationError("Товар недоступен для добавления")
        sp, created = StoreProduct.objects.get_or_create(store=store, product=product)
        return Response(
            StoreProductSerializer(sp).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
