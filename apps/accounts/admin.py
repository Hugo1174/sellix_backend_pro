from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import BuyerAddress, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("-created_at",)
    list_display = ("email", "full_name", "role", "auth_provider", "is_blocked", "is_staff")
    list_filter = ("role", "auth_provider", "is_blocked", "is_staff")
    search_fields = ("email", "full_name", "phone", "external_id")
    readonly_fields = ("id", "created_at", "updated_at", "last_login")
    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        ("Профиль", {"fields": ("full_name", "phone", "role", "auth_provider", "external_id")}),
        ("Статусы", {"fields": ("is_active", "is_blocked", "blocked_reason", "is_staff",
                                "is_superuser", "groups", "user_permissions")}),
        ("Даты", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",),
                "fields": ("email", "password1", "password2", "role")}),
    )


@admin.register(BuyerAddress)
class BuyerAddressAdmin(admin.ModelAdmin):
    list_display = ("user", "city", "address_line", "is_default")
    search_fields = ("user__email", "city", "address_line")
