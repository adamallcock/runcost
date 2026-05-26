#!/usr/bin/env python3
from __future__ import annotations

import json
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / "scripts" / "compare_invoice_dashboard.py"
SAMPLE = ROOT / "fixtures" / "source-files" / "invoice-dashboard-comparison-sample.json"
REPORT = ROOT / "docs" / "reports" / "2026-05-26-invoice-dashboard-comparison-sample.md"

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


def validate_comparison(comparison: dict[str, object], *, require_real: bool) -> None:
    if require_real:
        assert comparison["milestone8_real_evidence"] is True, "comparison is not real Milestone 8 dashboard/invoice evidence"
        assert comparison["evidence_type"] == "real_provider_export"
        assert comparison["contains_private_billing_export"] is False
        assert comparison["safe_to_commit"] is True
        return

    assert comparison["schema_version"] == "0.1"
    assert comparison["comparison_id"] == "openai-alpha-smoke-sample-2026-05-26"
    assert comparison["evidence_type"] == "sanitized_sample"
    assert comparison["milestone8_real_evidence"] is False
    assert comparison["safe_to_commit"] is True
    assert comparison["contains_private_billing_export"] is False
    assert comparison["summary"]["exact"] >= 6
    assert comparison["summary"]["estimated"] >= 1
    assert comparison["summary"]["unsupported"] >= 1

    fields = {row["field"] for row in comparison["rows"]}
    assert fields == EXPECTED_FIELDS
    for row in comparison["rows"]:
        assert row["status"] in {"exact", "estimated", "unsupported"}
        assert row["product_truth_action"]["type"] in {
            "none",
            "documented_limitation",
            "fixture",
            "structured_warning",
            "extractor_or_source_fix",
            "price_source_update",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check invoice/dashboard comparison mechanics or a real comparison artifact.")
    parser.add_argument("--comparison", help="Existing comparison JSON to validate instead of generating the checked-in sample.")
    parser.add_argument("--require-real", action="store_true", help="Require the comparison to be real sanitized provider evidence.")
    args = parser.parse_args()

    assert REPORT.exists(), "missing dated invoice/dashboard comparison report"
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
