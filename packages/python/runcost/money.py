"""Isolated 18-place, half-even arithmetic shared by all Python entrypoints."""

from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from typing import Any

_DECIMAL_PLACES = 18
_DECIMAL_QUANTUM = Decimal("0.000000000000000001")
_DECIMAL_CONTEXT = Context(prec=100, rounding=ROUND_HALF_EVEN)


def _decimal(value: Any) -> Decimal:
    with localcontext(_DECIMAL_CONTEXT):
        return Decimal(str(value))


def _format_decimal(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("decimal value must be finite")
    precision = max(
        _DECIMAL_CONTEXT.prec,
        len(value.as_tuple().digits) + abs(value.adjusted()) + _DECIMAL_PLACES + 4,
    )
    with localcontext(_DECIMAL_CONTEXT) as context:
        context.prec = precision
        rounded = value.quantize(_DECIMAL_QUANTUM, rounding=ROUND_HALF_EVEN) if value.as_tuple().exponent < -_DECIMAL_PLACES else value
        normalized = rounded.normalize()
    if normalized.is_zero():
        return "0"
    text = format(normalized, "f")
    if "." not in text:
        return text
    return text.rstrip("0").rstrip(".")


def _operation_context(*values: Decimal) -> Context:
    precision = max(
        _DECIMAL_CONTEXT.prec,
        sum(len(value.as_tuple().digits) + max(value.adjusted(), 0) for value in values)
        + _DECIMAL_PLACES
        + 8,
    )
    context = _DECIMAL_CONTEXT.copy()
    context.prec = precision
    return context


def _add(left: str, right: str) -> str:
    left_decimal = _decimal(left)
    right_decimal = _decimal(right)
    with localcontext(_operation_context(left_decimal, right_decimal)):
        return _format_decimal(left_decimal + right_decimal)


def _subtract(left: str, right: str) -> str:
    left_decimal = _decimal(left)
    right_decimal = _decimal(right)
    with localcontext(_operation_context(left_decimal, right_decimal)):
        return _format_decimal(left_decimal - right_decimal)


def _multiply_divide(quantity: Any, amount: Any, per: Any) -> str:
    quantity_decimal = _decimal(quantity)
    amount_decimal = _decimal(amount)
    per_decimal = _decimal(per)
    if per_decimal <= 0:
        raise ValueError("price.per must be greater than zero")
    with localcontext(_operation_context(quantity_decimal, amount_decimal, per_decimal)):
        return _format_decimal((quantity_decimal * amount_decimal) / per_decimal)
