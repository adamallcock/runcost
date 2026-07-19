#!/usr/bin/env python3
"""Adapt the genai-prices/Pydantic AI catalog shape and enrich an OTel span."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "python"))

from runcost import from_otel_genai_span, otel_cost_attributes, price_cards_from_genai_prices  # noqa: E402

catalog = {"providers": [{"id": "openai", "models": [{"id": "otel-example", "prices": [{"constraint": {}, "prices": {"input_mtok": "1", "cache_read_mtok": "0.1", "output_mtok": "2"}}]}]}]}
cards = price_cards_from_genai_prices(catalog, retrieved_at="2026-07-18T00:00:00Z", version="example")
span = {"trace_id": "trace_example", "attributes": {"gen_ai.provider.name": "openai", "gen_ai.operation.name": "chat", "gen_ai.request.model": "otel-example", "gen_ai.usage.input_tokens": 100, "gen_ai.usage.cache_read.input_tokens": 20, "gen_ai.usage.output_tokens": 50}}
ledger = from_otel_genai_span(span, price_cards=cards, attribution={"project": "docs-example"})
print(json.dumps({"total": ledger["total"], "attributes": otel_cost_attributes(ledger)}, sort_keys=True))
