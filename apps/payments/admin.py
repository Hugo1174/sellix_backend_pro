from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "provider", "amount", "status", "created_at")
    list_filter = ("status", "provider")
    search_fields = ("order__number", "provider_payment_id")
