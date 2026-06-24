"""Helpers for currency-safe arithmetic (PRD 5 — financial model)."""
from decimal import Decimal, ROUND_HALF_UP

CENTS = Decimal("0.01")


def to_money(value) -> Decimal:
    if value is None:
        value = 0
    return Decimal(str(value)).quantize(CENTS, rounding=ROUND_HALF_UP)


def apply_markup(base_price: Decimal, markup_percent=None, markup_amount=None,
                 final_price=None) -> Decimal:
    """Resolve the retail price from the seller's markup configuration.

    Priority: explicit final_price > fixed amount > percent. PRD 4.1.1.
    """
    base_price = to_money(base_price)
    if final_price is not None:
        return to_money(final_price)
    if markup_amount is not None:
        return to_money(base_price + to_money(markup_amount))
    if markup_percent is not None:
        factor = (Decimal("100") + Decimal(str(markup_percent))) / Decimal("100")
        return to_money(base_price * factor)
    return base_price
