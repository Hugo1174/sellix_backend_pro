"""Order Service — машина состояний, маршрутизация, сквозной флоу (PRD 6)."""
import logging
from decimal import Decimal

from django.conf import settings
from django.db import transaction

from apps.common.money import to_money
from apps.integrations.delivery_providers import get_delivery_provider
from apps.catalog.constants import ProductStatus
from apps.tenants.constants import IntegrationKind, IntegrationStatus
from .constants import (
    ALLOWED_TRANSITIONS,
    ActorType,
    OrderStatus,
    ShipmentStatus,
)
from .models import Order, OrderItem, OrderStatusEvent, Shipment

logger = logging.getLogger("sellix.orders")


class OrderError(Exception):
    pass


def _producer_delivery_provider(producer):
    integ = producer.integrations.filter(
        kind=IntegrationKind.DELIVERY, status=IntegrationStatus.ACTIVE
    ).first()
    if integ:
        return integ.provider, integ.credentials
    return "cdek", {}  # sandbox fallback (PRD 4.3 — тестовый контур)


def quote_delivery(store, items_by_producer, city):
    """Раздельная стоимость доставки по производителям (PRD 10.3 #7)."""
    quotes = {}
    for producer, items in items_by_producer.items():
        provider_code, creds = _producer_delivery_provider(producer)
        provider = get_delivery_provider(provider_code, creds)
        weight = sum(sp.product.weight_grams * qty for sp, qty in items)
        quotes[producer.id] = {
            "producer": producer,
            "provider": provider_code,
            "fee": provider.calculate(city=city, weight_grams=weight),
        }
    return quotes


@transaction.atomic
def create_order(*, buyer, store, items, address):
    """Создать заказ (PRD 6.4). items: list of (StoreProduct, quantity).

    Группирует по производителю, считает снимки цен и доставку построчно.
    """
    if not items:
        raise OrderError("Корзина пуста")

    # Группировка позиций по производителю (PRD 6.5)
    items_by_producer = {}
    for sp, qty in items:
        if not sp.product.is_orderable:
            raise OrderError(f"Товар «{sp.product.name}» недоступен к заказу")
        if sp.product.stock < qty:
            raise OrderError(f"Недостаточно остатка по товару «{sp.product.name}»")
        items_by_producer.setdefault(sp.product.producer, []).append((sp, qty))

    order = Order.objects.create(
        buyer=buyer,
        store=store,
        status=OrderStatus.CREATED,
        ship_full_name=address["full_name"],
        ship_phone=address["phone"],
        ship_city=address["city"],
        ship_address=address["address_line"],
        ship_postal_code=address.get("postal_code", ""),
    )

    # Снимки цен на уровне OrderItem (PRD 7.3)
    for sp, qty in items:
        OrderItem.objects.create(
            order=order,
            store_product=sp,
            product=sp.product,
            producer=sp.product.producer,
            product_name=sp.product.name,
            quantity=qty,
            unit_price=sp.retail_price,
            producer_payout_amount=to_money(sp.product.base_price),
            seller_markup_amount=sp.seller_markup_amount,
        )

    # Отгрузки + стоимость доставки по производителю (PRD 6.5, 10.3 #7)
    quotes = quote_delivery(store, items_by_producer, address["city"])
    for producer in items_by_producer:
        q = quotes[producer.id]
        Shipment.objects.create(
            order=order,
            producer=producer,
            delivery_provider=q["provider"],
            delivery_fee=q["fee"],
            status=ShipmentStatus.PENDING,
        )

    order.recalc_totals()
    order.save()
    _record_event(order, "", OrderStatus.CREATED, ActorType.SYSTEM)
    return order


