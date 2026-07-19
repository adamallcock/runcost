"""Explicit external price-source resolution for RunCost convenience APIs.

The deterministic calculation functions in :mod:`runcost.core` never call this
module.  Callers opt into network/cache policy through ``resolve_price_catalog``
or one of the ``*_auto`` convenience functions below.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import tempfile
import threading
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .core import CompiledPriceCatalog, calculate_cost, compile_price_catalog, extract_usage_ledger, from_response, infer_surface


DEFAULT_EXTERNAL_PRICE_SOURCES: Tuple[str, ...] = (
    "genai-prices",
    "models.dev",
    "litellm",
)
OPENROUTER_EXTERNAL_PRICE_SOURCES: Tuple[str, ...] = (
    "openrouter",
    *DEFAULT_EXTERNAL_PRICE_SOURCES,
)
DEFAULT_PRICE_CACHE_MAX_AGE_SECONDS = 24 * 60 * 60

EXTERNAL_PRICE_SOURCE_URLS: Dict[str, str] = {
    "genai-prices": "https://raw.githubusercontent.com/pydantic/genai-prices/main/prices/data_slim.json",
    "models.dev": "https://models.dev/api.json",
    "litellm": "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json",
    "openrouter": "https://openrouter.ai/api/v1/models",
}

_INCOMPLETE_WARNING_CODES = {
    "unknown_provider",
    "unknown_model",
    "price_not_found",
    "component_unpriced",
    "tool_component_unpriced",
    "source_capability_unsupported",
    "service_tier_unsupported",
    "long_context_rule_missing",
    "historical_price_missing",
    "pricing_period_required",
    "pricing_period_unsupported",
    "billing_schedule_unsupported",
}

_CACHE_LOCK = threading.RLock()
_CACHE_MEMORY: Dict[Path, Tuple[int, int, Dict[str, Any]]] = {}
_COMPILED_CACHE: "OrderedDict[int, Tuple[List[Dict[str, Any]], CompiledPriceCatalog]]" = OrderedDict()
_COMPILED_CACHE_LIMIT = 32


def default_price_cache_dir() -> Path:
    """Return the OS-appropriate persistent cache directory."""

    override = os.environ.get("RUNCOST_PRICE_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Caches" / "runcost" / "prices"
    if system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
        return base / "runcost" / "prices"
    base = Path(os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache"))
    return base / "runcost" / "prices"


def _utc_now(now: Optional[Any] = None) -> datetime:
    if isinstance(now, datetime):
        value = now
    elif isinstance(now, str):
        value = datetime.fromisoformat(now.replace("Z", "+00:00"))
    elif now is None:
        value = datetime.now(timezone.utc)
    else:
        raise TypeError("now must be an ISO timestamp, datetime, or None")
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _cache_path(cache_dir: Path, source: str, url: str) -> Path:
    safe_source = "".join(character if character.isalnum() or character in "-." else "-" for character in source)
    url_suffix = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    return cache_dir / f"{safe_source}-{url_suffix}.json"


def _safe_public_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme == "https" and parsed.hostname:
        return True
    return parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}


def _read_cache(path: Path, source: str, url: str) -> Optional[Dict[str, Any]]:
    try:
        stat = path.stat()
    except OSError:
        with _CACHE_LOCK:
            _CACHE_MEMORY.pop(path, None)
        return None
    signature = (stat.st_mtime_ns, stat.st_size)
    with _CACHE_LOCK:
        memoized = _CACHE_MEMORY.get(path)
        if memoized and memoized[:2] == signature:
            return memoized[2]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or data.get("schema_version") != "0.1":
        return None
    metadata = data.get("source")
    cards = data.get("price_cards")
    if not isinstance(metadata, dict) or not isinstance(cards, list):
        return None
    if metadata.get("name") != source or metadata.get("url") != url:
        return None
    expected = data.get("cards_checksum")
    if expected and expected != _sha256(_canonical_bytes(cards)):
        return None
    with _CACHE_LOCK:
        _CACHE_MEMORY[path] = (signature[0], signature[1], data)
    return data


def _atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    file_descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(file_descriptor, "wb") as file:
            file.write(encoded)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_name, path)
        stat = path.stat()
        if isinstance(value, dict):
            with _CACHE_LOCK:
                _CACHE_MEMORY[path] = (stat.st_mtime_ns, stat.st_size, value)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def _compiled_catalog(cards: List[Dict[str, Any]]) -> CompiledPriceCatalog:
    """Reuse indexes for resolver-owned card lists without changing public output."""

    key = id(cards)
    with _CACHE_LOCK:
        cached = _COMPILED_CACHE.get(key)
        if cached and cached[0] is cards:
            _COMPILED_CACHE.move_to_end(key)
            return cached[1]
    compiled = compile_price_catalog(cards)
    with _CACHE_LOCK:
        _COMPILED_CACHE[key] = (cards, compiled)
        _COMPILED_CACHE.move_to_end(key)
        while len(_COMPILED_CACHE) > _COMPILED_CACHE_LIMIT:
            _COMPILED_CACHE.popitem(last=False)
    return compiled


def _default_fetch(url: str, headers: Mapping[str, str], timeout: float, max_bytes: int) -> Tuple[int, Dict[str, str], bytes, str]:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "runcost-price-resolver/0.2", **dict(headers)})
    try:
        response = urlopen(request, timeout=timeout)  # nosec B310 - URL is validated before this call.
    except HTTPError as exc:
        if exc.code == 304:
            return 304, {key.lower(): value for key, value in exc.headers.items()}, b"", url
        raise
    with response:
        final_url = response.geturl()
        if not _safe_public_url(final_url):
            raise ValueError("price source redirected to an unsupported URL")
        body = response.read(max_bytes + 1)
        if len(body) > max_bytes:
            raise ValueError(f"price source exceeds the {max_bytes}-byte safety limit")
        return int(response.status), {key.lower(): value for key, value in response.headers.items()}, body, final_url


def _fetch(
    url: str,
    headers: Mapping[str, str],
    timeout: float,
    max_bytes: int,
    fetcher: Optional[Callable[..., Any]],
) -> Tuple[int, Dict[str, str], bytes, str]:
    if not _safe_public_url(url):
        raise ValueError("price source URL must use HTTPS (loopback HTTP is allowed for tests)")
    if fetcher is None:
        return _default_fetch(url, headers, timeout, max_bytes)
    result = fetcher(url, dict(headers), timeout)
    if isinstance(result, Mapping):
        status = int(result.get("status", 200))
        response_headers = {str(key).lower(): str(value) for key, value in dict(result.get("headers") or {}).items()}
        body_value = result.get("body", b"")
        final_url = str(result.get("url") or url)
    else:
        status, response_headers, body_value = result[:3]
        final_url = result[3] if len(result) > 3 else url
        status = int(status)
        response_headers = {str(key).lower(): str(value) for key, value in dict(response_headers).items()}
    body = body_value.encode("utf-8") if isinstance(body_value, str) else bytes(body_value)
    if len(body) > max_bytes:
        raise ValueError(f"price source exceeds the {max_bytes}-byte safety limit")
    if not _safe_public_url(final_url):
        raise ValueError("price source redirected to an unsupported URL")
    return status, response_headers, body, str(final_url)


def _adapt_source(source: str, payload: Any, *, url: str, retrieved_at: str) -> List[Dict[str, Any]]:
    if source == "genai-prices":
        from .expansion import price_cards_from_genai_prices

        return price_cards_from_genai_prices(payload, source_url=url, retrieved_at=retrieved_at)
    from .core import price_cards_from_litellm, price_cards_from_models_dev, price_cards_from_openrouter_models

    if source == "models.dev":
        return price_cards_from_models_dev(payload, source_url=url, retrieved_at=retrieved_at)
    if source == "litellm":
        return price_cards_from_litellm(payload, source_url=url, retrieved_at=retrieved_at)
    if source == "openrouter":
        return price_cards_from_openrouter_models(payload, source_url=url, retrieved_at=retrieved_at)
    raise ValueError(f"unsupported external price source: {source}")


def _cache_age_seconds(cache: Mapping[str, Any], now: datetime) -> Optional[float]:
    source = cache.get("source") if isinstance(cache.get("source"), Mapping) else {}
    checked = _parse_timestamp(source.get("validated_at") or source.get("retrieved_at"))
    return max(0.0, (now - checked).total_seconds()) if checked else None


def _source_warning(code: str, source: str, status: str) -> Dict[str, Any]:
    message = (
        f"Could not refresh external price source {source}; using its last-known-good cache."
        if code == "price_source_refresh_failed"
        else f"External price source {source} is unavailable and has no usable cache."
    )
    return {"code": code, "message": message, "metadata": {"source": source, "status": status}}


def _source_state(
    source: str,
    *,
    url: str,
    cache_dir: Path,
    offline: bool,
    refresh: bool,
    max_age_seconds: int,
    timeout: float,
    max_bytes: int,
    fetcher: Optional[Callable[..., Any]],
    now: datetime,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    path = _cache_path(cache_dir, source, url)
    cache = _read_cache(path, source, url)
    age = _cache_age_seconds(cache, now) if cache else None
    public_state: Dict[str, Any] = {
        "name": source,
        "type": "external",
        "url": url,
        "cache_key": path.name,
        "status": "unavailable",
        "card_count": 0,
    }
    warnings: List[Dict[str, Any]] = []
    if cache:
        metadata = cache["source"]
        public_state.update(
            {
                "retrieved_at": metadata.get("retrieved_at"),
                "validated_at": metadata.get("validated_at"),
                "checksum": metadata.get("checksum"),
                "etag": metadata.get("etag"),
                "last_modified": metadata.get("last_modified"),
                "card_count": len(cache["price_cards"]),
            }
        )
    if offline:
        if cache:
            public_state["status"] = "cache_fresh" if age is not None and age <= max_age_seconds else "cache_stale"
            public_state["price_cards"] = cache["price_cards"]
        else:
            warnings.append(_source_warning("price_source_unavailable", source, "offline_cache_miss"))
        return public_state, warnings
    if cache and not refresh and age is not None and age <= max_age_seconds:
        public_state["status"] = "cache_fresh"
        public_state["price_cards"] = cache["price_cards"]
        return public_state, warnings

    conditional_headers: Dict[str, str] = {}
    if cache:
        metadata = cache["source"]
        if metadata.get("etag"):
            conditional_headers["If-None-Match"] = str(metadata["etag"])
        if metadata.get("last_modified"):
            conditional_headers["If-Modified-Since"] = str(metadata["last_modified"])
    try:
        status, response_headers, body, final_url = _fetch(url, conditional_headers, timeout, max_bytes, fetcher)
        checked_at = _timestamp(now)
        if status == 304:
            if not cache:
                raise ValueError("received 304 without a cached representation")
            cache["source"]["validated_at"] = checked_at
            cache["source"]["etag"] = response_headers.get("etag") or cache["source"].get("etag")
            cache["source"]["last_modified"] = response_headers.get("last-modified") or cache["source"].get("last_modified")
            _atomic_write(path, cache)
            public_state.update(
                {
                    "status": "cache_validated",
                    "validated_at": checked_at,
                    "etag": cache["source"].get("etag"),
                    "last_modified": cache["source"].get("last_modified"),
                    "price_cards": cache["price_cards"],
                }
            )
            return public_state, warnings
        if status < 200 or status >= 300:
            raise ValueError(f"price source returned HTTP {status}")
        payload = json.loads(body.decode("utf-8"))
        retrieved_at = checked_at
        cards = _adapt_source(source, payload, url=final_url, retrieved_at=retrieved_at)
        if not cards:
            raise ValueError("price source produced no supported price cards")
        envelope: Dict[str, Any] = {
            "schema_version": "0.1",
            "source": {
                "name": source,
                "type": "external",
                "url": url,
                "resolved_url": final_url,
                "retrieved_at": retrieved_at,
                "validated_at": retrieved_at,
                "checksum": _sha256(body),
            },
            "cards_checksum": _sha256(_canonical_bytes(cards)),
            "price_cards": cards,
        }
        if response_headers.get("etag"):
            envelope["source"]["etag"] = response_headers["etag"]
        if response_headers.get("last-modified"):
            envelope["source"]["last_modified"] = response_headers["last-modified"]
        _atomic_write(path, envelope)
        public_state.update(
            {
                "status": "refreshed",
                "retrieved_at": retrieved_at,
                "validated_at": retrieved_at,
                "checksum": envelope["source"]["checksum"],
                "etag": envelope["source"].get("etag"),
                "last_modified": envelope["source"].get("last_modified"),
                "card_count": len(cards),
                "price_cards": cards,
            }
        )
        return public_state, warnings
    except (OSError, ValueError, TypeError, json.JSONDecodeError, HTTPError):
        if cache:
            public_state["status"] = "cache_stale"
            public_state["price_cards"] = cache["price_cards"]
            warnings.append(_source_warning("price_source_refresh_failed", source, "last_known_good"))
        else:
            warnings.append(_source_warning("price_source_unavailable", source, "fetch_failed"))
        return public_state, warnings


def _source_order(provider: Optional[str], sources: Optional[Iterable[str]]) -> List[str]:
    if sources is not None:
        order = [str(source) for source in sources]
    elif str(provider or "").lower() == "openrouter":
        order = list(OPENROUTER_EXTERNAL_PRICE_SOURCES)
    else:
        order = list(DEFAULT_EXTERNAL_PRICE_SOURCES)
    result: List[str] = []
    for source in order:
        if source not in EXTERNAL_PRICE_SOURCE_URLS:
            raise ValueError(f"unsupported external price source: {source}")
        if source not in result:
            result.append(source)
    if not result:
        raise ValueError("at least one external price source is required")
    return result


def _candidate_quality(usage_ledger: Mapping[str, Any], cards: Sequence[Dict[str, Any]]) -> Tuple[bool, int]:
    catalog = _compiled_catalog(cards if isinstance(cards, list) else list(cards))
    ledger = calculate_cost(usage_ledger=dict(usage_ledger), price_cards=catalog)
    codes = {
        str(warning.get("code"))
        for warning in ledger.get("warnings", [])
        if isinstance(warning, Mapping)
    }
    incomplete = codes & _INCOMPLETE_WARNING_CODES
    return not incomplete, len(ledger.get("components", []))


def resolve_price_catalog(
    *,
    usage_ledger: Optional[Mapping[str, Any]] = None,
    provider: Optional[str] = None,
    price_cards: Optional[Iterable[Dict[str, Any]]] = None,
    contract_price_cards: Optional[Iterable[Dict[str, Any]]] = None,
    sources: Optional[Iterable[str]] = None,
    source_urls: Optional[Mapping[str, str]] = None,
    cache_dir: Optional[Any] = None,
    offline: bool = False,
    refresh: bool = False,
    max_age_seconds: int = DEFAULT_PRICE_CACHE_MAX_AGE_SECONDS,
    timeout: float = 15.0,
    max_bytes: int = 64 * 1024 * 1024,
    fetcher: Optional[Callable[..., Any]] = None,
    now: Optional[Any] = None,
) -> Dict[str, Any]:
    """Resolve exactly one price source and return cards plus audit metadata.

    Explicit user or contract cards always win. External candidates are tried
    in order and are never merged. If no candidate fully covers a supplied
    usage ledger, the first partially applicable candidate is selected so the
    deterministic calculator can report its component-level limitations.
    """

    explicit_provided = contract_price_cards is not None or price_cards is not None
    raw_explicit_cards = contract_price_cards if contract_price_cards is not None else price_cards
    explicit_cards = raw_explicit_cards if isinstance(raw_explicit_cards, list) else list(raw_explicit_cards or [])
    observed_at = _utc_now(now)
    if explicit_provided:
        return {
            "schema_version": "0.1",
            "selected_source": "user",
            "price_cards": explicit_cards,
            "sources": [
                {
                    "name": "user",
                    "type": "contract" if contract_price_cards is not None else "user",
                    "status": "selected",
                    "card_count": len(explicit_cards),
                }
            ],
            "warnings": [],
            "resolved_at": _timestamp(observed_at),
        }

    resolved_provider = provider or (str(usage_ledger.get("provider")) if usage_ledger else None)
    order = _source_order(resolved_provider, sources)
    urls = {**EXTERNAL_PRICE_SOURCE_URLS, **dict(source_urls or {})}
    root = Path(cache_dir).expanduser() if cache_dir is not None else default_price_cache_dir()
    public_states: List[Dict[str, Any]] = []
    operational_warnings: List[Dict[str, Any]] = []
    first_partial: Optional[Tuple[str, List[Dict[str, Any]]]] = None
    selected: Optional[Tuple[str, List[Dict[str, Any]]]] = None

    for source in order:
        state, warnings = _source_state(
            source,
            url=urls[source],
            cache_dir=root,
            offline=offline,
            refresh=refresh,
            max_age_seconds=max_age_seconds,
            timeout=timeout,
            max_bytes=max_bytes,
            fetcher=fetcher,
            now=observed_at,
        )
        cards = list(state.pop("price_cards", []))
        public_states.append(state)
        operational_warnings.extend(warnings)
        if not cards:
            continue
        if usage_ledger is None:
            selected = (source, cards)
            break
        complete, priced_components = _candidate_quality(usage_ledger, cards)
        state["priced_component_count"] = priced_components
        state["applicable"] = priced_components > 0
        if priced_components > 0 and first_partial is None:
            first_partial = (source, cards)
        if complete:
            selected = (source, cards)
            break

    if selected is None:
        selected = first_partial
    selected_source = selected[0] if selected else None
    selected_cards = selected[1] if selected else []
    for state in public_states:
        state["selected"] = state["name"] == selected_source
    if not selected:
        operational_warnings.append(
            {
                "code": "price_source_unavailable",
                "message": "No configured external price source produced applicable price cards.",
                "metadata": {"source": ",".join(order), "status": "no_applicable_source"},
            }
        )
    deduplicated_warnings: List[Dict[str, Any]] = []
    seen_warning_keys = set()
    for warning in operational_warnings:
        key = (warning["code"], warning["metadata"]["source"], warning["metadata"]["status"])
        if key not in seen_warning_keys:
            seen_warning_keys.add(key)
            deduplicated_warnings.append(warning)
    return {
        "schema_version": "0.1",
        "selected_source": selected_source,
        "price_cards": selected_cards,
        "sources": public_states,
        "warnings": deduplicated_warnings,
        "resolved_at": _timestamp(observed_at),
    }


def _resolution_metadata(resolution: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": resolution.get("schema_version", "0.1"),
        "selected_source": resolution.get("selected_source"),
        "sources": resolution.get("sources", []),
        "resolved_at": resolution.get("resolved_at"),
    }


def attach_price_resolution(result: Dict[str, Any], resolution: Mapping[str, Any]) -> Dict[str, Any]:
    """Attach source provenance and operational warnings to a result ledger."""

    metadata = dict(result.get("metadata") or {})
    metadata["price_resolution"] = _resolution_metadata(resolution)
    result["metadata"] = metadata
    warnings = list(result.get("warnings") or [])
    existing = {
        (warning.get("code"), json.dumps(warning.get("metadata") or {}, sort_keys=True))
        for warning in warnings
        if isinstance(warning, Mapping)
    }
    for warning in resolution.get("warnings", []):
        key = (warning.get("code"), json.dumps(warning.get("metadata") or {}, sort_keys=True))
        if key not in existing:
            warnings.append(dict(warning))
            existing.add(key)
    result["warnings"] = warnings
    return result


_RESOLVER_OPTION_NAMES = {
    "contract_price_cards",
    "sources",
    "price_sources",
    "source_urls",
    "cache_dir",
    "offline",
    "refresh",
    "max_age_seconds",
    "timeout",
    "max_bytes",
    "fetcher",
    "now",
}


def _split_resolver_options(options: Mapping[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    calculation = dict(options)
    resolver: Dict[str, Any] = {}
    for name in _RESOLVER_OPTION_NAMES:
        if name in calculation:
            value = calculation.pop(name)
            resolver["sources" if name == "price_sources" else name] = value
    return calculation, resolver


def from_response_auto(response: Dict[str, Any], **options: Any) -> Dict[str, Any]:
    """Price a response using external sources and the persistent cache."""

    calculation, resolver_options = _split_resolver_options(options)
    explicit_cards = calculation.pop("price_cards", None)
    if explicit_cards is not None:
        resolution = resolve_price_catalog(price_cards=explicit_cards, **resolver_options)
        result = from_response(response, price_cards=_compiled_catalog(resolution["price_cards"]), **calculation)
        return attach_price_resolution(result, resolution)
    surface = calculation.get("surface") or infer_surface(response, provider=calculation.get("provider"))
    extraction_options = {
        key: value
        for key, value in calculation.items()
        if key not in {
            "discount_policies",
            "mode",
            "stale_after_days",
            "provider_reported_cost",
            "provider_reported_cost_mode",
            "price_source_priority",
            "debug_trace",
        }
    }
    extraction_options["surface"] = surface or "unknown"
    try:
        usage = extract_usage_ledger(response, **extraction_options)
    except ValueError:
        return from_response(response, price_cards=[], **calculation)
    resolution = resolve_price_catalog(usage_ledger=usage, provider=usage.get("provider"), **resolver_options)
    result = from_response(response, price_cards=_compiled_catalog(resolution["price_cards"]), **calculation)
    return attach_price_resolution(result, resolution)


def from_batch_results_auto(items: Iterable[Mapping[str, Any]], *, provider: str, **options: Any) -> Dict[str, Any]:
    """Price provider batch output with one externally resolved catalog."""

    from .expansion import from_batch_results

    calculation, resolver_options = _split_resolver_options(options)
    explicit_cards = calculation.pop("price_cards", None)
    resolution = resolve_price_catalog(
        provider=provider,
        price_cards=explicit_cards,
        **resolver_options,
    )
    result = from_batch_results(items, provider=provider, price_cards=_compiled_catalog(resolution["price_cards"]), **calculation)
    metadata = dict(result.get("metadata") or {})
    metadata["price_resolution"] = _resolution_metadata(resolution)
    result["metadata"] = metadata
    aggregate = result.get("aggregate")
    if isinstance(aggregate, dict):
        attach_price_resolution(aggregate, resolution)
    for item in result.get("items", []):
        if isinstance(item, dict) and isinstance(item.get("ledger"), dict):
            attach_price_resolution(item["ledger"], resolution)
    existing_codes = {
        (warning.get("code"), json.dumps(warning.get("metadata") or {}, sort_keys=True))
        for warning in result.get("warnings", [])
        if isinstance(warning, Mapping)
    }
    for warning in resolution.get("warnings", []):
        key = (warning.get("code"), json.dumps(warning.get("metadata") or {}, sort_keys=True))
        if key not in existing_codes:
            result.setdefault("warnings", []).append(dict(warning))
            existing_codes.add(key)
    return result


def from_otel_genai_span_auto(span: Mapping[str, Any], **options: Any) -> Dict[str, Any]:
    """Price an OpenTelemetry GenAI span through the external resolver."""

    from .expansion import from_otel_genai_span, usage_ledger_from_otel_genai_span

    calculation, resolver_options = _split_resolver_options(options)
    explicit_cards = calculation.pop("price_cards", None)
    usage = usage_ledger_from_otel_genai_span(
        span,
        provider=calculation.get("provider"),
        surface=calculation.get("surface"),
        model=calculation.get("model"),
        attribution=calculation.get("attribution"),
    )
    resolution = resolve_price_catalog(
        usage_ledger=usage,
        provider=usage.get("provider"),
        price_cards=explicit_cards,
        **resolver_options,
    )
    result = from_otel_genai_span(span, price_cards=_compiled_catalog(resolution["price_cards"]), **calculation)
    return attach_price_resolution(result, resolution)


def estimate_cost_auto(
    *,
    provider: str,
    surface: str,
    model: str,
    components: Any,
    **options: Any,
) -> Dict[str, Any]:
    """Estimate a call using one externally resolved price source."""

    from .expansion import estimate_cost

    calculation, resolver_options = _split_resolver_options(options)
    explicit_cards = calculation.pop("price_cards", None)
    if isinstance(components, Mapping):
        raw_components = [{"name": key, "quantity": value, "unit": "token"} for key, value in components.items()]
    else:
        raw_components = [dict(component) for component in components]
    usage = {
        "schema_version": "0.1",
        "provider": provider,
        "surface": surface,
        "model": {"requested": model, "returned": model, "billed": model, "alias_resolution": "none"},
        "components": [
            {
                "name": str(component.get("name")),
                "quantity": str(component.get("quantity", 0)),
                "unit": str(component.get("unit", "token")),
            }
            for component in raw_components
        ],
    }
    if isinstance(calculation.get("context"), Mapping):
        usage["context"] = dict(calculation["context"])
    resolution = resolve_price_catalog(
        usage_ledger=usage,
        provider=provider,
        price_cards=explicit_cards,
        **resolver_options,
    )
    result = estimate_cost(
        provider=provider,
        surface=surface,
        model=model,
        components=components,
        price_cards=_compiled_catalog(resolution["price_cards"]),
        **calculation,
    )
    return attach_price_resolution(result, resolution)


def price_cache_status(*, cache_dir: Optional[Any] = None, now: Optional[Any] = None) -> Dict[str, Any]:
    """Inspect cache metadata without reading provider payloads into output."""

    root = Path(cache_dir).expanduser() if cache_dir is not None else default_price_cache_dir()
    observed_at = _utc_now(now)
    entries: List[Dict[str, Any]] = []
    if root.exists():
        for path in sorted(root.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                entries.append({"cache_key": path.name, "status": "invalid"})
                continue
            source = data.get("source") if isinstance(data, Mapping) and isinstance(data.get("source"), Mapping) else {}
            age = _cache_age_seconds(data, observed_at) if isinstance(data, Mapping) else None
            entries.append(
                {
                    "cache_key": path.name,
                    "name": source.get("name"),
                    "url": source.get("url"),
                    "retrieved_at": source.get("retrieved_at"),
                    "validated_at": source.get("validated_at"),
                    "checksum": source.get("checksum"),
                    "etag": source.get("etag"),
                    "last_modified": source.get("last_modified"),
                    "card_count": len(data.get("price_cards", [])) if isinstance(data, Mapping) else 0,
                    "age_seconds": int(age) if age is not None else None,
                    "status": "valid" if source and isinstance(data.get("price_cards"), list) else "invalid",
                }
            )
    return {"schema_version": "0.1", "cache_dir": str(root), "checked_at": _timestamp(observed_at), "entries": entries}


def clear_price_cache(*, cache_dir: Optional[Any] = None, sources: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """Delete only RunCost-managed external price-cache files."""

    root = Path(cache_dir).expanduser() if cache_dir is not None else default_price_cache_dir()
    allowed = set(str(source) for source in sources) if sources is not None else None
    removed: List[str] = []
    if root.exists():
        for path in sorted(root.glob("*.json")):
            source = path.name.rsplit("-", 1)[0]
            if allowed is not None and source not in allowed:
                continue
            path.unlink()
            with _CACHE_LOCK:
                _CACHE_MEMORY.pop(path, None)
            removed.append(path.name)
    return {"schema_version": "0.1", "cache_dir": str(root), "removed": removed}
