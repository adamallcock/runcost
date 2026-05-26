from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

getcontext().prec = 50

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
    "file_search_units",
    "code_interpreter_session_units",
    "code_interpreter_call_units",
    "computer_use_action_units",
    "tool_call_units",
    "tool_execution_seconds",
    "rerank_search_units",
    "image_generation_units",
    "video_generation_units",
    "audio_generation_units",
    "transcription_seconds",
    "endpoint_runtime_seconds",
    "endpoint_instance_hours",
    "custom_units",
]
_COMPONENT_ORDER = {name: index for index, name in enumerate(_COMPONENT_ORDER_NAMES)}


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


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _format_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal("1")))
    return format(normalized, "f").rstrip("0").rstrip(".")


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
    return date.fromisoformat(text)


def _usage_context(usage_ledger: Dict[str, Any]) -> Dict[str, Any]:
    return usage_ledger.get("context", {})


def _card_identity_matches(usage_ledger: Dict[str, Any], card: Dict[str, Any]) -> bool:
    billed_model = _billed_model(usage_ledger)
    model_matches = card["model"] == billed_model or billed_model in card.get("aliases", [])
    provider_matches = card["provider"] == usage_ledger["provider"]
    surface_matches = "surface" not in card or card["surface"] == usage_ledger["surface"]
    return model_matches and provider_matches and surface_matches


def _effective_matches(card: Dict[str, Any], priced_at: Optional[str]) -> bool:
    if not priced_at:
        return True
    effective = card.get("effective") or {}
    from_date = effective.get("from")
    to_date = effective.get("to")
    if from_date and priced_at < from_date:
        return False
    if to_date and priced_at > to_date:
        return False
    return True


def _card_context_matches(usage_ledger: Dict[str, Any], card: Dict[str, Any]) -> bool:
    context = _usage_context(usage_ledger)
    service_tier = context.get("service_tier")
    region = context.get("region")
    priced_at = _date_part(context.get("priced_at"))

    if service_tier and card.get("service_tier") and card["service_tier"] != service_tier:
        return False
    if region and card.get("region") and card["region"] != region:
        return False
    return _effective_matches(card, priced_at)


def _card_score(usage_ledger: Dict[str, Any], card: Dict[str, Any]) -> int:
    context = _usage_context(usage_ledger)
    score = 0
    if card.get("surface") == usage_ledger["surface"]:
        score += 8
    if context.get("service_tier") and card.get("service_tier") == context["service_tier"]:
        score += 4
    if context.get("region") and card.get("region") == context["region"]:
        score += 2
    if card.get("effective"):
        score += 1
    return score


def _source_priority_score(card: Dict[str, Any], price_source_priority: Optional[Iterable[str]]) -> int:
    if not price_source_priority:
        return 0
    priority = list(price_source_priority)
    source_name = (card.get("source") or {}).get("name")
    if source_name not in priority:
        return 0
    return (len(priority) - priority.index(source_name)) * 100


def _matching_cards(
    usage_ledger: Dict[str, Any],
    price_cards: Iterable[Dict[str, Any]],
    price_source_priority: Optional[Iterable[str]] = None,
) -> List[Dict[str, Any]]:
    scored_cards = []
    for index, card in enumerate(price_cards):
        if not _card_identity_matches(usage_ledger, card):
            continue
        if not _card_context_matches(usage_ledger, card):
            continue
        score = _card_score(usage_ledger, card) + _source_priority_score(card, price_source_priority)
        source_name = str((card.get("source") or {}).get("name", ""))
        scored_cards.append((-score, source_name, str(card.get("id", "")), index, card))
    return [item[-1] for item in sorted(scored_cards, key=lambda item: item[:-1])]


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


def _warning_identity_metadata(usage_ledger: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "provider": usage_ledger.get("provider"),
        "surface": usage_ledger.get("surface"),
        "model": _billed_model(usage_ledger),
    }


def _unpriced_component_metadata(usage_ledger: Dict[str, Any], component: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "component": component.get("name"),
        "unit": component.get("unit"),
        "model": _billed_model(usage_ledger),
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
        metadata = card.get("metadata") if isinstance(card.get("metadata"), dict) else {}
        capabilities = metadata.get("source_capabilities")
        if not isinstance(capabilities, dict):
            continue
        unsupported = capabilities.get("unsupported_components") or capabilities.get("unsupportedComponents") or []
        if component_name in unsupported:
            source = card.get("source") if isinstance(card.get("source"), dict) else {}
            return {
                "code": "source_capability_unsupported",
                "message": f"Price source {source.get('name', card.get('id', 'unknown'))} explicitly does not price {component_name}.",
                "metadata": {
                    "component": component_name,
                    "price_card_id": card.get("id"),
                    "source": source.get("name"),
                },
            }
    return None


def _has_price_card_for_usage(
    usage_ledger: Dict[str, Any],
    price_cards: Iterable[Dict[str, Any]],
) -> bool:
    return any(_card_identity_matches(usage_ledger, card) for card in price_cards)


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
    priced_at = _date_part(context.get("priced_at"))
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
    priced_at = _date_value(_usage_context(usage_ledger).get("priced_at"))
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
    price_cards: Iterable[Dict[str, Any]],
    discount_policies: Optional[Iterable[Dict[str, Any]]] = None,
    mode: str = "compatibility",
    stale_after_days: Optional[int] = None,
    provider_reported_cost: Optional[Any] = None,
    provider_reported_cost_mode: str = "compare",
    price_source_priority: Optional[Iterable[str]] = None,
    debug_trace: bool = False,
) -> Dict[str, Any]:
    policies = list(discount_policies or [])
    price_cards_list = list(price_cards)
    source_priority = list(price_source_priority or [])
    components = []
    warnings = []
    applied_discounts = []
    sources_by_name: Dict[str, Dict[str, Any]] = {}
    trace = _new_debug_trace() if _debug_trace_enabled(debug_trace) else None
    total = "0"
    resolved_billed_model = _billed_model(usage_ledger)
    alias_resolution = usage_ledger["model"].get("alias_resolution", "none")
    has_model_card = _has_price_card_for_usage(usage_ledger, price_cards_list)
    matching_cards = _matching_cards(usage_ledger, price_cards_list, source_priority)
    if trace is not None:
        trace["decisions"].append(
            {
                "type": "price_card_candidates",
                "model": resolved_billed_model,
                "candidate_price_card_ids": [card["id"] for card in matching_cards],
                "source_priority": source_priority,
            }
        )
    warned_unknown_model = False
    warned_no_matching_card = False
    warned_stale_cards = set()

    for component in usage_ledger["components"]:
        if not has_model_card:
            if not warned_unknown_model:
                warnings.append(
                    {
                        "code": "unknown_model",
                        "message": f"No price card found for {resolved_billed_model}.",
                        "metadata": _warning_identity_metadata(usage_ledger),
                    }
                )
                warned_unknown_model = True
            if trace is not None:
                trace["summary"]["unpriced_components"] += 1
            continue

        if not matching_cards:
            if not warned_no_matching_card:
                warnings.append(_no_matching_card_warning(usage_ledger, price_cards_list))
                warned_no_matching_card = True
            if trace is not None:
                trace["summary"]["unpriced_components"] += 1
            continue

        candidates = _candidate_price_components(matching_cards, component)
        matches = [
            match
            for match in candidates
            if _conditions_match(usage_ledger, match["price_component"])
        ]
        if not matches:
            capability_warning = _source_capability_warning(matching_cards, component)
            long_context_warning = _long_context_rule_missing_warning(usage_ledger, candidates, component)
            if capability_warning:
                warnings.append(capability_warning)
            elif long_context_warning:
                warnings.append(long_context_warning)
            else:
                warnings.append(
                    {
                        "code": "tool_component_unpriced"
                        if "tool" in component["name"]
                        else "component_unpriced",
                        "message": f"No price found for {component['name']} ({component['unit']}).",
                        "metadata": _unpriced_component_metadata(usage_ledger, component),
                    }
                )
            if trace is not None:
                trace["summary"]["unpriced_components"] += 1
            continue

        disagreement_warning = _price_source_disagreement_warning(matches, component, price_source_priority)
        if disagreement_warning:
            warnings.append(disagreement_warning)
        match = matches[0]
        card = match["card"]
        price_component = match["price_component"]
        if trace is not None:
            trace["decisions"].append(
                {
                    "type": "price_component_match",
                    "component": component["name"],
                    "candidate_price_card_ids": [candidate["card"]["id"] for candidate in matches],
                    "selected_price_card_id": card["id"],
                    "selected_source": card["source"]["name"],
                }
            )
        if card["model"] != resolved_billed_model and resolved_billed_model in card.get("aliases", []):
            previous_billed_model = resolved_billed_model
            resolved_billed_model = card["model"]
            if alias_resolution == "none":
                alias_resolution = "source_exact"
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
            usage_ledger,
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
            stale_warning = _stale_price_warning(usage_ledger, card, stale_after_days)
            if stale_warning:
                warnings.append(stale_warning)
                warned_stale_cards.add(card["id"])

        components.append(
            {
                "name": component["name"],
                "quantity": component["quantity"],
                "unit": component["unit"],
                "unit_price": _multiply_divide(price["amount"], "1", price["per"]),
                "cost": discounted["cost"],
                "price_card_id": card["id"],
                "discount_eligible": discount_eligible,
            }
        )
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


def _compact_components(components: Iterable[Optional[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    return [component for component in components if component is not None]


def _base_usage_ledger(
    *,
    provider: str,
    surface: str,
    requested_model: Optional[str],
    returned_model: Optional[str],
    components: List[Dict[str, Any]],
    raw_usage: Dict[str, Any],
) -> Dict[str, Any]:
    model = returned_model or requested_model
    return {
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


def _openai_responses_payload(response: Dict[str, Any]) -> Dict[str, Any]:
    if response.get("type") == "response.completed" and isinstance(response.get("response"), dict):
        return response["response"]
    return response


def extract_openai_responses_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    response = _openai_responses_payload(response)
    usage = response.get("usage", {})
    surface = options.get("surface", "openai.responses")
    provider = options.get("provider") or ("xai" if surface == "xai.responses" else "openai")
    cached_input = usage.get("input_tokens_details", {}).get("cached_tokens", 0)
    reasoning = usage.get("output_tokens_details", {}).get("reasoning_tokens", 0)
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    tool_components = []
    for item in response.get("output", []):
        if item.get("type") == "web_search_call":
            tool_components.append(_positive_component("web_search_units", 1, "search", "$.output[*].type"))
        elif item.get("type") == "file_search_call":
            tool_components.append(_positive_component("file_search_units", 1, "call", "$.output[*].type"))
        elif item.get("type") == "code_interpreter_call":
            tool_components.append(_positive_component("code_interpreter_call_units", 1, "call", "$.output[*].type"))

    return _base_usage_ledger(
        provider=provider,
        surface=surface,
        requested_model=options.get("model", response.get("model")),
        returned_model=response.get("model"),
        raw_usage=usage,
        components=_compact_components(
            [
                _positive_component("input_uncached_tokens", input_tokens - cached_input, "token", "$.usage.input_tokens"),
                _positive_component("input_cache_read_tokens", cached_input, "token", "$.usage.input_tokens_details.cached_tokens"),
                _positive_component("output_text_tokens", output_tokens - reasoning, "token", "$.usage.output_tokens"),
                _positive_component("output_reasoning_tokens", reasoning, "token", "$.usage.output_tokens_details.reasoning_tokens"),
                *tool_components,
            ]
        ),
    )


def extract_openai_embeddings_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    usage = response.get("usage", {})
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


OPENAI_COMPATIBLE_CHAT_PROVIDERS = {
    "openai.chat_completions": "openai",
    "openrouter.chat_completions": "openrouter",
    "groq.chat_completions": "groq",
    "xai.chat_completions": "xai",
    "mistral.chat_completions": "mistral",
    "deepseek.chat_completions": "deepseek",
    "azure.openai.chat_completions": "azure",
    "huggingface.chat_completions": "huggingface",
}


def _openai_compatible_cached_input(usage: Dict[str, Any]) -> tuple[Any, str]:
    prompt_details = usage.get("prompt_tokens_details", {})
    if "cached_tokens" in prompt_details:
        return prompt_details.get("cached_tokens", 0), "$.usage.prompt_tokens_details.cached_tokens"
    if "prompt_cache_hit_tokens" in usage:
        return usage.get("prompt_cache_hit_tokens", 0), "$.usage.prompt_cache_hit_tokens"
    return 0, "$.usage.prompt_tokens_details.cached_tokens"


def _openai_compatible_reasoning_output(usage: Dict[str, Any]) -> tuple[Any, str]:
    completion_details = usage.get("completion_tokens_details", {})
    if "reasoning_tokens" in completion_details:
        return completion_details.get("reasoning_tokens", 0), "$.usage.completion_tokens_details.reasoning_tokens"
    output_details = usage.get("output_tokens_details", {})
    if "reasoning_tokens" in output_details:
        return output_details.get("reasoning_tokens", 0), "$.usage.output_tokens_details.reasoning_tokens"
    return 0, "$.usage.completion_tokens_details.reasoning_tokens"


def extract_openai_compatible_chat_completions_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    usage = response.get("usage", {})
    cached_input, cached_source = _openai_compatible_cached_input(usage)
    reasoning, reasoning_source = _openai_compatible_reasoning_output(usage)
    prompt_tokens = usage.get(
        "prompt_tokens",
        usage.get("prompt_cache_hit_tokens", 0) + usage.get("prompt_cache_miss_tokens", 0),
    )
    completion_tokens = usage.get("completion_tokens", 0)
    surface = options.get("surface", "openai.chat_completions")
    provider = options.get("provider", OPENAI_COMPATIBLE_CHAT_PROVIDERS.get(surface, "openai"))

    return _base_usage_ledger(
        provider=provider,
        surface=surface,
        requested_model=options.get("model", response.get("model")),
        returned_model=response.get("model"),
        raw_usage=usage,
        components=_compact_components(
            [
                _positive_component("input_uncached_tokens", prompt_tokens - cached_input, "token", "$.usage.prompt_tokens"),
                _positive_component("input_cache_read_tokens", cached_input, "token", cached_source),
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


def _anthropic_messages_payload(response: Dict[str, Any]) -> Dict[str, Any]:
    events = response.get("events")
    if not isinstance(events, list):
        return response

    message: Dict[str, Any] = {}
    usage: Dict[str, Any] = {}
    for event in events:
        if not isinstance(event, dict):
            continue
        if event.get("type") == "message_start" and isinstance(event.get("message"), dict):
            message = dict(event["message"])
            usage.update(message.get("usage") or {})
        elif event.get("type") == "message_delta":
            usage.update(event.get("usage") or {})
            if isinstance(event.get("delta"), dict):
                message.update(event["delta"])

    if not message:
        return response
    message["usage"] = usage
    return message


def extract_anthropic_messages_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    response = _anthropic_messages_payload(response)
    usage = response.get("usage", {})
    input_tokens = usage.get("input_tokens", 0)
    cache_write = usage.get("cache_creation_input_tokens", 0)
    cache_write_1h = usage.get("cache_creation_input_tokens_1h", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)

    return _base_usage_ledger(
        provider=options.get("provider", "anthropic"),
        surface=options.get("surface", "anthropic.messages"),
        requested_model=options.get("model", response.get("model")),
        returned_model=response.get("model"),
        raw_usage=usage,
        components=_compact_components(
            [
                _positive_component("input_uncached_tokens", input_tokens, "token", "$.usage.input_tokens"),
                _positive_component("input_cache_write_tokens", cache_write - cache_write_1h, "token", "$.usage.cache_creation_input_tokens"),
                _positive_component("input_cache_write_1h_tokens", cache_write_1h, "token", "$.usage.cache_creation_input_tokens_1h"),
                _positive_component("input_cache_read_tokens", cache_read, "token", "$.usage.cache_read_input_tokens"),
                _positive_component("output_text_tokens", output_tokens, "token", "$.usage.output_tokens"),
            ]
        ),
    )


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


def extract_gemini_generate_content_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
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

    return _base_usage_ledger(
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


def extract_vercel_ai_sdk_usage(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    usage, source_root = _vercel_ai_sdk_usage_payload(response)
    input_details = usage.get("inputTokenDetails", {})
    output_details = usage.get("outputTokenDetails", {})
    cache_read = input_details.get("cacheReadTokens", usage.get("cachedInputTokens", 0))
    cache_write = input_details.get("cacheWriteTokens", 0)
    input_tokens = usage.get("inputTokens", 0)
    uncached = input_details.get("noCacheTokens", input_tokens - cache_read - cache_write)
    output_tokens = usage.get("outputTokens", 0)
    reasoning = output_details.get("reasoningTokens", usage.get("reasoningTokens", 0))
    text_tokens = output_details.get("textTokens", output_tokens - reasoning)
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
                _positive_component("input_uncached_tokens", uncached, "token", f"{source_root}.inputTokenDetails.noCacheTokens"),
                _positive_component("input_cache_read_tokens", cache_read, "token", f"{source_root}.inputTokenDetails.cacheReadTokens"),
                _positive_component("input_cache_write_tokens", cache_write, "token", f"{source_root}.inputTokenDetails.cacheWriteTokens"),
                _positive_component("output_text_tokens", text_tokens, "token", f"{source_root}.outputTokenDetails.textTokens"),
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
    cached_input = _nested_dict(usage, "input_tokens_details").get("cached_tokens", 0)
    reasoning = _nested_dict(usage, "output_tokens_details").get("reasoning_tokens", 0)
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    returned_model = usage.get("model") or source_root_value.get("model") or response.get("model") or options.get("model")

    return _base_usage_ledger(
        provider=options.get("provider", "openai"),
        surface=options.get("surface", "openai.responses"),
        requested_model=options.get("model", returned_model),
        returned_model=returned_model,
        raw_usage=usage,
        components=_compact_components(
            [
                _positive_component("input_uncached_tokens", input_tokens - cached_input, "token", f"{source_root}.input_tokens"),
                _positive_component("input_cache_read_tokens", cached_input, "token", f"{source_root}.input_tokens_details.cached_tokens"),
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


def extract_usage_ledger(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    adapter = options.get("adapter") or options.get("framework")
    if adapter == "langchain.chat_message":
        return extract_langchain_chat_usage(response, **options)
    if adapter == "vercel_ai_sdk.generate_text":
        return extract_vercel_ai_sdk_usage(response, **options)
    if adapter == "vercel_ai_sdk.stream_text":
        return extract_vercel_ai_sdk_usage(response, **options)
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
    if surface in {"openai.responses", "xai.responses"}:
        return extract_openai_responses_usage(response, **options)
    if surface == "openai.embeddings":
        return extract_openai_embeddings_usage(response, **options)
    if surface == "openai.chat_completions":
        return extract_openai_chat_completions_usage(response, **options)
    if surface in OPENAI_COMPATIBLE_CHAT_PROVIDERS:
        return extract_openai_compatible_chat_completions_usage(response, **options)
    if surface == "anthropic.messages":
        return extract_anthropic_messages_usage(response, **options)
    if surface in {"google.gemini.generate_content", "vertex.gemini.generate_content"}:
        return extract_gemini_generate_content_usage(response, **options)
    if surface == "aws.bedrock.converse":
        return extract_bedrock_converse_usage(response, **options)
    if surface == "aws.bedrock.invoke_model":
        return extract_bedrock_invoke_model_usage(response, **options)
    if surface == "cohere.chat":
        return extract_cohere_chat_usage(response, **options)
    raise ValueError(f"Unsupported surface: {surface}")


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


def _price_cards_from_canonical_cards(raw_cards: Any) -> List[Dict[str, Any]]:
    if isinstance(raw_cards, list):
        return [card for card in raw_cards if isinstance(card, dict)]
    return []


def _source_cache_price_cards(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ("price_cards", "priceCards", "cards"):
        cards = entry.get(key)
        if isinstance(cards, list):
            return [card for card in cards if isinstance(card, dict)]
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
        components: List[Dict[str, Any]] = []
        for raw_component in row.get("components", []):
            if not isinstance(raw_component, dict):
                continue
            amount = raw_component.get("amount")
            if amount is None and isinstance(raw_component.get("price"), dict):
                amount = raw_component["price"].get("amount")
            _add_price_component(
                components,
                raw_component.get("usage_component"),
                raw_component.get("unit", "token"),
                amount,
                _number_string(raw_component.get("per") or raw_component.get("price", {}).get("per") or per),
            )
        _official_snapshot_component(components, row, "input_uncached_tokens", "token", ("input", "prompt", "input_uncached"), per)
        _official_snapshot_component(components, row, "input_cache_read_tokens", "token", ("cache_read", "cached_input", "input_cache_read"), per)
        _official_snapshot_component(components, row, "input_cache_write_tokens", "token", ("cache_write", "input_cache_write"), per)
        _official_snapshot_component(components, row, "input_cache_write_1h_tokens", "token", ("cache_write_1h", "input_cache_write_1h"), per)
        _official_snapshot_component(components, row, "output_text_tokens", "token", ("output", "completion", "output_text"), per)
        _official_snapshot_component(components, row, "output_reasoning_tokens", "token", ("reasoning", "thinking", "output_reasoning"), per)
        _official_snapshot_component(components, row, "input_audio_tokens", "token", ("input_audio", "audio_input"), per)
        _official_snapshot_component(components, row, "output_audio_tokens", "token", ("output_audio", "audio_output"), per)
        _official_snapshot_component(components, row, "request_units", "request", ("request", "per_request"), "1")
        _official_snapshot_component(components, row, "web_search_units", "search", ("web_search", "search"), "1")
        if not components:
            continue
        card = {
            "schema_version": "0.1",
            "id": row.get("price_card_id") or row.get("priceCardId") or f"{provider}:{model}:official-snapshot",
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
    response: Dict[str, Any],
    *,
    adapter: Optional[str] = None,
    framework: Optional[str] = None,
    provider: Optional[str] = None,
    surface: str,
    model: Optional[str] = None,
    ag2_usage_mode: Optional[str] = None,
    price_cards: Iterable[Dict[str, Any]],
    discount_policies: Optional[Iterable[Dict[str, Any]]] = None,
    mode: str = "compatibility",
    stale_after_days: Optional[int] = None,
    provider_reported_cost: Optional[Any] = None,
    provider_reported_cost_mode: str = "compare",
    price_source_priority: Optional[Iterable[str]] = None,
    debug_trace: bool = False,
) -> Dict[str, Any]:
    options: Dict[str, Any] = {"surface": surface}
    if adapter:
        options["adapter"] = adapter
    if framework:
        options["framework"] = framework
    if provider:
        options["provider"] = provider
    if model:
        options["model"] = model
    if ag2_usage_mode:
        options["ag2_usage_mode"] = ag2_usage_mode
    try:
        usage_ledger = extract_usage_ledger(response, **options)
    except ValueError:
        if mode == "strict":
            raise
        return _unsupported_surface_ledger(response, **options)
    return calculate_cost(
        usage_ledger=usage_ledger,
        price_cards=price_cards,
        discount_policies=discount_policies,
        mode=mode,
        stale_after_days=stale_after_days,
        provider_reported_cost=provider_reported_cost,
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
