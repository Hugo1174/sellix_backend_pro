"""Payment Service — приём оплаты, webhook, возврат (PRD 5.2, 6.4, 6.6)."""
import logging

from django.db import transaction

from apps.common.money import to_money
from apps.integrations.payment_providers import get_payment_provider
from apps.tenants.constants import IntegrationKind, IntegrationStatus
from .constants import PaymentStatus
from .models import Payment

logger = logging.getLogger("sellix.payments")


def _store_payment_provider(store):
    integ = store.integrations.filter(
        kind=IntegrationKind.PAYMENT, status=IntegrationStatus.ACTIVE
    ).first()
    if integ:
        return integ.provider, integ.credentials
    return "yookassa", {}  # sandbox fallback


@transaction.atomic
def initiate_payment(order):
    """Создать платёж у провайдера продавца (PRD 6.4)."""
    provider_code, creds = _store_payment_provider(order.store)
    provider = get_payment_provider(provider_code, creds)
    result = provider.create_payment(
        amount=order.grand_total,
        order_id=str(order.id),
        description=f"Заказ {order.number}",
    )
    payment = Payment.objects.create(
        order=order,
        provider=provider_code,
        provider_payment_id=result["provider_payment_id"],
        amount=to_money(order.grand_total),
        status=PaymentStatus.PENDING,
        confirmation_url=result["confirmation_url"],
    )
    return payment


@transaction.atomic
def confirm_payment(payment, raw=None):
    """Webhook об успешной оплате → перевод заказа в paid (PRD 6.6)."""
    from apps.orders.constants import ActorType, OrderStatus
    from apps.orders.services import transition

    if payment.status == PaymentStatus.SUCCEEDED:
        return payment
    payment.status = PaymentStatus.SUCCEEDED
    payment.raw_response = raw or {}
    payment.save(update_fields=["status", "raw_response", "updated_at"])
    transition(payment.order, OrderStatus.PAID, actor_type=ActorType.SYSTEM,
               comment="Webhook об оплате")
    return payment


@transaction.atomic
def fail_payment(payment, raw=None):
    payment.status = PaymentStatus.FAILED
    payment.raw_response = raw or {}
    payment.save(update_fields=["status", "raw_response", "updated_at"])
    return payment


@transaction.atomic
def refund_order(order):
    """Возврат средств при отмене (PRD 10.3 #4)."""
    payment = getattr(order, "payment", None)
    if payment and payment.status == PaymentStatus.SUCCEEDED:
        payment.status = PaymentStatus.REFUNDED
        payment.save(update_fields=["status", "updated_at"])
        logger.info("Refund issued for order %s", order.number)
    return payment


def handle_webhook(provider_code, payload):
    """Разбор webhook любого провайдера (sandbox-совместимо)."""
    provider = get_payment_provider(provider_code, {})
    parsed = provider.parse_webhook(payload)
    pid = parsed["provider_payment_id"]
    payment = Payment.objects.filter(provider_payment_id=pid).first()
    if payment is None:
        return None
    if parsed["status"] in ("succeeded", "paid", "success"):
        return confirm_payment(payment, raw=parsed["raw"])
    if parsed["status"] in ("canceled", "failed"):
        return fail_payment(payment, raw=parsed["raw"])
    return payment
