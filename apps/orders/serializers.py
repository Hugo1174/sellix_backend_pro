from rest_framework import serializers

from .constants import OrderStatus
from .models import Order, OrderItem, OrderStatusEvent, Shipment


class OrderItemSerializer(serializers.ModelSerializer):
    line_total = serializers.SerializerMethodField()
    producer_name = serializers.CharField(source="producer.company_name", read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id", "product_name", "producer", "producer_name", "quantity",
            "unit_price", "seller_markup_amount", "producer_payout_amount", "line_total",
        ]

    def get_line_total(self, obj):
        return str(obj.line_total)


class ShipmentSerializer(serializers.ModelSerializer):
    producer_name = serializers.CharField(source="producer.company_name", read_only=True)

    class Meta:
        model = Shipment
        fields = [
            "id", "producer", "producer_name", "status", "delivery_provider",
            "delivery_fee", "tracking_number", "tracking_url", "last_carrier_status",
        ]


class OrderStatusEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusEvent
        fields = ["from_status", "to_status", "actor_type", "comment", "created_at"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipments = ShipmentSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "number", "status", "status_display", "store",
            "ship_full_name", "ship_phone", "ship_city", "ship_address", "ship_postal_code",
            "goods_total", "delivery_total", "platform_commission", "grand_total",
            "items", "shipments", "created_at",
        ]


class OrderTrackingSerializer(serializers.ModelSerializer):
    """Интерактивный таймлайн для покупателя (PRD 6.7, US-50)."""

    timeline = serializers.SerializerMethodField()
    shipments = ShipmentSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Order
        fields = ["id", "number", "status", "status_display", "timeline", "shipments"]

    def get_timeline(self, obj):
        steps = [
            (OrderStatus.PAID, "Оплачен"),
            (OrderStatus.SENT_TO_PRODUCER, "Передан в сборку"),
            (OrderStatus.SHIPPED, "Отправлен"),
            (OrderStatus.IN_TRANSIT, "В пути"),
            (OrderStatus.DELIVERED, "Доставлен"),
        ]
        reached = {e.to_status for e in obj.status_events.all()}
        order_index = {s: i for i, (s, _) in enumerate(steps)}
        current_idx = order_index.get(obj.status, -1)
        result = []
        for i, (code, label) in enumerate(steps):
            result.append({
                "code": code,
                "label": label,
                "done": code in reached or i < current_idx,
                "current": code == obj.status,
            })
        return result


class CheckoutItemSerializer(serializers.Serializer):
    store_product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)


class CheckoutSerializer(serializers.Serializer):
    """US-32, US-33. Оформление заказа покупателем."""

    store_slug = serializers.SlugField()
    address = serializers.DictField(child=serializers.CharField(allow_blank=True))
    # Если items не передан — берём из серверной корзины
    items = CheckoutItemSerializer(many=True, required=False)

    def validate_address(self, value):
        required = ["full_name", "phone", "city", "address_line"]
        missing = [f for f in required if not value.get(f)]
        if missing:
            raise serializers.ValidationError(f"Не заполнено: {', '.join(missing)}")
        return value
