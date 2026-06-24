from django.db import models

from apps.common.models import BaseModel
from apps.orders.models import Order
from apps.tenants.models import Producer, Store
from .constants import PayeeType, PayoutStatus


class Payout(BaseModel):
    """Исходящая выплата продавцу/производителю (PRD 7.1 — PAYOUT, 5.6)."""

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payouts")
    payee_type = models.CharField(max_length=16, choices=PayeeType.choices)
    store = models.ForeignKey(Store, null=True, blank=True, on_delete=models.PROTECT,
                              related_name="payouts")
    producer = models.ForeignKey(Producer, null=True, blank=True, on_delete=models.PROTECT,
                                 related_name="payouts")

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=16, choices=PayoutStatus.choices,
                              default=PayoutStatus.PENDING, db_index=True)
    requisites_snapshot = models.JSONField(default=dict, blank=True)
    note = models.CharField(max_length=512, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["order", "payee_type", "store"],
                                    condition=models.Q(store__isnull=False),
                                    name="uniq_seller_payout"),
            models.UniqueConstraint(fields=["order", "payee_type", "producer"],
                                    condition=models.Q(producer__isnull=False),
                                    name="uniq_producer_payout"),
        ]

    def __str__(self):
        return f"Payout {self.payee_type} {self.amount}₽ ({self.status})"
