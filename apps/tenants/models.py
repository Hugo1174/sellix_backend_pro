from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.common.models import BaseModel
from .constants import (
    DeliveryProvider,
    IntegrationKind,
    IntegrationOwnerType,
    IntegrationStatus,
    PaymentProvider,
    ProducerStatus,
    StoreNiche,
    StoreStatus,
)


def _unique_slug(model, base):
    base = slugify(base, allow_unicode=False) or "shop"
    slug = base
    i = 1
    while model.objects.filter(slug=slug).exists():
        i += 1
        slug = f"{base}-{i}"
    return slug


class Store(BaseModel):
    """Магазин продавца (STORE). Один на пользователя."""

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="store"
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    niche = models.CharField(max_length=32, choices=StoreNiche.choices,
                             default=StoreNiche.OTHER)
    status = models.CharField(max_length=16, choices=StoreStatus.choices,
                              default=StoreStatus.DRAFT, db_index=True)

    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="stores/logos/", null=True, blank=True)
    banner = models.ImageField(upload_to="stores/banners/", null=True, blank=True)
    theme = models.CharField(max_length=32, default="default")

    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    inn = models.CharField("ИНН/ОГРНИП", max_length=32, blank=True)
    payout_requisites = models.JSONField(default=dict, blank=True)

    blocked_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Store, self.name)
        super().save(*args, **kwargs)

    @property
    def has_active_payment(self):
        return self.integrations.filter(
            kind=IntegrationKind.PAYMENT, status=IntegrationStatus.ACTIVE
        ).exists()

    def can_publish(self):
        return self.store_products.filter(is_visible=True).exists() and self.has_active_payment


class Producer(BaseModel):
    """Профиль производителя (PRODUCER).

    Production: main_category заменено на M2M categories (до 3 категорий).
    Старое поле main_category сохранено для обратной совместимости миграций.
    """

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="producer"
    )
    company_name = models.CharField(max_length=255)
    inn = models.CharField("ИНН", max_length=32, blank=True)
    ogrn = models.CharField("ОГРН/ОГРНИП", max_length=32, blank=True)

    # Старое поле — НЕ используется в новом коде, но остаётся для миграции.
    main_category = models.CharField(max_length=64, blank=True)

    # Новое: до 3 категорий производителя (M2M → catalog.Category).
    # blank=True: поле необязательно при создании.
    categories = models.ManyToManyField(
        "catalog.Category", blank=True, related_name="producers",
        help_text="До 3 категорий продукции производителя"
    )

    status = models.CharField(max_length=16, choices=ProducerStatus.choices,
                              default=ProducerStatus.PENDING, db_index=True)

    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    payout_requisites = models.JSONField(default=dict, blank=True)

    blocked_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.company_name

    def save(self, *args, **kwargs):
        if self._state.adding and settings.SELLIX["AUTO_APPROVE_PRODUCERS"]:
            self.status = ProducerStatus.APPROVED
        super().save(*args, **kwargs)


class ShopIntegration(BaseModel):
    """Подключённые платёжные системы и службы доставки (SHOP_INTEGRATION)."""

    owner_type = models.CharField(max_length=16, choices=IntegrationOwnerType.choices)
    store = models.ForeignKey(Store, null=True, blank=True, on_delete=models.CASCADE,
                              related_name="integrations")
    producer = models.ForeignKey(Producer, null=True, blank=True, on_delete=models.CASCADE,
                                 related_name="integrations")

    kind = models.CharField(max_length=16, choices=IntegrationKind.choices)
    provider = models.CharField(max_length=32)
    status = models.CharField(max_length=16, choices=IntegrationStatus.choices,
                              default=IntegrationStatus.NOT_CONNECTED)
    credentials = models.JSONField(default=dict, blank=True)
    last_error = models.CharField(max_length=512, blank=True)

    class Meta:
        ordering = ["kind", "provider"]
        constraints = [
            models.UniqueConstraint(
                fields=["store", "kind", "provider"],
                condition=models.Q(store__isnull=False),
                name="uniq_store_integration",
            ),
            models.UniqueConstraint(
                fields=["producer", "kind", "provider"],
                condition=models.Q(producer__isnull=False),
                name="uniq_producer_integration",
            ),
        ]

    def __str__(self):
        return f"{self.get_kind_display()}:{self.provider} ({self.status})"

    @staticmethod
    def valid_providers(kind):
        if kind == IntegrationKind.PAYMENT:
            return PaymentProvider
        return DeliveryProvider
