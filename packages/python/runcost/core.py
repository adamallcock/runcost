from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple, Union
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

getcontext().prec = 50

_WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
_WEEKDAY_SET = set(_WEEKDAYS)

_COMPONENT_ORDER_NAMES = [
    "input_uncached_tokens",
    "input_cache_read_tokens",
    "input_cache_write_tokens",
    "input_cache_write_1h_tokens",
    "input_image_units",
    "input_audio_tokens",
    "input_image_tokens",
    "input_video_tokens",
    "output_text_tokens",
    "output_reasoning_tokens",
    "output_audio_tokens",
    "output_image_tokens",
    "output_video_tokens",
    "embedding_tokens",
    "request_units",
    "web_search_units",
    "x_search_units",
    "file_search_units",
    "code_interpreter_session_units",
    "code_interpreter_call_units",
    "attachment_search_units",
    "computer_use_action_units",
    "tool_call_units",
    "tool_execution_seconds",
    "rerank_search_units",
    "image_generation_units",
    "video_generation_units",
    "audio_generation_units",
    "audio_generation_characters",
    "transcription_seconds",
    "endpoint_runtime_seconds",
    "endpoint_instance_hours",
    "storage_gb_days",
    "custom_units",
]
_COMPONENT_ORDER = {name: index for index, name in enumerate(_COMPONENT_ORDER_NAMES)}
_TOOL_OR_FEATURE_COMPONENTS = {
    "web_search_units",
    "x_search_units",
    "file_search_units",
    "code_interpreter_session_units",
    "code_interpreter_call_units",
    "attachment_search_units",
    "computer_use_action_units",
    "tool_call_units",
    "tool_execution_seconds",
    "rerank_search_units",
    "image_generation_units",
    "video_generation_units",
    "audio_generation_units",
    "audio_generation_characters",
    "transcription_seconds",
    "endpoint_runtime_seconds",
    "storage_gb_days",
}


class CompiledPriceCatalog:
    """Read-only price-card collection indexed by provider and model aliases."""

    def __init__(self, price_cards: Iterable[Dict[str, Any]]) -> None:
        self.price_cards = list(price_cards)
        self.by_provider_model: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        self.by_model: Dict[str, List[Dict[str, Any]]] = {}
        for card in self.price_cards:
            provider = str(card.get("provider") or "")
            names = [str(card.get("model") or ""), *(str(alias) for alias in card.get("aliases", []))]
            for name in dict.fromkeys(name for name in names if name):
                self.by_provider_model.setdefault((provider, name), []).append(card)
                self.by_model.setdefault(name, []).append(card)

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        return iter(self.price_cards)

    def __len__(self) -> int:
        return len(self.price_cards)

    def identity_candidates(self, usage_ledger: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.by_provider_model.get((str(usage_ledger.get("provider") or ""), _billed_model(usage_ledger)), [])

    def model_candidates(self, usage_ledger: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.by_model.get(_billed_model(usage_ledger), [])


def compile_price_catalog(price_cards: Iterable[Dict[str, Any]]) -> CompiledPriceCatalog:
    """Compile price cards once for repeated indexed selection."""

    if isinstance(price_cards, CompiledPriceCatalog):
        return price_cards
    return CompiledPriceCatalog(price_cards)


def _plain_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _plain_value(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_value(child) for child in value]
    if hasattr(value, "model_dump"):
        return _plain_value(value.model_dump())
    if hasattr(value, "dict") and callable(value.dict):
        return _plain_value(value.dict())
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return {
            key: _plain_value(child)
            for key, child in vars(value).items()
            if not key.startswith("_")
        }
    return value


def _response_mapping(value: Any) -> Dict[str, Any]:
    """Normalize SDK response models to the same mapping shape as raw JSON."""

    payload = _plain_value(value)
    if not isinstance(payload, dict):
        raise TypeError("response must be a mapping or an SDK object with model_dump()/dict()")
    return payload


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _format_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal("1")))
    return format(normalized, "f").rstrip("0").rstrip(".")


def _attribution_string(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float, Decimal)):
        number = _decimal(value)
        if not number.is_finite():
            return None
        return _format_decimal(number)
    return None


