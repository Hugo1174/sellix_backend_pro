from rest_framework import serializers

from apps.accounts.models import User
from apps.catalog.models import Product
from apps.finance.models import Payout
from apps.orders.models import Order
from apps.tenants.models import Producer, Store
from .models import AuditLog


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "full_name", "phone", "role", "auth_provider",
                  "is_blocked", "blocked_reason", "created_at"]


class AdminStoreSerializer(serializers.ModelSerializer):
    owner_email = serializers.CharField(source="owner.email", read_only=True)

    class Meta:
        model = Store
        fields = ["id", "name", "slug", "owner_email", "status", "niche",
                  "blocked_reason", "created_at"]


class AdminProducerSerializer(serializers.ModelSerializer):
    owner_email = serializers.CharField(source="owner.email", read_only=True)

    class Meta:
        model = Producer
        fields = ["id", "company_name", "owner_email", "inn", "status",
                  "blocked_reason", "created_at"]


class AdminProductSerializer(serializers.ModelSerializer):
    producer_name = serializers.CharField(source="producer.company_name", read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "producer_name", "category", "base_price",
                  "stock", "status", "created_at"]


class AdminOrderSerializer(serializers.ModelSerializer):
    buyer_email = serializers.CharField(source="buyer.email", read_only=True)
    store_name = serializers.CharField(source="store.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Order
        fields = ["id", "number", "buyer_email", "store_name", "status",
                  "status_display", "grand_total", "created_at"]


class AdminPayoutSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.number", read_only=True)

    class Meta:
        model = Payout
        fields = ["id", "order_number", "payee_type", "amount", "status",
                  "note", "created_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source="actor.email", read_only=True)

    class Meta:
        model = AuditLog
        fields = ["id", "actor_email", "action", "target_entity", "target_id",
                  "detail", "created_at"]
