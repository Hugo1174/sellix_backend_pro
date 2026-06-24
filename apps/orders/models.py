import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel
from apps.common.money import to_money
from apps.catalog.models import Product, StoreProduct
from apps.tenants.models import Producer, Store
from .constants import ActorType, OrderStatus, ShipmentStatus


def _order_number():
    return f"SLX-{uuid.uuid4().hex[:8].upper()}"


class Order(BaseModel):
    """Заказ покупателя (PRD 7.1 — ORDER). Единица оформления и оплаты."""

    number = models.CharField(max_length=20, unique=True, default=_order_number,
                              db_index=True)
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                              related_name="orders")
    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=24, choices=OrderStatus.choices,
                              default=OrderStatus.CREATED, db_index=True)

    # Снимок адреса доставки на момент заказа
    ship_full_name = models.CharField(max_length=255)
    ship_phone = models.CharField(max_length=32)
    ship_city = models.CharField(max_length=128)
    ship_address = models.CharField(max_length=512)
    ship_postal_code = models.CharField(max_length=16, blank=True)

    # Денежная разбивка (PRD 5.5). Все — снимки.
    goods_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    delivery_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    platform_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["buyer", "status"]),
                   models.Index(fields=["store", "status"])]

    def __str__(self):
        return self.number

    def recalc_totals(self):
        commission_pct = Decimal(str(settings.SELLIX["PLATFORM_COMMISSION_PERCENT"]))
        goods = sum((i.line_total for i in self.items.all()), Decimal("0.00"))
        delivery = sum((s.delivery_fee for s in self.shipments.all()), Decimal("0.00"))
        self.goods_total = to_money(goods)
        self.delivery_total = to_money(delivery)
        self.platform_commission = to_money(goods * commission_pct / Decimal("100"))
        self.grand_total = to_money(self.goods_total + self.delivery_total)


class OrderItem(BaseModel):
    """Позиция заказа со снимком цены/наценки/производителя (PRD 7.3)."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    store_product = models.ForeignKey(StoreProduct, on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    producer = models.ForeignKey(Producer, on_delete=models.PROTECT,
                                 related_name="order_items")

    product_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()

    # Снимки (PRD 7.3) — не пересчитываются после оформления.
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    producer_payout_amount = models.DecimalField(max_digits=12, decimal_places=2)
    seller_markup_amount = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def line_total(self):
        return to_money(self.unit_price * self.quantity)

    @property
    def line_producer_payout(self):
        return to_money(self.producer_payout_amount * self.quantity)

    @property
    def line_seller_markup(self):
        return to_money(self.seller_markup_amount * self.quantity)


class Shipment(BaseModel):
    """Отгрузка на одного производителя (PRD 2.3, 6.5).

    Один ORDER может породить несколько Shipment — по producer_id.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="shipments")
    producer = models.ForeignKey(Producer, on_delete=models.PROTECT,
                                 related_name="shipments")
    status = models.CharField(max_length=16, choices=ShipmentStatus.choices,
                              default=ShipmentStatus.PENDING, db_index=True)

    delivery_provider = models.CharField(max_length=32, blank=True)
    delivery_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tracking_number = models.CharField(max_length=64, blank=True)
    tracking_url = models.URLField(blank=True)
    last_carrier_status = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Shipment {self.order.number} / {self.producer.company_name}"

    @property
    def total_weight_grams(self):
        return sum(
            (i.product.weight_grams * i.quantity
             for i in self.order.items.filter(producer=self.producer)),
            0,
        )


class OrderStatusEvent(BaseModel):
    """Журнал смены статусов заказа (PRD 7.1 — ORDER_STATUS_EVENT)."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_events")
    from_status = models.CharField(max_length=24, blank=True)
    to_status = models.CharField(max_length=24)
    actor_type = models.CharField(max_length=16, choices=ActorType.choices)
    actor_id = models.UUIDField(null=True, blank=True)
    comment = models.CharField(max_length=512, blank=True)

    class Meta:
        ordering = ["created_at"]
