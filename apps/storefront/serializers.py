from rest_framework import serializers

from apps.catalog.models import StoreProduct
from apps.catalog.serializers import PublicStoreProductSerializer
from apps.tenants.models import Store
from .models import Cart, CartItem


class PublicStoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ["id", "name", "slug", "description", "logo", "banner", "theme", "niche"]


class CartItemSerializer(serializers.ModelSerializer):
    product = PublicStoreProductSerializer(source="store_product", read_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ["id", "store_product", "quantity", "product", "line_total"]
        read_only_fields = ["id", "product", "line_total"]

    def get_line_total(self, obj):
        return str(obj.line_total)


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "store", "items", "subtotal"]

    def get_subtotal(self, obj):
        return str(obj.subtotal)


class AddToCartSerializer(serializers.Serializer):
    store_product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, default=1)
