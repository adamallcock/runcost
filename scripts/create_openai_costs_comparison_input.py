#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

from compare_invoice_dashboard import validate_input_contract, validate_input_safety


def decimal_text(value: Any) -> str:
    return format(Decimal(str(value)).normalize(), "f")


def collect_costs(costs_page: dict[str, Any]) -> tuple[str, str, int]:
    total = Decimal("0")
    currencies: set[str] = set()
    line_items = 0
    for bucket in costs_page.get("data", []) if isinstance(costs_page.get("data"), list) else []:
        results = bucket.get("results", []) if isinstance(bucket, dict) else []
        for result in results if isinstance(results, list) else []:
            if not isinstance(result, dict):
                continue
            amount = result.get("amount")
            if not isinstance(amount, dict):
                raise AssertionError("OpenAI costs result must include amount object")
            total += Decimal(str(amount.get("value", "0")))
            currency = str(amount.get("currency", "")).upper()
            if not currency:
                raise AssertionError("OpenAI costs amount must include currency")
            currencies.add(currency)
            line_items += 1
    if not line_items:
        raise AssertionError("OpenAI costs page must include at least one result")
    if len(currencies) != 1:
        raise AssertionError("OpenAI costs comparison requires exactly one currency")
    return decimal_text(total), next(iter(currencies)), line_items


def validate_source(data: dict[str, Any]) -> None:
    if data.get("schema_version") != "0.1":
        raise AssertionError("OpenAI costs comparison source must use schema_version 0.1")
    for key in ["comparison_id", "description"]:
        if not isinstance(data.get(key), str) or not data[key]:
            raise AssertionError(f"OpenAI costs comparison source must include {key}")
    if data.get("evidence_type") not in {"sanitized_sample", "real_provider_export"}:
        raise AssertionError("OpenAI costs comparison source evidence_type is invalid")
    if data.get("safe_to_commit") is not True:
        raise AssertionError("OpenAI costs comparison source must be marked safe_to_commit")
    if data.get("contains_private_billing_export") is not False:
        raise AssertionError("OpenAI costs comparison source must not contain private billing export data")
    if not isinstance(data.get("provider"), dict):
        raise AssertionError("OpenAI costs comparison source must include provider object")
    if not isinstance(data.get("openai_costs"), dict):
        raise AssertionError("OpenAI costs comparison source must include openai_costs object")
    if not isinstance(data.get("runcost"), dict) or not isinstance(data["runcost"].get("cost_ledger"), dict):
        raise AssertionError("OpenAI costs comparison source must include runcost.cost_ledger object")

    probe = {
        "schema_version": "0.1",
        "comparison_id": data["comparison_id"],
        "description": data["description"],
        "evidence_type": data["evidence_type"],
        "safe_to_commit": data["safe_to_commit"],
        "contains_private_billing_export": data["contains_private_billing_export"],
        "provider": {
            "name": data["provider"].get("name", "openai"),
            "surface": data["provider"].get("surface", "openai.organization.costs"),
            "model": data["provider"].get("model", "multiple"),
            "source": data["provider"].get("source", "openai_costs_api"),
            "window": data["provider"].get("window", "unknown"),
            "values": {"probe": "1"},
        },
        "runcost": data["runcost"],
        "field_mappings": [
            {
                "field": "probe",
                "provider_path": "$.provider.values.probe",
                "runcost_value": "1",
                "status_rule": "exact",
                "notes": "Safety probe.",
            }
        ],
    }
    validate_input_safety(probe)


def build_comparison_input(data: dict[str, Any]) -> dict[str, Any]:
    provider_total, currency, line_item_count = collect_costs(data["openai_costs"])
    ledger = data["runcost"]["cost_ledger"]
    runcost_total = decimal_text(ledger.get("total", "0"))
    expected_line_item_count = str(data.get("expected_line_item_count", line_item_count))
    tolerance = str(data.get("cost_tolerance", "0"))
    provider = data["provider"]
    comparison_input = {
        "schema_version": "0.1",
        "comparison_id": data["comparison_id"],
        "description": data["description"],
        "evidence_type": data["evidence_type"],
        "safe_to_commit": data["safe_to_commit"],
        "contains_private_billing_export": data["contains_private_billing_export"],
        "provider": {
            "name": provider.get("name", "openai"),
            "surface": provider.get("surface", "openai.organization.costs"),
            "model": provider.get("model", ledger.get("model", {}).get("billed", "multiple")),
            "source": provider.get("source", "openai_costs_api"),
            "window": provider.get("window", "unknown"),
            "values": {
                "line_item_count": str(line_item_count),
                "provider_reported_cost": provider_total,
                "runcost_total": runcost_total,
                "currency": currency,
            },
        },
        "runcost": data["runcost"],
        "field_mappings": [
            {
                "field": "line_item_count",
                "provider_path": "$.provider.values.line_item_count",
                "runcost_value": expected_line_item_count,
                "status_rule": "exact",
                "notes": "Sanitized Costs API result count is retained for traceability without project identifiers.",
            },
            {
                "field": "provider_reported_cost",
                "provider_path": "$.provider.values.provider_reported_cost",
                "runcost_path": "$.runcost.cost_ledger.total",
                "status_rule": "estimated",
                "tolerance": tolerance,
                "notes": "OpenAI Costs API is invoice-oriented; RunCost totals are comparable but may differ because of provider reconciliation, credits, tax, rounding, or source-price timing.",
            },
            {
                "field": "runcost_total",
                "provider_path": "$.provider.values.runcost_total",
                "runcost_path": "$.runcost.cost_ledger.total",
                "status_rule": "exact",
                "notes": "Generated comparison input records the RunCost ledger total used for traceability.",
            },
        ],
    }
    validate_input_safety(comparison_input)
    validate_input_contract(comparison_input)
    return comparison_input


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a sanitized invoice comparison input from an OpenAI Costs API export.")
    parser.add_argument("--input", required=True, help="Sanitized OpenAI Costs API comparison source JSON.")
    parser.add_argument("--output", required=True, help="Path to write comparison input JSON.")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    validate_source(data)
    comparison_input = build_comparison_input(data)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(comparison_input, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote OpenAI Costs API comparison input to {output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"OpenAI Costs API comparison input failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
