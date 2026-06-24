from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "target_entity", "target_id", "actor", "created_at")
    list_filter = ("target_entity", "action")
    search_fields = ("target_id",)
    readonly_fields = ("created_at", "updated_at")
