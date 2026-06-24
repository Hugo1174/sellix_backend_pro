"""Notification Service — статусные уведомления (PRD 8.6, US-52).

На MVP отправка стаблена: уведомления логируются и пишутся в журнал
Notification. Реальные каналы (email/SMS/push) подключаются заменой _dispatch.
"""
import logging

from django.conf import settings

from .constants import NotificationChannel, NotificationStatus
from .models import Notification

logger = logging.getLogger("sellix.notifications")


# Человекочитаемые сообщения по статусам заказа (PRD 6.6)
ORDER_STATUS_MESSAGES = {
    "paid": "Ваш заказ {number} оплачен и передан в обработку.",
    "sent_to_producer": "Заказ {number} передан производителю на сборку.",
    "assembling": "Заказ {number} собирается.",
    "shipped": "Заказ {number} отправлен. Трек-номер скоро появится в отслеживании.",
    "in_transit": "Заказ {number} в пути.",
    "ready_for_pickup": "Заказ {number} прибыл в пункт выдачи.",
    "delivered": "Заказ {number} доставлен. Спасибо за покупку!",
    "completed": "Заказ {number} завершён.",
    "cancelled": "Заказ {number} отменён. Средства будут возвращены.",
}


def _dispatch(notification):
    """Точка интеграции с реальным провайдером. На sandbox — лог."""
    if settings.SELLIX["USE_SANDBOX_PROVIDERS"]:
        logger.info("[SANDBOX notify] %s → %s: %s",
                    notification.channel, notification.recipient_id, notification.subject)
        notification.status = NotificationStatus.SENT
    else:
        # TODO: подключить реальный email/SMS-провайдер
        notification.status = NotificationStatus.SENT
    notification.save(update_fields=["status", "updated_at"])
    return notification


def notify(recipient, subject, body="", channel=NotificationChannel.EMAIL,
           event_key="", meta=None):
    notification = Notification.objects.create(
        recipient=recipient, subject=subject, body=body,
        channel=channel, event_key=event_key, meta=meta or {},
    )
    return _dispatch(notification)


def notify_order_status(order):
    """Уведомить покупателя о смене статуса заказа (US-52)."""
    template = ORDER_STATUS_MESSAGES.get(order.status)
    if not template:
        return None
    message = template.format(number=order.number)
    return notify(
        recipient=order.buyer,
        subject=f"Заказ {order.number}: {order.get_status_display()}",
        body=message,
        event_key=f"order.{order.status}",
        meta={"order_id": str(order.id), "status": order.status},
    )
