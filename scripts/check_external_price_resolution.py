#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PYTHON_PACKAGE = ROOT / "packages" / "python"
if str(PYTHON_PACKAGE) not in sys.path:
    sys.path.insert(0, str(PYTHON_PACKAGE))

from runcost import (  # noqa: E402
    clear_price_cache,
    from_response_auto,
    price_cache_status,
    resolve_price_catalog,
)

GENAI_UNKNOWN = {
    "providers": [
        {
            "id": "openai",
            "models": [
                {"id": "another-model", "match": {"equals": "another-model"}, "prices": {"input_mtok": "9", "output_mtok": "9"}}
            ],
        }
    ]
}
MODELS_DEV_TARGET = {
    "openai": {
        "name": "OpenAI",
        "models": {"gpt-test": {"name": "GPT Test", "cost": {"input": "1", "output": "2"}}},
    }
}
OPENROUTER_TARGET = {
    "data": [
        {"id": "openai/gpt-test", "pricing": {"prompt": "0.000001", "completion": "0.000002"}}
    ]
}
RESPONSE = {
    "id": "chatcmpl_test",
    "object": "chat.completion",
    "model": "gpt-test",
    "choices": [],
    "usage": {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500},
}
USAGE = {
    "schema_version": "0.1",
    "provider": "openai",
    "surface": "openai.chat_completions",
    "model": {"requested": "gpt-test", "returned": "gpt-test", "billed": "gpt-test", "alias_resolution": "none"},
    "components": [
        {"name": "input_uncached_tokens", "quantity": "1000", "unit": "token"},
        {"name": "output_text_tokens", "quantity": "500", "unit": "token"},
    ],
}
SOURCE_URLS = {
    "genai-prices": "https://example.com/genai-prices.json",
    "models.dev": "https://example.com/models-dev.json",
    "openrouter": "https://example.com/openrouter.json",
}


class FixtureFetcher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str]]] = []
        self.mode = "normal"

    def __call__(self, url: str, headers: dict[str, str], _timeout: float) -> dict[str, Any]:
        self.calls.append((url, headers))
        if self.mode == "fail":
            raise OSError("fixture refresh failure")
        if self.mode == "not-modified":
            return {"status": 304, "headers": {"etag": '"fixture-v2"'}, "body": b"", "url": url}
        payload = GENAI_UNKNOWN if "genai" in url else MODELS_DEV_TARGET if "models-dev" in url else OPENROUTER_TARGET
        return {
            "status": 200,
            "headers": {"etag": '"fixture-v1"', "last-modified": "Fri, 18 Jul 2026 00:00:00 GMT"},
            "body": json.dumps(payload),
            "url": url,
        }


def assert_true(value: Any, message: str) -> None:
    if not value:
        raise AssertionError(message)


