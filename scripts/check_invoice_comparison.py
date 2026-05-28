#!/usr/bin/env python3
from __future__ import annotations

import json
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from check_invoice_comparison_contract import validate_comparison_contract

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / "scripts" / "compare_invoice_dashboard.py"
OPENAI_COSTS_CONVERTER = ROOT / "scripts" / "create_openai_costs_comparison_input.py"
OPENAI_COSTS_RUNNER = ROOT / "scripts" / "run_openai_costs_invoice_comparison.py"
SAMPLE = ROOT / "fixtures" / "source-files" / "invoice-dashboard-comparison-sample.json"
OPENAI_COSTS_SAMPLE = ROOT / "fixtures" / "source-files" / "openai-costs-comparison-source.json"
REPORT = ROOT / "docs" / "internal" / "reports" / "2026-05-26-invoice-dashboard-comparison-sample.md"

EXPECTED_FIELDS = {
    "request_count",
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_tokens",
    "tool_search_units",
    "provider_reported_cost",
    "runcost_total",
    "discounts_credits_taxes",
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
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{12,}\b", re.IGNORECASE),
]


def generated_sample_comparison() -> dict[str, object]:
    assert COMMAND.exists(), "missing invoice/dashboard comparison command"
    assert SAMPLE.exists(), "missing sanitized invoice/dashboard comparison sample"
    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / "comparison.json"
        subprocess.run(
            [
                sys.executable,
                str(COMMAND),
                "--input",
                str(SAMPLE),
                "--output",
                str(output),
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return json.loads(output.read_text(encoding="utf-8"))


def generated_openai_costs_sample_comparison() -> dict[str, object]:
    assert OPENAI_COSTS_CONVERTER.exists(), "missing OpenAI Costs API comparison-input converter"
    assert OPENAI_COSTS_SAMPLE.exists(), "missing sanitized OpenAI Costs API comparison sample"
    with tempfile.TemporaryDirectory() as temp_dir:
        comparison_input = Path(temp_dir) / "comparison-input.json"
        comparison_output = Path(temp_dir) / "comparison-output.json"
        subprocess.run(
            [
                sys.executable,
                str(OPENAI_COSTS_CONVERTER),
                "--input",
                str(OPENAI_COSTS_SAMPLE),
                "--output",
                str(comparison_input),
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        subprocess.run(
            [
                sys.executable,
                str(COMMAND),
                "--input",
                str(comparison_input),
                "--output",
                str(comparison_output),
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return json.loads(comparison_output.read_text(encoding="utf-8"))


def walk_sanitized(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = key.lower().replace("-", "_")
            if normalized in FORBIDDEN_KEYS:
                raise AssertionError(f"forbidden invoice comparison key {path}.{key}")
            walk_sanitized(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_sanitized(child, f"{path}[{index}]")
    elif isinstance(value, str):
        for pattern in SECRET_PATTERNS:
            if pattern.search(value):
                raise AssertionError(f"secret-like value found in invoice comparison at {path}")


def validate_rows(comparison: dict[str, object]) -> None:
    rows = comparison.get("rows")
    assert isinstance(rows, list) and rows, "comparison must include rows"
    summary = comparison.get("summary")
    assert isinstance(summary, dict), "comparison must include summary"
    counts = {"exact": 0, "estimated": 0, "unsupported": 0}
    for row in rows:
        assert isinstance(row, dict), "comparison row must be an object"
        status = row.get("status")
        assert status in counts, f"invalid comparison row status: {status!r}"
        counts[status] += 1
        assert isinstance(row.get("field"), str) and row["field"], "comparison row must include field"
        assert "provider_value" in row, f"{row['field']} missing provider_value"
        assert "runcost_value" in row, f"{row['field']} missing runcost_value"
        action = row.get("product_truth_action")
        assert isinstance(action, dict), f"{row['field']} missing product_truth_action"
        action_type = action.get("type")
        assert action_type in {
            "none",
            "documented_limitation",
            "fixture",
            "structured_warning",
            "extractor_or_source_fix",
            "price_source_update",
        }, f"{row['field']} has invalid product_truth_action type {action_type!r}"
        if status in {"estimated", "unsupported"}:
            assert action_type != "none", f"{row['field']} discrepancy must have a product-truth action"
            assert isinstance(action.get("reason"), str) and action["reason"], f"{row['field']} action must include reason"
    assert summary.get("exact") == counts["exact"], "exact summary count must match rows"
    assert summary.get("estimated") == counts["estimated"], "estimated summary count must match rows"
    assert summary.get("unsupported") == counts["unsupported"], "unsupported summary count must match rows"


def validate_common(comparison: dict[str, object]) -> None:
    validate_comparison_contract(comparison)
    walk_sanitized(comparison)
    assert comparison["schema_version"] == "0.1"
    assert isinstance(comparison.get("comparison_id"), str) and comparison["comparison_id"]
    assert comparison["safe_to_commit"] is True
    assert comparison["contains_private_billing_export"] is False
    assert isinstance(comparison.get("provider"), str) and comparison["provider"]
    assert isinstance(comparison.get("surface"), str) and comparison["surface"]
    assert isinstance(comparison.get("model"), str) and comparison["model"]
    validate_rows(comparison)


def validate_comparison(comparison: dict[str, object], *, require_real: bool) -> None:
    validate_common(comparison)
    if require_real:
        assert comparison["milestone8_real_evidence"] is True, "comparison is not real Milestone 8 dashboard/invoice evidence"
        assert comparison["evidence_type"] == "real_provider_export"
        assert comparison["summary"]["exact"] >= 1, "real comparison must classify at least one exact field"
        return

    assert comparison["comparison_id"] == "openai-alpha-smoke-sample-2026-05-26"
    assert comparison["evidence_type"] == "sanitized_sample"
    assert comparison["milestone8_real_evidence"] is False
    assert comparison["summary"]["exact"] >= 6
    assert comparison["summary"]["estimated"] >= 1
    assert comparison["summary"]["unsupported"] >= 1

    fields = {row["field"] for row in comparison["rows"]}
    assert fields == EXPECTED_FIELDS


def self_check_real_validation() -> None:
    valid_real = {
        "schema_version": "0.1",
        "comparison_id": "synthetic-real-comparison",
        "evidence_type": "real_provider_export",
        "milestone8_real_evidence": True,
        "safe_to_commit": True,
        "contains_private_billing_export": False,
        "provider": "provider",
        "surface": "surface",
        "model": "model",
        "provider_source": "sanitized real export",
        "provider_window": "2026-05-26T00:00:00Z/2026-05-26T00:05:00Z",
        "runcost_source": "sanitized smoke report",
        "summary": {"exact": 1, "estimated": 1, "unsupported": 0},
        "rows": [
            {
                "field": "input_tokens",
                "provider_value": "100",
                "runcost_value": "100",
                "status": "exact",
                "notes": "",
                "product_truth_action": {"type": "none", "reason": "matched"},
            },
            {
                "field": "runcost_total",
                "provider_value": "0.01",
                "runcost_value": "0.009",
                "status": "estimated",
                "notes": "provider rounding differs",
                "product_truth_action": {"type": "documented_limitation", "reason": "provider rounding differs"},
            },
        ],
    }
    validate_comparison(valid_real, require_real=True)

    invalid_real = json.loads(json.dumps(valid_real))
    invalid_real["rows"][1]["product_truth_action"] = {"type": "none", "reason": "missing action"}
    try:
        validate_comparison(invalid_real, require_real=True)
    except AssertionError as exc:
        if "product-truth action" not in str(exc):
            raise
    else:
        raise AssertionError("real comparison validation must reject discrepancies without product-truth actions")


def self_check_input_safety() -> None:
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))

    unsafe_private = json.loads(json.dumps(sample))
    unsafe_private["safe_to_commit"] = False
    unsafe_private["contains_private_billing_export"] = True

    unsafe_secret = json.loads(json.dumps(sample))
    unsafe_secret["provider"]["values"]["provider_reported_cost"] = "sk-test-secret"

    for unsafe in [unsafe_private, unsafe_secret]:
        with tempfile.TemporaryDirectory() as temp_dir:
            unsafe_input = Path(temp_dir) / "unsafe-input.json"
            unsafe_output = Path(temp_dir) / "unsafe-output.json"
            unsafe_input.write_text(json.dumps(unsafe), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(COMMAND),
                    "--input",
                    str(unsafe_input),
                    "--output",
                    str(unsafe_output),
                ],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            assert result.returncode != 0, "invoice comparison command must reject unsafe inputs"
            assert not unsafe_output.exists(), "invoice comparison command must not write output for unsafe inputs"


def self_check_openai_costs_converter() -> None:
    comparison = generated_openai_costs_sample_comparison()
    validate_common(comparison)
    assert comparison["comparison_id"] == "openai-costs-api-sample-2026-05-26"
    assert comparison["provider"] == "openai"
    assert comparison["surface"] == "openai.organization.costs"
    assert comparison["evidence_type"] == "sanitized_sample"
    assert comparison["milestone8_real_evidence"] is False
    fields = {row["field"] for row in comparison["rows"]}
    assert fields == {"line_item_count", "provider_reported_cost", "runcost_total"}
    assert comparison["summary"]["exact"] >= 2
    assert comparison["summary"]["estimated"] >= 1


def self_check_openai_costs_runner() -> None:
    assert OPENAI_COSTS_RUNNER.exists(), "missing OpenAI Costs API invoice comparison runner"
    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / "openai-costs-runner-comparison.json"
        subprocess.run(
            [
                sys.executable,
                str(OPENAI_COSTS_RUNNER),
                "--mode",
                "sample",
                "--output",
                str(output),
                "--allow-sample-prices",
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        comparison = json.loads(output.read_text(encoding="utf-8"))
    validate_common(comparison)
    assert comparison["comparison_id"] == "openai-costs-api-sample-2026-05-26"
    assert comparison["milestone8_real_evidence"] is False
    assert comparison["evidence_type"] == "sanitized_sample"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check invoice/dashboard comparison mechanics or a real comparison artifact.")
    parser.add_argument("--comparison", help="Existing comparison JSON to validate instead of generating the checked-in sample.")
    parser.add_argument("--require-real", action="store_true", help="Require the comparison to be real sanitized provider evidence.")
    args = parser.parse_args()

    assert REPORT.exists(), "missing dated invoice/dashboard comparison report"
    self_check_real_validation()
    self_check_input_safety()
    self_check_openai_costs_converter()
    self_check_openai_costs_runner()
    if args.comparison:
        comparison = json.loads(Path(args.comparison).read_text(encoding="utf-8"))
    else:
        comparison = generated_sample_comparison()
    validate_comparison(comparison, require_real=args.require_real)
    if args.require_real:
        print("Real invoice/dashboard comparison checks passed.")
        return 0

    report_text = REPORT.read_text(encoding="utf-8")
    assert "openai-alpha-smoke-sample-2026-05-26" in report_text
    assert "| Field | Provider value | RunCost value | Status | Notes |" in report_text
    assert "`estimated`" in report_text
    assert "`unsupported`" in report_text
    assert "Product-truth actions" in report_text

    print("Invoice/dashboard comparison checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
