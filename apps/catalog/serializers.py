from rest_framework import serializers

from apps.common.money import to_money
from .constants import ProductStatus
from .models import Category, Product, ProductImage, StoreProduct


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent", "is_active"]


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "is_primary", "position"]


class ProductSerializer(serializers.ModelSerializer):
    """Карточка товара в общем пуле (вид производителя/продавца)."""

    images = ProductImageSerializer(many=True, read_only=True)
    producer_name = serializers.CharField(source="producer.company_name", read_only=True)
    producer_id = serializers.UUIDField(source="producer.id", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    is_orderable = serializers.BooleanField(read_only=True)
    store_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "producer", "producer_id", "producer_name", "category", "category_name",
            "name", "description", "sku", "base_price", "stock", "low_stock_threshold",
            "weight_grams", "length_mm", "width_mm", "height_mm", "attributes",
            "status", "is_orderable", "store_count",
            "allowed_payment_providers", "allowed_delivery_providers",
            "images", "created_at",
        ]
        read_only_fields = ["id", "producer", "producer_id", "sku", "status", "created_at"]


class ProductWriteSerializer(serializers.ModelSerializer):
    """Создание/редактирование товара производителем.

    Production: включает allowed_payment_providers и allowed_delivery_providers
    для индивидуальных настроек на уровне товара.
    """

    class Meta:
        model = Product
        fields = [
            "category", "name", "description", "sku", "base_price", "stock",
            "low_stock_threshold", "weight_grams", "length_mm", "width_mm",
            "height_mm", "attributes",
            "allowed_payment_providers", "allowed_delivery_providers",
        ]


class StoreProductSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    retail_price = serializers.SerializerMethodField()
    seller_markup_amount = serializers.SerializerMethodField()
    has_markup = serializers.BooleanField(read_only=True)

    class Meta:
        model = StoreProduct
        fields = [
            "id", "product", "markup_percent", "markup_amount", "final_price",
            "is_visible", "has_markup", "retail_price", "seller_markup_amount",
            "created_at",
        ]
        read_only_fields = ["id", "product", "created_at"]

    def get_retail_price(self, obj):
        return str(obj.retail_price)

    def get_seller_markup_amount(self, obj):
        return str(obj.seller_markup_amount)

    def validate(self, attrs):
        instance = self.instance
        want_visible = attrs.get("is_visible",
                                 instance.is_visible if instance else False)
        markup_present = any(
            attrs.get(f, getattr(instance, f, None)) is not None
            for f in ("markup_percent", "markup_amount", "final_price")
        )
        if want_visible and not markup_present:
            raise serializers.ValidationError(
                "Нельзя показать товар на витрине без заданной наценки."
            )
        return attrs


class AddToStoreSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()


class PublicStoreProductSerializer(serializers.ModelSerializer):
    """Витрина — без отпускной цены производителя."""

    name = serializers.CharField(source="product.name", read_only=True)
    description = serializers.CharField(source="product.description", read_only=True)
    category_name = serializers.CharField(source="product.category.name", read_only=True)
    images = ProductImageSerializer(source="product.images", many=True, read_only=True)
    price = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()

    class Meta:
        model = StoreProduct
        fields = ["id", "name", "description", "category_name", "price",
                  "in_stock", "images"]

    def get_price(self, obj):
        return str(obj.retail_price)

    def get_in_stock(self, obj):
        return obj.product.is_orderable
