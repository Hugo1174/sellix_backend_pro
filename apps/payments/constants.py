from django.db import models


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Ожидает оплаты"
    SUCCEEDED = "succeeded", "Оплачен"
    FAILED = "failed", "Ошибка оплаты"
    REFUNDED = "refunded", "Возвращён"
