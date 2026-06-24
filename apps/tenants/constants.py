from django.db import models


class StoreStatus(models.TextChoices):
    DRAFT = "draft", "Черновик"
    PUBLISHED = "published", "Опубликован"
    BLOCKED = "blocked", "Заблокирован"


class ProducerStatus(models.TextChoices):
    PENDING = "pending", "На проверке"
    APPROVED = "approved", "Подтверждён"
    BLOCKED = "blocked", "Заблокирован"


class StoreNiche(models.TextChoices):
    CLOTHING = "clothing", "Одежда и обувь"
    ELECTRONICS = "electronics", "Электроника"
    HOME = "home", "Товары для дома"
    BEAUTY = "beauty", "Красота и здоровье"
    FOOD = "food", "Продукты питания"
    KIDS = "kids", "Детские товары"
    OTHER = "other", "Прочее"


class IntegrationOwnerType(models.TextChoices):
    STORE = "store", "Магазин"
    PRODUCER = "producer", "Производитель"


class IntegrationKind(models.TextChoices):
    PAYMENT = "payment", "Оплата"
    DELIVERY = "delivery", "Доставка"


class PaymentProvider(models.TextChoices):
    YOOKASSA = "yookassa", "ЮKassa"
    TKASSA = "tkassa", "Т-Касса"
    CLOUDPAYMENTS = "cloudpayments", "CloudPayments"


class DeliveryProvider(models.TextChoices):
    CDEK = "cdek", "СДЭК"
    POCHTA = "pochta", "Почта России"
    YANDEX = "yandex_delivery", "Яндекс Доставка"
    BOXBERRY = "boxberry", "Boxberry"


class IntegrationStatus(models.TextChoices):
    NOT_CONNECTED = "not_connected", "Не подключено"
    ACTIVE = "active", "Активно"
    ERROR = "error", "Ошибка подключения"
