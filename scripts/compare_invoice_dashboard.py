#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INPUT_SCHEMA = ROOT / "schemas" / "invoice-dashboard-comparison-input.schema.json"
ALLOWED_EVIDENCE_TYPES = {"sanitized_sample", "real_provider_export"}
ALLOWED_STATUS_RULES = {"exact", "estimated", "unsupported"}
FORBIDDEN_KEYS = {
    "account_id",
    "api_key",
    "authorization",
    "billing_address",
    "content",
    "customer_id",
    "email",
    "headers",
    "input",
    "invoice_id",
    "messages",
    "organization_id",
    "output",
    "payment_method",
    "project_id",
    "prompt",
    "raw_export",
    "raw_invoice",
    "raw_provider_response",
    "request_body",
    "secret",
    "tax_id",
}
SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{8,}\b", re.IGNORECASE),
]


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


def walk_sanitized_input(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = key.lower().replace("-", "_")
            if normalized in FORBIDDEN_KEYS:
                raise AssertionError(f"forbidden invoice comparison input key {path}.{key}")
            walk_sanitized_input(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_sanitized_input(child, f"{path}[{index}]")
    elif isinstance(value, str):
        for pattern in SECRET_PATTERNS:
            if pattern.search(value):
                raise AssertionError(f"secret-like value found in invoice comparison input at {path}")


def validate_input_safety(data: dict[str, Any]) -> None:
    if not INPUT_SCHEMA.exists():
        raise AssertionError("missing invoice/dashboard comparison input schema")
    evidence_type = data.get("evidence_type")
    if evidence_type not in ALLOWED_EVIDENCE_TYPES:
        raise AssertionError("invoice comparison input must declare sanitized_sample or real_provider_export evidence_type")
    if data.get("safe_to_commit") is not True:
        raise AssertionError("invoice comparison input must be marked safe_to_commit before comparison output is written")
    if data.get("contains_private_billing_export") is not False:
        raise AssertionError("invoice comparison input must not contain private billing export data")
    walk_sanitized_input(data)


def validate_input_contract(data: dict[str, Any]) -> None:
    if data.get("schema_version") != "0.1":
        raise AssertionError("invoice comparison input must use schema_version 0.1")
    for key in ["comparison_id", "description"]:
        if not isinstance(data.get(key), str) or not data[key]:
            raise AssertionError(f"invoice comparison input must include {key}")

    provider = data.get("provider")
    if not isinstance(provider, dict):
        raise AssertionError("invoice comparison input must include provider object")
    for key in ["name", "surface", "model", "source", "window"]:
        if not isinstance(provider.get(key), str) or not provider[key]:
            raise AssertionError(f"invoice comparison input provider.{key} is required")
    values = provider.get("values")
    if not isinstance(values, dict) or not values:
        raise AssertionError("invoice comparison input provider.values must be a non-empty object")

    runcost = data.get("runcost")
    if not isinstance(runcost, dict):
        raise AssertionError("invoice comparison input must include runcost object")
    if not isinstance(runcost.get("source"), str) or not runcost["source"]:
        raise AssertionError("invoice comparison input runcost.source is required")
    if not isinstance(runcost.get("cost_ledger"), dict):
        raise AssertionError("invoice comparison input runcost.cost_ledger is required")

    mappings = data.get("field_mappings")
    if not isinstance(mappings, list) or not mappings:
        raise AssertionError("invoice comparison input field_mappings must be a non-empty array")
    for index, mapping in enumerate(mappings):
        if not isinstance(mapping, dict):
            raise AssertionError(f"field_mappings[{index}] must be an object")
        path = f"field_mappings[{index}]"
        if not isinstance(mapping.get("field"), str) or not mapping["field"]:
            raise AssertionError(f"{path}.field is required")
        provider_path = mapping.get("provider_path")
        if not isinstance(provider_path, str) or not provider_path.startswith("$.provider.values."):
            raise AssertionError(f"{path}.provider_path must point under $.provider.values")
        if get_path(data, provider_path) is None:
            raise AssertionError(f"{path}.provider_path does not resolve: {provider_path}")
        rule = mapping.get("status_rule")
        if rule not in ALLOWED_STATUS_RULES:
            raise AssertionError(f"{path}.status_rule is invalid")
        has_runcost_value = any(key in mapping for key in ["runcost_value", "runcost_path", "components"])
        if rule in {"exact", "estimated"} and not has_runcost_value:
            raise AssertionError(f"{path} must name a RunCost value, path, or component set")
        if "runcost_path" in mapping and get_path(data, mapping["runcost_path"]) is None:
            raise AssertionError(f"{path}.runcost_path does not resolve: {mapping['runcost_path']}")
        if "components" in mapping:
            components = mapping["components"]
            if not isinstance(components, list) or not components or not all(isinstance(item, str) and item for item in components):
                raise AssertionError(f"{path}.components must be a non-empty string array")
        if "tolerance" in mapping:
            Decimal(str(mapping["tolerance"]))
        if not isinstance(mapping.get("notes"), str):
            raise AssertionError(f"{path}.notes must be a string")


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
    evidence_type = data.get("evidence_type", "unspecified")
    is_real_evidence = evidence_type == "real_provider_export" and data["contains_private_billing_export"] is False
    return {
        "schema_version": "0.1",
        "comparison_id": data["comparison_id"],
        "evidence_type": evidence_type,
        "milestone8_real_evidence": is_real_evidence,
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
    validate_input_safety(data)
    validate_input_contract(data)
    comparison = build_comparison(data)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote invoice/dashboard comparison to {output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"Invoice/dashboard comparison failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
