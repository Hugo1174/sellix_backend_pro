from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel
from apps.catalog.models import StoreProduct
from apps.tenants.models import Store


class Cart(BaseModel):
    """Корзина покупателя (PRD 6.2). На MVP — одна корзина на магазин."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.CASCADE, related_name="carts")
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="carts")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def subtotal(self):
        return sum((item.line_total for item in self.items.all()), Decimal("0.00"))


class CartItem(BaseModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    store_product = models.ForeignKey(StoreProduct, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cart", "store_product"],
                                    name="uniq_cart_item")
        ]

    @property
    def line_total(self):
        return self.store_product.retail_price * self.quantity
