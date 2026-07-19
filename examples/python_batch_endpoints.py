#!/usr/bin/env python3
"""Normalize seven provider batch result formats with one RunCost call."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "python"))

from runcost import from_batch_results  # noqa: E402

fixture = json.loads((ROOT / "fixtures" / "expansion" / "cases.json").read_text())
batch_cases = [case for case in fixture["cases"] if case["operation"] == "from_batch_results"]
summaries = {}
for case in batch_cases:
    value = dict(case["input"])
    items = value.pop("items")
    reference = value.pop("price_cards_ref")
    ledger = from_batch_results(items, price_cards=fixture["price_card_sets"][reference], **value)
    summaries[case["id"]] = ledger["summary"]

print(json.dumps(summaries, sort_keys=True))