def _normalize_attribution(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result: Dict[str, Any] = {}
    for key in ("run_id", "session_id", "workflow", "tenant_id", "feature"):
        normalized = _attribution_string(value.get(key))
        if normalized is not None:
            result[key] = normalized
    tags = value.get("tags")
    if isinstance(tags, dict):
        normalized_tags = {
            str(key): normalized
            for key, child in sorted(tags.items(), key=lambda item: str(item[0]))
            if (normalized := _attribution_string(child)) is not None
        }
        if normalized_tags:
            result["tags"] = normalized_tags
    return result


def _add(left: str, right: str) -> str:
    return _format_decimal(_decimal(left) + _decimal(right))


def _subtract(left: str, right: str) -> str:
    return _format_decimal(_decimal(left) - _decimal(right))


def _multiply_divide(quantity: Any, amount: Any, per: Any) -> str:
    per_decimal = _decimal(per)
    if per_decimal == 0:
        raise ValueError("price.per must not be zero")
    return _format_decimal((_decimal(quantity) * _decimal(amount)) / per_decimal)


def _billed_model(usage_ledger: Dict[str, Any]) -> str:
    model = usage_ledger["model"]
    return model.get("billed") or model.get("returned") or model["requested"]


def _date_part(value: Any) -> Optional[str]:
    if not value:
        return None
    return str(value)[:10]


def _date_value(value: Any) -> Optional[date]:
    text = _date_part(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _datetime_value(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    text = str(value)
    if "T" not in text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _unix_seconds_priced_at(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        seconds = int(_decimal(value))
        parsed = datetime.fromtimestamp(seconds, timezone.utc)
    except Exception:
        return None
    return parsed.isoformat().replace("+00:00", "Z")


def _usage_context(usage_ledger: Dict[str, Any]) -> Dict[str, Any]:
    return usage_ledger.get("context", {})


def _card_pricing_period(card: Dict[str, Any]) -> Optional[str]:
    value = card.get("pricing_period") or card.get("pricingPeriod")
    return str(value) if value else None


def _card_billing_schedule(card: Dict[str, Any]) -> Dict[str, Any]:
    schedule = card.get("billing_schedule") or card.get("billingSchedule") or {}
    return schedule if isinstance(schedule, dict) else {}


def _billing_window_days(window: Dict[str, Any]) -> Tuple[bool, Optional[set[str]]]:
    """Validate and return a window's optional schedule-local start days."""

    has_snake = "days_of_week" in window
    has_camel = "daysOfWeek" in window
    if has_snake and has_camel:
        return False, None
    if not has_snake and not has_camel:
        return True, None
    raw_days = window.get("days_of_week") if has_snake else window.get("daysOfWeek")
    if not isinstance(raw_days, list) or not raw_days:
        return False, None
    if (
        any(not isinstance(day, str) or day not in _WEEKDAY_SET for day in raw_days)
        or len(set(raw_days)) != len(raw_days)
    ):
        return False, None
    return True, set(raw_days)


def _normalize_billing_schedule(schedule: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(schedule, dict):
        return None
    normalized: Dict[str, Any] = {}
    timezone_name = schedule.get("timezone")
    if timezone_name is not None:
        normalized["timezone"] = timezone_name
    default_period = schedule.get("default_period") or schedule.get("defaultPeriod")
    if default_period is not None:
        normalized["default_period"] = default_period
    boundary_policy = schedule.get("boundary_policy") or schedule.get("boundaryPolicy")
    if boundary_policy is not None:
        normalized["boundary_policy"] = boundary_policy
    if isinstance(schedule.get("windows"), list):
        windows = []
        for window in schedule["windows"]:
            if not isinstance(window, dict):
                windows.append(window)
                continue
            normalized_window = {
                "period": window.get("period"),
                "start": window.get("start"),
                "end": window.get("end"),
            }
            if "days_of_week" in window and "daysOfWeek" in window:
                # Preserve the invalid/ambiguous shape so evaluation fails closed.
                normalized_window["days_of_week"] = []
            elif "days_of_week" in window:
                normalized_window["days_of_week"] = window["days_of_week"]
            elif "daysOfWeek" in window:
                normalized_window["days_of_week"] = window["daysOfWeek"]
            windows.append({key: value for key, value in normalized_window.items() if value is not None})
        normalized["windows"] = windows
    elif "windows" in schedule:
        normalized["windows"] = schedule["windows"]
    return normalized


def _time_seconds(value: Any) -> Optional[int]:
    if not isinstance(value, str):
        return None
    parts = value.split(":")
    if len(parts) not in {2, 3}:
        return None
    try:
        hour = int(parts[0])
        minute = int(parts[1])
        second = int(parts[2]) if len(parts) == 3 else 0
    except ValueError:
        return None
    if hour < 0 or hour > 23 or minute < 0 or minute > 59 or second < 0 or second > 59:
        return None
    return hour * 3600 + minute * 60 + second


def _time_in_window(current: int, start: int, end: int) -> bool:
    if start <= end:
        return start <= current < end
    return current >= start or current < end


def _pricing_period_from_schedule(schedule: Dict[str, Any], priced_at: datetime) -> Dict[str, Any]:
    timezone_name = schedule.get("timezone", "UTC")
    try:
        schedule_timezone = ZoneInfo(timezone_name)
    except (TypeError, ValueError, ZoneInfoNotFoundError):
        return {"unsupported_timezone": str(timezone_name)}
    boundary_policy = schedule.get("boundary_policy") or schedule.get("boundaryPolicy") or "start_inclusive_end_exclusive"
    if boundary_policy != "start_inclusive_end_exclusive":
        return {"unsupported_schedule": "boundary_policy"}
    windows = schedule.get("windows")
    if not isinstance(windows, list):
        return {"unsupported_schedule": "windows"}
    validated_windows: List[Tuple[Dict[str, Any], int, int, Optional[set[str]]]] = []
    for window in windows:
        if not isinstance(window, dict):
            return {"unsupported_schedule": "window"}
        start = _time_seconds(window.get("start"))
        end = _time_seconds(window.get("end"))
        period = window.get("period")
        if start is None or end is None or not period:
            return {"unsupported_schedule": "window"}
        days_valid, days = _billing_window_days(window)
        if not days_valid:
            return {"unsupported_schedule": "days_of_week"}
        validated_windows.append((window, start, end, days))

    local_priced_at = priced_at.astimezone(schedule_timezone)
    current = local_priced_at.hour * 3600 + local_priced_at.minute * 60 + local_priced_at.second
    for window, start, end, days in validated_windows:
        if _time_in_window(current, start, end):
            if days is not None:
                start_date = local_priced_at.date()
                if start > end and current < end:
                    start_date -= timedelta(days=1)
                if _WEEKDAYS[start_date.weekday()] not in days:
                    continue
            return {
                "pricing_period": str(period),
                "period_selection": "derived_from_priced_at",
                "pricing_window": f"{window.get('start')}-{window.get('end')}",
                "pricing_timezone": timezone_name,
            }
    default_period = schedule.get("default_period") or schedule.get("defaultPeriod")
    if default_period:
        return {
            "pricing_period": str(default_period),
            "period_selection": "derived_from_priced_at",
            "pricing_window": "default",
            "pricing_timezone": timezone_name,
        }
    return {}


def _pricing_period_selection(usage_ledger: Dict[str, Any], card: Dict[str, Any]) -> Dict[str, Any]:
    context = _usage_context(usage_ledger)
    explicit = context.get("pricing_period") or context.get("pricingPeriod")
    if explicit:
        return {"pricing_period": str(explicit), "period_selection": "explicit_context"}
    schedule = _card_billing_schedule(card)
    if not schedule:
        return {}
    priced_at = _datetime_value(context.get("priced_at") or context.get("pricedAt"))
    if priced_at is None:
        return {}
    return _pricing_period_from_schedule(schedule, priced_at)


def _card_pricing_period_matches(usage_ledger: Dict[str, Any], card: Dict[str, Any]) -> bool:
    card_period = _card_pricing_period(card)
    if not card_period:
        return True
    selection = _pricing_period_selection(usage_ledger, card)
    return selection.get("pricing_period") == card_period


def _card_period_rank(usage_ledger: Dict[str, Any], card: Dict[str, Any]) -> int:
    card_period = _card_pricing_period(card)
    if not card_period:
        return 0
    selection = _pricing_period_selection(usage_ledger, card)
    return 1 if selection.get("pricing_period") == card_period else 0


def _pricing_periods_for_cards(cards: Iterable[Dict[str, Any]]) -> List[str]:
    return sorted({period for card in cards if (period := _card_pricing_period(card))})


def _requested_pricing_period_for_cards(usage_ledger: Dict[str, Any], cards: Iterable[Dict[str, Any]]) -> Optional[str]:
    context = _usage_context(usage_ledger)
    explicit = context.get("pricing_period") or context.get("pricingPeriod")
    if explicit:
        return str(explicit)
    for card in cards:
        selection = _pricing_period_selection(usage_ledger, card)
        if selection.get("pricing_period"):
            return str(selection["pricing_period"])
    return None


def _unsupported_billing_schedule_reason(usage_ledger: Dict[str, Any], cards: Iterable[Dict[str, Any]]) -> Optional[str]:
    context = _usage_context(usage_ledger)
    if _datetime_value(context.get("priced_at") or context.get("pricedAt")) is None:
        return None
    for card in cards:
        selection = _pricing_period_selection(usage_ledger, card)
        if selection.get("unsupported_timezone"):
            return str(selection["unsupported_timezone"])
        if selection.get("unsupported_schedule"):
            return str(selection["unsupported_schedule"])
    return None


def _card_identity_matches(usage_ledger: Dict[str, Any], card: Dict[str, Any]) -> bool:
    billed_model = _billed_model(usage_ledger)
    model_matches = card["model"] == billed_model or billed_model in card.get("aliases", [])
    provider_matches = card["provider"] == usage_ledger["provider"]
    surface_matches = "surface" not in card or card["surface"] == usage_ledger["surface"]
    return model_matches and provider_matches and surface_matches


def _card_model_surface_matches(usage_ledger: Dict[str, Any], card: Dict[str, Any]) -> bool:
    billed_model = _billed_model(usage_ledger)
    model_matches = card["model"] == billed_model or billed_model in card.get("aliases", [])
    surface_matches = "surface" not in card or card["surface"] == usage_ledger["surface"]
    return model_matches and surface_matches


def _effective_bound(value: Any) -> Tuple[str, Any]:
    if value is None or value == "":
        return "missing", None
    text = str(value)
    if len(text) == 10:
        try:
            parsed_date = date.fromisoformat(text)
        except ValueError:
            parsed_date = None
        if parsed_date is not None and parsed_date.isoformat() == text:
            return "date", parsed_date
    parsed_timestamp = _datetime_value(value)
    if parsed_timestamp is not None:
        return "timestamp", parsed_timestamp
    return "invalid", None


def _effective_matches(card: Dict[str, Any], priced_at: Optional[str]) -> bool:
    effective = card.get("effective")
    if effective is None:
        return True
    if not isinstance(effective, dict):
        return False

    raw_from = effective.get("from") if "from" in effective else effective.get("from_")
    raw_to = effective.get("to")
    if "from" in effective and "from_" in effective:
        return False
    bounds = []
    for raw_value, is_lower_bound in ((raw_from, True), (raw_to, False)):
        precision, bound = _effective_bound(raw_value)
        if precision == "invalid":
            return False
        if precision != "missing":
            bounds.append((precision, bound, is_lower_bound))

    # Preserve date-only card compatibility when a provider does not supply a
    # timestamp, but never guess whether an instant-bounded card applies.
    if not priced_at:
        return all(precision != "timestamp" for precision, _, _ in bounds)

    usage_timestamp = _datetime_value(priced_at)
    if usage_timestamp is not None:
        usage_date = usage_timestamp.date()
    elif "T" in str(priced_at):
        # A malformed timestamp is not a safe temporal match.
        return False
    else:
        usage_date = _date_value(priced_at)
    if usage_date is None:
        return False

    for precision, bound, is_lower_bound in bounds:
        if precision == "timestamp" and usage_timestamp is None:
            return False
        if precision == "date":
            if is_lower_bound and usage_date < bound:
                return False
            if not is_lower_bound and usage_date > bound:
                return False
        elif is_lower_bound and usage_timestamp < bound:
            return False
        elif not is_lower_bound and usage_timestamp >= bound:
            return False
    return True


def _card_context_matches(usage_ledger: Dict[str, Any], card: Dict[str, Any]) -> bool:
    return _card_context_except_period_matches(usage_ledger, card) and _card_pricing_period_matches(usage_ledger, card)


def _card_context_except_period_matches(usage_ledger: Dict[str, Any], card: Dict[str, Any]) -> bool:
    context = _usage_context(usage_ledger)
    service_tier = context.get("service_tier")
    requested_service_tier = service_tier or "standard"
    region = context.get("region")
    priced_at = context.get("priced_at") or context.get("pricedAt")

    if card.get("service_tier") and card["service_tier"] != requested_service_tier:
        return False
    if region and card.get("region") and card["region"] != region:
        return False
    return _effective_matches(card, priced_at)


def _card_score(usage_ledger: Dict[str, Any], card: Dict[str, Any]) -> int:
    context = _usage_context(usage_ledger)
    requested_service_tier = context.get("service_tier") or "standard"
    score = 0
    if card.get("surface") == usage_ledger["surface"]:
        score += 8
    if card.get("service_tier") == requested_service_tier:
        score += 4
    if context.get("region") and card.get("region") == context["region"]:
        score += 2
    if card.get("effective"):
        score += 1
    if _card_pricing_period(card):
        score += 4
    return score


def _source_priority_score(card: Dict[str, Any], price_source_priority: Optional[Iterable[str]]) -> int:
    if not price_source_priority:
        return 0
    priority = list(price_source_priority)
    source_name = (card.get("source") or {}).get("name")
    if source_name not in priority:
        return 0
    return (len(priority) - priority.index(source_name)) * 100


def _matching_cards_exact(
    usage_ledger: Dict[str, Any],
    price_cards: Iterable[Dict[str, Any]],
    price_source_priority: Optional[Iterable[str]] = None,
) -> List[Dict[str, Any]]:
    cards = list(price_cards)
    scored_cards = []
    period_context_cards = [
        card
        for card in cards
        if _card_identity_matches(usage_ledger, card)
        and _card_pricing_period(card)
        and _card_context_except_period_matches(usage_ledger, card)
    ]
    for index, card in enumerate(cards):
        if not _card_identity_matches(usage_ledger, card):
            continue
        if not _card_context_matches(usage_ledger, card):
            continue
        period_rank = _card_period_rank(usage_ledger, card)
        score = _card_score(usage_ledger, card) + _source_priority_score(card, price_source_priority)
        source_name = str((card.get("source") or {}).get("name", ""))
        scored_cards.append((-period_rank, -score, source_name, str(card.get("id", "")), index, card))
    if period_context_cards and scored_cards and not any(item[0] == -1 for item in scored_cards):
        unsupported_reason = _unsupported_billing_schedule_reason(usage_ledger, period_context_cards)
        requested_period = _requested_pricing_period_for_cards(usage_ledger, period_context_cards)
        if unsupported_reason or requested_period:
            return []
    return [item[-1] for item in sorted(scored_cards, key=lambda item: item[:-1])]


def _matching_cards(
    usage_ledger: Dict[str, Any],
    price_cards: Iterable[Dict[str, Any]],
    price_source_priority: Optional[Iterable[str]] = None,
) -> List[Dict[str, Any]]:
    cards = list(price_cards)
    exact = _matching_cards_exact(usage_ledger, cards, price_source_priority)
    context = _usage_context(usage_ledger)
    if usage_ledger.get("provider") != "openai" or context.get("service_tier") != "fast":
        return exact
    exact_fast = [card for card in exact if card.get("service_tier") == "fast"]
    if exact_fast:
        return exact_fast
    fallback_usage_ledger = {
        **usage_ledger,
        "context": {**context, "service_tier": "priority"},
    }
    return [
        card
        for card in _matching_cards_exact(fallback_usage_ledger, cards, price_source_priority)
        if card.get("service_tier") == "priority"
    ]


def _service_tier_fallback_metadata(usage_ledger: Dict[str, Any], card: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    context = _usage_context(usage_ledger)
    if (
        usage_ledger.get("provider") == "openai"
        and context.get("service_tier") == "fast"
        and card.get("service_tier") == "priority"
    ):
        return {
            "requested": "fast",
            "priced_as": "priority",
            "fallback": True,
        }
    return None


def _price_lookup_cache_key(
    usage_ledger: Dict[str, Any],
    source_priority: Iterable[str],
) -> tuple[Any, ...]:
    context = _usage_context(usage_ledger)
    return (
        usage_ledger.get("provider"),
        usage_ledger.get("surface"),
        _billed_model(usage_ledger),
        context.get("service_tier") or "",
        context.get("region") or "",
        context.get("pricing_period") or context.get("pricingPeriod") or "",
        context.get("priced_at") or context.get("pricedAt") or "",
        tuple(source_priority),
    )


def _total_input_tokens(usage_ledger: Dict[str, Any]) -> Decimal:
    context = _usage_context(usage_ledger)
    if context.get("total_input_tokens") is not None:
        return _decimal(context["total_input_tokens"])
    total = Decimal("0")
    for component in usage_ledger.get("components", []):
        if component.get("unit") == "token" and str(component.get("name", "")).startswith("input_"):
            total += _decimal(component.get("quantity", "0"))
    return total


def _conditions_match(usage_ledger: Dict[str, Any], price_component: Dict[str, Any]) -> bool:
    conditions = price_component.get("conditions") or {}
    if not conditions:
        return True
    total_input = _total_input_tokens(usage_ledger)
    if conditions.get("min_total_input_tokens") is not None and total_input < _decimal(conditions["min_total_input_tokens"]):
        return False
    if conditions.get("max_total_input_tokens") is not None and total_input > _decimal(conditions["max_total_input_tokens"]):
        return False
    return True


def _candidate_price_components(
    price_cards: Iterable[Dict[str, Any]],
    component: Dict[str, Any],
) -> List[Dict[str, Any]]:
    matches = []
    for card in price_cards:
        for price_component in card["components"]:
            if (
                price_component["usage_component"] == component["name"]
                and price_component["unit"] == component["unit"]
            ):
                matches.append({"card": card, "price_component": price_component})

    return matches


def _find_price_components(
    usage_ledger: Dict[str, Any],
    price_cards: Iterable[Dict[str, Any]],
    component: Dict[str, Any],
) -> List[Dict[str, Any]]:
    return [
        match
        for match in _candidate_price_components(price_cards, component)
        if _conditions_match(usage_ledger, match["price_component"])
    ]


def _authoritative_source_candidates(
    usage_ledger: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    source_priority: Iterable[str],
) -> List[Dict[str, Any]]:
    priority = list(source_priority)
    if not candidates or not priority:
        return candidates
    source_name = str((candidates[0]["card"].get("source") or {}).get("name", ""))
    if source_name not in priority:
        return candidates
    metadata = candidates[0]["card"].get("metadata") or {}
    if not isinstance(metadata.get("official_snapshot"), dict):
        return candidates
    source_candidates = [
        candidate
        for candidate in candidates
        if str((candidate["card"].get("source") or {}).get("name", "")) == source_name
    ]
    if not any(candidate["price_component"].get("conditions") for candidate in source_candidates):
        return candidates
    if any(_conditions_match(usage_ledger, candidate["price_component"]) for candidate in source_candidates):
        return candidates
    return source_candidates


def _warning_identity_metadata(usage_ledger: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "provider": usage_ledger.get("provider"),
        "surface": usage_ledger.get("surface"),
        "model": _billed_model(usage_ledger),
    }


def _alias_inferred_warning(requested_model: str, billed_model: str) -> Dict[str, Any]:
    return {
        "code": "alias_inferred",
        "message": f"Resolved model alias {requested_model} to billed model {billed_model}.",
        "metadata": {
            "requested_model": requested_model,
            "billed_model": billed_model,
        },
    }


def _unpriced_component_metadata(usage_ledger: Dict[str, Any], component: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "component": component.get("name"),
        "unit": component.get("unit"),
        "model": _billed_model(usage_ledger),
    }


def _is_tool_or_feature_component(component_name: str) -> bool:
    return component_name in _TOOL_OR_FEATURE_COMPONENTS


def _unpriced_component_warning(usage_ledger: Dict[str, Any], component: Dict[str, Any]) -> Dict[str, Any]:
    component_name = component["name"]
    if _is_tool_or_feature_component(component_name):
        return {
            "code": "tool_component_unpriced",
            "message": (
                f"No price found for tool or feature component {component_name} "
                f"on model {_billed_model(usage_ledger)}."
            ),
            "metadata": _unpriced_component_metadata(usage_ledger, component),
        }
    return {
        "code": "component_unpriced",
        "message": f"No price found for {component_name} ({component['unit']}).",
        "metadata": _unpriced_component_metadata(usage_ledger, component),
    }


def _long_context_rule_missing_warning(
    usage_ledger: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    component: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    if not candidates or not any(match["price_component"].get("conditions") for match in candidates):
        return None
    total_input = _format_decimal(_total_input_tokens(usage_ledger))
    return {
        "code": "long_context_rule_missing",
        "message": f"No long-context pricing rule matched {component['name']} at {total_input} input tokens.",
        "metadata": {
            "component": component.get("name"),
            "unit": component.get("unit"),
            "total_input_tokens": total_input,
        },
    }


def _source_capability_warning(
    matching_cards: List[Dict[str, Any]],
    component: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    component_name = component["name"]
    for card in matching_cards:
        if _source_capability_unsupported(card, component_name):
            source = card.get("source") if isinstance(card.get("source"), dict) else {}
            return {
                "code": "source_capability_unsupported",
                "message": f"Price source {source.get('name', card.get('id', 'unknown'))} explicitly does not price {component_name}.",
                "metadata": {
                    "component": component_name,
                    "unit": component["unit"],
                    "price_card_id": card.get("id"),
                    "source": source.get("name"),
                },
            }
    return None


def _source_capability_unsupported(card: Dict[str, Any], component_name: str) -> bool:
    metadata = card.get("metadata") if isinstance(card.get("metadata"), dict) else {}
    capabilities = metadata.get("source_capabilities")
    if not isinstance(capabilities, dict):
        return False
    unsupported = capabilities.get("unsupported_components") or capabilities.get("unsupportedComponents") or []
    return component_name in unsupported


def _model_name_looks_gemini(value: Any) -> bool:
    text = str(value or "").lower()
    return text.startswith("gemini-") or text.startswith("google/gemini-")


def _model_name_looks_gemini_live_translate(value: Any) -> bool:
    text = str(value or "").lower()
    return text in {"gemini-3.5-live-translate-preview", "google/gemini-3.5-live-translate-preview"}


def _model_name_looks_xai(value: Any) -> bool:
    text = str(value or "").lower()
    return text.startswith("grok-") or text.startswith("xai/")


OUTPUT_PRICE_FALLBACK_COMPONENTS = [
    "output_text_tokens",
    "output_audio_tokens",
    "output_image_tokens",
    "output_video_tokens",
]

def _output_price_fallback_component_candidates(
    usage_ledger: Dict[str, Any],
    preferred: Optional[Iterable[str]] = None,
) -> List[str]:
    candidates: List[str] = []
    for component_name in preferred or []:
        if component_name in OUTPUT_PRICE_FALLBACK_COMPONENTS and component_name not in candidates:
            candidates.append(component_name)
    for component in usage_ledger.get("components", []):
        component_name = component.get("name")
        if (
            component.get("unit") == "token"
            and component_name in OUTPUT_PRICE_FALLBACK_COMPONENTS
            and _decimal(component.get("quantity", "0")) > 0
            and component_name not in candidates
        ):
            candidates.append(component_name)
    for component_name in OUTPUT_PRICE_FALLBACK_COMPONENTS:
        if component_name not in candidates:
            candidates.append(component_name)
    return candidates


def _gemini_thinking_priced_as_output_applies(
    usage_ledger: Dict[str, Any],
    card: Dict[str, Any],
) -> bool:
    provider = str(usage_ledger.get("provider") or card.get("provider") or "").lower()
    surface = str(usage_ledger.get("surface") or card.get("surface") or "").lower()
    if provider not in {"google", "vertex", "google-vertex"} and "gemini." not in surface:
        return False
    model_names = [_billed_model(usage_ledger), card.get("model"), *card.get("aliases", [])]
    return any(_model_name_looks_gemini(model_name) for model_name in model_names)


def _gemini_thinking_output_component_candidates(usage_ledger: Dict[str, Any], card: Dict[str, Any]) -> List[str]:
    surface = str(usage_ledger.get("surface") or card.get("surface") or "").lower()
    model_names = [_billed_model(usage_ledger), card.get("model"), *card.get("aliases", [])]
    is_live_translate = surface == "google.gemini.live" and any(_model_name_looks_gemini_live_translate(model_name) for model_name in model_names)
    preferred = ["output_audio_tokens"] if is_live_translate else None
    return _output_price_fallback_component_candidates(usage_ledger, preferred)


def _gemini_thinking_output_component_names(
    usage_ledger: Dict[str, Any],
    matching_cards: List[Dict[str, Any]],
) -> List[str]:
    component_names: List[str] = []
    for card in matching_cards:
        if not _gemini_thinking_priced_as_output_applies(usage_ledger, card):
            continue
        for component_name in _gemini_thinking_output_component_candidates(usage_ledger, card):
            if component_name not in component_names:
                component_names.append(component_name)
    return component_names


def _gemini_thinking_priced_as_output_matches(
    usage_ledger: Dict[str, Any],
    matching_cards: List[Dict[str, Any]],
    component: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if component.get("name") != "output_reasoning_tokens" or component.get("unit") != "token":
        return []
    matches: List[Dict[str, Any]] = []
    for output_component_name in _gemini_thinking_output_component_names(usage_ledger, matching_cards):
        output_component = {"name": output_component_name, "unit": component.get("unit")}
        for match in _find_price_components(usage_ledger, matching_cards, output_component):
            card = match["card"]
            if not _gemini_thinking_priced_as_output_applies(usage_ledger, card):
                continue
            if output_component_name not in _gemini_thinking_output_component_candidates(usage_ledger, card):
                continue
            if _source_capability_unsupported(card, "output_reasoning_tokens"):
                continue
            price_component = dict(match["price_component"])
            price_component["usage_component"] = "output_reasoning_tokens"
            price_component.setdefault("notes", "Gemini thinking tokens are priced at the output-token rate.")
            matches.append(
                {
                    "card": card,
                    "price_component": price_component,
                    "component_metadata": {
                        "pricing_policy": "gemini_thinking_tokens_priced_as_output_tokens",
                        "priced_as_component": output_component_name,
                    },
                }
            )
        if matches:
            return matches
    return []


def _xai_reasoning_priced_as_output_applies(
    usage_ledger: Dict[str, Any],
    card: Dict[str, Any],
) -> bool:
    provider = str(usage_ledger.get("provider") or card.get("provider") or "").lower()
    surface = str(usage_ledger.get("surface") or card.get("surface") or "").lower()
    if provider != "xai" and not surface.startswith("xai."):
        return False
    model_names = [_billed_model(usage_ledger), card.get("model"), *card.get("aliases", [])]
    return any(_model_name_looks_xai(model_name) for model_name in model_names) or provider == "xai"


def _xai_reasoning_priced_as_output_matches(
    usage_ledger: Dict[str, Any],
    matching_cards: List[Dict[str, Any]],
    component: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if component.get("name") != "output_reasoning_tokens" or component.get("unit") != "token":
        return []
    output_component = {"name": "output_text_tokens", "unit": component.get("unit")}
    matches: List[Dict[str, Any]] = []
    for match in _find_price_components(usage_ledger, matching_cards, output_component):
        card = match["card"]
        if not _xai_reasoning_priced_as_output_applies(usage_ledger, card):
            continue
        if _source_capability_unsupported(card, "output_reasoning_tokens"):
            continue
        price_component = dict(match["price_component"])
        price_component["usage_component"] = "output_reasoning_tokens"
        price_component.setdefault("notes", "xAI reasoning tokens are priced at the output-token rate.")
        matches.append(
            {
                "card": card,
                "price_component": price_component,
                "component_metadata": {
                    "pricing_policy": "xai_reasoning_tokens_priced_as_output_tokens",
                    "priced_as_component": "output_text_tokens",
                },
            }
        )
    return matches


def _generic_reasoning_priced_as_output_matches(
    usage_ledger: Dict[str, Any],
    matching_cards: List[Dict[str, Any]],
    component: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if component.get("name") != "output_reasoning_tokens" or component.get("unit") != "token":
        return []
    for output_component_name in _output_price_fallback_component_candidates(usage_ledger):
        output_component = {"name": output_component_name, "unit": component.get("unit")}
        matches: List[Dict[str, Any]] = []
        for match in _find_price_components(usage_ledger, matching_cards, output_component):
            card = match["card"]
            if _source_capability_unsupported(card, "output_reasoning_tokens"):
                continue
            price_component = dict(match["price_component"])
            price_component["usage_component"] = "output_reasoning_tokens"
            price_component.setdefault("notes", "Reasoning tokens are priced at the output-token rate by default.")
            matches.append(
                {
                    "card": card,
                    "price_component": price_component,
                    "component_metadata": {
                        "pricing_policy": "reasoning_tokens_priced_as_output_tokens",
                        "priced_as_component": output_component_name,
                        "fallback_reason": "no_separate_reasoning_price",
                    },
                }
            )
        if matches:
            return matches
    return []


def _output_reasoning_priced_as_output_matches(
    usage_ledger: Dict[str, Any],
    matching_cards: List[Dict[str, Any]],
    component: Dict[str, Any],
) -> List[Dict[str, Any]]:
    provider_specific_matches = [
        *_gemini_thinking_priced_as_output_matches(usage_ledger, matching_cards, component),
        *_xai_reasoning_priced_as_output_matches(usage_ledger, matching_cards, component),
    ]
    if provider_specific_matches:
        return provider_specific_matches
    return _generic_reasoning_priced_as_output_matches(usage_ledger, matching_cards, component)


def _has_price_card_for_usage(
    usage_ledger: Dict[str, Any],
    price_cards: Iterable[Dict[str, Any]],
) -> bool:
    return any(_card_identity_matches(usage_ledger, card) for card in price_cards)


def _has_price_card_for_model_surface(
    usage_ledger: Dict[str, Any],
    price_cards: Iterable[Dict[str, Any]],
) -> bool:
    return any(_card_model_surface_matches(usage_ledger, card) for card in price_cards)


def _unknown_provider_warning(usage_ledger: Dict[str, Any]) -> Dict[str, Any]:
    provider = usage_ledger.get("provider")
    return {
        "code": "unknown_provider",
        "message": f"No price card found for provider {provider}.",
        "metadata": _warning_identity_metadata(usage_ledger),
    }


def _unknown_model_warning(usage_ledger: Dict[str, Any]) -> Dict[str, Any]:
    model = _billed_model(usage_ledger)
    return {
        "code": "unknown_model",
        "message": f"No price card found for {model}.",
        "metadata": _warning_identity_metadata(usage_ledger),
    }


def _no_matching_card_warning(
    usage_ledger: Dict[str, Any],
    price_cards: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    context = _usage_context(usage_ledger)
    identity_cards = [card for card in price_cards if _card_identity_matches(usage_ledger, card)]
    service_tier = context.get("service_tier")
    if service_tier and identity_cards and all(card.get("service_tier") and card.get("service_tier") != service_tier for card in identity_cards):
        return {
            "code": "service_tier_unsupported",
            "message": f"No price card found for service tier {service_tier}.",
            "metadata": {
                "model": _billed_model(usage_ledger),
                "service_tier": service_tier,
            },
        }
    period_cards = [
        card
        for card in identity_cards
        if _card_pricing_period(card)
        and _card_context_except_period_matches(usage_ledger, card)
    ]
    if period_cards:
        unsupported_reason = _unsupported_billing_schedule_reason(usage_ledger, period_cards)
        if unsupported_reason:
            return {
                "code": "billing_schedule_unsupported",
                "message": f"Billing schedule {unsupported_reason} is not supported.",
                "metadata": {
                    **_warning_identity_metadata(usage_ledger),
                    "timezone": unsupported_reason,
                },
            }
        requested_period = _requested_pricing_period_for_cards(usage_ledger, period_cards)
        if requested_period:
            return {
                "code": "pricing_period_unsupported",
                "message": f"No price card found for pricing period {requested_period}.",
                "metadata": {
                    **_warning_identity_metadata(usage_ledger),
                    "pricing_period": requested_period,
                },
            }
        return {
            "code": "pricing_period_required",
            "message": "Pricing period is required for period-specific price cards.",
            "metadata": {
                **_warning_identity_metadata(usage_ledger),
                "pricing_periods": _pricing_periods_for_cards(period_cards),
            },
        }
    priced_at = _date_part(context.get("priced_at") or context.get("pricedAt"))
    if priced_at and identity_cards and not any(_effective_matches(card, priced_at) for card in identity_cards):
        return {
            "code": "historical_price_missing",
            "message": f"No price card effective for {priced_at}.",
            "metadata": {
                "model": _billed_model(usage_ledger),
                "priced_at": priced_at,
            },
        }
    return {
        "code": "price_not_found",
        "message": f"No price card matched provider, surface, model, and context for {_billed_model(usage_ledger)}.",
        "metadata": _warning_identity_metadata(usage_ledger),
    }


def _usage_metadata_field_warnings(
    usage_ledger: Dict[str, Any],
) -> List[Dict[str, Any]]:
    metadata = usage_ledger.get("metadata") if isinstance(usage_ledger.get("metadata"), dict) else {}
    warnings: List[Dict[str, Any]] = []
    for field in metadata.get("ignored_usage_fields") or []:
        field_name = str(field)
        warnings.append(
            {
                "code": "usage_field_ignored",
                "message": f"Usage field {field_name} was not mapped to a cost component.",
                "path": field_name,
                "metadata": {"field": field_name},
            }
        )
    for field in metadata.get("missing_usage_fields") or []:
        field_name = str(field)
        warnings.append(
            {
                "code": "usage_missing",
                "message": f"Usage field {field_name} was missing; RunCost could not extract billable usage from it.",
                "path": field_name,
                "metadata": {"field": field_name},
            }
        )
    for field in metadata.get("inclusive_usage_fields") or []:
        field_name = str(field)
        warnings.append(
            {
                "code": "inclusive_usage_ambiguous",
                "message": f"Usage field {field_name} appears inclusive; RunCost priced component fields instead.",
                "path": field_name,
                "metadata": {"field": field_name},
            }
        )
    return warnings


def _policy_matches(
    policy: Dict[str, Any],
    usage_ledger: Dict[str, Any],
    component: Dict[str, Any],
) -> bool:
    match = policy.get("match", {})
    billed_model = _billed_model(usage_ledger)

    if match.get("provider") and match["provider"] != usage_ledger["provider"]:
        return False
    if match.get("surface") and match["surface"] != usage_ledger["surface"]:
        return False
    if match.get("model") and match["model"] != billed_model:
        return False
    context = _usage_context(usage_ledger)
    if match.get("service_tier") and match["service_tier"] != context.get("service_tier"):
        return False
    if match.get("region") and match["region"] != context.get("region"):
        return False
    if match.get("components") and component["name"] not in match["components"]:
        return False
    if match.get("exclude_components") and component["name"] in match["exclude_components"]:
        return False
    requested_tags = match.get("tags")
    if isinstance(requested_tags, dict) and requested_tags:
        attribution = _normalize_attribution(usage_ledger.get("attribution"))
        actual_tags = attribution.get("tags") if isinstance(attribution.get("tags"), dict) else {}
        if any(actual_tags.get(str(key)) != str(value) for key, value in requested_tags.items()):
            return False
    return True


def _apply_discounts(
    cost: str,
    policies: Iterable[Dict[str, Any]],
    usage_ledger: Dict[str, Any],
    component: Dict[str, Any],
    discount_eligible: bool,
) -> Dict[str, Any]:
    if not discount_eligible:
        return {"cost": cost, "applied": []}

    current = cost
    applied: List[Dict[str, str]] = []
    sorted_policies = sorted(policies, key=lambda policy: policy.get("precedence", 100))

    for policy in sorted_policies:
        if not _policy_matches(policy, usage_ledger, component):
            continue

        before = current
        adjustment = policy["adjustment"]
        if adjustment["type"] == "multiplier":
            current = _multiply_divide(current, adjustment["value"], "1")
        elif adjustment["type"] == "percentage_discount":
            multiplier = _subtract("1", _multiply_divide(adjustment["value"], "1", "100"))
            current = _multiply_divide(current, multiplier, "1")
        elif adjustment["type"] == "percentage_markup":
            multiplier = _add("1", _multiply_divide(adjustment["value"], "1", "100"))
            current = _multiply_divide(current, multiplier, "1")

        applied.append(
            {
                "policy_id": policy["id"],
                "component": component["name"],
                "amount": _subtract(before, current),
            }
        )

    return {"cost": current, "applied": applied}


def _discount_not_applied_warnings(
    policies: Iterable[Dict[str, Any]],
    applied_discounts: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    applied_policy_ids = {discount["policy_id"] for discount in applied_discounts}
    warnings = []
    for policy in policies:
        metadata = policy.get("metadata") if isinstance(policy.get("metadata"), dict) else {}
        if metadata.get("warn_if_unapplied") is not True:
            continue
        policy_id = policy["id"]
        if policy_id in applied_policy_ids:
            continue
        warnings.append(
            {
                "code": "discount_not_applied",
                "message": f"Discount policy {policy_id} did not apply to any priced component.",
                "metadata": {
                    "policy_id": policy_id,
                },
            }
        )
    return warnings


def _stale_after_days(usage_ledger: Dict[str, Any], stale_after_days: Optional[int]) -> Optional[int]:
    if stale_after_days is not None:
        return int(stale_after_days)
    context = _usage_context(usage_ledger)
    value = context.get("stale_after_days") or context.get("price_stale_after_days")
    return int(value) if value is not None else None


def _stale_price_warning(
    usage_ledger: Dict[str, Any],
    card: Dict[str, Any],
    stale_after_days: Optional[int],
) -> Optional[Dict[str, Any]]:
    threshold = _stale_after_days(usage_ledger, stale_after_days)
    if threshold is None:
        return None
    context = _usage_context(usage_ledger)
    priced_at = _date_value(context.get("priced_at") or context.get("pricedAt"))
    retrieved_at = _date_value((card.get("source") or {}).get("retrieved_at"))
    if priced_at is None or retrieved_at is None:
        return None
    age_days = (priced_at - retrieved_at).days
    if age_days <= threshold:
        return None
    source_name = (card.get("source") or {}).get("name", "unknown")
    return {
        "code": "price_stale",
        "message": f"Price source {source_name} is {age_days} days old; threshold is {threshold} days.",
        "metadata": {
            "source": source_name,
            "age_days": age_days,
            "threshold_days": threshold,
            "retrieved_at": (card.get("source") or {}).get("retrieved_at"),
            "priced_at": _date_part(_usage_context(usage_ledger).get("priced_at")),
        },
    }


def _provider_reported_warning(
    total: str,
    provider_reported_cost: Optional[Any],
    provider_reported_cost_mode: str,
) -> Optional[Dict[str, Any]]:
    if provider_reported_cost is None or provider_reported_cost_mode != "compare":
        return None
    provider_total = _format_decimal(_decimal(provider_reported_cost))
    if provider_total == total:
        return None
    return {
        "code": "provider_reported_cost_mismatch",
        "message": f"Provider reported cost {provider_total} differs from calculated total {total}.",
        "metadata": {
            "provider_reported_cost": provider_total,
            "calculated_total": total,
        },
    }


def _xai_provider_reported_cost(
    response: Dict[str, Any],
    usage_ledger: Dict[str, Any],
) -> Optional[str]:
    provider = str(usage_ledger.get("provider") or "").lower()
    if provider != "xai":
        return None
    payload = _openai_responses_payload(response)
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    ticks = usage.get("cost_in_usd_ticks", usage.get("costInUsdTicks"))
    if ticks is None:
        return None
    return _multiply_divide(ticks, "1", "10000000000")


def _provider_reported_cost_from_raw_response(
    response: Dict[str, Any],
    usage_ledger: Dict[str, Any],
) -> Optional[str]:
    return _xai_provider_reported_cost(response, usage_ledger)


def _apply_provider_reported_cost_use(
    total: str,
    components: List[Dict[str, Any]],
    warnings: List[Dict[str, Any]],
    provider_reported_cost: Optional[Any],
    provider_reported_cost_mode: str,
) -> str:
    if provider_reported_cost is None or provider_reported_cost_mode != "use":
        return total
    provider_total = _format_decimal(_decimal(provider_reported_cost))
    adjustment = _subtract(provider_total, total)
    if adjustment != "0":
        components.append(
            {
                "name": "custom_units",
                "quantity": adjustment,
                "unit": "usd",
                "unit_price": "1",
                "cost": adjustment,
                "price_card_id": "__provider_reported_cost__",
                "discount_eligible": False,
                "metadata": {
                    "reason": "provider_reported_cost_reconciliation",
                    "calculated_total": total,
                    "provider_reported_cost": provider_total,
                },
            }
        )
    warnings.append(
        {
            "code": "provider_reported_cost_used",
            "message": f"Provider reported cost {provider_total} used as authoritative total.",
            "metadata": {
                "provider_reported_cost": provider_total,
                "calculated_total": total,
            },
        }
    )
    return provider_total


def _price_source_disagreement_warning(
    matches: List[Dict[str, Any]],
    component: Dict[str, Any],
    price_source_priority: Optional[Iterable[str]],
) -> Optional[Dict[str, Any]]:
    if price_source_priority or len(matches) < 2:
        return None
    unit_prices = set()
    for match in matches:
        price = match["price_component"]["price"]
        unit_prices.add(_multiply_divide(price["amount"], "1", price["per"]))
    if len(unit_prices) <= 1:
        return None
    chosen = matches[0]["card"]["id"]
    return {
        "code": "price_source_disagreement",
        "message": f"Multiple price sources disagree for {component['name']}; using {chosen}.",
        "metadata": {
            "component": component.get("name"),
            "selected_price_card_id": chosen,
            "candidate_price_card_ids": [match["card"]["id"] for match in matches],
        },
    }


def _debug_trace_enabled(value: Any) -> bool:
    return value is True


def _new_debug_trace() -> Dict[str, Any]:
    return {
        "schema_version": "0.1",
        "decisions": [],
        "summary": {
            "priced_components": 0,
            "unpriced_components": 0,
            "warnings": 0,
            "applied_discounts": 0,
        },
    }


def calculate_cost(
    *,
    usage_ledger: Dict[str, Any],
    price_cards: Union[Iterable[Dict[str, Any]], CompiledPriceCatalog],
    discount_policies: Optional[Iterable[Dict[str, Any]]] = None,
    mode: str = "compatibility",
    stale_after_days: Optional[int] = None,
    provider_reported_cost: Optional[Any] = None,
    provider_reported_cost_mode: str = "compare",
    price_source_priority: Optional[Iterable[str]] = None,
    debug_trace: bool = False,
) -> Dict[str, Any]:
    policies = list(discount_policies or [])
    compiled_catalog = compile_price_catalog(price_cards)
    price_cards_list = compiled_catalog.price_cards
    source_priority = list(price_source_priority or [])
    components = []
    warnings = _usage_metadata_field_warnings(usage_ledger)
    applied_discounts = []
    sources_by_name: Dict[str, Dict[str, Any]] = {}
    trace = _new_debug_trace() if _debug_trace_enabled(debug_trace) else None
    total = "0"
    resolved_billed_model = _billed_model(usage_ledger)
    alias_resolution = usage_ledger["model"].get("alias_resolution", "none")
    warned_unknown_model = set()
    warned_unknown_provider = set()
    warned_no_matching_card = set()
    warned_alias_inferred = False
    warned_stale_cards = set()
    service_tier_fallback_card_ids = set()
    price_lookup_cache: Dict[tuple[Any, ...], Dict[str, Any]] = {}

    for component in usage_ledger["components"]:
        component_usage_ledger = _usage_ledger_for_component(usage_ledger, component)
        component_billed_model = _billed_model(component_usage_ledger)
        component_warning_key = (
            component_usage_ledger["provider"],
            component_usage_ledger["surface"],
            component_billed_model,
        )
        lookup_key = _price_lookup_cache_key(component_usage_ledger, source_priority)
        lookup = price_lookup_cache.get(lookup_key)
        if lookup is None:
            identity_candidates = compiled_catalog.identity_candidates(component_usage_ledger)
            model_candidates = compiled_catalog.model_candidates(component_usage_ledger)
            lookup = {
                "has_model_card": _has_price_card_for_usage(component_usage_ledger, identity_candidates),
                "matching_cards": _matching_cards(component_usage_ledger, identity_candidates, source_priority),
                "model_surface_card_exists": _has_price_card_for_model_surface(component_usage_ledger, model_candidates),
                "identity_candidates": identity_candidates,
            }
            price_lookup_cache[lookup_key] = lookup
        has_model_card = lookup["has_model_card"]
        matching_cards = lookup["matching_cards"]
        model_surface_card_exists = lookup["model_surface_card_exists"]
        if trace is not None:
            trace["decisions"].append(
                {
                    "type": "price_card_candidates",
                    "component": component["name"],
                    "model": component_billed_model,
                    "candidate_price_card_ids": [card["id"] for card in matching_cards],
                    "source_priority": source_priority,
                }
            )

        if not has_model_card:
            if model_surface_card_exists:
                if component_warning_key not in warned_unknown_provider:
                    warnings.append(_unknown_provider_warning(component_usage_ledger))
                    warned_unknown_provider.add(component_warning_key)
            elif component_warning_key not in warned_unknown_model:
                warnings.append(_unknown_model_warning(component_usage_ledger))
                warned_unknown_model.add(component_warning_key)
            if trace is not None:
                trace["summary"]["unpriced_components"] += 1
            continue

        if not matching_cards:
            if component_warning_key not in warned_no_matching_card:
                warnings.append(_no_matching_card_warning(component_usage_ledger, lookup["identity_candidates"]))
                warned_no_matching_card.add(component_warning_key)
            if trace is not None:
                trace["summary"]["unpriced_components"] += 1
            continue

        candidates = _authoritative_source_candidates(
            component_usage_ledger,
            _candidate_price_components(matching_cards, component),
            source_priority,
        )
        matches = [
            match
            for match in candidates
            if _conditions_match(component_usage_ledger, match["price_component"])
        ]
        if not matches and not candidates:
            matches = _output_reasoning_priced_as_output_matches(component_usage_ledger, matching_cards, component)
        if not matches:
            capability_warning = _source_capability_warning(matching_cards, component)
            long_context_warning = _long_context_rule_missing_warning(component_usage_ledger, candidates, component)
            if capability_warning:
                warnings.append(capability_warning)
            elif long_context_warning:
                warnings.append(long_context_warning)
            else:
                warnings.append(_unpriced_component_warning(component_usage_ledger, component))
            if trace is not None:
                trace["summary"]["unpriced_components"] += 1
            continue

        disagreement_warning = _price_source_disagreement_warning(matches, component, price_source_priority)
        if disagreement_warning:
            warnings.append(disagreement_warning)
        match = matches[0]
        card = match["card"]
        price_component = match["price_component"]
        component_metadata = dict(match.get("component_metadata") or {})
        service_tier_resolution = _service_tier_fallback_metadata(component_usage_ledger, card)
        if service_tier_resolution:
            component_metadata["service_tier_resolution"] = service_tier_resolution
            service_tier_fallback_card_ids.add(card["id"])
        period_selection = _pricing_period_selection(component_usage_ledger, card)
        period_metadata = {
            key: value
            for key, value in period_selection.items()
            if key in {"pricing_period", "period_selection", "pricing_window", "pricing_timezone"}
            and period_selection.get("pricing_period") == _card_pricing_period(card)
        }
        if trace is not None:
            decision = {
                "type": "price_component_match",
                "component": component["name"],
                "candidate_price_card_ids": [candidate["card"]["id"] for candidate in matches],
                "selected_price_card_id": card["id"],
                "selected_source": card["source"]["name"],
            }
            decision.update(period_metadata)
            if service_tier_resolution:
                decision["service_tier_resolution"] = service_tier_resolution
            trace["decisions"].append(decision)
        if card["model"] != component_billed_model and component_billed_model in card.get("aliases", []):
            previous_billed_model = component_billed_model
            if not _component_billing_model(component):
                resolved_billed_model = card["model"]
                if alias_resolution == "none":
                    alias_resolution = "source_exact"
                    if not warned_alias_inferred:
                        warnings.append(_alias_inferred_warning(previous_billed_model, resolved_billed_model))
                        warned_alias_inferred = True
                if trace is not None:
                    trace["decisions"].append(
                        {
                            "type": "model_alias_resolution",
                            "from": previous_billed_model,
                            "to": resolved_billed_model,
                            "price_card_id": card["id"],
                            "resolution": alias_resolution,
                        }
                    )

        price = price_component["price"]
        base_cost = _multiply_divide(component["quantity"], price["amount"], price["per"])
        discount_eligible = price_component.get("discount_eligible", True)
        discounted = _apply_discounts(
            base_cost,
            policies,
            component_usage_ledger,
            component,
            discount_eligible,
        )

        applied_discounts.extend(discounted["applied"])
        if trace is not None:
            for applied in discounted["applied"]:
                trace["decisions"].append(
                    {
                        "type": "discount_application",
                        "component": applied["component"],
                        "policy_id": applied["policy_id"],
                        "amount": applied["amount"],
                    }
                )
        total = _add(total, discounted["cost"])
        sources_by_name[card["source"]["name"]] = card["source"]
        if card["id"] not in warned_stale_cards:
            stale_warning = _stale_price_warning(component_usage_ledger, card, stale_after_days)
            if stale_warning:
                warnings.append(stale_warning)
                warned_stale_cards.add(card["id"])

        cost_component = {
            "name": component["name"],
            "quantity": component["quantity"],
            "unit": component["unit"],
            "unit_price": _multiply_divide(price["amount"], "1", price["per"]),
            "cost": discounted["cost"],
            "price_card_id": card["id"],
            "discount_eligible": discount_eligible,
        }
        output_metadata = {}
        if isinstance(component.get("metadata"), dict):
            output_metadata.update(component["metadata"])
        if period_metadata:
            output_metadata.update(period_metadata)
        if component_metadata:
            output_metadata.update(component_metadata)
        if output_metadata:
            cost_component["metadata"] = output_metadata
        components.append(cost_component)
        if trace is not None:
            trace["summary"]["priced_components"] += 1

    model = usage_ledger["model"]
    total = _apply_provider_reported_cost_use(
        total,
        components,
        warnings,
        provider_reported_cost,
        provider_reported_cost_mode,
    )
    provider_warning = _provider_reported_warning(
        total,
        provider_reported_cost,
        provider_reported_cost_mode,
    )
    if provider_warning:
        warnings.append(provider_warning)
    warnings.extend(_discount_not_applied_warnings(policies, applied_discounts))
    components = _ordered_cost_components(components)
    price_sources = _ordered_price_sources(sources_by_name.values())
    applied_discounts = _ordered_applied_discounts(applied_discounts)
    warnings = _ordered_warnings(warnings)
    if trace is not None:
        for warning in warnings:
            trace["decisions"].append(
                {
                    "type": "warning",
                    "warning_code": warning["code"],
                    "message": warning["message"],
                }
            )
        trace["summary"]["warnings"] = len(warnings)
        trace["summary"]["applied_discounts"] = len(applied_discounts)
    result = {
        "schema_version": "0.1",
        "provider": usage_ledger["provider"],
        "surface": usage_ledger["surface"],
        "model": {
            "requested": model["requested"],
            "returned": model.get("returned") or "",
            "billed": resolved_billed_model,
            "alias_resolution": alias_resolution,
        },
        "currency": "USD",
        "components": components,
        "total": total,
        "price_sources": price_sources,
        "applied_discounts": applied_discounts,
        "warnings": warnings,
    }
    if trace is not None:
        result["debug_trace"] = trace
    if isinstance(usage_ledger.get("metadata"), dict) and usage_ledger["metadata"]:
        result["metadata"] = dict(usage_ledger["metadata"])
    if service_tier_fallback_card_ids:
        result.setdefault("metadata", {})["service_tier_resolution"] = {
            "requested": "fast",
            "priced_as": "priority",
            "fallback": True,
            "price_card_ids": sorted(service_tier_fallback_card_ids),
        }
    normalized_attribution = _normalize_attribution(usage_ledger.get("attribution"))
    if normalized_attribution:
        result["attribution"] = normalized_attribution
    if mode == "strict" and warnings:
        raise ValueError(f"strict mode cost calculation failed: {warnings[0]['code']}")
    return result


def _source_key(source: Dict[str, Any]) -> str:
    return "|".join(
        [
            str(source.get("name", "")),
            str(source.get("url", "")),
            str(source.get("retrieved_at", "")),
            str(source.get("version", "")),
        ]
    )


def _component_sort_key(component: Dict[str, Any]) -> tuple:
    name = str(component.get("name", ""))
    return (
        _COMPONENT_ORDER.get(name, len(_COMPONENT_ORDER)),
        name,
        str(component.get("unit", "")),
        str(component.get("unit_price", "")),
        str(component.get("price_card_id", "")),
        str(component.get("quantity", "")),
        str(component.get("cost", "")),
    )


def _discount_sort_key(discount: Dict[str, Any]) -> tuple:
    return (
        str(discount.get("component", "")),
        str(discount.get("policy_id", "")),
        str(discount.get("amount", "")),
    )


def _warning_sort_key(warning: Dict[str, Any]) -> tuple:
    metadata = json.dumps(warning.get("metadata", {}), sort_keys=True, separators=(",", ":"))
    return (
        str(warning.get("code", "")),
        str(warning.get("path", "")),
        str(warning.get("message", "")),
        metadata,
    )


def _ordered_cost_components(components: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(components, key=_component_sort_key)


def _ordered_price_sources(sources: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(sources, key=_source_key)


def _ordered_applied_discounts(discounts: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(discounts, key=_discount_sort_key)


def _ordered_warnings(warnings: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(warnings, key=_warning_sort_key)


def _component_key(component: Dict[str, Any]) -> str:
    return "|".join(
        [
            component.get("name", ""),
            component.get("unit", ""),
            component.get("unit_price", ""),
            component.get("price_card_id", ""),
            str(component.get("discount_eligible", True)),
        ]
    )


def _stream_usage_missing_warning(expected_count: Any = None, actual_count: int = 0) -> Dict[str, Any]:
    metadata = {"actual_ledger_count": actual_count}
    if expected_count is not None:
        metadata["expected_ledger_count"] = expected_count
    return {
        "code": "stream_usage_missing",
        "message": "Final streaming usage was expected but not observed; aggregate total may be incomplete.",
        "metadata": metadata,
    }


def aggregate_cost_ledgers(
    cost_ledgers: Iterable[Dict[str, Any]],
    *,
    provider: str = "aggregate",
    surface: str = "aggregate.cost_ledgers",
    model: str = "multiple",
    mode: str = "compatibility",
    expected_ledger_count: Optional[int] = None,
    stream_final_usage_expected: bool = False,
    stream_final_usage_present: bool = True,
    attribution: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ledgers = list(cost_ledgers)
    components_by_key: Dict[str, Dict[str, Any]] = {}
    price_sources_by_key: Dict[str, Dict[str, Any]] = {}
    applied_discounts: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    total = "0"

    for ledger_index, ledger in enumerate(ledgers):
        total = _add(total, ledger.get("total", "0"))
        for component in ledger.get("components", []):
            key = _component_key(component)
            if key not in components_by_key:
                merged = {
                    "name": component["name"],
                    "quantity": "0",
                    "unit": component["unit"],
                    "unit_price": component["unit_price"],
                    "cost": "0",
                }
                if component.get("price_card_id") is not None:
                    merged["price_card_id"] = component["price_card_id"]
                if component.get("discount_eligible") is not None:
                    merged["discount_eligible"] = component["discount_eligible"]
                merged["metadata"] = {"source_ledger_indexes": []}
                components_by_key[key] = merged
            merged = components_by_key[key]
            merged["quantity"] = _add(merged["quantity"], component.get("quantity", "0"))
            merged["cost"] = _add(merged["cost"], component.get("cost", "0"))
            merged["metadata"]["source_ledger_indexes"].append(ledger_index)
        for source in ledger.get("price_sources", []):
            price_sources_by_key.setdefault(_source_key(source), source)
        applied_discounts.extend(ledger.get("applied_discounts", []))
        warnings.extend(ledger.get("warnings", []))

    missing_stream_usage_warned = False
    if stream_final_usage_expected and not stream_final_usage_present:
        warnings.append(_stream_usage_missing_warning(expected_ledger_count, len(ledgers)))
        missing_stream_usage_warned = True
    if not missing_stream_usage_warned and expected_ledger_count is not None and len(ledgers) < int(expected_ledger_count):
        warnings.append(_stream_usage_missing_warning(expected_ledger_count, len(ledgers)))

    metadata = {
        "ledger_count": len(ledgers),
        "aggregation": "cost_ledgers",
    }
    if expected_ledger_count is not None:
        metadata["expected_ledger_count"] = expected_ledger_count

    result = {
        "schema_version": "0.1",
        "provider": provider,
        "surface": surface,
        "model": {
            "requested": model,
            "returned": model,
            "billed": model,
            "alias_resolution": "none",
        },
        "currency": "USD",
        "components": _ordered_cost_components(components_by_key.values()),
        "total": total,
        "price_sources": _ordered_price_sources(price_sources_by_key.values()),
        "applied_discounts": _ordered_applied_discounts(applied_discounts),
        "warnings": _ordered_warnings(warnings),
        "metadata": metadata,
    }
    normalized_attribution = _normalize_attribution(attribution)
    if normalized_attribution:
        result["attribution"] = normalized_attribution
    if mode == "strict" and result["warnings"]:
        raise ValueError(f"strict mode cost aggregation failed: {result['warnings'][0]['code']}")
    return result


def _number_string(value: Any) -> str:
    return str(value if value is not None else 0)


def _positive_component(name: str, quantity: Any, unit: str, source_path: str) -> Optional[Dict[str, Any]]:
    if _decimal(quantity) <= 0:
        return None
    return {
        "name": name,
        "quantity": _number_string(quantity),
        "unit": unit,
        "source_path": source_path,
    }


def _positive_component_with_metadata(
    name: str,
    quantity: Any,
    unit: str,
    source_path: str,
    metadata: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    component = _positive_component(name, quantity, unit, source_path)
    if component is None:
        return None
    component["metadata"] = dict(metadata)
    if metadata.get("billing_model"):
        component["billing_model"] = str(metadata["billing_model"])
    return component


def _component_billing_model(component: Dict[str, Any]) -> Optional[str]:
    value = component.get("billing_model")
    return str(value) if value else None


def _usage_ledger_for_component(usage_ledger: Dict[str, Any], component: Dict[str, Any]) -> Dict[str, Any]:
    billing_model = _component_billing_model(component)
    if not billing_model:
        return usage_ledger

    component_ledger = dict(usage_ledger)
    model = dict(usage_ledger["model"])
    model["billed"] = billing_model
    model["returned"] = billing_model
    component_ledger["model"] = model
    return component_ledger


def _compact_components(components: Iterable[Optional[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    return [component for component in components if component is not None]


_XAI_SERVER_SIDE_TOOL_USAGE_COMPONENTS = {
    "SERVER_SIDE_TOOL_WEB_SEARCH": ("web_search_units", "search"),
    "SERVER_SIDE_TOOL_IMAGE_SEARCH": ("web_search_units", "search"),
    "SERVER_SIDE_TOOL_X_SEARCH": ("x_search_units", "search"),
    "SERVER_SIDE_TOOL_CODE_EXECUTION": ("code_interpreter_call_units", "call"),
    "SERVER_SIDE_TOOL_COLLECTIONS_SEARCH": ("file_search_units", "call"),
    "SERVER_SIDE_TOOL_ATTACHMENT_SEARCH": ("attachment_search_units", "call"),
    "web_search": ("web_search_units", "search"),
    "image_search": ("web_search_units", "search"),
    "x_search": ("x_search_units", "search"),
    "code_execution": ("code_interpreter_call_units", "call"),
    "code_interpreter": ("code_interpreter_call_units", "call"),
    "collections_search": ("file_search_units", "call"),
    "file_search": ("file_search_units", "call"),
    "attachment_search": ("attachment_search_units", "call"),
}


def _xai_server_side_tool_usage(response: Dict[str, Any], usage: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
    for parent, key, source_path in (
        (response, "server_side_tool_usage", "$.server_side_tool_usage"),
        (response, "serverSideToolUsage", "$.serverSideToolUsage"),
        (usage, "server_side_tool_usage", "$.usage.server_side_tool_usage"),
        (usage, "serverSideToolUsage", "$.usage.serverSideToolUsage"),
    ):
        value = parent.get(key)
        if isinstance(value, dict):
            return value, source_path
    return {}, "$.server_side_tool_usage"


def _xai_server_side_tool_usage_components(response: Dict[str, Any], usage: Dict[str, Any]) -> tuple[List[Optional[Dict[str, Any]]], Decimal, bool]:
    server_side_tool_usage, source_root = _xai_server_side_tool_usage(response, usage)
    components: List[Optional[Dict[str, Any]]] = []
    total_count = Decimal("0")
    for raw_name, quantity in server_side_tool_usage.items():
        mapping = _XAI_SERVER_SIDE_TOOL_USAGE_COMPONENTS.get(str(raw_name))
        if mapping is None:
            continue
        component_name, unit = mapping
        total_count += _decimal(quantity)
        components.append(_positive_component(component_name, quantity, unit, f"{source_root}.{raw_name}"))
    return components, total_count, bool(server_side_tool_usage)


def _base_usage_ledger(
    *,
    provider: str,
    surface: str,
    requested_model: Optional[str],
    returned_model: Optional[str],
    components: List[Dict[str, Any]],
    raw_usage: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    model = returned_model or requested_model
    ledger = {
        "schema_version": "0.1",
        "provider": provider,
        "surface": surface,
        "model": {
            "requested": requested_model or model,
            "returned": returned_model,
            "billed": model,
            "alias_resolution": "none",
        },
        "components": components,
        "raw_usage": raw_usage,
    }
    if context:
        ledger["context"] = context
    return ledger


def _normalize_openai_service_tier(value: Any) -> Optional[str]:
    tier = str(value or "").strip().lower()
    if not tier:
        return None
    if tier in {"auto", "default", "standard"}:
        return "standard"
    return tier


def _usage_context_from_options(response: Dict[str, Any], provider: str, options: Dict[str, Any]) -> Dict[str, Any]:
    context = dict(options.get("context") or {})
    if provider == "openai":
        context_tier = context.get("service_tier", context.get("serviceTier"))
        if context_tier is not None:
            normalized_context_tier = _normalize_openai_service_tier(context_tier)
            if normalized_context_tier:
                context["service_tier"] = normalized_context_tier
            context.pop("serviceTier", None)
    priced_at = options.get("priced_at") or options.get("pricedAt")
    if priced_at is not None:
        context["priced_at"] = str(priced_at)
    elif provider in {"deepseek", "openai"} and "priced_at" not in context and "pricedAt" not in context:
        timestamp = response.get("created_at") if provider == "openai" else None
        if timestamp is None:
            timestamp = response.get("created")
        created_priced_at = _unix_seconds_priced_at(timestamp)
        if created_priced_at:
            context["priced_at"] = created_priced_at
    pricing_period = options.get("pricing_period") or options.get("pricingPeriod")
    if pricing_period is not None:
        context["pricing_period"] = str(pricing_period)
    service_tier = options.get("service_tier") or options.get("serviceTier")
    if service_tier is None and provider == "openai":
        service_tier = response.get("service_tier", response.get("serviceTier"))
    if service_tier is not None and "service_tier" not in context:
        normalized_tier = _normalize_openai_service_tier(service_tier) if provider == "openai" else str(service_tier)
        if normalized_tier:
            context["service_tier"] = normalized_tier
    return context


def _openai_responses_payload(response: Dict[str, Any]) -> Dict[str, Any]:
    if response.get("type") == "response.completed" and isinstance(response.get("response"), dict):
        return response["response"]
    return response


def _openai_responses_orchestration_usage(usage: Dict[str, Any]) -> tuple[Decimal, Decimal, Decimal]:
    input_details = usage.get("input_tokens_details") or {}
    output_details = usage.get("output_tokens_details") or {}
    return (
        _decimal(input_details.get("orchestration_input_tokens") or 0),
        _decimal(input_details.get("orchestration_input_cached_tokens") or 0),
        _decimal(output_details.get("orchestration_output_tokens") or 0),
    )


def _sum_openai_responses_orchestration_usage(usages: Iterable[Dict[str, Any]]) -> tuple[Decimal, Decimal, Decimal]:
    input_tokens = Decimal("0")
    cached_input_tokens = Decimal("0")
    output_tokens = Decimal("0")
    for usage in usages:
        orchestration_input, orchestration_cached_input, orchestration_output = _openai_responses_orchestration_usage(usage)
        input_tokens += orchestration_input
        cached_input_tokens += orchestration_cached_input
        output_tokens += orchestration_output
    return input_tokens, cached_input_tokens, output_tokens


def extract_openai_responses_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    response = _openai_responses_payload(response)
    usage = response.get("usage") or {}
    surface = options.get("surface", "openai.responses")
    response_provider_defaults = {
        "xai.responses": "xai",
        "meta.responses": "meta",
    }
    provider = options.get("provider") or response_provider_defaults.get(surface, "openai")
    input_details = usage.get("input_tokens_details") or {}
    output_details = usage.get("output_tokens_details") or {}
    cached_input = _decimal(input_details.get("cached_tokens") or 0)
    cache_write = _decimal(input_details.get("cache_write_tokens") or 0)
    orchestration_input, orchestration_cached_input, orchestration_output = _openai_responses_orchestration_usage(usage)
    reasoning = _decimal(output_details.get("reasoning_tokens") or 0)
    input_tokens = _decimal(usage.get("input_tokens") or 0)
    output_tokens = _decimal(usage.get("output_tokens") or 0)
    input_uncached = input_tokens - cached_input - cache_write + orchestration_input - orchestration_cached_input
    input_cache_read = cached_input + orchestration_cached_input
    output_text = output_tokens - reasoning + orchestration_output
    context = _usage_context_from_options(response, provider, options)
    tool_components = []
    function_call_count = 0
    explicit_server_side_tool_count = Decimal("0")
    xai_typed_tool_components: List[Optional[Dict[str, Any]]] = []
    xai_typed_tool_count = Decimal("0")
    xai_has_typed_tool_usage = False
    if str(provider).lower() == "xai":
        xai_typed_tool_components, xai_typed_tool_count, xai_has_typed_tool_usage = _xai_server_side_tool_usage_components(response, usage)
    for item in response.get("output", []):
        if item.get("type") == "web_search_call":
            explicit_server_side_tool_count += Decimal("1")
            if not xai_has_typed_tool_usage:
                tool_components.append(_positive_component("web_search_units", 1, "search", "$.output[*].type"))
        elif item.get("type") in {"file_search_call", "collections_search_call"}:
            explicit_server_side_tool_count += Decimal("1")
            if not xai_has_typed_tool_usage:
                tool_components.append(_positive_component("file_search_units", 1, "call", "$.output[*].type"))
        elif item.get("type") in {"code_interpreter_call", "code_execution_call"}:
            explicit_server_side_tool_count += Decimal("1")
            if not xai_has_typed_tool_usage:
                tool_components.append(_positive_component("code_interpreter_call_units", 1, "call", "$.output[*].type"))
        elif item.get("type") == "attachment_search_call":
            explicit_server_side_tool_count += Decimal("1")
            if not xai_has_typed_tool_usage:
                tool_components.append(_positive_component("attachment_search_units", 1, "call", "$.output[*].type"))
        elif item.get("type") == "computer_call":
            explicit_server_side_tool_count += Decimal("1")
            actions = item.get("actions")
            action_count = len(actions) if isinstance(actions, list) else 1
            tool_components.append(
                _positive_component("computer_use_action_units", action_count, "call", "$.output[*].actions[*]")
            )
        elif item.get("type") == "x_search_call":
            explicit_server_side_tool_count += Decimal("1")
            if not xai_has_typed_tool_usage:
                tool_components.append(_positive_component("x_search_units", 1, "search", "$.output[*].type"))
        elif item.get("type") == "function_call":
            function_call_count += 1
    tool_components.append(_positive_component("tool_call_units", function_call_count, "call", "$.output[*].type"))
    tool_components.extend(xai_typed_tool_components)
    if str(provider).lower() == "xai":
        reported_tool_count = _decimal(usage.get("num_server_side_tools_used", usage.get("numServerSideToolsUsed", 0)))
        if not xai_has_typed_tool_usage:
            remaining_tool_count = reported_tool_count - explicit_server_side_tool_count
            tool_components.append(
                _positive_component(
                    "tool_call_units",
                    _format_decimal(remaining_tool_count),
                    "call",
                    "$.usage.num_server_side_tools_used",
                )
            )

    return _base_usage_ledger(
        provider=provider,
        surface=surface,
        requested_model=options.get("model", response.get("model")),
        returned_model=response.get("model"),
        raw_usage=usage,
        context=context,
        components=_compact_components(
            [
                _positive_component(
                    "input_uncached_tokens",
                    _format_decimal(input_uncached),
                    "token",
                    "$.usage.input_tokens + $.usage.input_tokens_details.orchestration_input_tokens",
                ),
                _positive_component(
                    "input_cache_read_tokens",
                    _format_decimal(input_cache_read),
                    "token",
                    "$.usage.input_tokens_details.cached_tokens + $.usage.input_tokens_details.orchestration_input_cached_tokens",
                ),
                _positive_component(
                    "input_cache_write_tokens",
                    _format_decimal(cache_write),
                    "token",
                    "$.usage.input_tokens_details.cache_write_tokens",
                ),
                _positive_component(
                    "output_text_tokens",
                    _format_decimal(output_text),
                    "token",
                    "$.usage.output_tokens + $.usage.output_tokens_details.orchestration_output_tokens",
                ),
                _positive_component("output_reasoning_tokens", reasoning, "token", "$.usage.output_tokens_details.reasoning_tokens"),
                *tool_components,
            ]
        ),
    )


def extract_openai_embeddings_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    usage = response.get("usage") or {}
    tokens = usage.get("prompt_tokens", usage.get("total_tokens", 0))
    source_path = "$.usage.prompt_tokens" if "prompt_tokens" in usage else "$.usage.total_tokens"

    return _base_usage_ledger(
        provider=options.get("provider", "openai"),
        surface=options.get("surface", "openai.embeddings"),
        requested_model=options.get("model", response.get("model")),
        returned_model=response.get("model"),
        raw_usage=usage,
        components=_compact_components(
            [
                _positive_component("embedding_tokens", tokens, "token", source_path),
            ]
        ),
    )


def _transcription_duration_seconds(response: Dict[str, Any]) -> tuple[Any, Optional[str]]:
    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    if usage.get("type") == "duration" or "seconds" in usage:
        return usage.get("seconds", 0), "$.usage.seconds"
    for field, path in (
        ("duration", "$.duration"),
        ("durationInSeconds", "$.durationInSeconds"),
        ("duration_in_seconds", "$.duration_in_seconds"),
    ):
        if response.get(field) is not None:
            return response.get(field, 0), path
    finish = response.get("finish") if isinstance(response.get("finish"), dict) else {}
    for field, path in (
        ("durationInSeconds", "$.finish.durationInSeconds"),
        ("duration_in_seconds", "$.finish.duration_in_seconds"),
        ("duration", "$.finish.duration"),
    ):
        if finish.get(field) is not None:
            return finish.get(field, 0), path
    return None, None


def _vercel_ai_sdk_model_id(response: Dict[str, Any]) -> Optional[str]:
    response_metadata = response.get("response") if isinstance(response.get("response"), dict) else {}
    model_metadata = response.get("model") if isinstance(response.get("model"), dict) else {}
    for value in (
        response.get("model"),
        response_metadata.get("modelId"),
        response_metadata.get("model_id"),
        model_metadata.get("modelId"),
        model_metadata.get("model_id"),
    ):
        if isinstance(value, str) and value:
            return value
    return None


def extract_openai_audio_transcription_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    components: List[Dict[str, Any]] = []

    if usage.get("type") == "duration" or "seconds" in usage:
        components.append(_positive_component("transcription_seconds", usage.get("seconds", 0), "second", "$.usage.seconds"))
    elif usage:
        input_details = usage.get("input_token_details", {})
        audio_tokens = input_details.get("audio_tokens", 0)
        input_tokens = usage.get("input_tokens", 0)
        text_tokens = input_details.get("text_tokens", input_tokens - audio_tokens)
        output_tokens = usage.get("output_tokens", 0)
        components.extend(
            [
                _positive_component("input_uncached_tokens", text_tokens, "token", "$.usage.input_token_details.text_tokens"),
                _positive_component("input_audio_tokens", audio_tokens, "token", "$.usage.input_token_details.audio_tokens"),
                _positive_component("output_text_tokens", output_tokens, "token", "$.usage.output_tokens"),
            ]
        )
    else:
        duration_seconds, source_path = _transcription_duration_seconds(response)
        if duration_seconds is not None and source_path is not None:
            components.append(_positive_component("transcription_seconds", duration_seconds, "second", source_path))

    returned_model = _vercel_ai_sdk_model_id(response) or options.get("model")
    raw_usage = usage or {}
    if not raw_usage:
        duration_seconds, source_path = _transcription_duration_seconds(response)
        raw_usage = {"duration_seconds": duration_seconds, "source_path": source_path}
    return _base_usage_ledger(
        provider=options.get("provider", "openai"),
        surface=options.get("surface", "openai.audio_transcriptions"),
        requested_model=options.get("model", returned_model),
        returned_model=returned_model,
        raw_usage=raw_usage,
        components=_compact_components(components),
    )


def extract_openai_images_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    components: List[Dict[str, Any]] = []

    if usage:
        input_details = usage.get("input_tokens_details", {})
        input_image_tokens = input_details.get("image_tokens", 0)
        input_tokens = usage.get("input_tokens", 0)
        input_text_tokens = input_details.get("text_tokens", input_tokens - input_image_tokens)
        output_details = usage.get("output_tokens_details", {})
        output_image_tokens = output_details.get("image_tokens", usage.get("output_tokens", 0))
        components.extend(
            [
                _positive_component("input_uncached_tokens", input_text_tokens, "token", "$.usage.input_tokens_details.text_tokens"),
                _positive_component("input_image_tokens", input_image_tokens, "token", "$.usage.input_tokens_details.image_tokens"),
                _positive_component("output_image_tokens", output_image_tokens, "token", "$.usage.output_tokens"),
            ]
        )
    else:
        images = response.get("data") if isinstance(response.get("data"), list) else []
        components.append(_positive_component("image_generation_units", len(images), "image", "$.data"))

    returned_model = response.get("model") or options.get("model")
    return _base_usage_ledger(
        provider=options.get("provider", "openai"),
        surface=options.get("surface", "openai.images"),
        requested_model=options.get("model", returned_model),
        returned_model=returned_model,
        raw_usage=usage or {"image_count": len(response.get("data", [])) if isinstance(response.get("data"), list) else 0},
        components=_compact_components(components),
    )


def _openai_usage_images_count(response: Dict[str, Any]) -> Decimal:
    if response.get("object") == "organization.usage.images.result":
        return _decimal(response.get("images", 0))
    total = Decimal("0")
    for bucket in response.get("data", []) if isinstance(response.get("data"), list) else []:
        results = bucket.get("results", []) if isinstance(bucket, dict) else []
        for result in results if isinstance(results, list) else []:
            if isinstance(result, dict):
                total += _decimal(result.get("images", 0))
    if total == 0 and response.get("images") is not None:
        total += _decimal(response.get("images", 0))
    return total


def _openai_usage_first_result_value(response: Dict[str, Any], key: str) -> Optional[Any]:
    if response.get(key) is not None:
        return response.get(key)
    for bucket in response.get("data", []) if isinstance(response.get("data"), list) else []:
        results = bucket.get("results", []) if isinstance(bucket, dict) else []
        for result in results if isinstance(results, list) else []:
            if isinstance(result, dict) and result.get(key) is not None:
                return result.get(key)
    return None


def _openai_usage_sum_result_value(response: Dict[str, Any], key: str) -> Decimal:
    if response.get(key) is not None:
        return _decimal(response.get(key, 0))
    total = Decimal("0")
    for bucket in response.get("data", []) if isinstance(response.get("data"), list) else []:
        results = bucket.get("results", []) if isinstance(bucket, dict) else []
        for result in results if isinstance(results, list) else []:
            if isinstance(result, dict):
                total += _decimal(result.get(key, 0))
    return total


def extract_openai_usage_completions_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    input_tokens = _openai_usage_sum_result_value(response, "input_tokens")
    cached_tokens = _openai_usage_sum_result_value(response, "input_cached_tokens")
    uncached_tokens = max(Decimal("0"), input_tokens - cached_tokens)
    output_tokens = _openai_usage_sum_result_value(response, "output_tokens")
    input_audio_tokens = _openai_usage_sum_result_value(response, "input_audio_tokens")
    output_audio_tokens = _openai_usage_sum_result_value(response, "output_audio_tokens")
    num_model_requests = _openai_usage_sum_result_value(response, "num_model_requests")
    returned_model = response.get("model") or options.get("model") or _openai_usage_first_result_value(response, "model") or "completions"
    raw_usage = {
        "input_tokens": _format_decimal(input_tokens),
        "input_cached_tokens": _format_decimal(cached_tokens),
        "output_tokens": _format_decimal(output_tokens),
        "input_audio_tokens": _format_decimal(input_audio_tokens),
        "output_audio_tokens": _format_decimal(output_audio_tokens),
        "num_model_requests": _format_decimal(num_model_requests),
        "batch": _openai_usage_first_result_value(response, "batch"),
        "service_tier": _openai_usage_first_result_value(response, "service_tier"),
    }
    return _base_usage_ledger(
        provider=options.get("provider", "openai"),
        surface=options.get("surface", "openai.usage.completions"),
        requested_model=options.get("model", returned_model),
        returned_model=returned_model,
        raw_usage={key: value for key, value in raw_usage.items() if value is not None},
        components=_compact_components(
            [
                _positive_component("input_uncached_tokens", _format_decimal(uncached_tokens), "token", "$..input_tokens"),
                _positive_component("input_cache_read_tokens", _format_decimal(cached_tokens), "token", "$..input_cached_tokens"),
                _positive_component("input_audio_tokens", _format_decimal(input_audio_tokens), "token", "$..input_audio_tokens"),
                _positive_component("output_text_tokens", _format_decimal(output_tokens), "token", "$..output_tokens"),
                _positive_component("output_audio_tokens", _format_decimal(output_audio_tokens), "token", "$..output_audio_tokens"),
            ]
        ),
    )


def extract_openai_usage_images_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    images = _format_decimal(_openai_usage_images_count(response))
    returned_model = response.get("model") or options.get("model") or _openai_usage_first_result_value(response, "model") or "image-generation"
    raw_usage = {
        "images": images,
        "num_model_requests": _openai_usage_first_result_value(response, "num_model_requests"),
        "source": _openai_usage_first_result_value(response, "source"),
        "size": _openai_usage_first_result_value(response, "size"),
    }
    return _base_usage_ledger(
        provider=options.get("provider", "openai"),
        surface=options.get("surface", "openai.usage.images"),
        requested_model=options.get("model", returned_model),
        returned_model=returned_model,
        raw_usage={key: value for key, value in raw_usage.items() if value is not None},
        components=_compact_components(
            [
                _positive_component("image_generation_units", images, "image", "$..images"),
            ]
        ),
    )


def _openai_usage_audio_speech_characters(response: Dict[str, Any]) -> Decimal:
    if response.get("object") == "organization.usage.audio_speeches.result":
        return _decimal(response.get("characters", 0))
    total = Decimal("0")
    for bucket in response.get("data", []) if isinstance(response.get("data"), list) else []:
        results = bucket.get("results", []) if isinstance(bucket, dict) else []
        for result in results if isinstance(results, list) else []:
            if isinstance(result, dict):
                total += _decimal(result.get("characters", 0))
    if total == 0 and response.get("characters") is not None:
        total += _decimal(response.get("characters", 0))
    return total


def extract_openai_usage_audio_speeches_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    characters = _format_decimal(_openai_usage_audio_speech_characters(response))
    returned_model = response.get("model") or options.get("model") or _openai_usage_first_result_value(response, "model") or "audio-speech"
    raw_usage = {
        "characters": characters,
        "num_model_requests": _openai_usage_first_result_value(response, "num_model_requests"),
    }
    return _base_usage_ledger(
        provider=options.get("provider", "openai"),
        surface=options.get("surface", "openai.usage.audio_speeches"),
        requested_model=options.get("model", returned_model),
        returned_model=returned_model,
        raw_usage={key: value for key, value in raw_usage.items() if value is not None},
        components=_compact_components(
            [
                _positive_component("audio_generation_characters", characters, "character", "$..characters"),
            ]
        ),
    )


def _openai_usage_audio_transcription_seconds(response: Dict[str, Any]) -> Decimal:
    if response.get("object") == "organization.usage.audio_transcriptions.result":
        return _decimal(response.get("seconds", 0))
    total = Decimal("0")
    for bucket in response.get("data", []) if isinstance(response.get("data"), list) else []:
        results = bucket.get("results", []) if isinstance(bucket, dict) else []
        for result in results if isinstance(results, list) else []:
            if isinstance(result, dict):
                total += _decimal(result.get("seconds", 0))
    if total == 0 and response.get("seconds") is not None:
        total += _decimal(response.get("seconds", 0))
    return total


def extract_openai_usage_audio_transcriptions_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    seconds = _format_decimal(_openai_usage_audio_transcription_seconds(response))
    returned_model = response.get("model") or options.get("model") or _openai_usage_first_result_value(response, "model") or "audio-transcription"
    raw_usage = {
        "seconds": seconds,
        "num_model_requests": _openai_usage_first_result_value(response, "num_model_requests"),
    }
    return _base_usage_ledger(
        provider=options.get("provider", "openai"),
        surface=options.get("surface", "openai.usage.audio_transcriptions"),
        requested_model=options.get("model", returned_model),
        returned_model=returned_model,
        raw_usage={key: value for key, value in raw_usage.items() if value is not None},
        components=_compact_components(
            [
                _positive_component("transcription_seconds", seconds, "second", "$..seconds"),
            ]
        ),
    )


def _openai_usage_embedding_tokens(response: Dict[str, Any]) -> Decimal:
    if response.get("object") == "organization.usage.embeddings.result":
        return _decimal(response.get("input_tokens", 0))
    total = Decimal("0")
    for bucket in response.get("data", []) if isinstance(response.get("data"), list) else []:
        results = bucket.get("results", []) if isinstance(bucket, dict) else []
        for result in results if isinstance(results, list) else []:
            if isinstance(result, dict):
                total += _decimal(result.get("input_tokens", 0))
    if total == 0 and response.get("input_tokens") is not None:
        total += _decimal(response.get("input_tokens", 0))
    return total


def extract_openai_usage_embeddings_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    input_tokens = _format_decimal(_openai_usage_embedding_tokens(response))
    returned_model = response.get("model") or options.get("model") or _openai_usage_first_result_value(response, "model") or "embedding"
    raw_usage = {
        "input_tokens": input_tokens,
        "num_model_requests": _openai_usage_first_result_value(response, "num_model_requests"),
    }
    return _base_usage_ledger(
        provider=options.get("provider", "openai"),
        surface=options.get("surface", "openai.usage.embeddings"),
        requested_model=options.get("model", returned_model),
        returned_model=returned_model,
        raw_usage={key: value for key, value in raw_usage.items() if value is not None},
        components=_compact_components(
            [
                _positive_component("embedding_tokens", input_tokens, "token", "$..input_tokens"),
            ]
        ),
    )


def extract_openai_vector_store_storage_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    usage_bytes = response.get("usage_bytes", 0)
    storage_days = options.get("storage_days", options.get("storageDays", 0))
    components: List[Dict[str, Any]] = []

    if storage_days:
        quantity = _multiply_divide(usage_bytes, storage_days, "1000000000")
        components.append(_positive_component("storage_gb_days", quantity, "gb_day", "$.usage_bytes"))

    returned_model = response.get("model") or options.get("model") or "vector-store-storage"
    raw_usage = {
        "usage_bytes": usage_bytes,
        "storage_days": storage_days,
    }
    return _base_usage_ledger(
        provider=options.get("provider", "openai"),
        surface=options.get("surface", "openai.vector_stores"),
        requested_model=options.get("model", returned_model),
        returned_model=returned_model,
        raw_usage=raw_usage,
        components=_compact_components(components),
    )


def _openai_usage_code_interpreter_session_count(response: Dict[str, Any]) -> Decimal:
    if response.get("object") == "organization.usage.code_interpreter_sessions.result":
        return _decimal(response.get("num_sessions", 0))
    total = Decimal("0")
    for bucket in response.get("data", []) if isinstance(response.get("data"), list) else []:
        results = bucket.get("results", []) if isinstance(bucket, dict) else []
        for result in results if isinstance(results, list) else []:
            if isinstance(result, dict):
                total += _decimal(result.get("num_sessions", 0))
    if total == 0 and response.get("num_sessions") is not None:
        total += _decimal(response.get("num_sessions", 0))
    return total


def extract_openai_usage_code_interpreter_sessions_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    num_sessions = _format_decimal(_openai_usage_code_interpreter_session_count(response))
    returned_model = response.get("model") or options.get("model") or "code-interpreter-session"
    return _base_usage_ledger(
        provider=options.get("provider", "openai"),
        surface=options.get("surface", "openai.usage.code_interpreter_sessions"),
        requested_model=options.get("model", returned_model),
        returned_model=returned_model,
        raw_usage={"num_sessions": num_sessions},
        components=_compact_components(
            [
                _positive_component("code_interpreter_session_units", num_sessions, "session", "$..num_sessions"),
            ]
        ),
    )


OPENAI_COMPATIBLE_CHAT_PROVIDERS = {
    "openai.chat_completions": "openai",
    "openrouter.chat_completions": "openrouter",
    "groq.chat_completions": "groq",
    "xai.chat_completions": "xai",
    "meta.chat_completions": "meta",
    "mistral.chat_completions": "mistral",
    "deepseek.chat_completions": "deepseek",
    "azure.openai.chat_completions": "azure",
    "huggingface.chat_completions": "huggingface",
    "nvidia.chat_completions": "nvidia",
    "tinker.chat_completions": "tinker",
    "kimi.chat_completions": "kimi",
    "ai21.chat_completions": "ai21",
    "arcee.chat_completions": "arcee",
    "cohere.chat_completions_compatible": "cohere",
    "dashscope.chat_completions": "dashscope",
    "inception.chat_completions": "inception",
    "poolside.chat_completions": "poolside",
    "xiaomi.chat_completions": "xiaomi",
    "zai.chat_completions": "zai",
    "zhipu.chat_completions": "zhipu",
}


def _openai_compatible_cached_input(usage: Dict[str, Any]) -> tuple[Any, str]:
    prompt_details = usage.get("prompt_tokens_details", {})
    if "cached_tokens" in prompt_details:
        return prompt_details.get("cached_tokens", 0), "$.usage.prompt_tokens_details.cached_tokens"
    if "prompt_cache_hit_tokens" in usage:
        return usage.get("prompt_cache_hit_tokens", 0), "$.usage.prompt_cache_hit_tokens"
    return 0, "$.usage.prompt_tokens_details.cached_tokens"


def _openai_compatible_cache_write(usage: Dict[str, Any]) -> tuple[Any, str]:
    prompt_details = usage.get("prompt_tokens_details", {})
    if "cache_write_tokens" in prompt_details:
        return prompt_details.get("cache_write_tokens", 0), "$.usage.prompt_tokens_details.cache_write_tokens"
    return 0, "$.usage.prompt_tokens_details.cache_write_tokens"


def _openai_compatible_reasoning_output(usage: Dict[str, Any]) -> tuple[Any, str]:
    completion_details = usage.get("completion_tokens_details", {})
    if "reasoning_tokens" in completion_details:
        return completion_details.get("reasoning_tokens", 0), "$.usage.completion_tokens_details.reasoning_tokens"
    output_details = usage.get("output_tokens_details", {})
    if "reasoning_tokens" in output_details:
        return output_details.get("reasoning_tokens", 0), "$.usage.output_tokens_details.reasoning_tokens"
    return 0, "$.usage.completion_tokens_details.reasoning_tokens"


def _openai_compatible_chat_payload(response: Dict[str, Any]) -> Dict[str, Any]:
    chunks = response.get("chunks") or response.get("stream")
    if not isinstance(chunks, list):
        return response
    fallback_model = response.get("model")
    fallback_service_tier = response.get("service_tier", response.get("serviceTier"))
    for chunk in chunks:
        if isinstance(chunk, dict) and fallback_service_tier is None:
            fallback_service_tier = chunk.get("service_tier", chunk.get("serviceTier"))
    for chunk in reversed(chunks):
        if not isinstance(chunk, dict):
            continue
        if isinstance(chunk.get("usage"), dict):
            payload = dict(chunk)
            if payload.get("model") is None and fallback_model is not None:
                payload["model"] = fallback_model
            if payload.get("service_tier", payload.get("serviceTier")) is None and fallback_service_tier is not None:
                payload["service_tier"] = fallback_service_tier
            return payload
    return response


def extract_openai_compatible_chat_completions_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    response = _openai_compatible_chat_payload(response)
    usage = response.get("usage") or {}
    cached_input, cached_source = _openai_compatible_cached_input(usage)
    cache_write, cache_write_source = _openai_compatible_cache_write(usage)
    reasoning, reasoning_source = _openai_compatible_reasoning_output(usage)
    prompt_tokens = usage.get(
        "prompt_tokens",
        usage.get("prompt_cache_hit_tokens", 0) + usage.get("prompt_cache_miss_tokens", 0),
    )
    completion_tokens = usage.get("completion_tokens", 0)
    surface = options.get("surface", "openai.chat_completions")
    provider = options.get("provider", OPENAI_COMPATIBLE_CHAT_PROVIDERS.get(surface, "openai"))
    context = _usage_context_from_options(response, provider, options)

    return _base_usage_ledger(
        provider=provider,
        surface=surface,
        requested_model=options.get("model", response.get("model")),
        returned_model=response.get("model"),
        raw_usage=usage,
        context=context,
        components=_compact_components(
            [
                _positive_component("input_uncached_tokens", prompt_tokens - cached_input - cache_write, "token", "$.usage.prompt_tokens"),
                _positive_component("input_cache_read_tokens", cached_input, "token", cached_source),
                _positive_component("input_cache_write_tokens", cache_write, "token", cache_write_source),
                _positive_component("output_text_tokens", completion_tokens - reasoning, "token", "$.usage.completion_tokens"),
                _positive_component("output_reasoning_tokens", reasoning, "token", reasoning_source),
            ]
        ),
    )


def extract_openai_chat_completions_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    merged_options = {"provider": "openai", "surface": "openai.chat_completions"}
    merged_options.update(options)
    return extract_openai_compatible_chat_completions_usage(response, **merged_options)


def extract_openrouter_chat_completions_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    merged_options = {"provider": "openrouter", "surface": "openrouter.chat_completions"}
    merged_options.update(options)
    return extract_openai_compatible_chat_completions_usage(response, **merged_options)


def extract_meta_chat_completions_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    merged_options = {"provider": "meta", "surface": "meta.chat_completions"}
    merged_options.update(options)
    return extract_openai_compatible_chat_completions_usage(response, **merged_options)


def extract_meta_responses_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    merged_options = {"provider": "meta", "surface": "meta.responses"}
    merged_options.update(options)
    return extract_openai_responses_usage(response, **merged_options)


def _anthropic_messages_payload(response: Dict[str, Any]) -> Dict[str, Any]:
    events = response.get("events")
    if not isinstance(events, list):
        return response

    message: Dict[str, Any] = {}
    usage: Dict[str, Any] = {}
    content: List[Any] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        if event.get("type") == "message_start" and isinstance(event.get("message"), dict):
            message = dict(event["message"])
            usage.update(message.get("usage") or {})
            if isinstance(message.get("content"), list):
                content = list(message["content"])
        elif event.get("type") == "content_block_start" and isinstance(event.get("content_block"), dict):
            index = event.get("index")
            if isinstance(index, int) and index >= 0:
                while len(content) <= index:
                    content.append(None)
                content[index] = dict(event["content_block"])
        elif event.get("type") == "message_delta":
            usage.update(event.get("usage") or {})
            if isinstance(event.get("delta"), dict):
                message.update(event["delta"])

    if not message:
        return response
    message["usage"] = usage
    if content:
        message["content"] = [block for block in content if block is not None]
    serving_model = _anthropic_serving_model(message, usage)
    if serving_model:
        message["model"] = serving_model
    return message


def _anthropic_fallback_pairs(response: Dict[str, Any]) -> List[tuple[str, str]]:
    pairs = []
    content = response.get("content")
    if not isinstance(content, list):
        return pairs
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "fallback":
            continue
        from_model = (block.get("from") or {}).get("model") if isinstance(block.get("from"), dict) else None
        to_model = (block.get("to") or {}).get("model") if isinstance(block.get("to"), dict) else None
        if from_model and to_model:
            pairs.append((str(from_model), str(to_model)))
    return pairs


def _anthropic_refused(response: Dict[str, Any]) -> bool:
    return response.get("stop_reason") == "refusal"


def _anthropic_iterations(usage: Dict[str, Any]) -> List[Dict[str, Any]]:
    iterations = usage.get("iterations")
    if not isinstance(iterations, list):
        return []
    return [iteration for iteration in iterations if isinstance(iteration, dict)]


def _anthropic_serving_model(response: Dict[str, Any], usage: Dict[str, Any]) -> Optional[str]:
    fallback_iterations = [
        iteration
        for iteration in _anthropic_iterations(usage)
        if iteration.get("type") == "fallback_message" and iteration.get("model")
    ]
    if fallback_iterations:
        return str(fallback_iterations[-1]["model"])
    returned_model = response.get("model")
    return str(returned_model) if returned_model else None


def _anthropic_requested_model(response: Dict[str, Any], usage: Dict[str, Any], requested_model: Optional[str]) -> str:
    if requested_model:
        return str(requested_model)
    pairs = _anthropic_fallback_pairs(response)
    if pairs:
        return pairs[0][0]
    iterations = _anthropic_iterations(usage)
    if len(iterations) > 1 and iterations[0].get("model"):
        return str(iterations[0]["model"])
    return str(response.get("model") or "unknown")


def _anthropic_iteration_metadata(iteration: Dict[str, Any], index: int, billing_model: str) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {
        "billing_model": billing_model,
        "usage_iteration_index": index,
    }
    if iteration.get("type"):
        metadata["usage_iteration_type"] = iteration["type"]
    return metadata


def _anthropic_attempt_refused_before_output(
    response: Dict[str, Any],
    iteration: Dict[str, Any],
    index: int,
    iteration_count: int,
    has_fallback_iteration: bool,
) -> bool:
    if _decimal(iteration.get("output_tokens") or 0) > 0:
        return False
    if has_fallback_iteration and index < iteration_count - 1:
        return True
    return index == iteration_count - 1 and _anthropic_refused(response)


def _anthropic_messages_iteration_components(
    response: Dict[str, Any],
    usage: Dict[str, Any],
    requested_model: Optional[str],
) -> List[Dict[str, Any]]:
    iterations = _anthropic_iterations(usage)
    if not iterations:
        return []

    components: List[Optional[Dict[str, Any]]] = []
    has_fallback_iteration = any(
        iteration.get("type") == "fallback_message"
        for iteration in iterations
    )
    for index, raw_iteration in enumerate(iterations):
        iteration_model = str(raw_iteration.get("model") or response.get("model") or requested_model or "")
        source_root = f"$.usage.iterations[{index}]"
        metadata = _anthropic_iteration_metadata(raw_iteration, index, iteration_model)
        refused_before_output = _anthropic_attempt_refused_before_output(
            response,
            raw_iteration,
            index,
            len(iterations),
            has_fallback_iteration,
        )
        if not refused_before_output:
            cache_write = raw_iteration.get("cache_creation_input_tokens", 0)
            cache_write_1h = raw_iteration.get("cache_creation_input_tokens_1h", 0)
            components.extend(
                [
                    _positive_component_with_metadata("input_uncached_tokens", raw_iteration.get("input_tokens", 0), "token", f"{source_root}.input_tokens", metadata),
                    _positive_component_with_metadata("input_cache_write_tokens", _decimal(cache_write) - _decimal(cache_write_1h), "token", f"{source_root}.cache_creation_input_tokens", metadata),
                    _positive_component_with_metadata("input_cache_write_1h_tokens", cache_write_1h, "token", f"{source_root}.cache_creation_input_tokens_1h", metadata),
                    _positive_component_with_metadata("input_cache_read_tokens", raw_iteration.get("cache_read_input_tokens", 0), "token", f"{source_root}.cache_read_input_tokens", metadata),
                ]
            )
            components.append(
                _positive_component_with_metadata(
                    "output_text_tokens",
                    raw_iteration.get("output_tokens", 0),
                    "token",
                    f"{source_root}.output_tokens",
                    metadata,
                )
            )

    return _compact_components(components)


def _anthropic_client_fallback_credit_enabled(response: Dict[str, Any], options: Dict[str, Any]) -> bool:
    for key in ("anthropic_fallback_credit", "anthropicFallbackCredit", "fallback_credit", "fallbackCredit"):
        if options.get(key) is True:
            return True
    request = response.get("request") if isinstance(response.get("request"), dict) else {}
    metadata = response.get("metadata") if isinstance(response.get("metadata"), dict) else {}
    return bool(
        request.get("fallback_credit_token")
        or metadata.get("fallback_credit_token")
        or response.get("fallback_credit_token")
    )


def _anthropic_response_metadata(
    response: Dict[str, Any],
    usage: Dict[str, Any],
    requested_model: str,
    components: Iterable[Dict[str, Any]],
    fallback_credit_signaled: bool,
) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {}
    iterations = _anthropic_iterations(usage)
    fallback_iterations = [iteration for iteration in iterations if iteration.get("type") == "fallback_message"]
    fallback_pairs = _anthropic_fallback_pairs(response)
    fallback_attempted = bool(fallback_iterations or fallback_pairs)
    if fallback_attempted:
        serving_model = _anthropic_serving_model(response, usage)
        attempted_models = [str(iteration["model"]) for iteration in iterations if iteration.get("model")]
        pricing_models = []
        for component in components:
            billing_model = _component_billing_model(component)
            if billing_model and billing_model not in pricing_models:
                pricing_models.append(billing_model)
        if not pricing_models and serving_model and list(components):
            pricing_models.append(serving_model)
        fallback_metadata: Dict[str, Any] = {
            "attempted": True,
            "utilized": not _anthropic_refused(response),
            "requested_model": requested_model,
            "attempted_models": attempted_models,
            "pricing_models": pricing_models,
            "source": "usage.iterations" if fallback_iterations else "content.fallback",
        }
        if serving_model:
            fallback_metadata["serving_model"] = serving_model
        if fallback_pairs:
            fallback_metadata["hops"] = [
                {"from_model": from_model, "to_model": to_model}
                for from_model, to_model in fallback_pairs
            ]
        metadata["anthropic_fallback"] = fallback_metadata

    if _anthropic_refused(response):
        details = response.get("stop_details") if isinstance(response.get("stop_details"), dict) else {}
        refusal_metadata: Dict[str, Any] = {
            "detected": True,
            "pre_output": _decimal(usage.get("output_tokens") or 0) <= 0,
            "requires_retry": True,
        }
        for key in ("category", "recommended_model"):
            if details.get(key) is not None:
                refusal_metadata[key] = details[key]
        refusal_metadata["fallback_credit_available"] = bool(details.get("fallback_credit_token"))
        metadata["anthropic_refusal"] = refusal_metadata

    if fallback_credit_signaled:
        metadata["anthropic_fallback_credit"] = {
            "signaled": True,
            "pricing_source": "reported_usage",
        }
    return metadata


def extract_anthropic_messages_usage(response: Any, **options: Any) -> Dict[str, Any]:
    response = _response_mapping(response)
    response = _anthropic_messages_payload(response)
    usage_present = isinstance(response.get("usage"), dict)
    usage = response.get("usage") if usage_present else {}
    requested_model = _anthropic_requested_model(response, usage, options.get("model"))
    serving_model = _anthropic_serving_model(response, usage)
    input_tokens = usage.get("input_tokens", 0)
    cache_write = usage.get("cache_creation_input_tokens", 0)
    cache_write_1h = usage.get("cache_creation_input_tokens_1h", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    iteration_components = _anthropic_messages_iteration_components(response, usage, requested_model)
    metadata: Dict[str, Any] = {}
    refusal_zero_billable = _anthropic_refused(response) and _decimal(output_tokens) <= 0
    fallback_credit_signaled = _anthropic_client_fallback_credit_enabled(response, options)
    if iteration_components:
        components = iteration_components
    elif refusal_zero_billable:
        components = []
        metadata["zero_billable_reason"] = "anthropic_classifier_block"
    else:
        components = _compact_components(
            [
                _positive_component("input_uncached_tokens", input_tokens, "token", "$.usage.input_tokens"),
                _positive_component("input_cache_write_tokens", cache_write - cache_write_1h, "token", "$.usage.cache_creation_input_tokens"),
                _positive_component("input_cache_write_1h_tokens", cache_write_1h, "token", "$.usage.cache_creation_input_tokens_1h"),
                _positive_component("input_cache_read_tokens", cache_read, "token", "$.usage.cache_read_input_tokens"),
                _positive_component("output_text_tokens", output_tokens, "token", "$.usage.output_tokens"),
            ]
        )
        if not usage_present:
            metadata["missing_usage_fields"] = ["$.usage"]

    metadata.update(
        _anthropic_response_metadata(
            response,
            usage,
            requested_model,
            components,
            fallback_credit_signaled,
        )
    )

    ledger = _base_usage_ledger(
        provider=options.get("provider", "anthropic"),
        surface=options.get("surface", "anthropic.messages"),
        requested_model=requested_model,
        returned_model=serving_model,
        raw_usage=usage,
        components=components,
    )
    if not components and refusal_zero_billable:
        metadata.setdefault("zero_billable_reason", "anthropic_classifier_block")
    if metadata:
        ledger["metadata"] = metadata
    return ledger


GEMINI_INPUT_MODALITY_COMPONENTS = {
    "MODALITY_UNSPECIFIED": "input_uncached_tokens",
    "TEXT": "input_uncached_tokens",
    "DOCUMENT": "input_uncached_tokens",
    "IMAGE": "input_image_tokens",
    "AUDIO": "input_audio_tokens",
    "VIDEO": "input_video_tokens",
}

GEMINI_OUTPUT_MODALITY_COMPONENTS = {
    "MODALITY_UNSPECIFIED": "output_text_tokens",
    "TEXT": "output_text_tokens",
    "DOCUMENT": "output_text_tokens",
    "IMAGE": "output_image_tokens",
    "AUDIO": "output_audio_tokens",
    "VIDEO": "output_video_tokens",
}

GEMINI_INPUT_COMPONENT_ORDER = [
    "input_uncached_tokens",
    "input_image_tokens",
    "input_audio_tokens",
    "input_video_tokens",
]

GEMINI_OUTPUT_COMPONENT_ORDER = [
    "output_text_tokens",
    "output_image_tokens",
    "output_audio_tokens",
    "output_video_tokens",
]


def _gemini_modality_counts(details: Any) -> Dict[str, Decimal]:
    counts: Dict[str, Decimal] = {}
    if not isinstance(details, list):
        return counts
    for detail in details:
        if not isinstance(detail, dict):
            continue
        modality = str(detail.get("modality") or "MODALITY_UNSPECIFIED").upper()
        counts[modality] = counts.get(modality, Decimal("0")) + _decimal(detail.get("tokenCount", 0))
    return counts


def _gemini_sum_counts(counts: Dict[str, Decimal]) -> Decimal:
    total = Decimal("0")
    for quantity in counts.values():
        total += quantity
    return total


def _gemini_add_count(counts: Dict[str, Decimal], modality: str, quantity: Any) -> None:
    parsed = _decimal(quantity)
    if parsed == 0:
        return
    counts[modality] = counts.get(modality, Decimal("0")) + parsed


def _gemini_net_input_counts(
    prompt_counts: Dict[str, Decimal],
    cache_counts: Dict[str, Decimal],
    tool_counts: Dict[str, Decimal],
) -> Dict[str, Decimal]:
    net_counts: Dict[str, Decimal] = {}
    for modality in set(prompt_counts) | set(cache_counts) | set(tool_counts):
        net_counts[modality] = (
            prompt_counts.get(modality, Decimal("0"))
            - cache_counts.get(modality, Decimal("0"))
            + tool_counts.get(modality, Decimal("0"))
        )
    return net_counts


def _gemini_component_quantities(
    counts: Dict[str, Decimal],
    modality_components: Dict[str, str],
    fallback_component: str,
) -> Dict[str, Decimal]:
    quantities: Dict[str, Decimal] = {}
    for modality, quantity in counts.items():
        component = modality_components.get(modality, fallback_component)
        quantities[component] = quantities.get(component, Decimal("0")) + quantity
    return quantities


def _gemini_ordered_components(
    quantities: Dict[str, Decimal],
    order: Iterable[str],
    source_path: str,
) -> List[Optional[Dict[str, Any]]]:
    return [
        _positive_component(component, _format_decimal(quantities.get(component, Decimal("0"))), "token", source_path)
        for component in order
    ]


def _gemini_generate_content_payload(response: Dict[str, Any]) -> Dict[str, Any]:
    chunks = response.get("chunks") or response.get("stream")
    if not isinstance(chunks, list) or not chunks:
        return response
    for chunk in reversed(chunks):
        if isinstance(chunk, dict) and isinstance(chunk.get("usageMetadata"), dict):
            return chunk
    for chunk in reversed(chunks):
        if isinstance(chunk, dict):
            return chunk
    return response


def _normalize_gemini_service_tier(value: Any) -> Optional[str]:
    if value is None:
        return None
    tier = str(value).strip()
    if not tier:
        return None
    if "." in tier:
        tier = tier.rsplit(".", 1)[1]
    tier = tier.lower()
    if tier.startswith("service_tier_"):
        tier = tier.removeprefix("service_tier_")
    if tier == "unspecified":
        return "standard"
    return tier


def _response_header_value(response: Dict[str, Any], header_name: str) -> Optional[Any]:
    header_name_lower = header_name.lower()
    for field in ("headers", "response_headers", "responseHeaders"):
        headers = response.get(field)
        if not isinstance(headers, dict):
            continue
        for key, value in headers.items():
            if str(key).lower() == header_name_lower:
                return value
    return None


def _gemini_header_service_tier(*responses: Dict[str, Any]) -> Optional[str]:
    for response in responses:
        if not isinstance(response, dict):
            continue
        service_tier = _normalize_gemini_service_tier(_response_header_value(response, "x-gemini-service-tier"))
        if service_tier:
            return service_tier
    return None


def _gemini_usage_context(
    usage: Dict[str, Any],
    response: Optional[Dict[str, Any]] = None,
    original_response: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    service_tier = _gemini_header_service_tier(original_response or {}, response or {})
    if not service_tier:
        service_tier = _normalize_gemini_service_tier(usage.get("serviceTier", usage.get("service_tier")))
    if not service_tier:
        return {}
    return {"service_tier": service_tier}


def extract_gemini_generate_content_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    original_response = response
    response = _gemini_generate_content_payload(response)
    usage = response.get("usageMetadata", {})
    cached_input = _decimal(usage.get("cachedContentTokenCount", 0))
    prompt_tokens = _decimal(usage.get("promptTokenCount", 0))
    candidates_tokens = _decimal(usage.get("candidatesTokenCount", 0))
    thoughts_tokens = _decimal(usage.get("thoughtsTokenCount", 0))
    prompt_counts = _gemini_modality_counts(usage.get("promptTokensDetails"))
    cache_counts = _gemini_modality_counts(usage.get("cacheTokensDetails"))
    tool_counts = _gemini_modality_counts(usage.get("toolUsePromptTokensDetails"))
    candidate_counts = _gemini_modality_counts(usage.get("candidatesTokensDetails"))

    tool_prompt_tokens = (
        _decimal(usage.get("toolUsePromptTokenCount", 0))
        if "toolUsePromptTokenCount" in usage
        else _gemini_sum_counts(tool_counts)
    )
    tool_remainder = tool_prompt_tokens - _gemini_sum_counts(tool_counts)
    if tool_remainder > 0:
        _gemini_add_count(tool_counts, "TEXT", tool_remainder)

    detail_safe_for_input = bool(prompt_counts) and (cached_input == 0 or bool(cache_counts))
    if detail_safe_for_input:
        input_quantities = _gemini_component_quantities(
            _gemini_net_input_counts(prompt_counts, cache_counts, tool_counts),
            GEMINI_INPUT_MODALITY_COMPONENTS,
            "input_uncached_tokens",
        )
        input_components = _gemini_ordered_components(
            input_quantities,
            GEMINI_INPUT_COMPONENT_ORDER,
            "$.usageMetadata.promptTokensDetails",
        )
        cache_read_source = "$.usageMetadata.cachedContentTokenCount"
        cache_read = cached_input or _gemini_sum_counts(cache_counts)
    else:
        input_components = [
            _positive_component(
                "input_uncached_tokens",
                _format_decimal(prompt_tokens - cached_input + tool_prompt_tokens),
                "token",
                "$.usageMetadata.promptTokenCount",
            )
        ]
        cache_read_source = "$.usageMetadata.cachedContentTokenCount"
        cache_read = cached_input

    if candidate_counts:
        output_quantities = _gemini_component_quantities(
            candidate_counts,
            GEMINI_OUTPUT_MODALITY_COMPONENTS,
            "output_text_tokens",
        )
        output_components = _gemini_ordered_components(
            output_quantities,
            GEMINI_OUTPUT_COMPONENT_ORDER,
            "$.usageMetadata.candidatesTokensDetails",
        )
    else:
        output_components = [
            _positive_component(
                "output_text_tokens",
                _format_decimal(candidates_tokens),
                "token",
                "$.usageMetadata.candidatesTokenCount",
            )
        ]

    ledger = _base_usage_ledger(
        provider=options.get("provider", "google"),
        surface=options.get("surface", "google.gemini.generate_content"),
        requested_model=options.get("model", response.get("modelVersion")),
        returned_model=response.get("modelVersion") or options.get("model"),
        raw_usage=usage,
        components=_compact_components(
            input_components[:1]
            + [
                _positive_component("input_cache_read_tokens", _format_decimal(cache_read), "token", cache_read_source),
            ]
            + input_components[1:]
            + output_components[:1]
            + [
                _positive_component("output_reasoning_tokens", _format_decimal(thoughts_tokens), "token", "$.usageMetadata.thoughtsTokenCount"),
            ]
            + output_components[1:]
        ),
    )
    context = _gemini_usage_context(usage, response=response, original_response=original_response)
    if context:
        ledger["context"] = context
    return ledger


def extract_gemini_live_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    response = _gemini_generate_content_payload(response)
    requested_model = options.get("model", response.get("modelVersion"))
    returned_model = response.get("modelVersion") or options.get("model")
    is_live_translate = any(_model_name_looks_gemini_live_translate(model_name) for model_name in (requested_model, returned_model))
    input_fallback_component = "input_audio_tokens" if is_live_translate else "input_uncached_tokens"
    output_fallback_component = "output_audio_tokens" if is_live_translate else "output_text_tokens"
    usage = response.get("usageMetadata", {})
    cached_input = _decimal(usage.get("cachedContentTokenCount", 0))
    prompt_tokens = _decimal(usage.get("promptTokenCount", 0))
    response_tokens = _decimal(usage.get("responseTokenCount", 0))
    thoughts_tokens = _decimal(usage.get("thoughtsTokenCount", 0))
    prompt_counts = _gemini_modality_counts(usage.get("promptTokensDetails"))
    cache_counts = _gemini_modality_counts(usage.get("cacheTokensDetails"))
    tool_counts = _gemini_modality_counts(usage.get("toolUsePromptTokensDetails"))
    response_counts = _gemini_modality_counts(usage.get("responseTokensDetails"))

    tool_prompt_tokens = (
        _decimal(usage.get("toolUsePromptTokenCount", 0))
        if "toolUsePromptTokenCount" in usage
        else _gemini_sum_counts(tool_counts)
    )
    tool_remainder = tool_prompt_tokens - _gemini_sum_counts(tool_counts)
    if tool_remainder > 0:
        _gemini_add_count(tool_counts, "TEXT", tool_remainder)

    detail_safe_for_input = bool(prompt_counts) and (cached_input == 0 or bool(cache_counts))
    if detail_safe_for_input:
        input_quantities = _gemini_component_quantities(
            _gemini_net_input_counts(prompt_counts, cache_counts, tool_counts),
            GEMINI_INPUT_MODALITY_COMPONENTS,
            "input_uncached_tokens",
        )
        input_components = _gemini_ordered_components(
            input_quantities,
            GEMINI_INPUT_COMPONENT_ORDER,
            "$.usageMetadata.promptTokensDetails",
        )
        cache_read_source = "$.usageMetadata.cachedContentTokenCount"
        cache_read = cached_input or _gemini_sum_counts(cache_counts)
    else:
        input_components = [
            _positive_component(
                input_fallback_component,
                _format_decimal(prompt_tokens - cached_input + tool_prompt_tokens),
                "token",
                "$.usageMetadata.promptTokenCount",
            )
        ]
        cache_read_source = "$.usageMetadata.cachedContentTokenCount"
        cache_read = cached_input

    if response_counts:
        output_quantities = _gemini_component_quantities(
            response_counts,
            GEMINI_OUTPUT_MODALITY_COMPONENTS,
            "output_text_tokens",
        )
        output_components = _gemini_ordered_components(
            output_quantities,
            GEMINI_OUTPUT_COMPONENT_ORDER,
            "$.usageMetadata.responseTokensDetails",
        )
    else:
        output_components = [
            _positive_component(
                output_fallback_component,
                _format_decimal(response_tokens),
                "token",
                "$.usageMetadata.responseTokenCount",
            )
        ]

    ledger = _base_usage_ledger(
        provider=options.get("provider", "google"),
        surface=options.get("surface", "google.gemini.live"),
        requested_model=requested_model,
        returned_model=returned_model,
        raw_usage=usage,
        components=_compact_components(
            input_components[:1]
            + [
                _positive_component("input_cache_read_tokens", _format_decimal(cache_read), "token", cache_read_source),
            ]
            + input_components[1:]
            + output_components[:1]
            + [
                _positive_component("output_reasoning_tokens", _format_decimal(thoughts_tokens), "token", "$.usageMetadata.thoughtsTokenCount"),
            ]
            + output_components[1:]
        ),
    )
    context = _gemini_usage_context(usage)
    if context:
        ledger["context"] = context
    return ledger


def _interaction_usage_from_parent(parent: Dict[str, Any], source_root: str) -> Optional[tuple[Dict[str, Any], str]]:
    metadata = parent.get("metadata") if isinstance(parent.get("metadata"), dict) else {}
    for key in ("total_usage", "totalUsage", "usage"):
        value = metadata.get(key)
        if isinstance(value, dict):
            return value, f"{source_root}.metadata.{key}"
    for key in ("total_usage", "totalUsage", "usage"):
        value = parent.get(key)
        if isinstance(value, dict):
            return value, f"{source_root}.{key}"
    return None


def _google_interactions_usage_payload(response: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
    result = _interaction_usage_from_parent(response, "$")
    if result is not None:
        return result
    interaction = response.get("interaction")
    if isinstance(interaction, dict):
        result = _interaction_usage_from_parent(interaction, "$.interaction")
        if result is not None:
            return result
    for collection_name in ("chunks", "stream", "events"):
        collection = response.get(collection_name)
        if not isinstance(collection, list):
            continue
        for index in range(len(collection) - 1, -1, -1):
            item = collection[index]
            if not isinstance(item, dict):
                continue
            result = _interaction_usage_from_parent(item, f"$.{collection_name}[{index}]")
            if result is not None:
                return result
    return {}, "$.metadata.total_usage"


def _google_interactions_response_value(response: Dict[str, Any], *keys: str) -> Optional[Any]:
    interaction = response.get("interaction") if isinstance(response.get("interaction"), dict) else {}
    for parent in (response, interaction):
        for key in keys:
            value = parent.get(key)
            if value:
                return value
    for collection_name in ("chunks", "stream", "events"):
        collection = response.get(collection_name)
        if not isinstance(collection, list):
            continue
        for item in reversed(collection):
            if not isinstance(item, dict):
                continue
            interaction = item.get("interaction") if isinstance(item.get("interaction"), dict) else {}
            for parent in (item, interaction):
                for key in keys:
                    value = parent.get(key)
                    if value:
                        return value
    return None


def _google_interactions_service_tier(response: Dict[str, Any], usage: Dict[str, Any]) -> Optional[str]:
    header_service_tier = _gemini_header_service_tier(response)
    if header_service_tier:
        return header_service_tier
    candidates: List[Any] = []
    for parent in (
        usage,
        response.get("metadata") if isinstance(response.get("metadata"), dict) else {},
        response.get("interaction") if isinstance(response.get("interaction"), dict) else {},
        response,
    ):
        candidates.extend([parent.get("service_tier"), parent.get("serviceTier")])
    for value in candidates:
        service_tier = _normalize_gemini_service_tier(value)
        if service_tier:
            return service_tier
    return _normalize_gemini_service_tier(
        _google_interactions_response_value(response, "service_tier", "serviceTier")
    )


def _google_interactions_modality_counts(value: Any) -> Dict[str, Decimal]:
    counts: Dict[str, Decimal] = {}
    if not isinstance(value, list):
        return counts
    for detail in value:
        if not isinstance(detail, dict):
            continue
        modality = str(detail.get("modality") or "text").strip().upper()
        if not modality:
            modality = "TEXT"
        quantity = detail.get("tokens", detail.get("tokenCount", 0))
        _gemini_add_count(counts, modality, _decimal(quantity))
    return counts


_GOOGLE_INTERACTIONS_GROUNDING_COMPONENTS = {
    "google_search": ("web_search_units", "search"),
    "google_maps": ("tool_call_units", "call"),
    "retrieval": ("tool_call_units", "call"),
}


def _google_interactions_grounding_components(usage: Dict[str, Any], source_root: str) -> List[Optional[Dict[str, Any]]]:
    components: List[Optional[Dict[str, Any]]] = []
    grounding_counts = usage.get("grounding_tool_count")
    if not isinstance(grounding_counts, list):
        return components
    totals: Dict[tuple[str, str], Decimal] = {}
    for detail in grounding_counts:
        if not isinstance(detail, dict):
            continue
        mapping = _GOOGLE_INTERACTIONS_GROUNDING_COMPONENTS.get(str(detail.get("type") or ""))
        if mapping is None:
            continue
        component_name, unit = mapping
        key = (component_name, unit)
        totals[key] = totals.get(key, Decimal("0")) + _decimal(detail.get("count", 0))
    for (component_name, unit), quantity in totals.items():
        components.append(
            _positive_component(
                component_name,
                _format_decimal(quantity),
                unit,
                f"{source_root}.grounding_tool_count[*].count",
            )
        )
    return components


def extract_google_interactions_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    usage, source_root = _google_interactions_usage_payload(response)
    cached_input = _decimal(usage.get("total_cached_tokens", 0))
    input_tokens = _decimal(usage.get("total_input_tokens", 0))
    output_tokens = _decimal(usage.get("total_output_tokens", 0))
    thoughts_tokens = _decimal(usage.get("total_thought_tokens", 0))
    tool_use_tokens = _decimal(usage.get("total_tool_use_tokens", 0))
    input_counts = _google_interactions_modality_counts(usage.get("input_tokens_by_modality"))
    cache_counts = _google_interactions_modality_counts(usage.get("cached_tokens_by_modality"))
    output_counts = _google_interactions_modality_counts(usage.get("output_tokens_by_modality"))
    tool_counts = _google_interactions_modality_counts(usage.get("tool_use_tokens_by_modality"))

    tool_remainder = tool_use_tokens - _gemini_sum_counts(tool_counts)
    if tool_remainder > 0:
        _gemini_add_count(tool_counts, "TEXT", tool_remainder)

    detail_safe_for_input = bool(input_counts) and (cached_input == 0 or bool(cache_counts))
    if detail_safe_for_input:
        input_components = _gemini_ordered_components(
            _gemini_component_quantities(
                _gemini_net_input_counts(input_counts, cache_counts, tool_counts),
                GEMINI_INPUT_MODALITY_COMPONENTS,
                "input_uncached_tokens",
            ),
            GEMINI_INPUT_COMPONENT_ORDER,
            f"{source_root}.input_tokens_by_modality",
        )
        cache_read = cached_input or _gemini_sum_counts(cache_counts)
        cache_read_source = (
            f"{source_root}.total_cached_tokens"
            if "total_cached_tokens" in usage
            else f"{source_root}.cached_tokens_by_modality"
        )
    else:
        input_components = [
            _positive_component(
                "input_uncached_tokens",
                _format_decimal(input_tokens - cached_input + tool_use_tokens),
                "token",
                f"{source_root}.total_input_tokens",
            )
        ]
        cache_read = cached_input
        cache_read_source = f"{source_root}.total_cached_tokens"

    if output_counts:
        output_components = _gemini_ordered_components(
            _gemini_component_quantities(
                output_counts,
                GEMINI_OUTPUT_MODALITY_COMPONENTS,
                "output_text_tokens",
            ),
            GEMINI_OUTPUT_COMPONENT_ORDER,
            f"{source_root}.output_tokens_by_modality",
        )
    else:
        output_components = [
            _positive_component(
                "output_text_tokens",
                _format_decimal(output_tokens),
                "token",
                f"{source_root}.total_output_tokens",
            )
        ]

    returned_model = _google_interactions_response_value(response, "model", "agent") or options.get("model")
    ledger = _base_usage_ledger(
        provider=options.get("provider", "google"),
        surface=options.get("surface", "google.gemini.interactions"),
        requested_model=options.get("model", returned_model),
        returned_model=returned_model,
        raw_usage=usage,
        components=_compact_components(
            input_components[:1]
            + [
                _positive_component("input_cache_read_tokens", _format_decimal(cache_read), "token", cache_read_source),
            ]
            + input_components[1:]
            + output_components[:1]
            + [
                _positive_component("output_reasoning_tokens", _format_decimal(thoughts_tokens), "token", f"{source_root}.total_thought_tokens"),
            ]
            + output_components[1:]
            + _google_interactions_grounding_components(usage, source_root)
        ),
    )
    service_tier = _google_interactions_service_tier(response, usage)
    if service_tier:
        ledger["context"] = {"service_tier": service_tier}
    return ledger


def extract_bedrock_converse_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    usage = response.get("usage", {})
    cache_read = usage.get("cacheReadInputTokens", 0)
    cache_write = usage.get("cacheWriteInputTokens", 0)
    cache_write_1h = sum(
        detail.get("inputTokens", 0)
        for detail in usage.get("cacheDetails", [])
        if detail.get("ttl") == "1h"
    )
    input_tokens = usage.get("inputTokens", 0)
    output_tokens = usage.get("outputTokens", 0)
    returned_model = response.get("modelId") or options.get("model")

    return _base_usage_ledger(
        provider=options.get("provider", "bedrock"),
        surface=options.get("surface", "aws.bedrock.converse"),
        requested_model=options.get("model", returned_model),
        returned_model=returned_model,
        raw_usage=usage,
        components=_compact_components(
            [
                _positive_component("input_uncached_tokens", input_tokens - cache_read - cache_write, "token", "$.usage.inputTokens"),
                _positive_component("input_cache_write_tokens", cache_write - cache_write_1h, "token", "$.usage.cacheWriteInputTokens"),
                _positive_component("input_cache_write_1h_tokens", cache_write_1h, "token", "$.usage.cacheDetails"),
                _positive_component("input_cache_read_tokens", cache_read, "token", "$.usage.cacheReadInputTokens"),
                _positive_component("output_text_tokens", output_tokens, "token", "$.usage.outputTokens"),
            ]
        ),
    )


def _bedrock_invoke_model_body(response: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
    body = response.get("body")
    if body is None:
        return response, "$"
    if isinstance(body, dict):
        return body, "$.body"
    if isinstance(body, (bytes, bytearray)):
        body = body.decode("utf-8")
    elif hasattr(body, "read"):
        body = body.read()
        if isinstance(body, (bytes, bytearray)):
            body = body.decode("utf-8")
    if isinstance(body, str):
        try:
            decoded = json.loads(body)
        except json.JSONDecodeError:
            return {}, "$.body"
        if isinstance(decoded, dict):
            return decoded, "$.body"
    return {}, "$.body"


def extract_bedrock_invoke_model_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    body, source_root = _bedrock_invoke_model_body(response)
    usage = body.get("usage", {})
    input_tokens = usage.get("input_tokens", 0)
    cache_write = usage.get("cache_creation_input_tokens", 0)
    cache_write_1h = usage.get("cache_creation_input_tokens_1h", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    returned_model = response.get("modelId") or response.get("model_id") or options.get("model") or body.get("model")

    return _base_usage_ledger(
        provider=options.get("provider", "bedrock"),
        surface=options.get("surface", "aws.bedrock.invoke_model"),
        requested_model=options.get("model", returned_model),
        returned_model=returned_model,
        raw_usage=usage,
        components=_compact_components(
            [
                _positive_component("input_uncached_tokens", input_tokens, "token", f"{source_root}.usage.input_tokens"),
                _positive_component("input_cache_write_tokens", cache_write - cache_write_1h, "token", f"{source_root}.usage.cache_creation_input_tokens"),
                _positive_component("input_cache_write_1h_tokens", cache_write_1h, "token", f"{source_root}.usage.cache_creation_input_tokens_1h"),
                _positive_component("input_cache_read_tokens", cache_read, "token", f"{source_root}.usage.cache_read_input_tokens"),
                _positive_component("output_text_tokens", output_tokens, "token", f"{source_root}.usage.output_tokens"),
            ]
        ),
    )


def _cohere_chat_usage_payload(response: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
    usage = response.get("usage")
    if isinstance(usage, dict) and "billed_units" in usage:
        return usage, "$.usage"
    meta = response.get("meta", {})
    return meta if isinstance(meta, dict) else {}, "$.meta"


def extract_cohere_chat_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    usage, source_root = _cohere_chat_usage_payload(response)
    billed_units = usage.get("billed_units", {})
    input_tokens = billed_units.get("input_tokens", 0)
    output_tokens = billed_units.get("output_tokens", 0)
    returned_model = response.get("model") or options.get("model")

    return _base_usage_ledger(
        provider=options.get("provider", "cohere"),
        surface=options.get("surface", "cohere.chat"),
        requested_model=options.get("model", returned_model),
        returned_model=returned_model,
        raw_usage=usage,
        components=_compact_components(
            [
                _positive_component("input_uncached_tokens", input_tokens, "token", f"{source_root}.billed_units.input_tokens"),
                _positive_component("output_text_tokens", output_tokens, "token", f"{source_root}.billed_units.output_tokens"),
            ]
        ),
    )


def extract_cohere_rerank_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    meta = response.get("meta") if isinstance(response.get("meta"), dict) else {}
    billed_units = meta.get("billed_units") if isinstance(meta.get("billed_units"), dict) else {}
    search_units = billed_units.get("search_units", 0)
    returned_model = response.get("model") or options.get("model")

    return _base_usage_ledger(
        provider=options.get("provider", "cohere"),
        surface=options.get("surface", "cohere.rerank"),
        requested_model=options.get("model", returned_model),
        returned_model=returned_model,
        raw_usage=meta,
        components=_compact_components(
            [
                _positive_component("rerank_search_units", search_units, "search", "$.meta.billed_units.search_units"),
            ]
        ),
    )


def extract_langchain_chat_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    usage = response.get("usage_metadata") or response.get("usageMetadata") or {}
    input_details = usage.get("input_token_details", {})
    output_details = usage.get("output_token_details", {})
    cache_read = input_details.get("cache_read", 0)
    cache_write = input_details.get("cache_creation", 0)
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    reasoning = output_details.get("reasoning", 0)
    metadata = response.get("response_metadata", {})
    returned_model = metadata.get("model_name") or metadata.get("model") or options.get("model")

    return _base_usage_ledger(
        provider=options.get("provider", "unknown"),
        surface=options.get("surface", "framework.langchain.chat"),
        requested_model=options.get("model", returned_model),
        returned_model=returned_model,
        raw_usage=usage,
        components=_compact_components(
            [
                _positive_component("input_uncached_tokens", input_tokens - cache_read - cache_write, "token", "$.usage_metadata.input_tokens"),
                _positive_component("input_cache_read_tokens", cache_read, "token", "$.usage_metadata.input_token_details.cache_read"),
                _positive_component("input_cache_write_tokens", cache_write, "token", "$.usage_metadata.input_token_details.cache_creation"),
                _positive_component("output_text_tokens", output_tokens - reasoning, "token", "$.usage_metadata.output_tokens"),
                _positive_component("output_reasoning_tokens", reasoning, "token", "$.usage_metadata.output_token_details.reasoning"),
            ]
        ),
    )


def _vercel_ai_sdk_usage_payload(response: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
    if isinstance(response.get("totalUsage"), dict):
        return response["totalUsage"], "$.totalUsage"
    if isinstance(response.get("usage"), dict):
        return response["usage"], "$.usage"
    return {}, "$.usage"


def _vercel_ai_sdk_raw_usage_payloads(response: Dict[str, Any], usage: Dict[str, Any]) -> List[Dict[str, Any]]:
    step_raw_usages = []
    for step in response.get("steps", []):
        step_usage = step.get("usage") if isinstance(step, dict) else None
        if isinstance(step_usage, dict) and isinstance(step_usage.get("raw"), dict):
            step_raw_usages.append(step_usage["raw"])
    if step_raw_usages:
        return step_raw_usages
    if isinstance(usage.get("raw"), dict):
        return [usage["raw"]]
    for candidate in (
        response.get("usage", {}).get("raw") if isinstance(response.get("usage"), dict) else None,
        response.get("totalUsage", {}).get("raw") if isinstance(response.get("totalUsage"), dict) else None,
        response.get("finalStep", {}).get("usage", {}).get("raw") if isinstance(response.get("finalStep"), dict) else None,
    ):
        if isinstance(candidate, dict):
            return [candidate]
    return []


def extract_vercel_ai_sdk_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    usage, source_root = _vercel_ai_sdk_usage_payload(response)
    orchestration_input, orchestration_cached_input, orchestration_output = _sum_openai_responses_orchestration_usage(
        _vercel_ai_sdk_raw_usage_payloads(response, usage)
    )
    input_details = usage.get("inputTokenDetails", {})
    output_details = usage.get("outputTokenDetails", {})
    cache_read = _decimal(input_details.get("cacheReadTokens", usage.get("cachedInputTokens", 0)) or 0)
    cache_write = input_details.get("cacheWriteTokens", 0)
    input_tokens = usage.get("inputTokens", 0)
    base_uncached = _decimal(input_details.get("noCacheTokens", _decimal(input_tokens or 0) - cache_read - _decimal(cache_write or 0)) or 0)
    uncached = base_uncached + orchestration_input - orchestration_cached_input
    cache_read += orchestration_cached_input
    output_tokens = usage.get("outputTokens", 0)
    reasoning = output_details.get("reasoningTokens", usage.get("reasoningTokens", 0))
    base_text_tokens = _decimal(output_details.get("textTokens", _decimal(output_tokens or 0) - _decimal(reasoning or 0)) or 0)
    text_tokens = base_text_tokens + orchestration_output
    response_metadata = response.get("response", {})
    model_metadata = response.get("model", {})
    returned_model = response_metadata.get("modelId") or model_metadata.get("modelId") or options.get("model")

    return _base_usage_ledger(
        provider=options.get("provider") or model_metadata.get("provider", "unknown"),
        surface=options.get("surface", "framework.vercel_ai_sdk"),
        requested_model=options.get("model", returned_model),
        returned_model=returned_model,
        raw_usage=usage,
        components=_compact_components(
            [
                _positive_component("input_uncached_tokens", _format_decimal(uncached), "token", f"{source_root}.inputTokenDetails.noCacheTokens"),
                _positive_component("input_cache_read_tokens", _format_decimal(cache_read), "token", f"{source_root}.inputTokenDetails.cacheReadTokens"),
                _positive_component("input_cache_write_tokens", cache_write, "token", f"{source_root}.inputTokenDetails.cacheWriteTokens"),
                _positive_component("output_text_tokens", _format_decimal(text_tokens), "token", f"{source_root}.outputTokenDetails.textTokens"),
                _positive_component("output_reasoning_tokens", reasoning, "token", f"{source_root}.outputTokenDetails.reasoningTokens"),
            ]
        ),
    )


def extract_llamaindex_token_counter_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    events = response.get("llm_token_counts", [])
    if events:
        prompt_tokens = sum(event.get("prompt_token_count", 0) for event in events)
        completion_tokens = sum(event.get("completion_token_count", 0) for event in events)
    else:
        prompt_tokens = response.get("prompt_llm_token_count", 0)
        completion_tokens = response.get("completion_llm_token_count", 0)

    returned_model = response.get("model") or options.get("model")
    return _base_usage_ledger(
        provider=options.get("provider", "unknown"),
        surface=options.get("surface", "framework.llamaindex.token_counter"),
        requested_model=options.get("model", returned_model),
        returned_model=returned_model,
        raw_usage=response,
        components=_compact_components(
            [
                _positive_component("input_uncached_tokens", prompt_tokens, "token", "$.llm_token_counts[*].prompt_token_count"),
                _positive_component("output_text_tokens", completion_tokens, "token", "$.llm_token_counts[*].completion_token_count"),
            ]
        ),
    )


def _haystack_usage_payload(response: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any], str]:
    replies = response.get("replies")
    if isinstance(replies, list) and replies:
        reply = replies[0]
        if isinstance(reply, dict):
            metadata = reply.get("_meta") or reply.get("meta") or {}
            if isinstance(metadata, dict):
                return metadata.get("usage") or {}, metadata, "$.replies[0]._meta.usage"
    meta = response.get("meta")
    if isinstance(meta, list) and meta:
        first_meta = meta[0]
        if isinstance(first_meta, dict):
            return first_meta.get("usage") or {}, first_meta, "$.meta[0].usage"
    if isinstance(meta, dict):
        return meta.get("usage") or {}, meta, "$.meta.usage"
    return response.get("usage") or {}, response, "$.usage"


def extract_haystack_generator_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    usage, metadata, source_root = _haystack_usage_payload(response)
    cached_input, cached_source = _openai_compatible_cached_input(usage)
    reasoning, reasoning_source = _openai_compatible_reasoning_output(usage)
    prompt_tokens = usage.get(
        "prompt_tokens",
        usage.get("prompt_cache_hit_tokens", 0) + usage.get("prompt_cache_miss_tokens", 0),
    )
    completion_tokens = usage.get("completion_tokens", 0)
    returned_model = metadata.get("model") or response.get("model") or options.get("model")

    return _base_usage_ledger(
        provider=options.get("provider", "unknown"),
        surface=options.get("surface", "framework.haystack.generator"),
        requested_model=options.get("model", returned_model),
        returned_model=returned_model,
        raw_usage=usage,
        components=_compact_components(
            [
                _positive_component("input_uncached_tokens", prompt_tokens - cached_input, "token", f"{source_root}.prompt_tokens"),
                _positive_component("input_cache_read_tokens", cached_input, "token", cached_source.replace("$.usage", source_root)),
                _positive_component("output_text_tokens", completion_tokens - reasoning, "token", f"{source_root}.completion_tokens"),
                _positive_component("output_reasoning_tokens", reasoning, "token", reasoning_source.replace("$.usage", source_root)),
            ]
        ),
    )


def extract_litellm_proxy_response_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    hidden = response.get("_hidden_params") or response.get("hidden_params") or {}
    if not isinstance(hidden, dict):
        hidden = {}
    provider = options.get("provider") or hidden.get("custom_llm_provider") or hidden.get("litellm_provider")
    merged_options = dict(options)
    if provider:
        merged_options["provider"] = provider
    return extract_openai_compatible_chat_completions_usage(response, **merged_options)


def _ag2_usage_summary_payload(response: Dict[str, Any], options: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
    mode = options.get("ag2_usage_mode") or options.get("usage_mode") or "actual"
    if "usage_excluding_cached_inference" in response or "usage_including_cached_inference" in response:
        if mode in {"total", "including_cached", "usage_including_cached_inference"}:
            return response.get("usage_including_cached_inference") or {}, "usage_including_cached_inference"
        return response.get("usage_excluding_cached_inference") or {}, "usage_excluding_cached_inference"
    return response, str(mode)


def _ag2_model_usage(summary: Dict[str, Any], requested_model: Optional[str]) -> tuple[str, Dict[str, Any]]:
    if requested_model and isinstance(summary.get(requested_model), dict):
        return requested_model, summary[requested_model]
    for key, value in summary.items():
        if key != "total_cost" and isinstance(value, dict):
            return key, value
    return requested_model or "unknown", {}


def extract_ag2_usage_summary_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    summary, mode = _ag2_usage_summary_payload(response, options)
    returned_model, model_usage = _ag2_model_usage(summary, options.get("model"))
    prompt_tokens = model_usage.get("prompt_tokens", 0)
    completion_tokens = model_usage.get("completion_tokens", 0)

    return _base_usage_ledger(
        provider=options.get("provider", "unknown"),
        surface=options.get("surface", "framework.ag2.usage_summary"),
        requested_model=options.get("model", returned_model),
        returned_model=returned_model,
        raw_usage={
            "mode": mode,
            "summary": summary,
            "model_usage": model_usage,
        },
        components=_compact_components(
            [
                _positive_component("input_uncached_tokens", prompt_tokens, "token", f"$.{mode}.{returned_model}.prompt_tokens"),
                _positive_component("output_text_tokens", completion_tokens, "token", f"$.{mode}.{returned_model}.completion_tokens"),
            ]
        ),
    )


def _first_present(mapping: Dict[str, Any], *keys: str, default: Any = 0) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return default


def _nested_dict(mapping: Dict[str, Any], *keys: str) -> Dict[str, Any]:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _openai_agents_usage_payload(response: Dict[str, Any]) -> tuple[Dict[str, Any], str, Dict[str, Any]]:
    if isinstance(response.get("usage"), dict):
        return response["usage"], "$.usage", response
    for root_key in ("context_wrapper", "context"):
        root = response.get(root_key)
        if isinstance(root, dict) and isinstance(root.get("usage"), dict):
            return root["usage"], f"$.{root_key}.usage", root
    return response, "$", response


def extract_openai_agents_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    usage, source_root, source_root_value = _openai_agents_usage_payload(response)
    input_details = _nested_dict(usage, "input_tokens_details")
    cached_input = input_details.get("cached_tokens", 0)
    cache_write = input_details.get("cache_write_tokens", 0)
    reasoning = _nested_dict(usage, "output_tokens_details").get("reasoning_tokens", 0)
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    returned_model = usage.get("model") or source_root_value.get("model") or response.get("model") or options.get("model")
    provider = options.get("provider", "openai")
    context = _usage_context_from_options(source_root_value, provider, options)

    return _base_usage_ledger(
        provider=provider,
        surface=options.get("surface", "openai.responses"),
        requested_model=options.get("model", returned_model),
        returned_model=returned_model,
        raw_usage=usage,
        context=context,
        components=_compact_components(
            [
                _positive_component("input_uncached_tokens", input_tokens - cached_input - cache_write, "token", f"{source_root}.input_tokens"),
                _positive_component("input_cache_read_tokens", cached_input, "token", f"{source_root}.input_tokens_details.cached_tokens"),
                _positive_component("input_cache_write_tokens", cache_write, "token", f"{source_root}.input_tokens_details.cache_write_tokens"),
                _positive_component("output_text_tokens", output_tokens - reasoning, "token", f"{source_root}.output_tokens"),
                _positive_component("output_reasoning_tokens", reasoning, "token", f"{source_root}.output_tokens_details.reasoning_tokens"),
            ]
        ),
    )


def _langsmith_usage_payload(response: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
    if isinstance(response.get("usage_metadata"), dict):
        return response["usage_metadata"], "$.usage_metadata"
    if isinstance(response.get("usageMetadata"), dict):
        return response["usageMetadata"], "$.usageMetadata"
    outputs = response.get("outputs")
    if isinstance(outputs, dict):
        if isinstance(outputs.get("usage_metadata"), dict):
            return outputs["usage_metadata"], "$.outputs.usage_metadata"
        if isinstance(outputs.get("usageMetadata"), dict):
            return outputs["usageMetadata"], "$.outputs.usageMetadata"
        llm_output = outputs.get("llm_output")
        if isinstance(llm_output, dict) and isinstance(llm_output.get("usage"), dict):
            return llm_output["usage"], "$.outputs.llm_output.usage"
    if any(key in response for key in ("input_tokens", "inputTokens", "prompt_tokens", "promptTokens")):
        return response, "$"
    return {}, "$.usage_metadata"


def _langsmith_model(response: Dict[str, Any], usage: Dict[str, Any], options: Dict[str, Any]) -> Optional[str]:
    serialized = response.get("serialized")
    serialized_kwargs = serialized.get("kwargs", {}) if isinstance(serialized, dict) else {}
    return (
        usage.get("model")
        or usage.get("model_name")
        or response.get("model")
        or response.get("model_name")
        or serialized_kwargs.get("model")
        or serialized_kwargs.get("model_name")
        or options.get("model")
    )


def extract_langsmith_run_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    usage, source_root = _langsmith_usage_payload(response)
    input_details = _nested_dict(usage, "input_token_details", "inputTokenDetails")
    output_details = _nested_dict(usage, "output_token_details", "outputTokenDetails")
    cache_read = _first_present(input_details, "cache_read", "cacheReadTokens", "cache_read_tokens", default=0)
    cache_write = _first_present(input_details, "cache_creation", "cacheWriteTokens", "cache_write_tokens", default=0)
    input_tokens = _first_present(usage, "input_tokens", "inputTokens", "prompt_tokens", "promptTokens", default=0)
    output_tokens = _first_present(usage, "output_tokens", "outputTokens", "completion_tokens", "completionTokens", default=0)
    reasoning = _first_present(output_details, "reasoning", "reasoningTokens", "reasoning_tokens", default=0)
    returned_model = _langsmith_model(response, usage, options)

    return _base_usage_ledger(
        provider=options.get("provider", "unknown"),
        surface=options.get("surface", "framework.langsmith.run_usage"),
        requested_model=options.get("model", returned_model),
        returned_model=returned_model,
        raw_usage=usage,
        components=_compact_components(
            [
                _positive_component("input_uncached_tokens", input_tokens - cache_read - cache_write, "token", f"{source_root}.input_tokens"),
                _positive_component("input_cache_read_tokens", cache_read, "token", f"{source_root}.input_token_details.cache_read"),
                _positive_component("input_cache_write_tokens", cache_write, "token", f"{source_root}.input_token_details.cache_creation"),
                _positive_component("output_text_tokens", output_tokens - reasoning, "token", f"{source_root}.output_tokens"),
                _positive_component("output_reasoning_tokens", reasoning, "token", f"{source_root}.output_token_details.reasoning"),
            ]
        ),
    )


def _semantic_kernel_usage_payload(response: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
    for key in ("usage", "token_usage", "tokenUsage"):
        if isinstance(response.get(key), dict):
            return response[key], f"$.{key}"
    metadata = response.get("metadata")
    if isinstance(metadata, dict):
        for key in ("usage", "token_usage", "tokenUsage"):
            if isinstance(metadata.get(key), dict):
                return metadata[key], f"$.metadata.{key}"
    return response, "$"


def extract_semantic_kernel_telemetry_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    usage, source_root = _semantic_kernel_usage_payload(response)
    input_tokens = _first_present(usage, "prompt_tokens", "promptTokens", "input_tokens", "inputTokens", default=0)
    output_tokens = _first_present(usage, "completion_tokens", "completionTokens", "output_tokens", "outputTokens", default=0)
    metadata = response.get("metadata") if isinstance(response.get("metadata"), dict) else {}
    returned_model = usage.get("model") or metadata.get("model") or response.get("model") or options.get("model")
    raw_usage = dict(usage)
    for key in ("plugin_name", "function_name", "pluginName", "functionName"):
        if key in response:
            raw_usage[key] = response[key]

    return _base_usage_ledger(
        provider=options.get("provider", "unknown"),
        surface=options.get("surface", "framework.semantic_kernel.telemetry"),
        requested_model=options.get("model", returned_model),
        returned_model=returned_model,
        raw_usage=raw_usage,
        components=_compact_components(
            [
                _positive_component("input_uncached_tokens", input_tokens, "token", f"{source_root}.prompt_tokens"),
                _positive_component("output_text_tokens", output_tokens, "token", f"{source_root}.completion_tokens"),
            ]
        ),
    )


def _openrouter_sdk_response_payload(response: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(response.get("response"), dict) and isinstance(response["response"].get("usage"), dict):
        return response["response"]
    return response


def extract_openrouter_sdk_response_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    payload = _openrouter_sdk_response_payload(response)
    usage = payload.get("usage", {})
    if any(key in usage for key in ("inputTokens", "outputTokens", "cachedTokens", "reasoningTokens")):
        input_tokens = _first_present(usage, "inputTokens", "promptTokens", default=0)
        cached_input = _first_present(usage, "cachedTokens", "cachedInputTokens", default=0)
        output_tokens = _first_present(usage, "outputTokens", "completionTokens", default=0)
        reasoning = _first_present(usage, "reasoningTokens", default=0)
        return _base_usage_ledger(
            provider=options.get("provider", "openrouter"),
            surface=options.get("surface", "openrouter.chat_completions"),
            requested_model=options.get("model", payload.get("model")),
            returned_model=payload.get("model"),
            raw_usage=usage,
            components=_compact_components(
                [
                    _positive_component("input_uncached_tokens", input_tokens - cached_input, "token", "$.usage.inputTokens"),
                    _positive_component("input_cache_read_tokens", cached_input, "token", "$.usage.cachedTokens"),
                    _positive_component("output_text_tokens", output_tokens - reasoning, "token", "$.usage.outputTokens"),
                    _positive_component("output_reasoning_tokens", reasoning, "token", "$.usage.reasoningTokens"),
                ]
            ),
        )
    merged_options = {"provider": "openrouter", "surface": "openrouter.chat_completions"}
    merged_options.update(options)
    return extract_openai_compatible_chat_completions_usage(payload, **merged_options)


def extract_usage_ledger(response: Any, **options: Any) -> Dict[str, Any]:
    response = _response_mapping(response)
    adapter = options.get("adapter") or options.get("framework")
    if adapter == "langchain.chat_message":
        return extract_langchain_chat_usage(response, **options)
    if adapter == "vercel_ai_sdk.generate_text":
        return extract_vercel_ai_sdk_usage(response, **options)
    if adapter == "vercel_ai_sdk.stream_text":
        return extract_vercel_ai_sdk_usage(response, **options)
    if adapter == "vercel_ai_sdk.stream_transcribe":
        merged_options = {"provider": "openai", "surface": "openai.audio_transcriptions"}
        merged_options.update(options)
        return extract_openai_audio_transcription_usage(response, **merged_options)
    if adapter == "llamaindex.token_counter":
        return extract_llamaindex_token_counter_usage(response, **options)
    if adapter == "haystack.generator_result":
        return extract_haystack_generator_usage(response, **options)
    if adapter == "litellm.proxy_response":
        return extract_litellm_proxy_response_usage(response, **options)
    if adapter == "ag2.usage_summary":
        return extract_ag2_usage_summary_usage(response, **options)
    if adapter == "openai_agents.usage":
        return extract_openai_agents_usage(response, **options)
    if adapter == "langsmith.run_usage":
        return extract_langsmith_run_usage(response, **options)
    if adapter == "semantic_kernel.telemetry":
        return extract_semantic_kernel_telemetry_usage(response, **options)
    if adapter == "openrouter.sdk_response":
        return extract_openrouter_sdk_response_usage(response, **options)

    surface = options.get("surface")
    if surface in {"openai.responses", "xai.responses", "meta.responses"}:
        return extract_openai_responses_usage(response, **options)
    if surface == "openai.embeddings":
        return extract_openai_embeddings_usage(response, **options)
    if surface == "openai.audio_transcriptions":
        return extract_openai_audio_transcription_usage(response, **options)
    if surface == "openai.images":
        return extract_openai_images_usage(response, **options)
    if surface == "openai.usage.images":
        return extract_openai_usage_images_usage(response, **options)
    if surface == "openai.usage.completions":
        return extract_openai_usage_completions_usage(response, **options)
    if surface == "openai.usage.audio_speeches":
        return extract_openai_usage_audio_speeches_usage(response, **options)
    if surface == "openai.usage.audio_transcriptions":
        return extract_openai_usage_audio_transcriptions_usage(response, **options)
    if surface == "openai.usage.embeddings":
        return extract_openai_usage_embeddings_usage(response, **options)
    if surface == "openai.vector_stores":
        return extract_openai_vector_store_storage_usage(response, **options)
    if surface == "openai.usage.code_interpreter_sessions":
        return extract_openai_usage_code_interpreter_sessions_usage(response, **options)
    if surface == "openai.chat_completions":
        return extract_openai_chat_completions_usage(response, **options)
    if surface in OPENAI_COMPATIBLE_CHAT_PROVIDERS:
        return extract_openai_compatible_chat_completions_usage(response, **options)
    if surface in {"anthropic.messages", "minimax.messages"}:
        return extract_anthropic_messages_usage(response, **options)
    if surface in {"google.gemini.generate_content", "vertex.gemini.generate_content"}:
        return extract_gemini_generate_content_usage(response, **options)
    if surface == "google.gemini.live":
        return extract_gemini_live_usage(response, **options)
    if surface == "google.gemini.interactions":
        return extract_google_interactions_usage(response, **options)
    if surface == "aws.bedrock.converse":
        return extract_bedrock_converse_usage(response, **options)
    if surface == "aws.bedrock.invoke_model":
        return extract_bedrock_invoke_model_usage(response, **options)
    if surface == "cohere.chat":
        return extract_cohere_chat_usage(response, **options)
    if surface == "cohere.rerank":
        return extract_cohere_rerank_usage(response, **options)
    raise ValueError(f"Unsupported surface: {surface}")


def infer_surface(response: Any, *, provider: Optional[str] = None) -> Optional[str]:
    """Infer only response shapes that identify an endpoint unambiguously."""

    payload = _response_mapping(response)
    provider_name = str(provider or "").lower()
    object_type = str(payload.get("object") or payload.get("type") or "").lower()
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    if isinstance(payload.get("usageMetadata"), dict) or isinstance(payload.get("usage_metadata"), dict):
        return "vertex.gemini.generate_content" if provider_name in {"vertex", "google-vertex"} else "google.gemini.generate_content"
    if object_type == "message" and ("input_tokens" in usage or "cache_read_input_tokens" in usage):
        return "minimax.messages" if provider_name == "minimax" else "anthropic.messages"
    if object_type == "response" or str(payload.get("id") or "").startswith("resp_") or (
        "output" in payload and "input_tokens" in usage
    ):
        if provider_name == "xai":
            return "xai.responses"
        if provider_name == "meta":
            return "meta.responses"
        return "openai.responses"
    if object_type == "list" and isinstance(payload.get("data"), list) and "prompt_tokens" in usage:
        return "openai.embeddings"
    if isinstance(payload.get("choices"), list) and usage:
        provider_surfaces = {
            "openai": "openai.chat_completions",
            "openrouter": "openrouter.chat_completions",
            "groq": "groq.chat_completions",
            "xai": "xai.chat_completions",
            "meta": "meta.chat_completions",
            "mistral": "mistral.chat_completions",
            "deepseek": "deepseek.chat_completions",
            "azure": "azure.openai.chat_completions",
            "huggingface": "huggingface.chat_completions",
            "nvidia": "nvidia.chat_completions",
            "tinker": "tinker.chat_completions",
            "kimi": "kimi.chat_completions",
            "ai21": "ai21.chat_completions",
            "arcee": "arcee.chat_completions",
            "cohere": "cohere.chat_completions_compatible",
            "dashscope": "dashscope.chat_completions",
            "inception": "inception.chat_completions",
            "poolside": "poolside.chat_completions",
            "xiaomi": "xiaomi.chat_completions",
            "zai": "zai.chat_completions",
            "zhipu": "zhipu.chat_completions",
        }
        return provider_surfaces.get(provider_name) or ("openai.chat_completions" if not provider_name else None)
    if isinstance(payload.get("metrics"), dict) and isinstance(payload.get("usage"), dict):
        return "aws.bedrock.converse"
    return None


def _unsupported_surface_ledger(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    surface = options.get("surface", "unknown")
    provider = options.get("provider", "unknown")
    model = options.get("model") or response.get("model") or "unknown"
    return {
        "schema_version": "0.1",
        "provider": provider,
        "surface": surface,
        "model": {
            "requested": model,
            "returned": response.get("model"),
            "billed": model,
            "alias_resolution": "unknown",
        },
        "currency": "USD",
        "components": [],
        "total": "0",
        "price_sources": [],
        "applied_discounts": [],
        "warnings": [
            {
                "code": "unknown_surface",
                "message": f"Unsupported surface: {surface}.",
                "metadata": {
                    "provider": provider,
                    "surface": surface,
                    "model": model,
                },
            }
        ],
    }


def _llm_prices_is_historical(data: Dict[str, Any]) -> bool:
    for price in data.get("prices", []):
        if isinstance(price, dict) and ("from_date" in price or "to_date" in price):
            return True
    return False


def price_cards_from_llm_prices(data: Dict[str, Any], **options: Any) -> List[Dict[str, Any]]:
    retrieved_at = options.get("retrieved_at") or options.get("retrievedAt") or f"{data.get('updated_at', '1970-01-01')}T00:00:00Z"
    default_url = "https://www.llm-prices.com/historical-v1.json" if _llm_prices_is_historical(data) else "https://www.llm-prices.com/current-v1.json"
    source_url = options.get("source_url") or options.get("sourceUrl") or default_url
    cards = []

    for price in data.get("prices", []):
        components = [
            {
                "usage_component": "input_uncached_tokens",
                "unit": "token",
                "price": {"amount": _number_string(price["input"]), "currency": "USD", "per": "1000000"},
            },
            {
                "usage_component": "output_text_tokens",
                "unit": "token",
                "price": {"amount": _number_string(price["output"]), "currency": "USD", "per": "1000000"},
            },
        ]
        if price.get("input_cached") is not None:
            components.append(
                {
                    "usage_component": "input_cache_read_tokens",
                    "unit": "token",
                    "price": {"amount": _number_string(price["input_cached"]), "currency": "USD", "per": "1000000"},
                }
            )

        cards.append(
            {
                "schema_version": "0.1",
                "id": f"{price['vendor']}:{price['id']}:llm-prices",
                "provider": price["vendor"],
                "model": price["id"],
                "aliases": [price["name"]] if price.get("name") else [],
                "effective": {
                    "from": price.get("from_date"),
                    "to": price.get("to_date"),
                },
                "components": components,
                "source": {
                    "name": "llm-prices",
                    "url": source_url,
                    "retrieved_at": retrieved_at,
                },
            }
        )

    return cards


def _add_price_component(
    components: List[Dict[str, Any]],
    usage_component: str,
    unit: str,
    amount: Any,
    per: str = "1",
    **extra: Any,
) -> None:
    if amount is None:
        return
    component = {
        "usage_component": usage_component,
        "unit": unit,
        "price": {"amount": _number_string(amount), "currency": "USD", "per": per},
    }
    component.update(extra)
    components.append(component)


def price_cards_from_litellm(data: Dict[str, Any], **options: Any) -> List[Dict[str, Any]]:
    retrieved_at = options.get("retrieved_at") or f"{data.get('updated_at', '1970-01-01')}T00:00:00Z"
    source_url = options.get("source_url", "https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json")
    cards = []
    for model, config in data.items():
        if model in {"sample_spec", "updated_at"} or not isinstance(config, dict):
            continue
        provider = config.get("litellm_provider") or options.get("provider", "unknown")
        components: List[Dict[str, Any]] = []
        _add_price_component(components, "input_uncached_tokens", "token", config.get("input_cost_per_token"))
        _add_price_component(components, "output_text_tokens", "token", config.get("output_cost_per_token"))
        _add_price_component(components, "input_cache_read_tokens", "token", config.get("cache_read_input_token_cost"))
        _add_price_component(components, "input_cache_write_tokens", "token", config.get("cache_creation_input_token_cost"))
        _add_price_component(components, "input_cache_write_1h_tokens", "token", config.get("cache_creation_input_token_cost_1h"))
        _add_price_component(
            components,
            "output_reasoning_tokens",
            "token",
            config.get("output_cost_per_reasoning_token", config.get("output_cost_per_token")),
        )
        if not components:
            continue
        cards.append(
            {
                "schema_version": "0.1",
                "id": f"{provider}:{model}:litellm",
                "provider": provider,
                "model": model,
                "components": components,
                "source": {
                    "name": "litellm",
                    "url": source_url,
                    "retrieved_at": retrieved_at,
                },
            }
        )
    return cards


def price_cards_from_portkey(data: Dict[str, Any], **options: Any) -> List[Dict[str, Any]]:
    retrieved_at = options.get("retrieved_at") or f"{data.get('updated_at', '1970-01-01')}T00:00:00Z"
    source_url = options.get("source_url", "https://github.com/Portkey-AI/models")
    provider = data.get("provider") or options.get("provider", "unknown")
    cards = []
    for model, entry in data.get("models", {}).items():
        pricing = entry.get("pricing") or entry.get("pay_as_you_go") or {}
        components: List[Dict[str, Any]] = []
        _add_price_component(
            components,
            "input_uncached_tokens",
            "token",
            None if pricing.get("request_token") is None else _multiply_divide(pricing["request_token"], "1", "100"),
        )
        _add_price_component(
            components,
            "output_text_tokens",
            "token",
            None if pricing.get("response_token") is None else _multiply_divide(pricing["response_token"], "1", "100"),
        )
        _add_price_component(
            components,
            "input_cache_read_tokens",
            "token",
            None if pricing.get("cache_read_input_token") is None else _multiply_divide(pricing["cache_read_input_token"], "1", "100"),
        )
        _add_price_component(
            components,
            "input_cache_write_tokens",
            "token",
            None if pricing.get("cache_write_input_token") is None else _multiply_divide(pricing["cache_write_input_token"], "1", "100"),
        )
        additional = pricing.get("additional_units", {})
        _add_price_component(
            components,
            "output_reasoning_tokens",
            "token",
            None if additional.get("thinking_token") is None else _multiply_divide(additional["thinking_token"], "1", "100"),
        )
        _add_price_component(
            components,
            "web_search_units",
            "search",
            None if additional.get("web_search") is None else _multiply_divide(additional["web_search"], "1", "100"),
        )
        if not components:
            continue
        cards.append(
            {
                "schema_version": "0.1",
                "id": f"{provider}:{model}:portkey",
                "provider": provider,
                "model": model,
                "components": components,
                "source": {
                    "name": "portkey",
                    "url": source_url,
                    "retrieved_at": retrieved_at,
                },
            }
        )
    return cards


def _openrouter_pricing_tiers(pricing: Any) -> List[Dict[str, Any]]:
    if isinstance(pricing, list):
        return [tier for tier in pricing if isinstance(tier, dict)]
    if isinstance(pricing, dict):
        return [pricing]
    return []


def _openrouter_tier_conditions(tiers: List[Dict[str, Any]], index: int) -> Dict[str, Any]:
    tier = tiers[index]
    conditions: Dict[str, Any] = {}
    if tier.get("min_context") is not None:
        conditions["min_total_input_tokens"] = _number_string(tier["min_context"])
    if tier.get("min_context") is None:
        next_min_context = next((candidate.get("min_context") for candidate in tiers[index + 1:] if candidate.get("min_context") is not None), None)
        if next_min_context is not None:
            conditions["max_total_input_tokens"] = _subtract(next_min_context, "1")
    return {"conditions": conditions} if conditions else {}


def _threshold_tier_conditions(tiers: List[Dict[str, Any]], index: int) -> Dict[str, Any]:
    tier = tiers[index]
    conditions: Dict[str, Any] = {}
    threshold = tier.get("threshold")
    if threshold is not None and _decimal(threshold) > 0:
        conditions["min_total_input_tokens"] = _number_string(threshold)
    next_threshold = next((candidate.get("threshold") for candidate in tiers[index + 1:] if candidate.get("threshold") is not None), None)
    if next_threshold is not None:
        conditions["max_total_input_tokens"] = _subtract(next_threshold, "1")
    return {"conditions": conditions} if conditions else {}


def price_cards_from_openrouter_models(data: Dict[str, Any], **options: Any) -> List[Dict[str, Any]]:
    retrieved_at = options.get("retrieved_at") or options.get("retrievedAt") or f"{data.get('updated_at', '1970-01-01')}T00:00:00Z"
    source_url = options.get("source_url") or options.get("sourceUrl") or "https://openrouter.ai/api/v1/models"
    provider = options.get("provider", "openrouter")
    cards = []
    for model in data.get("data", []):
        if not isinstance(model, dict):
            continue
        model_id = model.get("id") or model.get("canonical_slug")
        if not model_id:
            continue
        tiers = _openrouter_pricing_tiers(model.get("pricing"))
        components: List[Dict[str, Any]] = []
        for index, tier in enumerate(tiers):
            token_conditions = _openrouter_tier_conditions(tiers, index)
            _add_price_component(components, "input_uncached_tokens", "token", tier.get("prompt"), "1", **token_conditions)
            _add_price_component(components, "output_text_tokens", "token", tier.get("completion"), "1", **token_conditions)
            _add_price_component(components, "input_cache_read_tokens", "token", tier.get("input_cache_read"), "1", **token_conditions)
            _add_price_component(components, "input_cache_write_tokens", "token", tier.get("input_cache_write"), "1", **token_conditions)
            _add_price_component(components, "output_reasoning_tokens", "token", tier.get("internal_reasoning"), "1", **token_conditions)
            if index == 0:
                _add_price_component(components, "input_image_units", "image", tier.get("image"), "1")
                _add_price_component(components, "request_units", "request", tier.get("request"), "1")
                _add_price_component(components, "web_search_units", "search", tier.get("web_search"), "1")
        if not components:
            continue
        aliases = [
            alias
            for alias in [model.get("canonical_slug"), model.get("name")]
            if alias and alias != model_id
        ]
        effective: Dict[str, Any] = {}
        if model.get("expiration_date"):
            effective["to"] = model["expiration_date"]
        card = {
            "schema_version": "0.1",
            "id": f"{provider}:{model_id}:openrouter-models",
            "provider": provider,
            "model": model_id,
            "aliases": aliases,
            "components": components,
            "source": {
                "name": "openrouter",
                "url": source_url,
                "retrieved_at": retrieved_at,
            },
        }
        if effective:
            card["effective"] = effective
        cards.append(card)
    return cards


def _models_dev_tiers(cost: Any) -> List[Dict[str, Any]]:
    if not isinstance(cost, dict):
        return []
    raw_tiers = []
    for tier in cost.get("tiers", []):
        if not isinstance(tier, dict):
            continue
        tier_info = tier.get("tier") if isinstance(tier.get("tier"), dict) else {}
        if tier_info.get("type") == "context" and tier_info.get("size") is not None:
            raw_tiers.append({"cost": tier, "size": tier_info["size"]})
    raw_tiers.sort(key=lambda tier: _decimal(tier["size"]))
    base_conditions: Dict[str, Any] = {}
    if raw_tiers:
        base_conditions["max_total_input_tokens"] = _subtract(raw_tiers[0]["size"], "1")
    tiers = [{"cost": cost, "conditions": base_conditions}]
    for index, tier in enumerate(raw_tiers):
        conditions: Dict[str, Any] = {"min_total_input_tokens": _number_string(tier["size"])}
        if index + 1 < len(raw_tiers):
            conditions["max_total_input_tokens"] = _subtract(raw_tiers[index + 1]["size"], "1")
        tiers.append({"cost": tier["cost"], "conditions": conditions})
    return tiers


def _add_models_dev_cost_components(components: List[Dict[str, Any]], cost: Dict[str, Any], conditions: Dict[str, Any]) -> None:
    extra = {"conditions": conditions} if conditions else {}
    _add_price_component(components, "input_uncached_tokens", "token", cost.get("input"), "1000000", **extra)
    _add_price_component(components, "output_text_tokens", "token", cost.get("output"), "1000000", **extra)
    _add_price_component(components, "output_reasoning_tokens", "token", cost.get("reasoning"), "1000000", **extra)
    _add_price_component(components, "input_cache_read_tokens", "token", cost.get("cache_read"), "1000000", **extra)
    _add_price_component(components, "input_cache_write_tokens", "token", cost.get("cache_write"), "1000000", **extra)
    _add_price_component(components, "input_audio_tokens", "token", cost.get("input_audio"), "1000000", **extra)
    _add_price_component(components, "output_audio_tokens", "token", cost.get("output_audio"), "1000000", **extra)


def price_cards_from_models_dev(data: Dict[str, Any], **options: Any) -> List[Dict[str, Any]]:
    retrieved_at = options.get("retrieved_at") or options.get("retrievedAt") or f"{data.get('updated_at', '1970-01-01')}T00:00:00Z"
    source_url = options.get("source_url") or options.get("sourceUrl") or "https://models.dev/api.json"
    cards = []
    for provider_id, provider in data.items():
        if not isinstance(provider, dict):
            continue
        models = provider.get("models") if isinstance(provider.get("models"), dict) else {}
        for model_id, model in models.items():
            if not isinstance(model, dict):
                continue
            components: List[Dict[str, Any]] = []
            for tier in _models_dev_tiers(model.get("cost")):
                _add_models_dev_cost_components(components, tier["cost"], tier["conditions"])
            if not components:
                continue
            aliases = [
                alias
                for alias in [model.get("name"), f"{provider_id}/{model_id}"]
                if alias and alias != model_id
            ]
            metadata = {
                "models_dev": {
                    "provider_name": provider.get("name"),
                    "family": model.get("family"),
                    "limit": model.get("limit"),
                    "modalities": model.get("modalities"),
                    "reasoning": model.get("reasoning"),
                    "tool_call": model.get("tool_call"),
                    "status": model.get("status"),
                    "release_date": model.get("release_date"),
                    "last_updated": model.get("last_updated"),
                }
            }
            cards.append(
                {
                    "schema_version": "0.1",
                    "id": f"{provider_id}:{model_id}:models-dev",
                    "provider": provider_id,
                    "model": model_id,
                    "aliases": aliases,
                    "components": components,
                    "source": {
                        "name": "models.dev",
                        "url": source_url,
                        "retrieved_at": retrieved_at,
                        "license": "MIT",
                    },
                    "metadata": metadata,
                }
            )
    return cards


def _source_info(data: Dict[str, Any], default_name: str, default_url: str, **options: Any) -> Dict[str, Any]:
    source = data.get("source") if isinstance(data.get("source"), dict) else {}
    retrieved_at = (
        options.get("retrieved_at")
        or options.get("retrievedAt")
        or source.get("retrieved_at")
        or source.get("retrievedAt")
        or data.get("retrieved_at")
        or data.get("retrievedAt")
        or f"{data.get('updated_at', '1970-01-01')}T00:00:00Z"
    )
    source_info = {
        "name": options.get("source_name") or options.get("sourceName") or source.get("name") or default_name,
        "url": options.get("source_url") or options.get("sourceUrl") or source.get("url") or default_url,
        "retrieved_at": retrieved_at,
    }
    if source.get("version"):
        source_info["version"] = source["version"]
    if source.get("license"):
        source_info["license"] = source["license"]
    return source_info


def _component_amount(entry: Dict[str, Any], *keys: str) -> Any:
    prices = entry.get("prices") if isinstance(entry.get("prices"), dict) else {}
    pricing = entry.get("pricing") if isinstance(entry.get("pricing"), dict) else {}
    for key in keys:
        if key in entry:
            return entry[key]
        if key in prices:
            return prices[key]
        if key in pricing:
            return pricing[key]
    return None


def _normalize_price_card(card: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(card)
    schedule = _normalize_billing_schedule(normalized.get("billing_schedule") or normalized.get("billingSchedule"))
    if schedule:
        normalized["billing_schedule"] = schedule
        normalized.pop("billingSchedule", None)
    return normalized


def _price_cards_from_canonical_cards(raw_cards: Any) -> List[Dict[str, Any]]:
    if isinstance(raw_cards, list):
        return [_normalize_price_card(card) for card in raw_cards if isinstance(card, dict)]
    return []


def _source_cache_price_cards(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ("price_cards", "priceCards", "cards"):
        cards = entry.get(key)
        if isinstance(cards, list):
            return _price_cards_from_canonical_cards(cards)
    return []


def _source_cache_source(entry: Dict[str, Any]) -> Dict[str, Any]:
    source = entry.get("source") if isinstance(entry.get("source"), dict) else {}
    source_type = entry.get("type") or entry.get("source_type") or entry.get("sourceType")
    name = entry.get("name") or source.get("name") or source_type or "source-cache"
    info: Dict[str, Any] = {"name": name}
    url = entry.get("url") or source.get("url")
    if url:
        info["url"] = url
    retrieved_at = entry.get("retrieved_at") or entry.get("retrievedAt") or source.get("retrieved_at") or source.get("retrievedAt")
    if retrieved_at:
        info["retrieved_at"] = retrieved_at
    version = entry.get("version") or source.get("version")
    if version:
        info["version"] = version
    license_value = entry.get("license") or source.get("license")
    if license_value:
        info["license"] = license_value
    return info


def _source_cache_metadata(data: Dict[str, Any], entry: Dict[str, Any], card_count: int) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {"card_count": card_count}
    for output_key, *input_keys in (
        ("generated_at", "generated_at", "generatedAt"),
        ("checksum", "checksum", "sha256"),
        ("source_type", "type", "source_type", "sourceType"),
    ):
        for input_key in input_keys:
            value = entry.get(input_key) if input_key in entry else data.get(input_key)
            if value:
                metadata[output_key] = value
                break
    return metadata


def price_cards_from_source_cache(data: Any, **_: Any) -> List[Dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    entries = data.get("sources") if isinstance(data.get("sources"), list) else [data]
    cards: List[Dict[str, Any]] = []
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            continue
        raw_cards = _source_cache_price_cards(raw_entry)
        source = _source_cache_source(raw_entry)
        cache_metadata = _source_cache_metadata(data, raw_entry, len(raw_cards))
        for raw_card in raw_cards:
            card = dict(raw_card)
            card.setdefault("schema_version", "0.1")
            card.setdefault("source", source)
            metadata = dict(card.get("metadata")) if isinstance(card.get("metadata"), dict) else {}
            metadata["source_cache"] = cache_metadata
            card["metadata"] = metadata
            cards.append(card)
    return cards


def price_cards_from_json_file(path: Any, source_type: str = "user-pricing", **options: Any) -> List[Dict[str, Any]]:
    file_path = Path(path)
    data = json.loads(file_path.read_text(encoding="utf-8"))
    adapter_options = dict(options)
    adapter_options.setdefault("source_url", file_path.resolve().as_uri())
    adapter_options.setdefault("sourceUrl", file_path.resolve().as_uri())
    if source_type == "llm-prices":
        return price_cards_from_llm_prices(data, **adapter_options)
    if source_type == "litellm":
        return price_cards_from_litellm(data, **adapter_options)
    if source_type == "openrouter-models":
        return price_cards_from_openrouter_models(data, **adapter_options)
    if source_type == "models-dev":
        return price_cards_from_models_dev(data, **adapter_options)
    if source_type == "official-snapshot":
        return price_cards_from_official_snapshot(data, **adapter_options)
    if source_type == "portkey":
        return price_cards_from_portkey(data, **adapter_options)
    if source_type == "source-cache":
        return price_cards_from_source_cache(data, **adapter_options)
    if source_type == "user-pricing":
        return price_cards_from_user_pricing(data, **adapter_options)
    if source_type == "helicone":
        return price_cards_from_helicone(data, **adapter_options)
    raise ValueError(f"Unsupported JSON price source type: {source_type}")


def _strip_yaml_comment(line: str) -> str:
    in_quote: Optional[str] = None
    for index, char in enumerate(line):
        if char in {"'", '"'}:
            in_quote = None if in_quote == char else char if in_quote is None else in_quote
        if char == "#" and in_quote is None and (index == 0 or line[index - 1].isspace()):
            return line[:index].rstrip()
    return line.rstrip()


def _yaml_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"", "null", "Null", "NULL", "~"}:
        return None
    if value in {"true", "True", "TRUE"}:
        return True
    if value in {"false", "False", "FALSE"}:
        return False
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_yaml_scalar(part.strip()) for part in inner.split(",")]
    return value


def _yaml_key_value(content: str) -> tuple[str, str]:
    if ":" not in content:
        raise ValueError(f"Unsupported YAML line: {content}")
    key, value = content.split(":", 1)
    return key.strip(), value.strip()


def _yaml_lines(text: str) -> List[tuple[int, str]]:
    lines: List[tuple[int, str]] = []
    for raw_line in text.splitlines():
        cleaned = _strip_yaml_comment(raw_line.rstrip())
        if not cleaned.strip():
            continue
        indent = len(cleaned) - len(cleaned.lstrip(" "))
        lines.append((indent, cleaned.strip()))
    return lines


def _parse_yaml_block(lines: List[tuple[int, str]], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(lines) or lines[index][0] < indent:
        return {}, index
    if lines[index][1].startswith("- "):
        values: List[Any] = []
        while index < len(lines) and lines[index][0] == indent and lines[index][1].startswith("- "):
            rest = lines[index][1][2:].strip()
            index += 1
            if not rest:
                value, index = _parse_yaml_block(lines, index, indent + 2)
                values.append(value)
            elif ":" in rest:
                key, raw_value = _yaml_key_value(rest)
                item: Dict[str, Any] = {}
                if raw_value:
                    item[key] = _yaml_scalar(raw_value)
                else:
                    item[key], index = _parse_yaml_block(lines, index, indent + 2)
                if index < len(lines) and lines[index][0] >= indent + 2:
                    extra, index = _parse_yaml_block(lines, index, indent + 2)
                    if isinstance(extra, dict):
                        item.update(extra)
                values.append(item)
            else:
                values.append(_yaml_scalar(rest))
        return values, index

    mapping: Dict[str, Any] = {}
    while index < len(lines):
        line_indent, content = lines[index]
        if line_indent < indent:
            break
        if line_indent > indent or content.startswith("- "):
            break
        key, raw_value = _yaml_key_value(content)
        index += 1
        if raw_value:
            mapping[key] = _yaml_scalar(raw_value)
        else:
            mapping[key], index = _parse_yaml_block(lines, index, indent + 2)
    return mapping, index


def _parse_simple_yaml(text: str) -> Any:
    lines = _yaml_lines(text)
    if not lines:
        return {}
    data, index = _parse_yaml_block(lines, 0, lines[0][0])
    if index != len(lines):
        raise ValueError("Unsupported YAML structure")
    return data


def price_cards_from_yaml_file(path: Any, source_type: str = "user-pricing", **options: Any) -> List[Dict[str, Any]]:
    file_path = Path(path)
    data = _parse_simple_yaml(file_path.read_text(encoding="utf-8"))
    adapter_options = dict(options)
    adapter_options.setdefault("source_url", file_path.resolve().as_uri())
    adapter_options.setdefault("sourceUrl", file_path.resolve().as_uri())
    return _price_cards_from_source_data(data, source_type, **adapter_options)


def _price_cards_from_source_data(data: Any, source_type: str, **adapter_options: Any) -> List[Dict[str, Any]]:
    if source_type == "llm-prices":
        return price_cards_from_llm_prices(data, **adapter_options)
    if source_type == "litellm":
        return price_cards_from_litellm(data, **adapter_options)
    if source_type == "openrouter-models":
        return price_cards_from_openrouter_models(data, **adapter_options)
    if source_type == "models-dev":
        return price_cards_from_models_dev(data, **adapter_options)
    if source_type == "official-snapshot":
        return price_cards_from_official_snapshot(data, **adapter_options)
    if source_type == "portkey":
        return price_cards_from_portkey(data, **adapter_options)
    if source_type == "source-cache":
        return price_cards_from_source_cache(data, **adapter_options)
    if source_type == "user-pricing":
        return price_cards_from_user_pricing(data, **adapter_options)
    if source_type == "helicone":
        return price_cards_from_helicone(data, **adapter_options)
    raise ValueError(f"Unsupported price source type: {source_type}")


def _official_snapshot_component(components: List[Dict[str, Any]], row: Dict[str, Any], component_name: str, unit: str, keys: Iterable[str], per: str) -> None:
    _add_price_component(components, component_name, unit, _component_amount(row, *keys), per)


def price_cards_from_official_snapshot(data: Any, **options: Any) -> List[Dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    for key in ("price_cards", "priceCards"):
        if key in data:
            return _price_cards_from_canonical_cards(data[key])

    source = _source_info(data, "official-snapshot", "file://official-pricing-snapshot", **options)
    provider_default = data.get("provider") or options.get("provider", "unknown")
    surface_default = data.get("surface") or options.get("surface")
    per_default = _number_string(data.get("per", "1000000"))
    schedule_default = _normalize_billing_schedule(data.get("billing_schedule") or data.get("billingSchedule"))
    tool_price_defaults = data.get("tool_prices") or data.get("toolPrices") or {}
    if not isinstance(tool_price_defaults, dict):
        tool_price_defaults = {}
    rows = data.get("rows") or data.get("models") or []
    cards: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        model = row.get("model") or row.get("id")
        provider = row.get("provider") or provider_default
        if not model or not provider:
            continue
        per = _number_string(row.get("per", per_default))
        row_tool_prices = row.get("tool_prices") or row.get("toolPrices") or {}
        if not isinstance(row_tool_prices, dict):
            row_tool_prices = {}
        pricing_row = {**tool_price_defaults, **row_tool_prices, **row}
        components: List[Dict[str, Any]] = []
        for raw_component in row.get("components", []):
            if not isinstance(raw_component, dict):
                continue
            amount = raw_component.get("amount")
            if amount is None and isinstance(raw_component.get("price"), dict):
                amount = raw_component["price"].get("amount")
            extra: Dict[str, Any] = {}
            if isinstance(raw_component.get("conditions"), dict):
                extra["conditions"] = raw_component["conditions"]
            if isinstance(raw_component.get("discount_eligible"), bool):
                extra["discount_eligible"] = raw_component["discount_eligible"]
            if isinstance(raw_component.get("notes"), str):
                extra["notes"] = raw_component["notes"]
            _add_price_component(
                components,
                raw_component.get("usage_component"),
                raw_component.get("unit", "token"),
                amount,
                _number_string(raw_component.get("per") or raw_component.get("price", {}).get("per") or per),
                **extra,
            )
        _official_snapshot_component(components, pricing_row, "input_uncached_tokens", "token", ("input", "prompt", "input_uncached"), per)
        _official_snapshot_component(components, pricing_row, "input_cache_read_tokens", "token", ("cache_read", "cached_input", "input_cache_read"), per)
        _official_snapshot_component(components, pricing_row, "input_cache_write_tokens", "token", ("cache_write", "input_cache_write"), per)
        _official_snapshot_component(components, pricing_row, "input_cache_write_1h_tokens", "token", ("cache_write_1h", "input_cache_write_1h"), per)
        _official_snapshot_component(components, pricing_row, "output_text_tokens", "token", ("output", "completion", "output_text"), per)
        _official_snapshot_component(components, pricing_row, "output_reasoning_tokens", "token", ("reasoning", "thinking", "output_reasoning"), per)
        _official_snapshot_component(components, pricing_row, "input_audio_tokens", "token", ("input_audio", "audio_input"), per)
        _official_snapshot_component(components, pricing_row, "output_audio_tokens", "token", ("output_audio", "audio_output"), per)
        _official_snapshot_component(components, pricing_row, "request_units", "request", ("request", "per_request"), "1")
        _official_snapshot_component(components, pricing_row, "web_search_units", "search", ("web_search", "search"), "1")
        _official_snapshot_component(components, pricing_row, "x_search_units", "search", ("x_search",), "1")
        _official_snapshot_component(components, pricing_row, "file_search_units", "call", ("file_search", "collections_search"), "1")
        _official_snapshot_component(components, pricing_row, "code_interpreter_call_units", "call", ("code_interpreter_call", "code_interpreter", "code_execution"), "1")
        _official_snapshot_component(components, pricing_row, "attachment_search_units", "call", ("attachment_search",), "1")
        if not components:
            continue
        pricing_period = row.get("pricing_period") or row.get("pricingPeriod")
        default_card_id = f"{provider}:{model}:official-snapshot"
        if pricing_period:
            default_card_id = f"{provider}:{model}:{pricing_period}:official-snapshot"
        card = {
            "schema_version": "0.1",
            "id": row.get("price_card_id") or row.get("priceCardId") or default_card_id,
            "provider": provider,
            "model": model,
            "aliases": row.get("aliases", []),
            "components": components,
            "source": source,
        }
        surface = row.get("surface") or surface_default
        if surface:
            card["surface"] = surface
        for key in ("service_tier", "region"):
            if row.get(key):
                card[key] = row[key]
        if pricing_period:
            card["pricing_period"] = pricing_period
        schedule = _normalize_billing_schedule(row.get("billing_schedule") or row.get("billingSchedule")) or schedule_default
        if schedule:
            card["billing_schedule"] = schedule
        if isinstance(row.get("effective"), dict):
            card["effective"] = row["effective"]
        metadata = {
            "official_snapshot": {
                "source_label": row.get("source_label") or row.get("sourceLabel"),
                "notes": row.get("notes"),
                "capabilities": row.get("capabilities"),
            },
            "source_capabilities": row.get("capabilities") if isinstance(row.get("capabilities"), dict) else {},
        }
        card["metadata"] = metadata
        cards.append(card)
        service_tier = card.get("service_tier")
        service_tier_aliases = (row.get("capabilities") or {}).get("service_tier_aliases", [])
        for raw_alias in service_tier_aliases if isinstance(service_tier_aliases, list) else []:
            alias = str(raw_alias or "").strip().lower()
            if not alias or alias == service_tier:
                continue
            marker = f":{service_tier}:" if service_tier else ""
            alias_id = str(card["id"]).replace(marker, f":{alias}:", 1) if marker and marker in str(card["id"]) else f"{card['id']}:{alias}"
            alias_card = {
                **card,
                "id": alias_id,
                "service_tier": alias,
                "metadata": {
                    **metadata,
                    "service_tier_resolution": {
                        "independent_card": True,
                        "currently_equivalent_to": service_tier,
                    },
                },
            }
            cards.append(alias_card)
    return cards


def price_cards_from_user_pricing(data: Any, **options: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return _price_cards_from_canonical_cards(data)
    if not isinstance(data, dict):
        return []
    for key in ("price_cards", "priceCards"):
        if key in data:
            return _price_cards_from_canonical_cards(data[key])

    source = _source_info(data, "user-pricing", "file://user-pricing", **options)
    provider_default = data.get("provider") or options.get("provider", "user")
    surface_default = data.get("surface") or options.get("surface")
    service_tier_default = data.get("service_tier") or data.get("serviceTier")
    pricing_period_default = data.get("pricing_period") or data.get("pricingPeriod")
    schedule_default = _normalize_billing_schedule(data.get("billing_schedule") or data.get("billingSchedule"))
    region_default = data.get("region")
    per_default = _number_string(data.get("per", "1000000"))
    cards: List[Dict[str, Any]] = []

    for entry in data.get("models", []):
        if not isinstance(entry, dict):
            continue
        if entry.get("components") and entry.get("provider") and (entry.get("model") or entry.get("id")):
            card = dict(entry)
            card.setdefault("schema_version", "0.1")
            card.setdefault("model", card.get("id"))
            card.setdefault("source", source)
            schedule = _normalize_billing_schedule(card.get("billing_schedule") or card.get("billingSchedule"))
            if schedule:
                card["billing_schedule"] = schedule
                card.pop("billingSchedule", None)
            cards.append(card)
            continue

        model = entry.get("model") or entry.get("id")
        if not model:
            continue
        provider = entry.get("provider") or provider_default
        per = _number_string(entry.get("per", per_default))
        components: List[Dict[str, Any]] = []
        _add_price_component(components, "input_uncached_tokens", "token", _component_amount(entry, "input", "input_uncached", "input_uncached_tokens"), per)
        _add_price_component(components, "input_cache_read_tokens", "token", _component_amount(entry, "cached_input", "input_cached", "cache_read", "input_cache_read"), per)
        _add_price_component(components, "input_cache_write_tokens", "token", _component_amount(entry, "cache_write", "input_cache_write"), per)
        _add_price_component(components, "input_cache_write_1h_tokens", "token", _component_amount(entry, "cache_write_1h", "input_cache_write_1h"), per)
        _add_price_component(components, "output_text_tokens", "token", _component_amount(entry, "output", "completion", "output_text"), per)
        _add_price_component(components, "output_reasoning_tokens", "token", _component_amount(entry, "reasoning", "thinking", "output_reasoning"), per)
        _add_price_component(components, "request_units", "request", _component_amount(entry, "request", "per_request"), "1")
        _add_price_component(components, "web_search_units", "search", _component_amount(entry, "web_search"), "1")
        if not components:
            continue

        card = {
            "schema_version": "0.1",
            "id": entry.get("price_card_id") or entry.get("priceCardId") or f"{provider}:{model}:user-pricing",
            "provider": provider,
            "model": model,
            "aliases": entry.get("aliases", []),
            "components": components,
            "source": source,
        }
        surface = entry.get("surface") or surface_default
        if surface:
            card["surface"] = surface
        service_tier = entry.get("service_tier") or entry.get("serviceTier") or service_tier_default
        if service_tier:
            card["service_tier"] = service_tier
        pricing_period = entry.get("pricing_period") or entry.get("pricingPeriod") or pricing_period_default
        if pricing_period:
            card["pricing_period"] = pricing_period
        schedule = _normalize_billing_schedule(entry.get("billing_schedule") or entry.get("billingSchedule")) or schedule_default
        if schedule:
            card["billing_schedule"] = schedule
        region = entry.get("region") or region_default
        if region:
            card["region"] = region
        effective = entry.get("effective")
        if isinstance(effective, dict):
            card["effective"] = effective
        cards.append(card)
    return cards


def _helicone_endpoint_items(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    endpoints = data.get("endpoints") if isinstance(data.get("endpoints"), dict) else data
    if isinstance(endpoints, dict):
        return [entry for entry in endpoints.values() if isinstance(entry, dict)]
    if isinstance(endpoints, list):
        return [entry for entry in endpoints if isinstance(entry, dict)]
    return []


def _helicone_pricing_tiers(pricing: Any) -> List[Dict[str, Any]]:
    tiers = pricing if isinstance(pricing, list) else [pricing]
    return sorted([tier for tier in tiers if isinstance(tier, dict)], key=lambda tier: _decimal(tier.get("threshold", 0)))


def _helicone_add_modality_components(components: List[Dict[str, Any]], tier: Dict[str, Any], modality: str, conditions: Dict[str, Any]) -> None:
    pricing = tier.get(modality)
    if not isinstance(pricing, dict):
        return
    component_names = {
        "image": ("input_image_tokens", "output_image_tokens"),
        "audio": ("input_audio_tokens", "output_audio_tokens"),
        "video": ("input_video_tokens", "output_video_tokens"),
    }
    if modality not in component_names:
        return
    input_component, output_component = component_names[modality]
    _add_price_component(components, input_component, "token", pricing.get("input"), "1", **conditions)
    _add_price_component(components, output_component, "token", pricing.get("output"), "1", **conditions)


def price_cards_from_helicone(data: Dict[str, Any], **options: Any) -> List[Dict[str, Any]]:
    source = _source_info(data, "helicone", "https://github.com/Helicone/helicone/tree/main/packages/cost", **options)
    cards: List[Dict[str, Any]] = []
    for endpoint in _helicone_endpoint_items(data):
        model = endpoint.get("providerModelId")
        provider = endpoint.get("provider") or options.get("provider")
        if not model or not provider:
            continue
        tiers = _helicone_pricing_tiers(endpoint.get("pricing"))
        components: List[Dict[str, Any]] = []
        for index, tier in enumerate(tiers):
            conditions = _threshold_tier_conditions(tiers, index)
            input_price = tier.get("input")
            _add_price_component(components, "input_uncached_tokens", "token", input_price, "1", **conditions)
            _add_price_component(components, "output_text_tokens", "token", tier.get("output"), "1", **conditions)
            cache_multipliers = tier.get("cacheMultipliers") if isinstance(tier.get("cacheMultipliers"), dict) else {}
            if input_price is not None:
                if cache_multipliers.get("cachedInput") is not None:
                    _add_price_component(components, "input_cache_read_tokens", "token", _multiply_divide(input_price, cache_multipliers["cachedInput"], "1"), "1", **conditions)
                if cache_multipliers.get("write5m") is not None:
                    _add_price_component(components, "input_cache_write_tokens", "token", _multiply_divide(input_price, cache_multipliers["write5m"], "1"), "1", **conditions)
                if cache_multipliers.get("write1h") is not None:
                    _add_price_component(components, "input_cache_write_1h_tokens", "token", _multiply_divide(input_price, cache_multipliers["write1h"], "1"), "1", **conditions)
            _add_price_component(components, "output_reasoning_tokens", "token", tier.get("thinking"), "1", **conditions)
            if index == 0:
                _add_price_component(components, "request_units", "request", tier.get("request"), "1")
                _add_price_component(components, "web_search_units", "search", tier.get("web_search"), "1")
            for modality in ("image", "audio", "video"):
                _helicone_add_modality_components(components, tier, modality, conditions)
        if not components:
            continue
        aliases = []
        for alias in endpoint.get("providerModelIdAliases", []) or []:
            if alias and alias != model:
                aliases.append(alias)
        card = {
            "schema_version": "0.1",
            "id": f"{provider}:{model}:helicone",
            "provider": provider,
            "model": model,
            "aliases": aliases,
            "components": components,
            "source": source,
            "metadata": {
                "author": endpoint.get("author"),
                "context_length": endpoint.get("contextLength"),
                "max_completion_tokens": endpoint.get("maxCompletionTokens"),
                "ptb_enabled": endpoint.get("ptbEnabled"),
            },
        }
        cards.append(card)
    return cards


def from_response(
    response: Any,
    *,
    adapter: Optional[str] = None,
    framework: Optional[str] = None,
    provider: Optional[str] = None,
    surface: Optional[str] = None,
    model: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    priced_at: Optional[str] = None,
    pricing_period: Optional[str] = None,
    storage_days: Optional[Any] = None,
    storageDays: Optional[Any] = None,
    ag2_usage_mode: Optional[str] = None,
    anthropic_fallback_credit: Optional[bool] = None,
    anthropicFallbackCredit: Optional[bool] = None,
    fallback_credit: Optional[bool] = None,
    fallbackCredit: Optional[bool] = None,
    attribution: Optional[Dict[str, Any]] = None,
    price_cards: Optional[Iterable[Dict[str, Any]]] = None,
    discount_policies: Optional[Iterable[Dict[str, Any]]] = None,
    mode: str = "compatibility",
    stale_after_days: Optional[int] = None,
    provider_reported_cost: Optional[Any] = None,
    provider_reported_cost_mode: str = "compare",
    price_source_priority: Optional[Iterable[str]] = None,
    debug_trace: bool = False,
) -> Dict[str, Any]:
    response = _response_mapping(response)
    resolved_surface = surface or infer_surface(response, provider=provider)
    options: Dict[str, Any] = {"surface": resolved_surface or "unknown"}
    if adapter:
        options["adapter"] = adapter
    if framework:
        options["framework"] = framework
    if provider:
        options["provider"] = provider
    if model:
        options["model"] = model
    if context:
        options["context"] = context
    if priced_at is not None:
        options["priced_at"] = priced_at
    if pricing_period is not None:
        options["pricing_period"] = pricing_period
    if storage_days is not None:
        options["storage_days"] = storage_days
    if storageDays is not None:
        options["storageDays"] = storageDays
    if ag2_usage_mode:
        options["ag2_usage_mode"] = ag2_usage_mode
    if anthropic_fallback_credit is not None:
        options["anthropic_fallback_credit"] = anthropic_fallback_credit
    if anthropicFallbackCredit is not None:
        options["anthropicFallbackCredit"] = anthropicFallbackCredit
    if fallback_credit is not None:
        options["fallback_credit"] = fallback_credit
    if fallbackCredit is not None:
        options["fallbackCredit"] = fallbackCredit
    try:
        usage_ledger = extract_usage_ledger(response, **options)
    except ValueError:
        if mode == "strict":
            raise
        return _unsupported_surface_ledger(response, **options)
    if context:
        merged_context = {**(usage_ledger.get("context") or {}), **context}
        if usage_ledger.get("provider") == "openai":
            context_tier = merged_context.get("service_tier", merged_context.get("serviceTier"))
            if context_tier is not None:
                normalized_tier = _normalize_openai_service_tier(context_tier)
                if normalized_tier:
                    merged_context["service_tier"] = normalized_tier
                merged_context.pop("serviceTier", None)
        usage_ledger["context"] = merged_context
    normalized_attribution = _normalize_attribution(attribution)
    if normalized_attribution:
        usage_ledger["attribution"] = normalized_attribution
    extracted_provider_reported_cost = _provider_reported_cost_from_raw_response(response, usage_ledger)
    resolved_price_cards: Union[Iterable[Dict[str, Any]], CompiledPriceCatalog]
    if isinstance(price_cards, CompiledPriceCatalog):
        resolved_price_cards = price_cards
    else:
        resolved_price_cards = list(price_cards or [])
    return calculate_cost(
        usage_ledger=usage_ledger,
        price_cards=resolved_price_cards,
        discount_policies=discount_policies,
        mode=mode,
        stale_after_days=stale_after_days,
        provider_reported_cost=provider_reported_cost if provider_reported_cost is not None else extracted_provider_reported_cost,
        provider_reported_cost_mode=provider_reported_cost_mode,
        price_source_priority=price_source_priority,
        debug_trace=debug_trace,
    )


def from_langchain_message(message: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    merged_options = dict(options)
    merged_options["adapter"] = "langchain.chat_message"
    return from_response(message, **merged_options)


def from_vercel_ai_sdk_result(result: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    merged_options = dict(options)
    merged_options["adapter"] = "vercel_ai_sdk.generate_text"
    return from_response(result, **merged_options)


def from_vercel_ai_sdk_stream_finish(result: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    merged_options = dict(options)
    merged_options["adapter"] = "vercel_ai_sdk.stream_text"
    return from_response(result, **merged_options)


def from_vercel_ai_sdk_stream_transcribe_finish(result: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    merged_options = dict(options)
    merged_options["adapter"] = "vercel_ai_sdk.stream_transcribe"
    return from_response(result, **merged_options)


def from_llamaindex_token_counter(counter: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    merged_options = dict(options)
    merged_options["adapter"] = "llamaindex.token_counter"
    return from_response(counter, **merged_options)


def from_haystack_generator_result(result: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    merged_options = dict(options)
    merged_options["adapter"] = "haystack.generator_result"
    return from_response(result, **merged_options)


def from_litellm_response(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    merged_options = dict(options)
    hidden = response.get("_hidden_params") or response.get("hidden_params") or {}
    if isinstance(hidden, dict) and "provider_reported_cost" not in merged_options:
        response_cost = hidden.get("response_cost")
        if response_cost is not None:
            merged_options["provider_reported_cost"] = response_cost
            merged_options.setdefault("provider_reported_cost_mode", "compare")
    merged_options["adapter"] = "litellm.proxy_response"
    return from_response(response, **merged_options)


def from_ag2_usage_summary(summary: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    merged_options = dict(options)
    usage_summary, _mode = _ag2_usage_summary_payload(summary, merged_options)
    _model_name, model_usage = _ag2_model_usage(usage_summary, merged_options.get("model"))
    if "provider_reported_cost" not in merged_options:
        reported_cost = model_usage.get("cost") or usage_summary.get("total_cost")
        if reported_cost is not None:
            merged_options["provider_reported_cost"] = reported_cost
            merged_options.setdefault("provider_reported_cost_mode", "compare")
    merged_options["adapter"] = "ag2.usage_summary"
    return from_response(summary, **merged_options)


def from_openai_agents_usage(usage: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    merged_options = dict(options)
    merged_options["adapter"] = "openai_agents.usage"
    return from_response(usage, **merged_options)


def _langsmith_reported_cost(run: Dict[str, Any]) -> Any:
    usage = run.get("usage_metadata") if isinstance(run.get("usage_metadata"), dict) else {}
    return (
        run.get("total_cost")
        or run.get("totalCost")
        or run.get("cost")
        or usage.get("total_cost")
        or usage.get("totalCost")
    )


def from_langsmith_run(run: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    merged_options = dict(options)
    if "provider_reported_cost" not in merged_options:
        reported_cost = _langsmith_reported_cost(run)
        if reported_cost is not None:
            merged_options["provider_reported_cost"] = reported_cost
            merged_options.setdefault("provider_reported_cost_mode", "compare")
    merged_options["adapter"] = "langsmith.run_usage"
    return from_response(run, **merged_options)


def from_semantic_kernel_telemetry(telemetry: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    merged_options = dict(options)
    merged_options["adapter"] = "semantic_kernel.telemetry"
    return from_response(telemetry, **merged_options)


def _openrouter_reported_cost(response: Dict[str, Any]) -> Any:
    payload = _openrouter_sdk_response_payload(response)
    payload = _openai_compatible_chat_payload(payload)
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    return usage.get("cost") or usage.get("totalCost") or payload.get("cost") or payload.get("totalCost")


def from_openrouter_sdk_response(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    merged_options = dict(options)
    if "provider_reported_cost" not in merged_options:
        reported_cost = _openrouter_reported_cost(response)
        if reported_cost is not None:
            merged_options["provider_reported_cost"] = reported_cost
            merged_options.setdefault("provider_reported_cost_mode", "compare")
    merged_options["adapter"] = "openrouter.sdk_response"
    return from_response(response, **merged_options)


def _langchain_message_from_generation(generation: Any) -> Optional[Dict[str, Any]]:
    plain_generation = _plain_value(generation)
    if isinstance(plain_generation, dict):
        message = plain_generation.get("message")
        if isinstance(message, dict):
            return message
        if "usage_metadata" in plain_generation or "usageMetadata" in plain_generation:
            return plain_generation
    return None


def _langchain_messages_from_llm_result(result: Any) -> List[Dict[str, Any]]:
    plain_result = _plain_value(result)
    if isinstance(plain_result, dict) and ("usage_metadata" in plain_result or "usageMetadata" in plain_result):
        return [plain_result]
    messages: List[Dict[str, Any]] = []
    for generation_group in (plain_result or {}).get("generations", []) if isinstance(plain_result, dict) else []:
        generations = generation_group if isinstance(generation_group, list) else [generation_group]
        for generation in generations:
            message = _langchain_message_from_generation(generation)
            if message is not None:
                messages.append(message)
    return messages


class RunCostLangChainCallback:
    """Small LangChain-compatible callback handler that records RunCost ledgers."""

    def __init__(self, **options: Any) -> None:
        self.options = dict(options)
        self.ledgers: List[Dict[str, Any]] = []

    def __enter__(self) -> "RunCostLangChainCallback":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        return None

    def as_config(self) -> Dict[str, Any]:
        return {"callbacks": [self]}

    def record_message(self, message: Any) -> Dict[str, Any]:
        ledger = from_langchain_message(_plain_value(message), **self.options)
        self.ledgers.append(ledger)
        return ledger

    def on_llm_end(self, response: Any, **_: Any) -> None:
        for message in _langchain_messages_from_llm_result(response):
            self.record_message(message)

    def on_chat_model_end(self, response: Any, **kwargs: Any) -> None:
        self.on_llm_end(response, **kwargs)

    @property
    def latest(self) -> Optional[Dict[str, Any]]:
        return self.ledgers[-1] if self.ledgers else None

    @property
    def total(self) -> str:
        total = "0"
        for ledger in self.ledgers:
            total = _add(total, ledger["total"])
        return total


def track_langchain_costs(**options: Any) -> RunCostLangChainCallback:
    return RunCostLangChainCallback(**options)