@transaction.atomic
def transition(order, to_status, *, actor_type=ActorType.SYSTEM, actor_id=None,
               comment="", force=False):
    """Безопасный переход статуса с валидацией и журналированием (PRD 6.6)."""
    from_status = order.status
    if from_status == to_status:
        return order
    if not force and to_status not in ALLOWED_TRANSITIONS.get(from_status, set()):
        raise OrderError(f"Недопустимый переход: {from_status} → {to_status}")

    order.status = to_status
    order.save(update_fields=["status", "updated_at"])
    _record_event(order, from_status, to_status, actor_type, actor_id, comment)

    # Побочные эффекты
    if to_status == OrderStatus.PAID:
        _on_paid(order)
    elif to_status == OrderStatus.DELIVERED:
        _on_delivered(order)
    elif to_status == OrderStatus.COMPLETED:
        _on_completed(order)
    elif to_status == OrderStatus.CANCELLED:
        _on_cancelled(order)
    return order


def _on_paid(order):
    """Бесшовная маршрутизация к производителю + списание остатка (PRD 6.5)."""
    for item in order.items.select_related("product"):
        product = item.product
        product.stock = max(0, product.stock - item.quantity)
        product.save(update_fields=["stock", "status", "updated_at"])
    # Авто-переход paid → sent_to_producer (PRD 6.6)
    transition(order, OrderStatus.SENT_TO_PRODUCER, actor_type=ActorType.SYSTEM,
               comment="Автомаршрутизация после оплаты")
    from apps.notifications.services import notify_order_status
    notify_order_status(order)


def _on_delivered(order):
    for shipment in order.shipments.all():
        if shipment.status != ShipmentStatus.DELIVERED:
            shipment.status = ShipmentStatus.DELIVERED
            shipment.save(update_fields=["status", "updated_at"])
    from apps.notifications.services import notify_order_status
    notify_order_status(order)
    # MVP: completed == delivered (PRD 6.6)
    if settings.SELLIX["COMPLETE_ON_DELIVERED"]:
        transition(order, OrderStatus.COMPLETED, actor_type=ActorType.SYSTEM,
                   comment="Авто-завершение (completed == delivered на MVP)")


def _on_completed(order):
    """Триггер выплат после завершения заказа (PRD 5.2, 5.6)."""
    from apps.finance.services import generate_payouts_for_order
    generate_payouts_for_order(order)


def _on_cancelled(order):
    """Возврат остатков + возврат средств (PRD 10.3 #4)."""
    for item in order.items.select_related("product"):
        product = item.product
        product.stock += item.quantity
        product.save(update_fields=["stock", "status", "updated_at"])
    from apps.payments.services import refund_order
    refund_order(order)


def _record_event(order, from_status, to_status, actor_type, actor_id=None, comment=""):
    OrderStatusEvent.objects.create(
        order=order,
        from_status=from_status or "",
        to_status=to_status,
        actor_type=actor_type,
        actor_id=actor_id,
        comment=comment,
    )


@transaction.atomic
def mark_assembling(shipment, actor_id=None):
    """Производитель отмечает «собирается» (PRD 6.6, US-42)."""
    shipment.status = ShipmentStatus.ASSEMBLING
    shipment.save(update_fields=["status", "updated_at"])
    order = shipment.order
    if order.status == OrderStatus.SENT_TO_PRODUCER:
        transition(order, OrderStatus.ASSEMBLING, actor_type=ActorType.PRODUCER,
                   actor_id=actor_id)
    return shipment


@transaction.atomic
def create_shipment_label(shipment, actor_id=None):
    """Производитель создаёт отгрузку, получает трек-номер (US-42, US-43)."""
    provider = get_delivery_provider(
        shipment.delivery_provider or "cdek", {}
    )
    order = shipment.order
    result = provider.create_shipment(
        city=order.ship_city,
        address=order.ship_address,
        weight_grams=shipment.total_weight_grams,
        recipient=order.ship_full_name,
    )
    shipment.tracking_number = result["tracking_number"]
    shipment.tracking_url = result["tracking_url"]
    shipment.status = ShipmentStatus.SHIPPED
    shipment.save(update_fields=["tracking_number", "tracking_url", "status", "updated_at"])

    if order.status in (OrderStatus.ASSEMBLING, OrderStatus.SENT_TO_PRODUCER):
        transition(order, OrderStatus.SHIPPED, actor_type=ActorType.PRODUCER,
                   actor_id=actor_id, comment=f"Трек: {shipment.tracking_number}")
    return shipment
