from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .constants import Role
from .models import BuyerAddress, User


def issue_tokens(user):
    refresh = RefreshToken.for_user(user)
    refresh["role"] = user.role or ""
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class UserSerializer(serializers.ModelSerializer):
    role_assigned = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "full_name", "phone", "role", "role_assigned",
            "auth_provider", "is_blocked", "created_at",
        ]
        read_only_fields = ["id", "auth_provider", "is_blocked", "created_at", "role"]


class OAuthLoginSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=["yandex", "vk"])
    code = serializers.CharField()
    redirect_uri = serializers.CharField(required=False, allow_blank=True, default="")


class RoleSelectSerializer(serializers.Serializer):
    """Шаг 2 онбординга — выбор роли (PRD 3.2.3). Только продавец/производитель."""

    role = serializers.ChoiceField(choices=[Role.SELLER, Role.PRODUCER])


class BuyerAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuyerAddress
        fields = [
            "id", "full_name", "phone", "city", "address_line",
            "postal_code", "is_default", "created_at",
        ]
        read_only_fields = ["id", "created_at"]
