from django.contrib import admin

from .models import Category, Product, ProductImage, StoreProduct


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "producer", "category", "base_price", "stock", "status")
    list_filter = ("status", "category")
    search_fields = ("name", "sku", "producer__company_name")
    inlines = [ProductImageInline]
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(StoreProduct)
class StoreProductAdmin(admin.ModelAdmin):
    list_display = ("store", "product", "is_visible", "markup_percent", "final_price")
    list_filter = ("is_visible",)
    search_fields = ("store__name", "product__name")
