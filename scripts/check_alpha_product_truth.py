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
    if register.get("schema_version") != "0.1":
        raise AssertionError("alpha smoke product-truth register must use schema_version 0.1")
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
        artifact = entry.get("artifact")
        if classification != "none":
            if not isinstance(artifact, str) or not artifact:
                raise AssertionError(f"{scenario} classification {classification} must name an artifact")
            if not (ROOT / artifact).exists():
                raise AssertionError(f"{scenario} product-truth artifact does not exist: {artifact}")
        if not isinstance(entry.get("resolution"), str) or not entry["resolution"]:
            raise AssertionError(f"{scenario} must include a resolution")
        by_key[key] = entry
    return by_key


def validate_report(report: dict[str, Any], register: dict[str, Any]) -> None:
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate alpha smoke findings against product-truth artifacts.")
    parser.add_argument("--smoke-report", help="Validate this live smoke JSON report instead of generating a no-credential report.")
    parser.add_argument("--register", default=str(DEFAULT_REGISTER), help="Path to the product-truth register.")
    args = parser.parse_args()

    register = load_json(Path(args.register))
    report = load_json(Path(args.smoke_report)) if args.smoke_report else generated_no_credentials_report()
    validate_report(report, register)
    print("Alpha smoke product-truth checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
