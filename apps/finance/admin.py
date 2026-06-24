from django.contrib import admin

from .models import Payout


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ("order", "payee_type", "amount", "status", "created_at")
    list_filter = ("status", "payee_type")
    search_fields = ("order__number",)
