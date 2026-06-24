from rest_framework import serializers

from .models import Payout


class PayoutSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.number", read_only=True)
    payee_type_display = serializers.CharField(source="get_payee_type_display",
                                               read_only=True)

    class Meta:
        model = Payout
        fields = ["id", "order", "order_number", "payee_type", "payee_type_display",
                  "amount", "status", "note", "created_at"]
