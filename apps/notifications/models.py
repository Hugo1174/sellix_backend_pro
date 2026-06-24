from django.conf import settings
from django.db import models

from apps.common.models import BaseModel
from .constants import NotificationChannel, NotificationStatus


class Notification(BaseModel):
    """Журнал уведомлений покупателю/продавцу/производителю (PRD 8.6)."""

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name="notifications")
    channel = models.CharField(max_length=16, choices=NotificationChannel.choices,
                               default=NotificationChannel.EMAIL)
    subject = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=NotificationStatus.choices,
                              default=NotificationStatus.QUEUED)
    event_key = models.CharField(max_length=64, blank=True, db_index=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.channel}:{self.subject} → {self.recipient_id}"