def check_python() -> None:
    explicit = [
        {
            "schema_version": "0.1",
            "id": "openai:gpt-test:user",
            "provider": "openai",
            "model": "gpt-test",
            "components": [
                {"usage_component": "input_uncached_tokens", "unit": "token", "price": {"amount": "1", "currency": "USD", "per": "1000000"}}
            ],
            "source": {"name": "user", "url": "https://example.com/contract", "retrieved_at": "2026-07-18T00:00:00Z"},
        }
    ]
    fetcher = FixtureFetcher()
    explicit_resolution = resolve_price_catalog(price_cards=explicit, fetcher=fetcher)
    assert_true(explicit_resolution["selected_source"] == "user" and not fetcher.calls, "explicit cards must bypass network sources")
    explicit_empty = resolve_price_catalog(price_cards=[], fetcher=fetcher)
    assert_true(
        explicit_empty["selected_source"] == "user" and explicit_empty["price_cards"] == [] and not fetcher.calls,
        "an explicit empty catalog must disable network resolution",
    )

    with tempfile.TemporaryDirectory(prefix="runcost-resolver-") as cache:
        resolution = resolve_price_catalog(
            usage_ledger=USAGE,
            sources=["genai-prices", "models.dev"],
            source_urls=SOURCE_URLS,
            cache_dir=cache,
            fetcher=fetcher,
            now="2026-07-18T00:00:00Z",
        )
        assert_true(resolution["selected_source"] == "models.dev", "resolver must fall back to the first applicable source")
        assert_true(len(fetcher.calls) == 2, "resolver must try external sources in order")
        assert_true({card["source"]["name"] for card in resolution["price_cards"]} == {"models.dev"}, "resolver must never mix source cards")

        call_count = len(fetcher.calls)
        fresh = resolve_price_catalog(
            usage_ledger=USAGE,
            sources=["models.dev"],
            source_urls=SOURCE_URLS,
            cache_dir=cache,
            fetcher=fetcher,
            now="2026-07-18T01:00:00Z",
        )
        assert_true(len(fetcher.calls) == call_count and fresh["sources"][0]["status"] == "cache_fresh", "fresh cache must avoid the network")

        fetcher.mode = "not-modified"
        validated = resolve_price_catalog(
            usage_ledger=USAGE,
            sources=["models.dev"],
            source_urls=SOURCE_URLS,
            cache_dir=cache,
            fetcher=fetcher,
            refresh=True,
            now="2026-07-18T02:00:00Z",
        )
        assert_true(validated["sources"][0]["status"] == "cache_validated", "HTTP 304 must revalidate cached cards")
        assert_true(fetcher.calls[-1][1].get("If-None-Match") == '"fixture-v1"', "conditional refresh must send ETag")

        fetcher.mode = "fail"
        stale = resolve_price_catalog(
            usage_ledger=USAGE,
            sources=["models.dev"],
            source_urls=SOURCE_URLS,
            cache_dir=cache,
            fetcher=fetcher,
            refresh=True,
            now="2026-07-20T00:00:00Z",
        )
        assert_true(stale["selected_source"] == "models.dev", "refresh failure must retain last-known-good cards")
        assert_true(any(warning["code"] == "price_source_refresh_failed" for warning in stale["warnings"]), "refresh failure warning missing")

        calls_before_offline = len(fetcher.calls)
        offline = resolve_price_catalog(
            usage_ledger=USAGE,
            sources=["models.dev"],
            source_urls=SOURCE_URLS,
            cache_dir=cache,
            offline=True,
            now="2026-07-20T00:00:00Z",
        )
        assert_true(len(fetcher.calls) == calls_before_offline, "offline mode must never fetch")
        assert_true(offline["sources"][0]["status"] == "cache_stale", "offline stale cache status missing")

        ledger = from_response_auto(
            RESPONSE,
            provider="openai",
            surface="openai.chat_completions",
            sources=["models.dev"],
            source_urls=SOURCE_URLS,
            cache_dir=cache,
            offline=True,
        )
        assert_true(ledger["total"] == "0.002", f"auto response total mismatch: {ledger['total']}")
        assert_true(ledger["metadata"]["price_resolution"]["selected_source"] == "models.dev", "ledger resolution provenance missing")

        status = price_cache_status(cache_dir=cache)
        assert_true(status["entries"] and status["entries"][0]["checksum"].startswith("sha256:"), "cache status must expose checksum metadata")
        removed = clear_price_cache(cache_dir=cache, sources=["models.dev"])
        assert_true(removed["removed"], "selective cache clear removed no entries")

    with tempfile.TemporaryDirectory(prefix="runcost-offline-") as cache:
        no_cache_fetcher = FixtureFetcher()
        missing = resolve_price_catalog(
            usage_ledger=USAGE,
            sources=["models.dev"],
            source_urls=SOURCE_URLS,
            cache_dir=cache,
            offline=True,
            fetcher=no_cache_fetcher,
        )
        assert_true(not no_cache_fetcher.calls and missing["selected_source"] is None, "offline cache miss must not fetch or select a source")
        assert_true(any(warning["code"] == "price_source_unavailable" for warning in missing["warnings"]), "offline cache-miss warning missing")

    with tempfile.TemporaryDirectory(prefix="runcost-openrouter-") as cache:
        openrouter_fetcher = FixtureFetcher()
        openrouter_usage = {**USAGE, "provider": "openrouter", "model": {**USAGE["model"], "requested": "openai/gpt-test", "returned": "openai/gpt-test", "billed": "openai/gpt-test"}}
        routed = resolve_price_catalog(
            usage_ledger=openrouter_usage,
            source_urls=SOURCE_URLS,
            cache_dir=cache,
            fetcher=openrouter_fetcher,
        )
        assert_true(routed["selected_source"] == "openrouter", "OpenRouter-billed usage must prefer OpenRouter's own price API")
        assert_true(len(openrouter_fetcher.calls) == 1 and "openrouter" in openrouter_fetcher.calls[0][0], "OpenRouter route must not proxy direct-provider pricing")

    for relative in (
        "packages/python/runcost/data/default-source-cache.json",
        "packages/javascript/core/data/default-source-cache.json",
        "packages/go/ledger/data/default-source-cache.json",
    ):
        assert_true(not (ROOT / relative).exists(), f"bundled catalog still exists: {relative}")


def main() -> int:
    check_python()
    subprocess.run(["node", "scripts/check_external_price_resolution.mjs"], cwd=ROOT, check=True)
    print("External price resolution checks passed for Python and JavaScript/browser.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"External price resolution check failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
