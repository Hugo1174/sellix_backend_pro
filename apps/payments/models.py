from django.db import models

from apps.common.models import BaseModel
from apps.orders.models import Order
from .constants import PaymentStatus


class Payment(BaseModel):
    """Входящий платёж от покупателя (PRD 7.1 — PAYMENT)."""

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    provider = models.CharField(max_length=32)
    provider_payment_id = models.CharField(max_length=128, blank=True, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=16, choices=PaymentStatus.choices,
                              default=PaymentStatus.PENDING, db_index=True)
    confirmation_url = models.URLField(blank=True)
    raw_response = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment {self.order.number} ({self.status})"
