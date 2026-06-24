from django.contrib import admin

from .models import Order, OrderItem, OrderStatusEvent, Shipment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "producer", "quantity", "unit_price",
                       "seller_markup_amount", "producer_payout_amount")


class ShipmentInline(admin.TabularInline):
    model = Shipment
    extra = 0


class OrderStatusEventInline(admin.TabularInline):
    model = OrderStatusEvent
    extra = 0
    readonly_fields = ("from_status", "to_status", "actor_type", "comment", "created_at")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "buyer", "store", "status", "grand_total", "created_at")
    list_filter = ("status",)
    search_fields = ("number", "buyer__email", "store__name")
    inlines = [OrderItemInline, ShipmentInline, OrderStatusEventInline]
    readonly_fields = ("id", "number", "created_at", "updated_at")


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ("order", "producer", "status", "delivery_provider", "tracking_number")
    list_filter = ("status", "delivery_provider")
