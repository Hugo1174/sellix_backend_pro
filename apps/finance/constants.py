from django.db import models


class PayoutStatus(models.TextChoices):
    PENDING = "pending", "Ожидает обработки"
    PROCESSING = "processing", "В обработке"
    PAID = "paid", "Выплачено"
    FAILED = "failed", "Ошибка"


class PayeeType(models.TextChoices):
    SELLER = "seller", "Продавец"
    PRODUCER = "producer", "Производитель"
