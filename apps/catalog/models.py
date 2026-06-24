import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.common.models import BaseModel
from apps.common.money import apply_markup, to_money
from apps.tenants.models import Producer, Store
from .constants import ProductStatus


class Category(BaseModel):
    """Справочник категорий."""

    name = models.CharField(max_length=128, unique=True)
    slug = models.SlugField(max_length=128, unique=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL,
                               related_name="children")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Product(BaseModel):
    """Товар в общем пуле, принадлежит ровно одному производителю.

    Production: добавлены поля allowed_payment_providers и allowed_delivery_providers
    для индивидуальных настроек оплаты/доставки на уровне каждого товара.
    """

    producer = models.ForeignKey(Producer, on_delete=models.CASCADE, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")

    name = models.CharField(max_length=255)
    description = models.TextField()
    sku = models.CharField(max_length=64, blank=True, db_index=True)

    base_price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    stock = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(null=True, blank=True)

    weight_grams = models.PositiveIntegerField(help_text="Вес, г")
    length_mm = models.PositiveIntegerField(null=True, blank=True)
    width_mm = models.PositiveIntegerField(null=True, blank=True)
    height_mm = models.PositiveIntegerField(null=True, blank=True)
    attributes = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=16, choices=ProductStatus.choices,
                              default=ProductStatus.DRAFT, db_index=True)

    # Production: индивидуальные способы оплаты и доставки для каждого товара.
    # Список строк-кодов провайдеров, например ["yookassa", "tkassa"].
    # Пустой список = все провайдеры производителя доступны (обратная совместимость).
    allowed_payment_providers = models.JSONField(
        default=list, blank=True,
        help_text='Допустимые способы оплаты, например: ["yookassa", "cloudpayments"]'
    )
    allowed_delivery_providers = models.JSONField(
        default=list, blank=True,
        help_text='Допустимые службы доставки, например: ["cdek", "pochta"]'
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "category"]),
            models.Index(fields=["producer", "status"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = f"SKU-{uuid.uuid4().hex[:10].upper()}"
        if self.status in (ProductStatus.PUBLISHED, ProductStatus.OUT_OF_STOCK):
            self.status = (
                ProductStatus.OUT_OF_STOCK if self.stock == 0 else ProductStatus.PUBLISHED
            )
        super().save(*args, **kwargs)

    @property
    def is_orderable(self):
        return self.status == ProductStatus.PUBLISHED and self.stock > 0

    @property
    def store_count(self):
        return self.store_links.count()


class ProductImage(BaseModel):
    """До 8 изображений, первое — главное."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    is_primary = models.BooleanField(default=False)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "created_at"]


class StoreProduct(BaseModel):
    """Связующая таблица «один товар — много магазинов» (STORE_PRODUCT)."""

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="store_products")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="store_links")

    markup_percent = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    markup_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    final_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    is_visible = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["store", "product"], name="uniq_store_product")
        ]

    def __str__(self):
        return f"{self.store.name} ← {self.product.name}"

    @property
    def has_markup(self):
        return any(v is not None for v in (self.markup_percent, self.markup_amount,
                                           self.final_price))

    @property
    def retail_price(self):
        return apply_markup(
            self.product.base_price,
            markup_percent=self.markup_percent,
            markup_amount=self.markup_amount,
            final_price=self.final_price,
        )

    @property
    def seller_markup_amount(self):
        return to_money(self.retail_price - to_money(self.product.base_price))
