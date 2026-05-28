#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "invoice-dashboard-comparison.schema.json"
INPUT_SCHEMA = ROOT / "schemas" / "invoice-dashboard-comparison-input.schema.json"
COMMAND = ROOT / "scripts" / "compare_invoice_dashboard.py"
SAMPLE = ROOT / "fixtures" / "source-files" / "invoice-dashboard-comparison-sample.json"

from compare_invoice_dashboard import validate_input_contract, validate_input_safety  # noqa: E402

ALLOWED_EVIDENCE_TYPES = {"sanitized_sample", "real_provider_export"}
ALLOWED_ROW_STATUSES = {"exact", "estimated", "unsupported"}
ALLOWED_ACTION_TYPES = {
    "none",
    "documented_limitation",
    "fixture",
    "structured_warning",
    "extractor_or_source_fix",
    "price_source_update",
}
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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def walk_sanitized(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = key.lower().replace("-", "_")
            assert_true(normalized not in FORBIDDEN_KEYS, f"forbidden invoice comparison key {path}.{key}")
            walk_sanitized(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_sanitized(child, f"{path}[{index}]")
    elif isinstance(value, str):
        for pattern in SECRET_PATTERNS:
            assert_true(not pattern.search(value), f"secret-like value found in invoice comparison at {path}")


def validate_comparison_contract(comparison: dict[str, Any]) -> None:
    assert_true(comparison.get("schema_version") == "0.1", "invoice comparison must use schema_version 0.1")
    assert_true(isinstance(comparison.get("comparison_id"), str) and comparison["comparison_id"], "comparison_id required")
    assert_true(comparison.get("evidence_type") in ALLOWED_EVIDENCE_TYPES, "invalid evidence_type")
    assert_true(comparison.get("safe_to_commit") is True, "invoice comparison must be safe_to_commit")
    assert_true(comparison.get("contains_private_billing_export") is False, "invoice comparison must not contain private billing export")
    expected_real = comparison["evidence_type"] == "real_provider_export"
    assert_true(
        comparison.get("milestone8_real_evidence") is expected_real,
        "milestone8_real_evidence must match evidence_type",
    )
    for key in ["provider", "surface", "model", "provider_source", "provider_window", "runcost_source"]:
        assert_true(isinstance(comparison.get(key), str) and comparison[key], f"{key} required")
    walk_sanitized(comparison)

    summary = comparison.get("summary")
    assert_true(isinstance(summary, dict), "summary must be an object")
    assert_true(set(summary) == {"exact", "estimated", "unsupported"}, "summary keys must be exact/estimated/unsupported")
    rows = comparison.get("rows")
    assert_true(isinstance(rows, list) and rows, "rows must be a non-empty array")
    counts = {"exact": 0, "estimated": 0, "unsupported": 0}
    for index, row in enumerate(rows):
        path = f"$.rows[{index}]"
        assert_true(isinstance(row, dict), f"{path} must be an object")
        assert_true(isinstance(row.get("field"), str) and row["field"], f"{path}.field required")
        assert_true(isinstance(row.get("provider_value"), str), f"{path}.provider_value must be a string")
        assert_true(isinstance(row.get("runcost_value"), str), f"{path}.runcost_value must be a string")
        status = row.get("status")
        assert_true(status in ALLOWED_ROW_STATUSES, f"{path}.status invalid")
        counts[status] += 1
        assert_true(isinstance(row.get("notes"), str), f"{path}.notes must be a string")
        action = row.get("product_truth_action")
        assert_true(isinstance(action, dict), f"{path}.product_truth_action must be an object")
        action_type = action.get("type")
        assert_true(action_type in ALLOWED_ACTION_TYPES, f"{path}.product_truth_action.type invalid")
        assert_true(isinstance(action.get("reason"), str) and action["reason"], f"{path}.product_truth_action.reason required")
        if status in {"estimated", "unsupported"}:
            assert_true(action_type != "none", f"{path} discrepancy must have a product-truth action")
    assert_true(summary == counts, "summary counts must match row statuses")


def validate_schema_contracts() -> None:
    assert_true(SCHEMA.exists(), "missing invoice/dashboard comparison schema")
    assert_true(INPUT_SCHEMA.exists(), "missing invoice/dashboard comparison input schema")
    output_schema = load_json(SCHEMA)
    input_schema = load_json(INPUT_SCHEMA)
    assert_true(output_schema.get("title") == "RunCost Invoice Dashboard Comparison", "unexpected comparison schema title")
    assert_true(
        input_schema.get("title") == "RunCost Invoice Dashboard Comparison Input",
        "unexpected comparison input schema title",
    )
    input_defs = input_schema.get("$defs")
    assert_true(isinstance(input_defs, dict), "comparison input schema missing $defs")
    mapping = input_defs.get("fieldMapping", {})
    assert_true(
        set(mapping.get("properties", {}).get("status_rule", {}).get("enum", [])) == {"exact", "estimated", "unsupported"},
        "comparison input status_rule enum drifted",
    )


def validate_input_contract_sample() -> None:
    sample = load_json(SAMPLE)
    validate_input_safety(sample)
    validate_input_contract(sample)

    bad_missing_value = json.loads(json.dumps(sample))
    bad_missing_value["field_mappings"][0].pop("runcost_value")
    try:
        validate_input_contract(bad_missing_value)
    except AssertionError as exc:
        assert_true("RunCost value" in str(exc), "input contract should require comparable RunCost values")
    else:
        raise AssertionError("comparison input contract must reject exact mappings without a RunCost value")

    bad_provider_path = json.loads(json.dumps(sample))
    bad_provider_path["field_mappings"][0]["provider_path"] = "$.provider.values.missing_field"
    try:
        validate_input_contract(bad_provider_path)
    except AssertionError as exc:
        assert_true("does not resolve" in str(exc), "input contract should reject unresolved provider paths")
    else:
        raise AssertionError("comparison input contract must reject unresolved provider paths")


def generate_sample_comparison() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / "invoice-comparison.json"
        subprocess.run(
            [sys.executable, str(COMMAND), "--input", str(SAMPLE), "--output", str(output)],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return load_json(output)


def self_check_rejections() -> None:
    sample = generate_sample_comparison()
    bad_secret = json.loads(json.dumps(sample))
    bad_secret["rows"][0]["notes"] = "leaked sk-test-secret"
    try:
        validate_comparison_contract(bad_secret)
    except AssertionError as exc:
        assert_true("secret-like" in str(exc), "secret self-check should fail for secret-like value")
    else:
        raise AssertionError("invoice comparison contract must reject secret-like values")

    bad_action = json.loads(json.dumps(sample))
    for row in bad_action["rows"]:
        if row["status"] == "estimated":
            row["product_truth_action"] = {"type": "none", "reason": "missing action"}
            break
    try:
        validate_comparison_contract(bad_action)
    except AssertionError as exc:
        assert_true("product-truth action" in str(exc), "action self-check should fail for discrepancy without action")
    else:
        raise AssertionError("invoice comparison contract must reject discrepancies without product-truth actions")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate sanitized invoice/dashboard comparison contract.")
    parser.add_argument("--comparison", action="append", default=[], help="Comparison JSON to validate.")
    args = parser.parse_args()

    validate_schema_contracts()
    validate_input_contract_sample()
    self_check_rejections()
    comparisons = [load_json(Path(path)) for path in args.comparison] if args.comparison else [generate_sample_comparison()]
    for comparison in comparisons:
        validate_comparison_contract(comparison)
    print("Invoice/dashboard comparison contract checks passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"Invoice/dashboard comparison contract check failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
