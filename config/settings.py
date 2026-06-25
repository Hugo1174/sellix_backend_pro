"""
Django settings for the Sellix backend (config project).

Multi-tenant B2B2C e-commerce platform. See PRD (Sellix_PRD_MVP).
"""

from pathlib import Path
from datetime import timedelta
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(os.path.join(BASE_DIR, ".env"))


def env_bool(key, default=False):
    val = os.environ.get(key)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def env_list(key, default=None):
    val = os.environ.get(key)
    if not val:
        return default or []
    return [item.strip() for item in val.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "default-unsafe-key")
DEBUG = env_bool("DEBUG", False)

ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS",
    ["mysellix.ru", "www.mysellix.ru", "45.151.30.153", "127.0.0.1", "localhost"],
)

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.common",
    "apps.accounts",
    "apps.tenants",
    "apps.integrations",
    "apps.catalog",
    "apps.storefront",
    "apps.orders",
    "apps.payments",
    "apps.finance",
    "apps.logistics",
    "apps.notifications",
    "apps.adminpanel",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "sellix_db"),
        "USER": os.environ.get("DB_USER", "sellix_user"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "Oper800!"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", ""),
    }
}

# ---------------------------------------------------------------------------
# Custom user model
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# i18n / l10n  (PRD 10.1 — RU locale, RUB, MSK)
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
MEDIA_URL = "media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# DRF + JWT
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.DefaultPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.environ.get("JWT_ACCESS_MIN", "60"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.environ.get("JWT_REFRESH_DAYS", "14"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Sellix API",
    "DESCRIPTION": "Мультиарендная B2B2C e-commerce платформа — MVP backend.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    ["https://mysellix.ru", "https://www.mysellix.ru", "http://localhost:3000"],
)
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Cache / Redis (PRD 2.2.3)
# ---------------------------------------------------------------------------
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache"
        if env_bool("DISABLE_REDIS", True)
        else "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "sellix-local" if env_bool("DISABLE_REDIS", True) else REDIS_URL,
    }
}

# ---------------------------------------------------------------------------
# Sellix domain configuration (PRD 5.4, 6.6, 10.1)
# ---------------------------------------------------------------------------
SELLIX = {
    # Default platform commission, 0% on MVP (PRD 5.4).
    "PLATFORM_COMMISSION_PERCENT": float(os.environ.get("PLATFORM_COMMISSION_PERCENT", "0")),
    # completed == delivered on MVP (no return window). PRD 6.6.
    "COMPLETE_ON_DELIVERED": env_bool("COMPLETE_ON_DELIVERED", True),
    # Producer assembling SLA in hours before escalation. PRD 10.3 #3.
    "ASSEMBLING_SLA_HOURS": int(os.environ.get("ASSEMBLING_SLA_HOURS", "72")),
    # Auto-approve producer profiles on MVP. PRD 3.2.5.
    "AUTO_APPROVE_PRODUCERS": env_bool("AUTO_APPROVE_PRODUCERS", True),
    # Use sandbox stubs for OAuth / payment / delivery providers.
    "USE_SANDBOX_PROVIDERS": env_bool("USE_SANDBOX_PROVIDERS", True),
    "CURRENCY": "RUB",
}

# OAuth provider credentials (PRD 3.2.1). Sandbox-safe when empty.
OAUTH_PROVIDERS = {
    "yandex": {
        "client_id": os.environ.get("YANDEX_CLIENT_ID", ""),
        "client_secret": os.environ.get("YANDEX_CLIENT_SECRET", ""),
        "redirect_uri": os.environ.get("YANDEX_REDIRECT_URI", ""),
    },
    "vk": {
        "client_id": os.environ.get("VK_CLIENT_ID", ""),
        "client_secret": os.environ.get("VK_CLIENT_SECRET", ""),
        "redirect_uri": os.environ.get("VK_REDIRECT_URI", ""),
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
    "loggers": {
        "sellix": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

# Security hardening for production (PRD 10.2)
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    CSRF_TRUSTED_ORIGINS = env_list(
        "CSRF_TRUSTED_ORIGINS", ["https://mysellix.ru", "https://www.mysellix.ru"]
    )
