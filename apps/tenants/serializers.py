from rest_framework import serializers

from apps.catalog.serializers import CategorySerializer
from .constants import IntegrationKind, IntegrationOwnerType, IntegrationStatus, StoreStatus
from .models import Producer, ShopIntegration, Store, _unique_slug


class StoreSerializer(serializers.ModelSerializer):
    can_publish = serializers.SerializerMethodField()
    has_active_payment = serializers.BooleanField(read_only=True)

    class Meta:
        model = Store
        fields = [
            "id", "name", "slug", "niche", "status", "description", "logo", "banner",
            "theme", "contact_email", "contact_phone", "inn", "payout_requisites",
            "can_publish", "has_active_payment", "created_at",
        ]
        read_only_fields = ["id", "slug", "status", "created_at"]

    def get_can_publish(self, obj):
        return obj.can_publish()


class StoreCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ["name", "niche", "contact_email", "contact_phone"]

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["owner"] = user
        validated_data["slug"] = _unique_slug(Store, validated_data["name"])
        return super().create(validated_data)


class ProducerSerializer(serializers.ModelSerializer):
    """Полный сериализатор профиля производителя с категориями."""

    categories = CategorySerializer(many=True, read_only=True)
    category_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False,
        help_text="До 3 UUID категорий производителя"
    )

    class Meta:
        model = Producer
        fields = [
            "id", "company_name", "inn", "ogrn", "categories", "category_ids",
            "status", "contact_email", "contact_phone", "payout_requisites", "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def validate_category_ids(self, value):
        if len(value) > 3:
            raise serializers.ValidationError("Можно выбрать не более 3 категорий.")
        from apps.catalog.models import Category
        existing = Category.objects.filter(id__in=value, is_active=True).count()
        if existing != len(value):
            raise serializers.ValidationError("Одна или несколько категорий не найдены.")
        return value

    def update(self, instance, validated_data):
        category_ids = validated_data.pop("category_ids", None)
        instance = super().update(instance, validated_data)
        if category_ids is not None:
            instance.categories.set(category_ids)
        return instance


class ProducerCreateSerializer(serializers.ModelSerializer):
    """Создание профиля производителя с выбором до 3 категорий."""

    category_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list,
        help_text="До 3 UUID категорий"
    )

    class Meta:
        model = Producer
        fields = ["company_name", "inn", "ogrn", "category_ids",
                  "contact_email", "contact_phone"]

    def validate_category_ids(self, value):
        if len(value) > 3:
            raise serializers.ValidationError("Можно выбрать не более 3 категорий.")
        return value

    def create(self, validated_data):
        category_ids = validated_data.pop("category_ids", [])
        validated_data["owner"] = self.context["request"].user
        producer = super().create(validated_data)
        if category_ids:
            producer.categories.set(category_ids)
        return producer


class ProducerPublicSerializer(serializers.ModelSerializer):
    """Публичный профиль производителя (для просмотра продавцами в пуле)."""

    categories = CategorySerializer(many=True, read_only=True)
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Producer
        fields = [
            "id", "company_name", "categories", "status",
            "contact_email", "contact_phone", "product_count", "created_at",
        ]

    def get_product_count(self, obj):
        return getattr(obj, "_product_count", obj.products.count())


class SlugCheckSerializer(serializers.Serializer):
    name = serializers.CharField()


class IntegrationSerializer(serializers.ModelSerializer):
    credentials = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = ShopIntegration
        fields = [
            "id", "owner_type", "kind", "provider", "status",
            "credentials", "last_error", "created_at",
        ]
        read_only_fields = ["id", "owner_type", "status", "last_error", "created_at"]
