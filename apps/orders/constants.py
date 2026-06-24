from django.db import models


class OrderStatus(models.TextChoices):
    CREATED = "created", "Ожидает оплаты"
    PAID = "paid", "Оплачен, передан в обработку"
    SENT_TO_PRODUCER = "sent_to_producer", "Передан производителю"
    ASSEMBLING = "assembling", "Собирается"
    SHIPPED = "shipped", "Отправлен"
    IN_TRANSIT = "in_transit", "В пути"
    READY_FOR_PICKUP = "ready_for_pickup", "Ожидает в пункте выдачи"
    DELIVERED = "delivered", "Доставлен"
    COMPLETED = "completed", "Заказ завершён"
    CANCELLED = "cancelled", "Отменён"


# Допустимые переходы машины состояний (PRD 6.6).
ALLOWED_TRANSITIONS = {
    OrderStatus.CREATED: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.SENT_TO_PRODUCER, OrderStatus.CANCELLED},
    OrderStatus.SENT_TO_PRODUCER: {OrderStatus.ASSEMBLING, OrderStatus.CANCELLED},
    OrderStatus.ASSEMBLING: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.IN_TRANSIT, OrderStatus.READY_FOR_PICKUP,
                          OrderStatus.DELIVERED},
    OrderStatus.IN_TRANSIT: {OrderStatus.READY_FOR_PICKUP, OrderStatus.DELIVERED},
    OrderStatus.READY_FOR_PICKUP: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: {OrderStatus.COMPLETED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
}


class ShipmentStatus(models.TextChoices):
    PENDING = "pending", "Ожидает сборки"
    ASSEMBLING = "assembling", "Собирается"
    SHIPPED = "shipped", "Отправлена"
    IN_TRANSIT = "in_transit", "В пути"
    DELIVERED = "delivered", "Доставлена"
    CANCELLED = "cancelled", "Отменена"


class ActorType(models.TextChoices):
    SYSTEM = "system", "Система"
    BUYER = "buyer", "Покупатель"
    SELLER = "seller", "Продавец"
    PRODUCER = "producer", "Производитель"
    CARRIER = "carrier", "Служба доставки"
    ADMIN = "admin", "Суперадмин"
