"""Службы доставки РФ (PRD 4.3, 10.1): СДЭК, Почта России, Я.Доставка, Boxberry.

Sandbox: calculate возвращает детерминированный тариф по весу/городу,
create_shipment выдаёт фейковый трек-номер и tracking_url.
"""
import hashlib
import uuid
from decimal import Decimal

from django.conf import settings

from apps.common.money import to_money


class DeliveryProviderError(Exception):
    pass


class BaseDeliveryProvider:
    code = "base"
    tracking_base = "https://example.com/track/"

    def __init__(self, credentials: dict | None = None):
        self.credentials = credentials or {}

    def verify_credentials(self) -> tuple[bool, str]:
        if settings.SELLIX["USE_SANDBOX_PROVIDERS"]:
            return True, ""
        if not self.credentials.get("token"):
            return False, "Не указан API-токен"
        return True, ""

    def calculate(self, *, city, weight_grams, dims=None) -> Decimal:
        """Стоимость доставки по адресу и весогабаритам (PRD 5.1, 6.4)."""
        if settings.SELLIX["USE_SANDBOX_PROVIDERS"]:
            base = Decimal("150")
            weight_part = to_money(Decimal(weight_grams or 0) / Decimal("1000") * Decimal("40"))
            city_factor = int(hashlib.md5((city or "").encode()).hexdigest(), 16) % 100
            return to_money(base + weight_part + Decimal(city_factor))
        raise DeliveryProviderError("Боевая интеграция не сконфигурирована")

    def create_shipment(self, *, city, address, weight_grams, recipient,
                        dims=None) -> dict:
        """Returns {tracking_number, tracking_url, provider}."""
        if settings.SELLIX["USE_SANDBOX_PROVIDERS"]:
            track = f"{self.code.upper()}{uuid.uuid4().hex[:10].upper()}"
            return {
                "tracking_number": track,
                "tracking_url": f"{self.tracking_base}{track}",
                "provider": self.code,
            }
        raise DeliveryProviderError("Боевая интеграция не сконфигурирована")

    def fetch_status(self, tracking_number) -> str:
        """Polling fallback (PRD 6.7). Sandbox returns a stable 'in_transit'."""
        return "in_transit"


class CdekProvider(BaseDeliveryProvider):
    code = "cdek"
    tracking_base = "https://www.cdek.ru/ru/tracking?order_id="


class PochtaProvider(BaseDeliveryProvider):
    code = "pochta"
    tracking_base = "https://www.pochta.ru/tracking#"


class YandexDeliveryProvider(BaseDeliveryProvider):
    code = "yandex_delivery"
    tracking_base = "https://yandex.ru/delivery/track/"


class BoxberryProvider(BaseDeliveryProvider):
    code = "boxberry"
    tracking_base = "https://boxberry.ru/tracking/?id="


_REGISTRY = {
    "cdek": CdekProvider,
    "pochta": PochtaProvider,
    "yandex_delivery": YandexDeliveryProvider,
    "boxberry": BoxberryProvider,
}


def get_delivery_provider(provider_code, credentials=None):
    cls = _REGISTRY.get(provider_code)
    if cls is None:
        raise DeliveryProviderError(f"Неизвестная служба доставки: {provider_code}")
    return cls(credentials)
