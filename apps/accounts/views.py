from django.contrib.auth import authenticate
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.permissions import IsBuyer
from .constants import AuthProvider, Role
from .models import BuyerAddress, User
from .oauth import OAuthError, exchange_code
from .serializers import (
    BuyerAddressSerializer,
    OAuthLoginSerializer,
    RoleSelectSerializer,
    UserSerializer,
    issue_tokens,
)


class OAuthLoginView(APIView):
    """US-01 / US-31. Вход через Яндекс ID или VK ID.

    Возвращает JWT и флаг role_assigned: фронт решает, вести ли в кабинет
    или на экран выбора роли (PRD 3.2.2).
    """

    permission_classes = [AllowAny]

    def post(self, request):
        ser = OAuthLoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        provider = ser.validated_data["provider"]
        try:
            identity = exchange_code(
                provider,
                ser.validated_data["code"],
                ser.validated_data.get("redirect_uri", ""),
            )
        except OAuthError as exc:  # US-05 — понятная ошибка авторизации
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )

        user, created = User.objects.get_or_create_oauth(
            provider=provider,
            external_id=identity.external_id,
            email=identity.email,
            full_name=identity.full_name,
            phone=identity.phone,
        )
        if user.is_blocked:
            return Response(
                {"detail": "Учётная запись заблокирована"},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(
            {
                "tokens": issue_tokens(user),
                "user": UserSerializer(user).data,
                "is_new": created,
            },
            status=status.HTTP_200_OK,
        )


class AdminLoginView(APIView):
    """PRD 3.5 — отдельный вход в Admin Panel: email + пароль, без OAuth."""

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        user = authenticate(request, username=email, password=password)
        if user is None or not (user.is_staff or user.role == Role.ADMIN):
            return Response(
                {"detail": "Неверные учётные данные администратора"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if user.is_blocked:
            return Response({"detail": "Заблокирован"}, status=status.HTTP_403_FORBIDDEN)
        return Response({"tokens": issue_tokens(user), "user": UserSerializer(user).data})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        ser = UserSerializer(request.user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class SelectRoleView(APIView):
    """Шаг 2 онбординга. Роль выбирается один раз и далее не меняется
    пользователем (PRD 3.2.3)."""

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        if request.user.role_assigned:
            return Response(
                {"detail": "Роль уже назначена. Смена роли — через поддержку."},
                status=status.HTTP_409_CONFLICT,
            )
        ser = RoleSelectSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        request.user.role = ser.validated_data["role"]
        request.user.save(update_fields=["role", "updated_at"])
        return Response(
            {"user": UserSerializer(request.user).data, "tokens": issue_tokens(request.user)}
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Stateless JWT — client drops tokens. Endpoint kept for contract symmetry.
        return Response(status=status.HTTP_205_RESET_CONTENT)


class BuyerAddressViewSet(viewsets.ModelViewSet):
    """Адреса доставки покупателя (PRD 6.4)."""

    serializer_class = BuyerAddressSerializer
    permission_classes = [IsBuyer]

    def get_queryset(self):
        return BuyerAddress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        addr = serializer.save(user=self.request.user)
        if addr.is_default:
            BuyerAddress.objects.filter(user=self.request.user).exclude(
                pk=addr.pk
            ).update(is_default=False)
