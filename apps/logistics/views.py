from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Shipment
from .services import apply_carrier_status


class CarrierWebhookView(APIView):
    """Webhook от службы доставки (PRD 6.7). Идентификация по tracking_number."""

    permission_classes = [AllowAny]

    def post(self, request, provider):
        tracking = request.data.get("tracking_number")
        carrier_status = request.data.get("status")
        shipment = Shipment.objects.filter(
            tracking_number=tracking, delivery_provider=provider
        ).first()
        if shipment is None:
            return Response({"detail": "Отгрузка не найдена"},
                            status=status.HTTP_404_NOT_FOUND)
        apply_carrier_status(shipment, carrier_status)
        return Response({"shipment_status": shipment.status,
                         "order_status": shipment.order.status})
