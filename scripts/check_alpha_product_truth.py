#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SMOKE_COMMAND = ROOT / "scripts" / "run_alpha_smoke.py"
DEFAULT_REGISTER = ROOT / "fixtures" / "source-files" / "alpha-smoke-product-truth-register.json"
REGISTER_SCHEMA = ROOT / "schemas" / "alpha-smoke-product-truth-register.schema.json"

from check_alpha_smoke_contract import validate_report as validate_alpha_smoke_contract  # noqa: E402

ALLOWED_CLASSIFICATIONS = {
    "none",
    "fixture",
    "structured_warning",
    "documented_limitation",
    "extractor_source_fix",
    "price_source_update",
}
ALLOWED_ARTIFACT_KINDS = {
    "none",
    "fixture",
    "sample_fixture",
    "report",
    "docs",
    "schema",
    "code",
    "source_data",
}
CLASSIFICATION_ARTIFACT_KINDS = {
    "none": {"none", "sample_fixture"},
    "fixture": {"fixture", "sample_fixture"},
    "structured_warning": {"code", "fixture", "schema"},
    "documented_limitation": {"docs", "report"},
    "extractor_source_fix": {"code"},
    "price_source_update": {"source_data"},
}
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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def walk_sanitized(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = key.lower().replace("-", "_")
            if normalized in FORBIDDEN_KEYS:
                raise AssertionError(f"forbidden smoke output key {path}.{key}")
            walk_sanitized(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_sanitized(child, f"{path}[{index}]")


def generated_no_credentials_report() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / "alpha-smoke-live-no-credentials.json"
        env = dict(os.environ)
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"]:
            env.pop(key, None)
        subprocess.run(
            [
                sys.executable,
                str(SMOKE_COMMAND),
                "--mode",
                "live",
                "--output",
                str(output),
                "--allow-sample-prices",
            ],
            cwd=ROOT,
            env=env,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return load_json(output)


def validate_register(register: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    if not REGISTER_SCHEMA.exists():
        raise AssertionError("missing alpha smoke product-truth register schema")
    if register.get("schema_version") != "0.1":
        raise AssertionError("alpha smoke product-truth register must use schema_version 0.1")
    if not isinstance(register.get("description"), str) or not register["description"]:
        raise AssertionError("alpha smoke product-truth register must include a description")
    entries = register.get("entries")
    if not isinstance(entries, list) or not entries:
        raise AssertionError("alpha smoke product-truth register must contain entries")

    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in entries:
        scenario = entry.get("scenario")
        status = entry.get("status")
        if not isinstance(scenario, str) or not scenario:
            raise AssertionError(f"register entry has invalid scenario: {entry}")
        if not isinstance(status, str) or not status:
            raise AssertionError(f"register entry has invalid status: {entry}")
        key = (scenario, status)
        if key in by_key:
            raise AssertionError(f"duplicate register entry for scenario/status {key}")
        classification = entry.get("classification")
        if classification not in ALLOWED_CLASSIFICATIONS:
            raise AssertionError(f"{scenario} has invalid classification {classification!r}")
        artifact_kind = entry.get("artifact_kind")
        if artifact_kind not in ALLOWED_ARTIFACT_KINDS:
            raise AssertionError(f"{scenario} has invalid artifact_kind {artifact_kind!r}")
        if artifact_kind not in CLASSIFICATION_ARTIFACT_KINDS[classification]:
            raise AssertionError(
                f"{scenario}/{status} classification {classification!r} is incompatible with "
                f"artifact_kind {artifact_kind!r}"
            )
        next_action_type = entry.get("next_action_type")
        if not isinstance(next_action_type, str) or not next_action_type:
            raise AssertionError(f"{scenario}/{status} must include next_action_type")
        if status == "passed":
            if classification != "none":
                raise AssertionError(f"{scenario}/passed entries must use classification none")
            if next_action_type != "none":
                raise AssertionError(f"{scenario}/passed entries must use next_action_type none")
        elif classification == "none":
            raise AssertionError(f"{scenario}/{status} must resolve to product truth")
        artifact = entry.get("artifact")
        if classification != "none":
            if not isinstance(artifact, str) or not artifact:
                raise AssertionError(f"{scenario} classification {classification} must name an artifact")
            if not (ROOT / artifact).exists():
                raise AssertionError(f"{scenario} product-truth artifact does not exist: {artifact}")
        elif artifact_kind == "none":
            if artifact not in {"", None}:
                raise AssertionError(f"{scenario}/{status} artifact must be empty when artifact_kind is none")
        elif not isinstance(artifact, str) or not artifact:
            raise AssertionError(f"{scenario}/{status} artifact_kind {artifact_kind} must name an artifact")
        if not isinstance(entry.get("resolution"), str) or not entry["resolution"]:
            raise AssertionError(f"{scenario} must include a resolution")
        by_key[key] = entry
    return by_key


def self_check_register_semantics(register: dict[str, Any]) -> None:
    validate_register(register)
    bad_non_passing = json.loads(json.dumps(register))
    for entry in bad_non_passing["entries"]:
        if entry["status"] != "passed":
            entry["classification"] = "none"
            entry["artifact_kind"] = "sample_fixture"
            break
    try:
        validate_register(bad_non_passing)
    except AssertionError as exc:
        if "must resolve to product truth" not in str(exc):
            raise
    else:
        raise AssertionError("product-truth register must reject non-passing entries with classification none")

    bad_artifact_kind = json.loads(json.dumps(register))
    for entry in bad_artifact_kind["entries"]:
        if entry["classification"] == "documented_limitation":
            entry["artifact_kind"] = "fixture"
            break
    try:
        validate_register(bad_artifact_kind)
    except AssertionError as exc:
        if "incompatible" not in str(exc):
            raise
    else:
        raise AssertionError("product-truth register must reject incompatible classification/artifact_kind pairs")


def validate_report(report: dict[str, Any], register: dict[str, Any]) -> None:
    validate_alpha_smoke_contract(report)
    if report.get("schema_version") != "0.1":
        raise AssertionError("alpha smoke report must use schema_version 0.1")
    if report.get("mode") != "live":
        raise AssertionError("product-truth checks validate live smoke reports")
    if report.get("sanitized") is not True or report.get("safe_to_attach_to_issue") is not True:
        raise AssertionError("alpha smoke report must be sanitized and safe to attach")
    walk_sanitized(report)

    registered = validate_register(register)
    scenarios = report.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise AssertionError("alpha smoke report must contain scenarios")

    has_live_pass = any(
        item.get("status") == "passed" and (item.get("evidence") or {}).get("source") == "live"
        for item in scenarios
    )
    if has_live_pass:
        discount_item = next((item for item in scenarios if item.get("scenario") == "multi_provider_discount"), None)
        if discount_item is None:
            raise AssertionError("credentialed live smoke reports must include multi_provider_discount in the same review set")
        if discount_item.get("status") != "passed":
            raise AssertionError("credentialed live smoke reports must include a passing multi_provider_discount scenario")

    for item in scenarios:
        scenario = item.get("scenario")
        status = item.get("status")
        next_action = item.get("next_action") or {}
        next_action_type = next_action.get("type")
        key = (scenario, status)
        entry = registered.get(key)
        if entry is None and status == "passed":
            continue
        if entry is None:
            raise AssertionError(f"missing product-truth register entry for {scenario}/{status}")
        if entry.get("next_action_type") != next_action_type:
            raise AssertionError(
                f"{scenario}/{status} next_action type drifted: "
                f"{next_action_type!r} != {entry.get('next_action_type')!r}"
            )
        reason_contains = entry.get("reason_contains")
        if reason_contains and reason_contains not in str(next_action.get("reason", "")):
            raise AssertionError(f"{scenario}/{status} next_action reason no longer contains {reason_contains!r}")
        if status != "passed" and entry.get("classification") == "none":
            raise AssertionError(f"{scenario}/{status} must be classified as product truth")


def self_check_live_discount_requirement(register: dict[str, Any]) -> None:
    base_report = {
        "schema_version": "0.1",
        "generated_at": "2026-05-26T00:00:00Z",
        "mode": "live",
        "sanitized": True,
        "safe_to_attach_to_issue": True,
        "sample_prices": True,
        "summary": {"total": 1, "passed": 1, "skipped": 0, "needs_product_truth": 0, "failed": 0},
        "scenarios": [
            {
                "scenario": "openai_responses",
                "status": "passed",
                "evidence": {
                    "component_names": ["input_uncached_tokens"],
                    "warning_codes": [],
                    "total": "0.001",
                    "usage_fields_present": ["usage"],
                    "raw_response_retained": False,
                    "exactness": "sample_prices_not_invoice_exact",
                    "source": "live",
                },
                "next_action": {"type": "none", "reason": "synthetic passed live scenario"},
            }
        ],
    }
    try:
        validate_report(base_report, register)
    except AssertionError as exc:
        if "multi_provider_discount" not in str(exc):
            raise
    else:
        raise AssertionError("live product-truth check must require multi_provider_discount beside live passes")

    valid_report = {
        **base_report,
        "summary": {"total": 2, "passed": 2, "skipped": 0, "needs_product_truth": 0, "failed": 0},
        "scenarios": [
            *base_report["scenarios"],
            {
                "scenario": "multi_provider_discount",
                "status": "passed",
                "evidence": {
                    "component_names": ["input_uncached_tokens"],
                    "warning_codes": [],
                    "total": "0.001",
                    "usage_fields_present": ["usage_ledger.components"],
                    "raw_response_retained": False,
                    "exactness": "synthetic_sample",
                    "source": "sample",
                },
                "next_action": {"type": "none", "reason": "synthetic discount scenario"},
            },
        ],
    }
    validate_report(valid_report, register)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate alpha smoke findings against product-truth artifacts.")
    parser.add_argument("--smoke-report", help="Validate this live smoke JSON report instead of generating a no-credential report.")
    parser.add_argument("--register", default=str(DEFAULT_REGISTER), help="Path to the product-truth register.")
    args = parser.parse_args()

    register = load_json(Path(args.register))
    report = load_json(Path(args.smoke_report)) if args.smoke_report else generated_no_credentials_report()
    self_check_register_semantics(register)
    self_check_live_discount_requirement(register)
    validate_report(report, register)
    print("Alpha smoke product-truth checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
