"""Finance/Payouts Service — расчёт и реестр выплат (PRD 5.2.1, 5.5, 5.6)."""
import logging
from decimal import Decimal

from django.db import transaction

from apps.common.money import to_money
from .constants import PayeeType, PayoutStatus
from .models import Payout

logger = logging.getLogger("sellix.finance")


@transaction.atomic
def generate_payouts_for_order(order):
    """После completed: продавцу — сумма наценки, производителю(ям) — отпускная цена.

    Идемпотентно (get_or_create по уникальным ограничениям). PRD 5.2.1.
    """
    if order.payouts.exists():
        return list(order.payouts.all())

    # Выплата продавцу — суммарная наценка по заказу
    seller_amount = sum((i.line_seller_markup for i in order.items.all()),
                        Decimal("0.00"))
    payouts = []
    if seller_amount > 0:
        payout, _ = Payout.objects.get_or_create(
            order=order, payee_type=PayeeType.SELLER, store=order.store,
            defaults={
                "amount": to_money(seller_amount),
                "requisites_snapshot": order.store.payout_requisites,
            },
        )
        payouts.append(payout)

    # Выплаты производителям — отпускная цена, сгруппировано по producer
    by_producer = {}
    for item in order.items.select_related("producer"):
        by_producer.setdefault(item.producer, Decimal("0.00"))
        by_producer[item.producer] += item.line_producer_payout

    for producer, amount in by_producer.items():
        if amount <= 0:
            continue
        payout, _ = Payout.objects.get_or_create(
            order=order, payee_type=PayeeType.PRODUCER, producer=producer,
            defaults={
                "amount": to_money(amount),
                "requisites_snapshot": producer.payout_requisites,
            },
        )
        payouts.append(payout)

    logger.info("Generated %d payouts for order %s", len(payouts), order.number)
    return payouts


@transaction.atomic
def confirm_payout(payout, note=""):
    """Суперадмин подтверждает выплату из реестра (US-62, PRD 5.2.1)."""
    payout.status = PayoutStatus.PAID
    if note:
        payout.note = note
    payout.save(update_fields=["status", "note", "updated_at"])
    return payout


@transaction.atomic
def mark_payout_processing(payout):
    payout.status = PayoutStatus.PROCESSING
    payout.save(update_fields=["status", "updated_at"])
    return payout


@transaction.atomic
def fail_payout(payout, note=""):
    payout.status = PayoutStatus.FAILED
    payout.note = note
    payout.save(update_fields=["status", "note", "updated_at"])
    return payout
