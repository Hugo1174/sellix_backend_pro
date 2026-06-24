from rest_framework.permissions import BasePermission, SAFE_METHODS

from apps.accounts.constants import Role


class RolePermission(BasePermission):
    """Allow access only to users whose role is in ``allowed_roles``."""

    allowed_roles: tuple = ()

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in self.allowed_roles)


class IsSeller(RolePermission):
    allowed_roles = (Role.SELLER,)


class IsProducer(RolePermission):
    allowed_roles = (Role.PRODUCER,)


class IsBuyer(RolePermission):
    allowed_roles = (Role.BUYER,)


class IsPlatformAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.role == Role.ADMIN or user.is_staff or user.is_superuser)
        )


class IsSellerOrProducer(RolePermission):
    allowed_roles = (Role.SELLER, Role.PRODUCER)


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS
