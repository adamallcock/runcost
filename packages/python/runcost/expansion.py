"""Stateless product-expansion helpers for RunCost.

This module deliberately stays beside the deterministic core. It unwraps
provider batch records, maps maintained upstream/telemetry formats, and adds
policy/reporting helpers without introducing storage, network calls, routing,
or a telemetry backend. Network-enabled convenience functions live in
``runcost.price_resolver``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from .core import (
    _normalize_openai_service_tier,
    _normalize_attribution as _normalize_core_attribution,
    aggregate_cost_ledgers,
    calculate_cost,
    compile_price_catalog,
    extract_usage_ledger,
    from_response,
    _response_mapping,
)

def normalize_attribution(value: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """Return schema-safe passive attribution metadata."""

    return _normalize_core_attribution(dict(value) if isinstance(value, Mapping) else value)


def _number(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


def _decimal_string(value: Any) -> str:
    number = _number(value)
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _nonnegative_difference(total: Any, *parts: Any) -> str:
    value = _number(total) - sum((_number(part) for part in parts), Decimal("0"))
    return _decimal_string(max(value, Decimal("0")))


def _error_object(value: Any, fallback: str) -> Dict[str, Any]:
    if isinstance(value, Mapping):
        result = {str(key): child for key, child in value.items()}
        message = result.get("message") or result.get("detail") or result.get("status") or fallback
        result["message"] = str(message)
        return result
    if value not in (None, ""):
        return {"message": str(value)}
    return {"message": fallback}


def _batch_surface_from_endpoint(endpoint: Optional[str], fallback: Optional[str]) -> Optional[str]:
    if fallback:
        return fallback
    text = str(endpoint or "").lower()
    if "responses" in text:
        return "openai.responses"
    if "chat/completions" in text:
        return "openai.chat_completions"
    if "embeddings" in text:
        return "openai.embeddings"
    if "images" in text:
        return "openai.images"
    if "audio/transcriptions" in text:
        return "openai.audio_transcriptions"
    return None


def _batch_item_id(item: Mapping[str, Any], index: int) -> str:
    for key in ("custom_id", "customId", "recordId", "record_id", "key", "id"):
        if item.get(key) not in (None, ""):
            return str(item[key])
    request = item.get("request")
    if isinstance(request, Mapping):
        labels = request.get("labels")
        if isinstance(labels, Mapping):
            for key in ("id", "key", "custom_id"):
                if labels.get(key) not in (None, ""):
                    return str(labels[key])
    response = item.get("response")
    if isinstance(response, Mapping):
        for key in ("responseId", "response_id", "id"):
            if response.get(key) not in (None, ""):
                return str(response[key])
    return str(index)


def _openai_batch_item(item: Mapping[str, Any], *, surface: Optional[str], endpoint: Optional[str]) -> Tuple[str, Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[int], Dict[str, Any]]:
    response = item.get("response") if isinstance(item.get("response"), Mapping) else {}
    status_code = response.get("status_code", response.get("statusCode"))
    http_status = int(status_code) if isinstance(status_code, (int, float)) or str(status_code or "").isdigit() else None
    error = item.get("error")
    if error or (http_status is not None and not 200 <= http_status < 300):
        return "errored", None, _error_object(error or response.get("body"), "OpenAI batch item failed."), http_status, {}
    body = response.get("body")
    if not isinstance(body, Mapping):
        return "pending", None, _error_object(None, "OpenAI batch item has no response body yet."), http_status, {}
    resolved_surface = _batch_surface_from_endpoint(endpoint or item.get("url"), surface)
    return "succeeded", dict(body), None, http_status, {"surface": resolved_surface}


def _anthropic_batch_item(item: Mapping[str, Any]) -> Tuple[str, Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[int], Dict[str, Any]]:
    result = item.get("result") if isinstance(item.get("result"), Mapping) else {}
    result_type = str(result.get("type") or "pending").lower()
    if result_type == "succeeded" and isinstance(result.get("message"), Mapping):
        return "succeeded", dict(result["message"]), None, None, {"surface": "anthropic.messages"}
    status = result_type if result_type in {"errored", "canceled", "expired"} else "pending"
    error = result.get("error") or item.get("error")
    return status, None, _error_object(error, f"Anthropic batch item is {status}."), None, {}


def _gemini_batch_item(item: Mapping[str, Any], *, vertex: bool) -> Tuple[str, Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[int], Dict[str, Any]]:
    surface = "vertex.gemini.generate_content" if vertex else "google.gemini.generate_content"
    if vertex:
        response = item.get("response")
        status_value = item.get("status")
        if isinstance(response, Mapping) and response:
            metadata = {key: item[key] for key in ("processed_time", "processedTime") if item.get(key) is not None}
            return "succeeded", dict(response), None, None, {"surface": surface, **metadata}
        if status_value not in (None, "", {}):
            return "errored", None, _error_object(status_value, "Vertex batch item failed."), None, {"surface": surface}
        return "pending", None, _error_object(None, "Vertex batch item has no response yet."), None, {"surface": surface}

    if isinstance(item.get("response"), Mapping):
        return "succeeded", dict(item["response"]), None, None, {"surface": surface}
    if isinstance(item.get("usageMetadata"), Mapping) or isinstance(item.get("usage_metadata"), Mapping):
        return "succeeded", dict(item), None, None, {"surface": surface}
    error = item.get("error") or item.get("status")
    if error not in (None, "", {}):
        return "errored", None, _error_object(error, "Gemini batch item failed."), None, {"surface": surface}
    return "pending", None, _error_object(None, "Gemini batch item has no response yet."), None, {"surface": surface}


def _bedrock_batch_item(item: Mapping[str, Any], *, surface: Optional[str]) -> Tuple[str, Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[int], Dict[str, Any]]:
    error = item.get("error")
    if error not in (None, "", {}):
        return "errored", None, _error_object(error, "Bedrock batch item failed."), None, {}
    output = item.get("modelOutput", item.get("model_output"))
    if isinstance(output, Mapping):
        return "succeeded", dict(output), None, None, {"surface": surface or "aws.bedrock.invoke_model"}
    return "pending", None, _error_object(None, "Bedrock batch item has no modelOutput yet."), None, {}


def from_batch_results(
    items: Iterable[Any],
    *,
    provider: str,
    surface: Optional[str] = None,
    endpoint: Optional[str] = None,
    model: Optional[str] = None,
    batch_id: Optional[str] = None,
    price_cards: Optional[Iterable[Dict[str, Any]]] = None,
    discount_policies: Optional[Iterable[Dict[str, Any]]] = None,
    mode: str = "compatibility",
    attribution: Optional[Mapping[str, Any]] = None,
    **options: Any,
) -> Dict[str, Any]:
    """Price provider batch output records without hiding partial failures."""

    normalized_provider = provider.lower().replace("_", "-")
    supported_providers = {
        "openai", "kimi", "moonshot", "moonshot-ai", "dashscope", "alibaba",
        "anthropic", "google", "gemini", "google-gemini", "vertex", "google-vertex",
        "vertex-ai", "bedrock", "aws-bedrock",
    }
    if normalized_provider not in supported_providers:
        raise ValueError(f"unsupported batch provider: {provider}")
    cards = compile_price_catalog(price_cards or [])
    normalized_attribution = normalize_attribution(attribution)
    batch_items: List[Dict[str, Any]] = []
    successful_ledgers: List[Dict[str, Any]] = []

    for index, raw_item in enumerate(items):
        item = _response_mapping(raw_item)
        item_id = _batch_item_id(item, index)
        if normalized_provider in {"openai", "kimi", "moonshot", "moonshot-ai", "dashscope", "alibaba"}:
            status, response, error, http_status, metadata = _openai_batch_item(item, surface=surface, endpoint=endpoint)
            item_provider = "openai" if normalized_provider == "openai" else "kimi" if normalized_provider in {"kimi", "moonshot", "moonshot-ai"} else "dashscope"
            if item_provider != "openai" and metadata.get("surface") == "openai.chat_completions":
                metadata["surface"] = f"{item_provider}.chat_completions"
        elif normalized_provider == "anthropic":
            status, response, error, http_status, metadata = _anthropic_batch_item(item)
            item_provider = "anthropic"
        elif normalized_provider in {"google", "gemini", "google-gemini"}:
            status, response, error, http_status, metadata = _gemini_batch_item(item, vertex=False)
            item_provider = "google"
        elif normalized_provider in {"vertex", "google-vertex", "vertex-ai"}:
            status, response, error, http_status, metadata = _gemini_batch_item(item, vertex=True)
            item_provider = "vertex"
        elif normalized_provider in {"bedrock", "aws-bedrock"}:
            status, response, error, http_status, metadata = _bedrock_batch_item(item, surface=surface)
            item_provider = "bedrock"
        else:
            raise ValueError(f"unsupported batch provider: {provider}")

        output_item: Dict[str, Any] = {"id": item_id, "status": status}
        if http_status is not None:
            output_item["http_status"] = http_status
        if metadata:
            output_item["metadata"] = {key: value for key, value in metadata.items() if key != "surface" and value is not None}
            if not output_item["metadata"]:
                output_item.pop("metadata")
        item_metadata = dict(output_item.get("metadata") or {})
        item_metadata.update({"service_tier": "batch", "batch_item_id": item_id})
        if batch_id:
            item_metadata["batch_id"] = batch_id
        if endpoint:
            item_metadata["endpoint"] = endpoint
        output_item["metadata"] = item_metadata
        if normalized_attribution:
            output_item["attribution"] = dict(normalized_attribution)

        if status == "succeeded" and response is not None:
            item_surface = metadata.get("surface") or surface
            if not item_surface:
                raise ValueError(f"surface or endpoint is required for {provider} batch item {item_id}")
            context = dict(options.get("context") or {})
            context["service_tier"] = "batch"
            context["batch_item_id"] = item_id
            if batch_id:
                context["batch_id"] = batch_id
            ledger = from_response(
                response,
                provider=item_provider,
                surface=item_surface,
                model=model,
                context=context,
                attribution=normalized_attribution or None,
                price_cards=cards,
                discount_policies=discount_policies,
                mode=mode,
                **{key: value for key, value in options.items() if key != "context"},
            )
            output_item["ledger"] = ledger
            if item_provider == "anthropic":
                refusal = (ledger.get("metadata") or {}).get("anthropic_refusal")
                if isinstance(refusal, Mapping) and refusal.get("detected") is True:
                    output_item["metadata"]["refusal"] = True
                    output_item["metadata"]["requires_retry"] = bool(refusal.get("requires_retry"))
                    if refusal.get("recommended_model"):
                        output_item["metadata"]["recommended_model"] = refusal["recommended_model"]
            successful_ledgers.append(ledger)
        else:
            output_item["error"] = error or _error_object(None, f"Batch item is {status}.")
        batch_items.append(output_item)

    aggregate = aggregate_cost_ledgers(
        successful_ledgers,
        provider=provider,
        surface=f"{provider}.batch",
        model=model or "multiple",
        mode=mode,
    )
    if normalized_attribution:
        aggregate["attribution"] = dict(normalized_attribution)
    succeeded = sum(item["status"] == "succeeded" for item in batch_items)
    pending = sum(item["status"] == "pending" for item in batch_items)
    failed = len(batch_items) - succeeded - pending
    warnings: List[Dict[str, Any]] = []
    if failed:
        warnings.append(
            {
                "code": "batch_items_failed",
                "message": f"{failed} batch item(s) did not succeed and remain visible in items.",
                "metadata": {"failed": failed, "total": len(batch_items)},
            }
        )
    if pending:
        warnings.append(
            {
                "code": "batch_items_pending",
                "message": f"{pending} batch item(s) have no terminal result yet.",
                "metadata": {"pending": pending, "total": len(batch_items)},
            }
        )
    result: Dict[str, Any] = {
        "schema_version": "0.1",
        "provider": provider,
        "surface": f"{provider}.batch",
        "currency": "USD",
        "items": batch_items,
        "summary": {
            "total": len(batch_items),
            "succeeded": succeeded,
            "failed": failed,
            "pending": pending,
            "total_cost": aggregate["total"],
        },
        "aggregate": aggregate,
        "warnings": warnings,
    }
    if batch_id:
        result["batch_id"] = batch_id
    if normalized_attribution:
        result["attribution"] = normalized_attribution
    return result


def _static_match_aliases(match: Any) -> Tuple[List[str], bool]:
    if not isinstance(match, Mapping):
        return [], False
    if isinstance(match.get("equals"), str):
        return [match["equals"]], False
    if isinstance(match.get("or"), Sequence) and not isinstance(match.get("or"), (str, bytes)):
        aliases: List[str] = []
        unsupported = False
        for child in match["or"]:
            child_aliases, child_unsupported = _static_match_aliases(child)
            aliases.extend(child_aliases)
            unsupported = unsupported or child_unsupported
        return sorted(set(aliases)), unsupported
    return [], bool(match)


def _tier_values(value: Any) -> List[Tuple[Any, Optional[Any], Optional[Any]]]:
    if not isinstance(value, Mapping) or "base" not in value:
        return [(value, None, None)] if value is not None else []
    tiers = sorted(
        [tier for tier in value.get("tiers", []) if isinstance(tier, Mapping) and tier.get("start") is not None],
        key=lambda tier: _number(tier["start"]),
    )
    values: List[Tuple[Any, Optional[Any], Optional[Any]]] = []
    first_start = tiers[0]["start"] if tiers else None
    values.append((value.get("base"), None, _number(first_start) - 1 if first_start is not None else None))
    for index, tier in enumerate(tiers):
        next_start = tiers[index + 1]["start"] if index + 1 < len(tiers) else None
        values.append((tier.get("price"), tier["start"], _number(next_start) - 1 if next_start is not None else None))
    return [entry for entry in values if entry[0] is not None]


GENAI_PRICE_COMPONENTS = {
    "input_mtok": ("input_uncached_tokens", "token", "1000000"),
    "cache_write_mtok": ("input_cache_write_tokens", "token", "1000000"),
    "cache_read_mtok": ("input_cache_read_tokens", "token", "1000000"),
    "output_mtok": ("output_text_tokens", "token", "1000000"),
    "input_audio_mtok": ("input_audio_tokens", "token", "1000000"),
    "cache_audio_read_mtok": ("input_cache_read_tokens", "token", "1000000"),
    "output_audio_mtok": ("output_audio_tokens", "token", "1000000"),
    "requests_kcount": ("request_units", "request", "1000"),
}


def _genai_price_components(prices: Mapping[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    components: List[Dict[str, Any]] = []
    warnings: List[str] = []
    for key, value in prices.items():
        mapping = GENAI_PRICE_COMPONENTS.get(key)
        if not mapping:
            warnings.append(f"unsupported price field retained in metadata: {key}")
            continue
        usage_component, unit, per = mapping
        for amount, minimum, maximum in _tier_values(value):
            price_component: Dict[str, Any] = {
                "usage_component": usage_component,
                "unit": unit,
                "price": {"amount": _decimal_string(amount), "currency": "USD", "per": per},
            }
            conditions: Dict[str, Any] = {}
            if minimum is not None:
                conditions["min_total_input_tokens"] = _decimal_string(minimum)
            if maximum is not None:
                conditions["max_total_input_tokens"] = _decimal_string(maximum)
            if conditions:
                price_component["conditions"] = conditions
            components.append(price_component)
    return components, warnings


def _previous_day(value: str) -> str:
    return (date.fromisoformat(value) - timedelta(days=1)).isoformat()


def _time_without_zone(value: Any) -> str:
    return str(value or "00:00:00").removesuffix("Z")


def price_cards_from_genai_prices(data: Any, **options: Any) -> List[Dict[str, Any]]:
    """Map Pydantic ``genai-prices`` JSON into canonical price cards."""

    providers = data if isinstance(data, list) else data.get("providers", []) if isinstance(data, Mapping) else []
    retrieved_at = options.get("retrieved_at") or options.get("retrievedAt")
    version = options.get("version") or options.get("source_version") or options.get("sourceVersion")
    cards: List[Dict[str, Any]] = []
    for raw_provider in providers:
        if not isinstance(raw_provider, Mapping):
            continue
        provider = str(raw_provider.get("id") or "unknown")
        source: Dict[str, Any] = {"name": "genai-prices"}
        urls = raw_provider.get("pricing_urls")
        if isinstance(urls, list) and urls:
            source["url"] = str(urls[0])
        if retrieved_at:
            source["retrieved_at"] = str(retrieved_at)
        if version:
            source["version"] = str(version)
        for raw_model in raw_provider.get("models", []) or []:
            if not isinstance(raw_model, Mapping) or not raw_model.get("id"):
                continue
            model = str(raw_model["id"])
            aliases, unsupported_match = _static_match_aliases(raw_model.get("match"))
            aliases = [alias for alias in aliases if alias != model]
            raw_prices = raw_model.get("prices")
            conditional = raw_prices if isinstance(raw_prices, list) else [{"prices": raw_prices or {}}]
            dated_starts = sorted(
                str(entry.get("constraint", {}).get("start_date"))
                for entry in conditional
                if isinstance(entry, Mapping) and isinstance(entry.get("constraint"), Mapping) and entry["constraint"].get("start_date")
            )
            time_entry_indices = [
                index for index, entry in enumerate(conditional)
                if isinstance(entry, Mapping)
                and isinstance(entry.get("constraint"), Mapping)
                and (entry["constraint"].get("start_time") or entry["constraint"].get("end_time"))
            ]
            time_entry_periods = {entry_index: period for period, entry_index in enumerate(time_entry_indices, start=1)}
            schedule = None
            if time_entry_indices:
                windows = []
                for period, entry_index in enumerate(time_entry_indices, start=1):
                    entry = conditional[entry_index]
                    constraint = entry["constraint"]
                    windows.append(
                        {
                            "period": f"scheduled-{period}",
                            "start": _time_without_zone(constraint.get("start_time")),
                            "end": _time_without_zone(constraint.get("end_time")),
                        }
                    )
                schedule = {
                    "timezone": "UTC",
                    "default_period": "default",
                    "boundary_policy": "start_inclusive_end_exclusive",
                    "windows": windows,
                }

            used_card_ids: set[str] = set()
            for index, entry in enumerate(conditional):
                if not isinstance(entry, Mapping) or not isinstance(entry.get("prices"), Mapping):
                    continue
                constraint = entry.get("constraint") if isinstance(entry.get("constraint"), Mapping) else {}
                components, adapter_warnings = _genai_price_components(entry["prices"])
                if not components:
                    continue
                suffix = "current"
                card: Dict[str, Any] = {
                    "schema_version": "0.1",
                    "id": f"{provider}:{model}:genai-prices:{index}",
                    "provider": provider,
                    "model": model,
                    "aliases": aliases,
                    "components": components,
                    "source": source,
                    "metadata": {
                        "genai_prices": {
                            "provider_name": raw_provider.get("name"),
                            "provider_match": raw_provider.get("provider_match"),
                            "model_match": raw_model.get("match"),
                            "api_pattern": raw_provider.get("api_pattern"),
                            "context_window": raw_model.get("context_window"),
                            "constraint": constraint,
                        }
                    },
                }
                if unsupported_match:
                    adapter_warnings.append("non-enumerable model match clause retained in metadata")
                start_date = constraint.get("start_date")
                if start_date:
                    start_text = str(start_date)
                    suffix = start_text
                    effective: Dict[str, Any] = {"from": start_text}
                    later = [candidate for candidate in dated_starts if candidate > start_text]
                    if later:
                        effective["to"] = _previous_day(later[0])
                    card["effective"] = effective
                elif dated_starts and not constraint:
                    card["effective"] = {"to": _previous_day(dated_starts[0])}
                    suffix = "historical"
                if constraint.get("start_time") or constraint.get("end_time"):
                    time_index = time_entry_periods[index]
                    card["pricing_period"] = f"scheduled-{time_index}"
                    card["billing_schedule"] = schedule
                    suffix = f"scheduled-{time_index}"
                elif schedule:
                    card["pricing_period"] = "default"
                    card["billing_schedule"] = schedule
                    suffix = "default" if suffix == "current" else f"{suffix}-default"
                unsupported_constraints = sorted(set(constraint) - {"start_date", "start_time", "end_time"})
                if unsupported_constraints:
                    adapter_warnings.append(
                        "unsupported constraints retained in metadata: " + ", ".join(unsupported_constraints)
                    )
                if adapter_warnings:
                    card["metadata"]["adapter_warnings"] = sorted(set(adapter_warnings))
                card_id = f"{provider}:{model}:genai-prices:{suffix}"
                if card_id in used_card_ids:
                    card_id = f"{card_id}:{index}"
                used_card_ids.add(card_id)
                card["id"] = card_id
                cards.append(card)
    return cards


OTEL_PROVIDER_MAP = {
    "openai": "openai",
    "anthropic": "anthropic",
    "aws.bedrock": "bedrock",
    "azure.ai.openai": "azure",
    "gcp.gen_ai": "google",
    "gcp.vertex_ai": "vertex",
    "x_ai": "xai",
}


def _otel_attributes(span: Mapping[str, Any]) -> Dict[str, Any]:
    attributes = span.get("attributes")
    if isinstance(attributes, Mapping):
        return {str(key): value for key, value in attributes.items()}
    return {str(key): value for key, value in span.items() if "." in str(key)}


def _otel_surface(provider: str, operation: str) -> str:
    if operation == "generate_content":
        return "vertex.gemini.generate_content" if provider == "vertex" else "google.gemini.generate_content"
    if provider == "anthropic":
        return "anthropic.messages"
    if provider == "bedrock":
        return "aws.bedrock.converse"
    if operation == "embeddings":
        return "openai.embeddings"
    return f"{provider}.chat_completions" if provider != "openai" else "openai.chat_completions"


def usage_ledger_from_otel_genai_span(
    span: Mapping[str, Any],
    *,
    provider: Optional[str] = None,
    surface: Optional[str] = None,
    model: Optional[str] = None,
    attribution: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Normalize current OpenTelemetry GenAI attributes without a backend."""

    attributes = _otel_attributes(span)
    provider_name = provider or OTEL_PROVIDER_MAP.get(str(attributes.get("gen_ai.provider.name") or ""), str(attributes.get("gen_ai.provider.name") or "unknown"))
    operation = str(attributes.get("gen_ai.operation.name") or "chat")
    requested_model = str(model or attributes.get("gen_ai.request.model") or attributes.get("gen_ai.response.model") or "unknown")
    returned_model = str(attributes.get("gen_ai.response.model") or requested_model)
    input_total = attributes.get("gen_ai.usage.input_tokens", 0)
    output_total = attributes.get("gen_ai.usage.output_tokens", 0)
    cache_write = attributes.get("gen_ai.usage.cache_creation.input_tokens", 0)
    cache_read = attributes.get("gen_ai.usage.cache_read.input_tokens", 0)
    reasoning = attributes.get("gen_ai.usage.reasoning.output_tokens", 0)
    components: List[Dict[str, Any]] = []
    component_values = [
        ("input_uncached_tokens", _nonnegative_difference(input_total, cache_write, cache_read), "$.attributes.gen_ai.usage.input_tokens"),
        ("input_cache_read_tokens", _decimal_string(cache_read), "$.attributes.gen_ai.usage.cache_read.input_tokens"),
        ("input_cache_write_tokens", _decimal_string(cache_write), "$.attributes.gen_ai.usage.cache_creation.input_tokens"),
        ("output_text_tokens", _nonnegative_difference(output_total, reasoning), "$.attributes.gen_ai.usage.output_tokens"),
        ("output_reasoning_tokens", _decimal_string(reasoning), "$.attributes.gen_ai.usage.reasoning.output_tokens"),
    ]
    for name, quantity, source_path in component_values:
        if _number(quantity) > 0:
            components.append({"name": name, "quantity": quantity, "unit": "token", "source_path": source_path})
    context: Dict[str, Any] = {}
    service_tier = (
        attributes.get("gen_ai.request.service_tier")
        or attributes.get("gen_ai.response.service_tier")
        or attributes.get("openai.response.service_tier")
        or attributes.get("openai.request.service_tier")
    )
    if service_tier:
        normalized_tier = _normalize_openai_service_tier(service_tier) if provider_name == "openai" else str(service_tier)
        if normalized_tier:
            context["service_tier"] = normalized_tier
    request_id = attributes.get("gen_ai.response.id") or attributes.get("openai.response.id")
    if request_id:
        context["request_id"] = str(request_id)
    trace_id = span.get("trace_id", span.get("traceId"))
    if trace_id:
        context["trace_id"] = str(trace_id)
    known = {
        "gen_ai.provider.name",
        "gen_ai.operation.name",
        "gen_ai.request.model",
        "gen_ai.response.model",
        "gen_ai.usage.input_tokens",
        "gen_ai.usage.output_tokens",
        "gen_ai.usage.cache_creation.input_tokens",
        "gen_ai.usage.cache_read.input_tokens",
        "gen_ai.usage.reasoning.output_tokens",
    }
    unknown = {key: value for key, value in attributes.items() if key.startswith("gen_ai.") and key not in known}
    ledger: Dict[str, Any] = {
        "schema_version": "0.1",
        "provider": provider_name,
        "surface": surface or _otel_surface(provider_name, operation),
        "model": {
            "requested": requested_model,
            "returned": returned_model,
            "billed": requested_model,
            "alias_resolution": "none",
        },
        "components": components,
        "raw_usage": {key: value for key, value in attributes.items() if key.startswith("gen_ai.usage.")},
        "metadata": {
            "otel_genai": {
                "operation": operation,
                "provider_attribute": attributes.get("gen_ai.provider.name"),
                "unknown_attributes": unknown,
            }
        },
    }
    if context:
        ledger["context"] = context
    normalized_attribution = normalize_attribution(attribution)
    if normalized_attribution:
        ledger["attribution"] = normalized_attribution
    return ledger


def from_otel_genai_span(
    span: Mapping[str, Any],
    *,
    price_cards: Optional[Iterable[Dict[str, Any]]] = None,
    discount_policies: Optional[Iterable[Dict[str, Any]]] = None,
    **options: Any,
) -> Dict[str, Any]:
    usage = usage_ledger_from_otel_genai_span(
        span,
        provider=options.pop("provider", None),
        surface=options.pop("surface", None),
        model=options.pop("model", None),
        attribution=options.pop("attribution", None),
    )
    cards = compile_price_catalog(price_cards or [])
    return calculate_cost(
        usage_ledger=usage,
        price_cards=cards,
        discount_policies=discount_policies,
        **options,
    )


def otel_cost_attributes(cost_ledger: Mapping[str, Any], *, prefix: str = "runcost") -> Dict[str, Any]:
    """Return telemetry attributes/events; it never exports them."""

    warnings = cost_ledger.get("warnings") if isinstance(cost_ledger.get("warnings"), list) else []
    return {
        f"{prefix}.cost.total": str(cost_ledger.get("total", "0")),
        f"{prefix}.cost.currency": str(cost_ledger.get("currency", "USD")),
        f"{prefix}.cost.component_count": len(cost_ledger.get("components", [])),
        f"{prefix}.cost.warning_count": len(warnings),
        f"{prefix}.cost.warning_codes": [str(warning.get("code")) for warning in warnings if isinstance(warning, Mapping)],
        f"{prefix}.cost.price_card_ids": sorted(
            {
                str(component.get("price_card_id"))
                for component in cost_ledger.get("components", [])
                if isinstance(component, Mapping) and component.get("price_card_id")
            }
        ),
    }


def estimate_cost(
    *,
    provider: str,
    surface: str,
    model: str,
    components: Union[Mapping[str, Any], Iterable[Mapping[str, Any]]],
    context: Optional[Mapping[str, Any]] = None,
    attribution: Optional[Mapping[str, Any]] = None,
    price_cards: Optional[Iterable[Dict[str, Any]]] = None,
    discount_policies: Optional[Iterable[Dict[str, Any]]] = None,
    **options: Any,
) -> Dict[str, Any]:
    """Stateless pre-call estimate from caller-provided expected quantities."""

    normalized_components: List[Dict[str, Any]] = []
    if isinstance(components, Mapping):
        iterable = ({"name": key, "quantity": value} for key, value in components.items())
    else:
        iterable = components
    for raw in iterable:
        item = dict(raw)
        item["quantity"] = _decimal_string(item.get("quantity", 0))
        item.setdefault("unit", "token")
        normalized_components.append(item)
    usage: Dict[str, Any] = {
        "schema_version": "0.1",
        "provider": provider,
        "surface": surface,
        "model": {"requested": model, "returned": model, "billed": model, "alias_resolution": "none"},
        "components": normalized_components,
        "metadata": {"estimate": True},
    }
    if context:
        usage["context"] = dict(context)
    normalized_attribution = normalize_attribution(attribution)
    if normalized_attribution:
        usage["attribution"] = normalized_attribution
    cards = compile_price_catalog(price_cards or [])
    return calculate_cost(
        usage_ledger=usage,
        price_cards=cards,
        discount_policies=discount_policies,
        **options,
    )


def evaluate_budget(
    ledger_or_total: Any,
    *,
    budget: Any,
    warning_threshold: Any = "0.8",
) -> Dict[str, Any]:
    """Evaluate one estimate/ledger against a stateless budget policy."""

    ledger = ledger_or_total if isinstance(ledger_or_total, Mapping) else None
    total = _number(ledger.get("total", 0) if ledger else ledger_or_total)
    limit = _number(budget)
    threshold = _number(warning_threshold)
    if limit < 0:
        raise ValueError("budget must be non-negative")
    if threshold < 0 or threshold > 1:
        raise ValueError("warning_threshold must be between 0 and 1")
    status = "exceeded" if total > limit else "warning" if limit > 0 and total >= limit * threshold else "within_budget"
    result: Dict[str, Any] = {
        "schema_version": "0.1",
        "status": status,
        "estimated_cost": _decimal_string(total),
        "budget": _decimal_string(limit),
        "remaining": _decimal_string(limit - total),
        "warning_threshold": _decimal_string(threshold),
        "currency": str(ledger.get("currency", "USD") if ledger else "USD"),
    }
    if ledger:
        result["ledger"] = dict(ledger)
    return result


def reconcile_cost(
    cost_ledger_or_total: Any,
    reported_total: Any,
    *,
    tolerance: Any = "0",
    currency: str = "USD",
) -> Dict[str, Any]:
    """Compare independent and provider-reported totals without replacing either."""

    ledger = cost_ledger_or_total if isinstance(cost_ledger_or_total, Mapping) else None
    calculated = _number(ledger.get("total", 0) if ledger else cost_ledger_or_total)
    reported = _number(reported_total)
    allowed = _number(tolerance)
    if allowed < 0:
        raise ValueError("tolerance must be non-negative")
    residual = reported - calculated
    absolute = abs(residual)
    status = "matched" if absolute == 0 else "within_tolerance" if absolute <= allowed else "mismatch"
    return {
        "schema_version": "0.1",
        "status": status,
        "calculated_total": _decimal_string(calculated),
        "reported_total": _decimal_string(reported),
        "signed_residual": _decimal_string(residual),
        "absolute_residual": _decimal_string(absolute),
        "tolerance": _decimal_string(allowed),
        "currency": str(ledger.get("currency", currency) if ledger else currency),
    }


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def verify_catalog_manifest(manifest: Mapping[str, Any], *, root: Union[str, Path]) -> Dict[str, Any]:
    """Verify every manifest artifact and return a machine-readable result."""

    root_path = Path(root)
    raw_shards = manifest.get("shards")
    entries = [manifest.get("catalog")] + (list(raw_shards) if isinstance(raw_shards, list) else [])
    checked: List[Dict[str, Any]] = []
    valid = (
        manifest.get("schema_version") == "0.1"
        and manifest.get("algorithm") == "sha256"
        and isinstance(manifest.get("catalog"), Mapping)
        and isinstance(raw_shards, list)
    )
    for raw in entries:
        if not isinstance(raw, Mapping):
            valid = False
            checked.append({"path": "", "exists": False, "sha256": None, "matches": False})
            continue
        relative = str(raw.get("path") or "")
        expected_digest = raw.get("sha256")
        if not relative or not isinstance(expected_digest, str) or len(expected_digest) != 64:
            valid = False
            checked.append({"path": relative, "exists": False, "sha256": None, "matches": False})
            continue
        path = root_path / relative
        exists = path.is_file()
        try:
            digest = sha256_bytes(path.read_bytes()) if exists else None
        except OSError:
            exists = False
            digest = None
        matches = exists and digest == expected_digest
        valid = valid and matches
        checked.append({"path": relative, "exists": exists, "sha256": digest, "matches": matches})
    return {"schema_version": "0.1", "valid": valid, "algorithm": "sha256", "artifacts": checked}


__all__ = [
    "canonical_json_bytes",
    "estimate_cost",
    "evaluate_budget",
    "from_batch_results",
    "from_otel_genai_span",
    "normalize_attribution",
    "otel_cost_attributes",
    "price_cards_from_genai_prices",
    "reconcile_cost",
    "sha256_bytes",
    "usage_ledger_from_otel_genai_span",
    "verify_catalog_manifest",
]
