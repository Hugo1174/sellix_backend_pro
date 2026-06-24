from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("subject", "recipient", "channel", "status", "created_at")
    list_filter = ("channel", "status")
    search_fields = ("subject", "recipient__email", "event_key")
