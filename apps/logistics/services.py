"""Logistics Service — обновление трек-статусов (PRD 6.7).

Webhook предпочтителен, polling — фоллбэк (раз в 1-4 часа).
"""
import logging

from django.db import transaction

from apps.integrations.delivery_providers import get_delivery_provider
from apps.orders.constants import ActorType, OrderStatus, ShipmentStatus
from apps.orders.models import Shipment
from apps.orders.services import transition

logger = logging.getLogger("sellix.logistics")

# Маппинг статусов перевозчика → статус заказа/отгрузки
CARRIER_MAP = {
    "in_transit": (ShipmentStatus.IN_TRANSIT, OrderStatus.IN_TRANSIT),
    "ready_for_pickup": (ShipmentStatus.IN_TRANSIT, OrderStatus.READY_FOR_PICKUP),
    "delivered": (ShipmentStatus.DELIVERED, OrderStatus.DELIVERED),
}


@transaction.atomic
def apply_carrier_status(shipment, carrier_status):
    mapping = CARRIER_MAP.get(carrier_status)
    shipment.last_carrier_status = carrier_status
    if mapping:
        ship_status, order_status = mapping
        shipment.status = ship_status
    shipment.save(update_fields=["last_carrier_status", "status", "updated_at"])

    if mapping:
        order = shipment.order
        _, order_status = mapping
        # Заказ переходит в delivered только когда ВСЕ отгрузки доставлены
        if order_status == OrderStatus.DELIVERED:
            if order.shipments.exclude(status=ShipmentStatus.DELIVERED).exists():
                return shipment
        try:
            transition(order, order_status, actor_type=ActorType.CARRIER,
                       comment=f"Статус перевозчика: {carrier_status}")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Carrier transition skipped: %s", exc)
    return shipment


def poll_active_shipments():
    """Фоллбэк-опрос статусов (PRD 6.7). Вызывается из management-команды/cron."""
    active = Shipment.objects.filter(
        status__in=[ShipmentStatus.SHIPPED, ShipmentStatus.IN_TRANSIT]
    ).exclude(tracking_number="")
    updated = 0
    for shipment in active:
        provider = get_delivery_provider(shipment.delivery_provider or "cdek", {})
        carrier_status = provider.fetch_status(shipment.tracking_number)
        apply_carrier_status(shipment, carrier_status)
        updated += 1
    return updated
