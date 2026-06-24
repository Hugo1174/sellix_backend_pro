"""OAuth providers: Яндекс ID / VK ID (PRD 3.2.1, 10.1).

When SELLIX["USE_SANDBOX_PROVIDERS"] is True (default for the internal MVP test),
the exchange is stubbed: any code is accepted and a deterministic fake identity
is returned, so the full onboarding flow can be exercised without real OAuth apps.
Set USE_SANDBOX_PROVIDERS=False and fill OAUTH_PROVIDERS to go live.
"""
import hashlib
import logging

import requests
from django.conf import settings

from .constants import AuthProvider

logger = logging.getLogger("sellix.oauth")

SUPPORTED = {AuthProvider.YANDEX, AuthProvider.VK}


class OAuthError(Exception):
    pass


class OAuthIdentity:
    def __init__(self, external_id, email=None, full_name="", phone=""):
        self.external_id = str(external_id)
        self.email = email
        self.full_name = full_name or ""
        self.phone = phone or ""


def exchange_code(provider: str, code: str, redirect_uri: str = "") -> OAuthIdentity:
    if provider not in SUPPORTED:
        raise OAuthError(f"Неподдерживаемый провайдер: {provider}")
    if not code:
        raise OAuthError("Отсутствует authorization code")

    if settings.SELLIX["USE_SANDBOX_PROVIDERS"]:
        return _sandbox_identity(provider, code)

    if provider == AuthProvider.YANDEX:
        return _yandex_identity(code, redirect_uri)
    return _vk_identity(code, redirect_uri)


def _sandbox_identity(provider: str, code: str) -> OAuthIdentity:
    digest = hashlib.sha256(f"{provider}:{code}".encode()).hexdigest()[:16]
    return OAuthIdentity(
        external_id=digest,
        email=f"{provider}_{digest}@sandbox.sellix.local",
        full_name=f"Sandbox {provider.capitalize()} User",
        phone="",
    )


def _yandex_identity(code: str, redirect_uri: str) -> OAuthIdentity:
    cfg = settings.OAUTH_PROVIDERS["yandex"]
    token_resp = requests.post(
        "https://oauth.yandex.ru/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "redirect_uri": redirect_uri or cfg["redirect_uri"],
        },
        timeout=10,
    )
    if token_resp.status_code != 200:
        raise OAuthError("Яндекс ID: не удалось обменять код на токен")
    access_token = token_resp.json().get("access_token")
    info = requests.get(
        "https://login.yandex.ru/info",
        headers={"Authorization": f"OAuth {access_token}"},
        params={"format": "json"},
        timeout=10,
    )
    if info.status_code != 200:
        raise OAuthError("Яндекс ID: не удалось получить профиль")
    data = info.json()
    return OAuthIdentity(
        external_id=data.get("id"),
        email=data.get("default_email"),
        full_name=data.get("real_name") or data.get("display_name") or "",
        phone=(data.get("default_phone") or {}).get("number", ""),
    )


def _vk_identity(code: str, redirect_uri: str) -> OAuthIdentity:
    cfg = settings.OAUTH_PROVIDERS["vk"]
    token_resp = requests.get(
        "https://oauth.vk.com/access_token",
        params={
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "redirect_uri": redirect_uri or cfg["redirect_uri"],
            "code": code,
        },
        timeout=10,
    )
    if token_resp.status_code != 200:
        raise OAuthError("VK ID: не удалось обменять код на токен")
    payload = token_resp.json()
    user_id = payload.get("user_id")
    email = payload.get("email")
    return OAuthIdentity(external_id=user_id, email=email, full_name="", phone="")
