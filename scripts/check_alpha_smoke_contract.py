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
SCHEMA = ROOT / "schemas" / "alpha-smoke-report.schema.json"
SMOKE_COMMAND = ROOT / "scripts" / "run_alpha_smoke.py"
PREFLIGHT_COMMAND = ROOT / "scripts" / "run_alpha_smoke_preflight.py"

FORBIDDEN_KEYS = {
    "api_key",
    "authorization",
    "headers",
    "prompt",
    "messages",
    "input",
    "output",
    "content",
    "raw_response",
    "request_body",
}
SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{8,}\b", re.IGNORECASE),
]
ALLOWED_MODES = {"sample", "live", "live_preflight"}
ALLOWED_STATUSES = {"passed", "skipped", "needs_product_truth", "failed", "ready", "not_ready"}
SMOKE_SUMMARY_KEYS = {"total", "passed", "skipped", "needs_product_truth", "failed"}
PREFLIGHT_SUMMARY_KEYS = {"ready_count", "not_ready_count", "ready_scenarios", "not_ready_scenarios"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_schema_contract(schema: dict[str, Any]) -> None:
    assert_true(schema.get("title") == "RunCost Alpha Smoke Report", "unexpected alpha smoke schema title")
    defs = schema.get("$defs")
    assert_true(isinstance(defs, dict), "alpha smoke schema missing $defs")
    assert_true(set(defs.get("scenarioStatus", {}).get("enum", [])) == ALLOWED_STATUSES, "scenario status enum drifted")
    smoke_summary = defs.get("smokeSummary", {})
    preflight_summary = defs.get("preflightSummary", {})
    assert_true(set(smoke_summary.get("required", [])) == SMOKE_SUMMARY_KEYS, "smoke summary schema keys drifted")
    assert_true(set(preflight_summary.get("required", [])) == PREFLIGHT_SUMMARY_KEYS, "preflight summary schema keys drifted")
    rules = schema.get("allOf")
    assert_true(isinstance(rules, list) and len(rules) >= 3, "alpha smoke schema must encode mode-specific rules")
    rule_modes = set()
    for rule in rules:
        mode_schema = rule.get("if", {}).get("properties", {}).get("mode", {})
        if "const" in mode_schema:
            rule_modes.add(mode_schema["const"])
        else:
            rule_modes.update(mode_schema.get("enum", []))
    assert_true(rule_modes == ALLOWED_MODES, "alpha smoke schema mode-specific rules must cover every mode")


def walk_sanitized(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = key.lower().replace("-", "_")
            assert_true(normalized not in FORBIDDEN_KEYS, f"forbidden alpha smoke key {path}.{key}")
            walk_sanitized(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_sanitized(child, f"{path}[{index}]")
    elif isinstance(value, str):
        for pattern in SECRET_PATTERNS:
            assert_true(not pattern.search(value), f"secret-like value found in alpha smoke report at {path}")


def validate_evidence(evidence: object, path: str) -> None:
    assert_true(isinstance(evidence, dict), f"{path} evidence must be an object")
    for key in ["component_names", "warning_codes", "usage_fields_present"]:
        assert_true(isinstance(evidence.get(key), list), f"{path}.evidence.{key} must be a list")
    assert_true("total" in evidence, f"{path}.evidence.total is required")
    assert_true(evidence.get("raw_response_retained") is False, f"{path}.evidence.raw_response_retained must be false")
    assert_true(evidence.get("source") in {"sample", "live"}, f"{path}.evidence.source must be sample or live")
    assert_true(
        evidence.get("exactness") in {"synthetic_sample", "sample_prices_not_invoice_exact", "not_run", "requires_review"},
        f"{path}.evidence.exactness has invalid value",
    )


def validate_next_action(next_action: object, path: str) -> None:
    assert_true(isinstance(next_action, dict), f"{path}.next_action must be an object")
    assert_true(isinstance(next_action.get("type"), str) and next_action["type"], f"{path}.next_action.type required")
    assert_true(isinstance(next_action.get("reason"), str) and next_action["reason"], f"{path}.next_action.reason required")


def validate_smoke_scenario(item: object, path: str, mode: str) -> None:
    assert_true(isinstance(item, dict), f"{path} must be an object")
    assert_true(isinstance(item.get("scenario"), str) and item["scenario"], f"{path}.scenario required")
    assert_true(item.get("status") in ALLOWED_STATUSES, f"{path}.status has invalid value")
    if mode == "live_preflight":
        for key in [
            "required_env",
            "env_present",
            "env_missing",
            "required_inputs",
            "inputs_present",
            "inputs_missing",
            "optional_dependencies_present",
            "optional_dependencies_missing",
        ]:
            assert_true(isinstance(item.get(key), list), f"{path}.{key} must be a list")
        assert_true(item.get("secret_values_emitted") is False, f"{path}.secret_values_emitted must be false")
        if "next_action" in item:
            validate_next_action(item["next_action"], path)
        return
    validate_evidence(item.get("evidence"), path)
    validate_next_action(item.get("next_action"), path)


def validate_report(report: dict[str, Any]) -> None:
    assert_true(report.get("schema_version") == "0.1", "alpha smoke report must use schema_version 0.1")
    assert_true(isinstance(report.get("generated_at"), str) and report["generated_at"], "alpha smoke report missing generated_at")
    mode = report.get("mode")
    assert_true(mode in ALLOWED_MODES, f"alpha smoke report has invalid mode {mode!r}")
    assert_true(report.get("sanitized") is True, "alpha smoke report must be sanitized")
    assert_true(report.get("safe_to_attach_to_issue") is True, "alpha smoke report must be safe to attach")
    walk_sanitized(report)
    if "next_action" in report:
        validate_next_action(report["next_action"], "$")

    if mode == "live_preflight":
        validate_preflight_report(report)
        return

    assert_true(report.get("sample_prices") is True, "alpha smoke reports must acknowledge sample price cards")

    if isinstance(report.get("scenarios"), list):
        scenarios = report["scenarios"]
        assert_true(scenarios, "aggregate alpha smoke report must include scenarios")
        for index, item in enumerate(scenarios):
            validate_smoke_scenario(item, f"$.scenarios[{index}]", mode)
        validate_smoke_summary(report, scenarios)
        return

    assert_true(isinstance(report.get("scenario"), str) and report["scenario"], "single-scenario smoke report missing scenario")
    assert_true(report.get("status") in ALLOWED_STATUSES, "single-scenario smoke report has invalid status")
    validate_evidence(report.get("evidence"), "$")
    validate_next_action(report.get("next_action"), "$")


def validate_smoke_summary(report: dict[str, Any], scenarios: list[dict[str, Any]]) -> None:
    summary = report.get("summary")
    assert_true(isinstance(summary, dict), "aggregate alpha smoke report must include summary")
    assert_true(set(summary) == SMOKE_SUMMARY_KEYS, "aggregate alpha smoke summary keys drifted")
    counts = {key: 0 for key in SMOKE_SUMMARY_KEYS}
    counts["total"] = len(scenarios)
    for item in scenarios:
        status = item["status"]
        if status in counts:
            counts[status] += 1
    for key, value in counts.items():
        assert_true(summary.get(key) == value, f"aggregate alpha smoke summary.{key} must match scenarios")


def validate_preflight_report(report: dict[str, Any]) -> None:
    scenarios = report.get("scenarios")
    assert_true(isinstance(scenarios, list) and scenarios, "preflight report must contain scenarios")
    for index, item in enumerate(scenarios):
        validate_smoke_scenario(item, f"$.scenarios[{index}]", "live_preflight")
    summary = report.get("summary")
    assert_true(isinstance(summary, dict), "preflight report must include summary")
    assert_true(set(summary) == PREFLIGHT_SUMMARY_KEYS, "preflight summary keys drifted")
    ready = [item["scenario"] for item in scenarios if item["status"] == "ready"]
    not_ready = [item["scenario"] for item in scenarios if item["status"] != "ready"]
    assert_true(summary["ready_count"] == len(ready), "preflight ready_count must match scenarios")
    assert_true(summary["not_ready_count"] == len(not_ready), "preflight not_ready_count must match scenarios")
    assert_true(summary["ready_scenarios"] == ready, "preflight ready_scenarios must match scenarios")
    assert_true(summary["not_ready_scenarios"] == not_ready, "preflight not_ready_scenarios must match scenarios")
    assert_true(report.get("live_ready") is (not not_ready), "preflight live_ready must match scenario readiness")


def generate_sample_reports() -> list[dict[str, Any]]:
    with tempfile.TemporaryDirectory() as temp_dir:
        smoke_output = Path(temp_dir) / "alpha-smoke.json"
        preflight_output = Path(temp_dir) / "alpha-smoke-preflight.json"
        subprocess.run(
            [
                sys.executable,
                str(SMOKE_COMMAND),
                "--mode",
                "sample",
                "--output",
                str(smoke_output),
                "--allow-sample-prices",
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        subprocess.run(
            [sys.executable, str(PREFLIGHT_COMMAND), "--output", str(preflight_output)],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return [load_json(smoke_output), load_json(preflight_output)]


def self_check_secret_rejection() -> None:
    bad = {
        "schema_version": "0.1",
        "generated_at": "2026-05-26T00:00:00Z",
        "mode": "live",
        "sanitized": True,
        "safe_to_attach_to_issue": True,
        "scenarios": [
            {
                "scenario": "bad",
                "status": "skipped",
                "evidence": {
                    "component_names": [],
                    "warning_codes": [],
                    "total": "0",
                    "usage_fields_present": [],
                    "raw_response_retained": False,
                    "exactness": "not_run",
                    "source": "live",
                },
                "next_action": {"type": "documented_limitation", "reason": "skipped with sk-secretvalue"},
            }
        ],
        "summary": {"total": 1, "passed": 0, "skipped": 1, "needs_product_truth": 0, "failed": 0},
    }
    try:
        validate_report(bad)
    except AssertionError as exc:
        assert_true("secret-like" in str(exc), "secret self-check should fail for the secret-like value")
    else:
        raise AssertionError("alpha smoke contract must reject secret-like values")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate sanitized alpha smoke report contracts.")
    parser.add_argument("--report", action="append", default=[], help="Alpha smoke or preflight JSON report to validate.")
    args = parser.parse_args()

    assert_true(SCHEMA.exists(), "missing alpha smoke report schema")
    validate_schema_contract(load_json(SCHEMA))
    self_check_secret_rejection()
    reports = [load_json(Path(path)) for path in args.report] if args.report else generate_sample_reports()
    for report in reports:
        validate_report(report)
    print("Alpha smoke contract checks passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"Alpha smoke contract check failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
