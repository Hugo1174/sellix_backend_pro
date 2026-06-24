from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.number", read_only=True)

    class Meta:
        model = Payment
        fields = ["id", "order", "order_number", "provider", "provider_payment_id",
                  "amount", "status", "confirmation_url", "created_at"]
