from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Payment
from .services import confirm_payment, handle_webhook


class PaymentWebhookView(APIView):
    """Webhook от платёжного провайдера (PRD 6.6). Без авторизации, по подписи провайдера.

    На sandbox-MVP подпись не проверяется; для прода добавить верификацию по
    секрету провайдера перед обработкой.
    """

    permission_classes = [AllowAny]

    def post(self, request, provider):
        payment = handle_webhook(provider, request.data)
        if payment is None:
            return Response({"detail": "Платёж не найден"},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({"status": payment.status})


class PaymentSandboxConfirmView(APIView):
    """Эмуляция успешной оплаты на sandbox-контуре (для сквозного теста)."""

    permission_classes = [AllowAny]

    def post(self, request, payment_id):
        payment = Payment.objects.filter(id=payment_id).first()
        if payment is None:
            return Response({"detail": "Не найдено"}, status=status.HTTP_404_NOT_FOUND)
        confirm_payment(payment, raw={"sandbox": True})
        return Response({"status": payment.status, "order": payment.order.status})
