#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "python"))

from runcost import from_langsmith_run, from_openai_agents_usage  # noqa: E402


def token_price_card(surface: str) -> dict[str, object]:
    return {
        "schema_version": "0.1",
        "id": f"openai:gpt-framework-example:{surface}",
        "provider": "openai",
        "surface": surface,
        "model": "gpt-framework-example",
        "components": [
            {
                "usage_component": "input_uncached_tokens",
                "unit": "token",
                "price": {"amount": "1", "currency": "USD", "per": "1000000"},
            },
            {
                "usage_component": "input_cache_read_tokens",
                "unit": "token",
                "price": {"amount": "0.1", "currency": "USD", "per": "1000000"},
            },
            {
                "usage_component": "input_cache_write_tokens",
                "unit": "token",
                "price": {"amount": "1.25", "currency": "USD", "per": "1000000"},
            },
            {
                "usage_component": "output_text_tokens",
                "unit": "token",
                "price": {"amount": "2", "currency": "USD", "per": "1000000"},
            },
            {
                "usage_component": "output_reasoning_tokens",
                "unit": "token",
                "price": {"amount": "2", "currency": "USD", "per": "1000000"},
            },
        ],
        "source": {"name": "framework-example", "retrieved_at": "2026-05-27T00:00:00Z"},
    }


agents_usage = {
    "usage": {
        "model": "gpt-framework-example",
        "input_tokens": 640,
        "input_tokens_details": {"cached_tokens": 120},
        "output_tokens": 90,
        "output_tokens_details": {"reasoning_tokens": 20},
    },
    "request_usage_entries": [
        {"input_tokens": 300, "output_tokens": 40},
        {"input_tokens": 340, "output_tokens": 50},
    ],
}

agents_ledger = from_openai_agents_usage(
    agents_usage,
    provider="openai",
    surface="framework.openai_agents",
    model="gpt-framework-example",
    price_cards=[token_price_card("framework.openai_agents")],
)

langsmith_run = {
    "usage_metadata": {
        "model": "gpt-framework-example",
        "input_tokens": 500,
        "input_token_details": {"cache_read": 50, "cache_creation": 25},
        "output_tokens": 120,
        "output_token_details": {"reasoning": 30},
    },
    "total_cost": 0.0007125,
}

langsmith_ledger = from_langsmith_run(
    langsmith_run,
    provider="openai",
    surface="framework.langsmith.run_usage",
    model="gpt-framework-example",
    price_cards=[token_price_card("framework.langsmith.run_usage")],
    provider_reported_cost=langsmith_run["total_cost"],
)

print(
    json.dumps(
        {
            "openai_agents_total": agents_ledger["total"],
            "langsmith_total": langsmith_ledger["total"],
            "langsmith_warnings": [warning["code"] for warning in langsmith_ledger["warnings"]],
        },
        indent=2,
    )
)
