"""Domain services for connecting/verifying integrations (PRD 4.3)."""
from apps.integrations.delivery_providers import get_delivery_provider
from apps.integrations.payment_providers import get_payment_provider
from .constants import IntegrationKind, IntegrationStatus


def verify_integration(integration):
    """Тестовый запрос к API провайдера, обновляет статус. PRD 4.3."""
    creds = integration.credentials or {}
    try:
        if integration.kind == IntegrationKind.PAYMENT:
            provider = get_payment_provider(integration.provider, creds)
        else:
            provider = get_delivery_provider(integration.provider, creds)
        ok, err = provider.verify_credentials()
    except Exception as exc:  # noqa: BLE001 — surface any provider error to UI
        ok, err = False, str(exc)

    if ok:
        integration.status = IntegrationStatus.ACTIVE
        integration.last_error = ""
    else:
        integration.status = IntegrationStatus.ERROR
        integration.last_error = err or "Ошибка подключения"
    integration.save(update_fields=["status", "last_error", "updated_at"])
    return integration
