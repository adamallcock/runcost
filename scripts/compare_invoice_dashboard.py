#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any


def decimal_text(value: Any) -> str:
    if value is None:
        return ""
    return format(Decimal(str(value)).normalize(), "f")


def get_path(data: dict[str, Any], path: str | None) -> Any:
    if not path:
        return None
    current: Any = data
    for part in path.removeprefix("$.").split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def component_quantity(ledger: dict[str, Any], names: list[str]) -> Decimal:
    total = Decimal("0")
    for component in ledger.get("components", []):
        if component.get("name") in names:
            total += Decimal(str(component.get("quantity", "0")))
    return total


def runcost_value(data: dict[str, Any], mapping: dict[str, Any]) -> Any:
    if "runcost_value" in mapping:
        return mapping["runcost_value"]
    if "runcost_path" in mapping:
        return get_path(data, mapping["runcost_path"])
    components = mapping.get("components")
    if components:
        return str(component_quantity(data["runcost"]["cost_ledger"], components))
    return None


def classify(provider_value: Any, runcost: Any, mapping: dict[str, Any]) -> str:
    rule = mapping["status_rule"]
    if rule == "unsupported":
        return "unsupported"
    if rule == "estimated":
        tolerance = Decimal(str(mapping.get("tolerance", "0")))
        difference = abs(Decimal(str(provider_value)) - Decimal(str(runcost)))
        return "estimated" if difference <= tolerance else "unsupported"
    return "exact" if Decimal(str(provider_value)) == Decimal(str(runcost)) else "estimated"


def product_truth_action(status: str, mapping: dict[str, Any]) -> dict[str, str]:
    if status == "exact":
        return {"type": "none", "reason": "Provider sample and RunCost value match for this field."}
    if status == "estimated":
        return {
            "type": "documented_limitation",
            "reason": mapping.get("notes", "Provider and RunCost values are comparable but not invoice-exact."),
        }
    return {
        "type": "documented_limitation",
        "reason": mapping.get("notes", "Provider value is not currently modeled by RunCost."),
    }


def build_comparison(data: dict[str, Any]) -> dict[str, Any]:
    rows = []
    summary = {"exact": 0, "estimated": 0, "unsupported": 0}
    for mapping in data["field_mappings"]:
        provider_value = get_path(data, mapping["provider_path"])
        run_value = runcost_value(data, mapping)
        status = classify(provider_value, run_value, mapping)
        summary[status] += 1
        rows.append(
            {
                "field": mapping["field"],
                "provider_value": decimal_text(provider_value),
                "runcost_value": decimal_text(run_value),
                "status": status,
                "notes": mapping.get("notes", ""),
                "product_truth_action": product_truth_action(status, mapping),
            }
        )
    return {
        "schema_version": "0.1",
        "comparison_id": data["comparison_id"],
        "safe_to_commit": data["safe_to_commit"],
        "contains_private_billing_export": data["contains_private_billing_export"],
        "provider": data["provider"]["name"],
        "surface": data["provider"]["surface"],
        "model": data["provider"]["model"],
        "provider_source": data["provider"]["source"],
        "provider_window": data["provider"]["window"],
        "runcost_source": data["runcost"]["source"],
        "summary": summary,
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare a sanitized provider dashboard/invoice sample with a RunCost ledger.")
    parser.add_argument("--input", required=True, help="Sanitized comparison input JSON.")
    parser.add_argument("--output", required=True, help="Path to write comparison JSON.")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    comparison = build_comparison(data)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote invoice/dashboard comparison to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
