from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class AuditLog(BaseModel):
    """Журнал действий администратора (PRD 2.2.2, NFR — логирование)."""

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="audit_logs")
    action = models.CharField(max_length=64)
    target_entity = models.CharField(max_length=64)
    target_id = models.CharField(max_length=64, blank=True)
    detail = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} {self.target_entity}:{self.target_id}"


def write_audit(actor, action, entity, target_id="", detail=None):
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action, target_entity=entity, target_id=str(target_id),
        detail=detail or {},
    )
