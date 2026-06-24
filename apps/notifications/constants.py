from django.db import models


class NotificationChannel(models.TextChoices):
    EMAIL = "email", "Email"
    SMS = "sms", "SMS"
    PUSH = "push", "Push"


class NotificationStatus(models.TextChoices):
    QUEUED = "queued", "В очереди"
    SENT = "sent", "Отправлено"
    FAILED = "failed", "Ошибка"
