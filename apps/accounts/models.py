from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from apps.common.models import BaseModel
from .constants import AuthProvider, Role


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        email = self.normalize_email(email) if email else None
        user = self.model(email=email, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra):
        extra.setdefault("role", Role.BUYER)
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("role", Role.ADMIN)
        extra.setdefault("auth_provider", AuthProvider.LOCAL)
        extra["is_staff"] = True
        extra["is_superuser"] = True
        return self._create_user(email, password, **extra)

    def get_or_create_oauth(self, *, provider, external_id, email=None, full_name="",
                            phone=""):
        """Identity-service lookup by (auth_provider, external_id). PRD 3.2.2."""
        try:
            user = self.get(auth_provider=provider, external_id=external_id)
            created = False
        except self.model.DoesNotExist:
            user = self.create_user(
                email=email,
                auth_provider=provider,
                external_id=external_id,
                full_name=full_name or "",
                phone=phone or "",
                role=None,  # role chosen later during onboarding
            )
            created = True
        return user, created


class User(BaseModel, AbstractBaseUser, PermissionsMixin):
    """Единая учётная запись для всех ролей (PRD 7.1 — USER)."""

    email = models.EmailField(null=True, blank=True)
    full_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=32, blank=True)

    role = models.CharField(max_length=16, choices=Role.choices, null=True, blank=True,
                            db_index=True)
    auth_provider = models.CharField(max_length=16, choices=AuthProvider.choices,
                                     default=AuthProvider.LOCAL)
    external_id = models.CharField(max_length=128, blank=True,
                                   help_text="ID пользователя у OAuth-провайдера")

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)
    blocked_reason = models.CharField(max_length=255, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["auth_provider", "external_id"],
                condition=~models.Q(external_id=""),
                name="uniq_provider_external_id",
            ),
        ]
        indexes = [models.Index(fields=["role", "is_active"])]

    def __str__(self):
        return self.email or f"{self.auth_provider}:{self.external_id}" or str(self.id)

    @property
    def role_assigned(self):
        return self.role is not None


class BuyerAddress(BaseModel):
    """Сохранённые адреса доставки покупателя.

    Production: добавлено опциональное поле store для привязки покупателя
    к конкретному магазину (раздельная регистрация по магазинам).
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    store = models.ForeignKey(
        "tenants.Store", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="buyer_addresses",
        help_text="Магазин, к которому привязан покупатель (опционально)"
    )
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32)
    city = models.CharField(max_length=128)
    address_line = models.CharField(max_length=512)
    postal_code = models.CharField(max_length=16, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.city}, {self.address_line}"
