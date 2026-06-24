from django.urls import path

from .views import PaymentSandboxConfirmView, PaymentWebhookView

urlpatterns = [
    path("payments/webhook/<str:provider>/", PaymentWebhookView.as_view(),
         name="payment-webhook"),
    path("payments/<uuid:payment_id>/sandbox-confirm/",
         PaymentSandboxConfirmView.as_view(), name="payment-sandbox-confirm"),
]
