#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SMOKE_COMMAND = ROOT / "scripts" / "run_alpha_smoke.py"
PRODUCT_TRUTH_REGISTER = ROOT / "fixtures" / "source-files" / "alpha-smoke-product-truth-register.json"

sys.path.insert(0, str(ROOT / "scripts"))
from check_alpha_product_truth import validate_register, walk_sanitized  # noqa: E402
from check_alpha_smoke_contract import validate_report as validate_alpha_smoke_contract  # noqa: E402
from check_invoice_comparison import generated_sample_comparison, validate_comparison  # noqa: E402

REQUIRED_SCENARIOS = {
    "openai_responses",
    "anthropic_prompt_caching",
    "vercel_ai_sdk_stream_text",
    "langchain_agent_run",
    "openrouter_cost_compare",
    "multi_provider_discount",
}
LIVE_SOURCE_REQUIRED = REQUIRED_SCENARIOS - {"multi_provider_discount"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def generate_sample_smoke_report() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / "alpha-smoke-sample.json"
        subprocess.run(
            [
                sys.executable,
                str(SMOKE_COMMAND),
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
        return load_json(output)


def smoke_items(report: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    validate_alpha_smoke_contract(report)
    if report.get("schema_version") != "0.1":
        raise AssertionError("alpha smoke report must use schema_version 0.1")
    if report.get("sanitized") is not True or report.get("safe_to_attach_to_issue") is not True:
        raise AssertionError("alpha smoke report must be sanitized and safe to attach")
    if report.get("mode") not in {"sample", "live"}:
        raise AssertionError("alpha smoke report mode must be sample or live")
    if report.get("sample_prices") is not True:
        raise AssertionError("alpha smoke reports must acknowledge sample price cards")
    walk_sanitized(report)

    if isinstance(report.get("scenarios"), list):
        return [(str(report.get("mode")), item) for item in report["scenarios"]]
    if isinstance(report.get("scenario"), str):
        return [(str(report.get("mode")), report)]
    raise AssertionError("alpha smoke report must contain scenarios or scenario")


def validate_product_truth(items: list[tuple[str, dict[str, Any]]]) -> None:
    register = load_json(PRODUCT_TRUTH_REGISTER)
    registered = validate_register(register)
    for _mode, item in items:
        scenario = item.get("scenario")
        status = item.get("status")
        if status == "passed":
            continue
        entry = registered.get((scenario, status))
        if entry is None:
            raise AssertionError(f"missing product-truth register entry for {scenario}/{status}")
        next_action_type = (item.get("next_action") or {}).get("type")
        if next_action_type != entry.get("next_action_type"):
            raise AssertionError(
                f"{scenario}/{status} next_action type drifted: "
                f"{next_action_type!r} != {entry.get('next_action_type')!r}"
            )
        if entry.get("classification") == "none":
            raise AssertionError(f"{scenario}/{status} must resolve to product truth")


def validate_scenario_coverage(items: list[tuple[str, dict[str, Any]]], *, require_real: bool) -> None:
    by_scenario: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for mode, item in items:
        scenario = item.get("scenario")
        if isinstance(scenario, str) and scenario:
            by_scenario.setdefault(scenario, []).append((mode, item))

    missing = sorted(REQUIRED_SCENARIOS - set(by_scenario))
    if missing:
        raise AssertionError(f"alpha evidence bundle missing scenario(s): {', '.join(missing)}")

    if not require_real:
        return

    for scenario in sorted(REQUIRED_SCENARIOS):
        passed = [entry for entry in by_scenario[scenario] if entry[1].get("status") == "passed"]
        if not passed:
            raise AssertionError(f"{scenario} must have a passing smoke result")
        if scenario in LIVE_SOURCE_REQUIRED:
            has_live_pass = any(
                mode == "live" and (item.get("evidence") or {}).get("source") == "live"
                for mode, item in passed
            )
            if not has_live_pass:
                raise AssertionError(f"{scenario} must have a passing live-source smoke result")
            continue
        has_live_review = any(mode == "live" for mode, _item in passed)
        if not has_live_review:
            raise AssertionError(f"{scenario} must be present in the same live review set")


def validate_bundle(
    smoke_reports: list[dict[str, Any]],
    invoice_comparison: dict[str, Any],
    *,
    require_real: bool,
) -> None:
    if not smoke_reports:
        raise AssertionError("alpha evidence bundle must include at least one smoke report")
    items: list[tuple[str, dict[str, Any]]] = []
    for report in smoke_reports:
        items.extend(smoke_items(report))
    validate_scenario_coverage(items, require_real=require_real)
    validate_product_truth(items)
    validate_comparison(invoice_comparison, require_real=require_real)


def self_check_real_rejection() -> None:
    sample_report = generate_sample_smoke_report()
    sample_comparison = generated_sample_comparison()
    validate_bundle([sample_report], sample_comparison, require_real=False)
    missing_ack = json.loads(json.dumps(sample_report))
    missing_ack.pop("sample_prices", None)
    try:
        validate_bundle([missing_ack], sample_comparison, require_real=False)
    except AssertionError as exc:
        if "sample price" not in str(exc):
            raise
    else:
        raise AssertionError("alpha evidence bundle must reject smoke reports without sample price acknowledgement")
    try:
        validate_bundle([sample_report], sample_comparison, require_real=True)
    except AssertionError as exc:
        if "live-source" not in str(exc) and "real Milestone 8" not in str(exc):
            raise
    else:
        raise AssertionError("sample alpha evidence bundle must not satisfy --require-real")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a complete RunCost alpha evidence bundle.")
    parser.add_argument(
        "--smoke-report",
        action="append",
        default=[],
        help="Sanitized alpha smoke JSON. Repeat for aggregate, Vercel, and LangChain reports.",
    )
    parser.add_argument("--invoice-comparison", help="Sanitized invoice/dashboard comparison JSON.")
    parser.add_argument("--require-real", action="store_true", help="Require live smoke evidence and real provider export comparison.")
    args = parser.parse_args()

    self_check_real_rejection()
    smoke_reports = [load_json(Path(path)) for path in args.smoke_report] if args.smoke_report else [generate_sample_smoke_report()]
    invoice_comparison = load_json(Path(args.invoice_comparison)) if args.invoice_comparison else generated_sample_comparison()
    validate_bundle(smoke_reports, invoice_comparison, require_real=args.require_real)
    if args.require_real:
        print("Real alpha evidence bundle checks passed.")
    else:
        print("Alpha evidence bundle checks passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"Alpha evidence bundle check failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
