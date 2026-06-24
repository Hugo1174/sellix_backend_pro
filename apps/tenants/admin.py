from django.contrib import admin

from .models import Producer, ShopIntegration, Store


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "owner", "niche", "status", "created_at")
    list_filter = ("status", "niche")
    search_fields = ("name", "slug", "owner__email")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Producer)
class ProducerAdmin(admin.ModelAdmin):
    list_display = ("company_name", "owner", "inn", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("company_name", "inn", "ogrn", "owner__email")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(ShopIntegration)
class ShopIntegrationAdmin(admin.ModelAdmin):
    list_display = ("owner_type", "kind", "provider", "status", "store", "producer")
    list_filter = ("owner_type", "kind", "status", "provider")
