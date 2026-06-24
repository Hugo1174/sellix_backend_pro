"""Платёжные провайдеры РФ (PRD 4.3, 10.1): ЮKassa, Т-Касса, CloudPayments.

Sandbox-режим (по умолчанию для MVP): create_payment генерирует псевдо-URL
и id, verify_credentials всегда True. Реальная интеграция подключается заменой
тел метода без изменения вызывающего кода (Order/Payment Service).
"""
import uuid

from django.conf import settings


class PaymentProviderError(Exception):
    pass


class BasePaymentProvider:
    code = "base"

    def __init__(self, credentials: dict):
        self.credentials = credentials or {}

    def verify_credentials(self) -> tuple[bool, str]:
        if settings.SELLIX["USE_SANDBOX_PROVIDERS"]:
            return True, ""
        if not self.credentials.get("api_key") and not self.credentials.get("shop_id"):
            return False, "Не указаны ключи API"
        return True, ""

    def create_payment(self, *, amount, order_id, return_url="", description=""):
        """Returns dict: provider_payment_id, confirmation_url, status."""
        if settings.SELLIX["USE_SANDBOX_PROVIDERS"]:
            pid = f"sandbox_{self.code}_{uuid.uuid4().hex[:12]}"
            return {
                "provider_payment_id": pid,
                "confirmation_url": f"https://sandbox.{self.code}.local/pay/{pid}",
                "status": "pending",
            }
        raise PaymentProviderError("Боевая интеграция не сконфигурирована")

    def parse_webhook(self, payload: dict) -> dict:
        """Normalize provider webhook -> {provider_payment_id, status, raw}."""
        return {
            "provider_payment_id": payload.get("provider_payment_id")
            or payload.get("object", {}).get("id"),
            "status": payload.get("status")
            or payload.get("object", {}).get("status", "succeeded"),
            "raw": payload,
        }


class YooKassaProvider(BasePaymentProvider):
    code = "yookassa"


class TKassaProvider(BasePaymentProvider):
    code = "tkassa"


class CloudPaymentsProvider(BasePaymentProvider):
    code = "cloudpayments"


_REGISTRY = {
    "yookassa": YooKassaProvider,
    "tkassa": TKassaProvider,
    "cloudpayments": CloudPaymentsProvider,
}


def get_payment_provider(provider_code, credentials):
    cls = _REGISTRY.get(provider_code)
    if cls is None:
        raise PaymentProviderError(f"Неизвестный платёжный провайдер: {provider_code}")
    return cls(credentials)
