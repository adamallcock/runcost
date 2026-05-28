#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "v1-stabilization-checklist.schema.json"
DEFAULT_CHECKLIST = ROOT / "fixtures" / "source-files" / "v1-stabilization-checklist-template.json"

BOOLEAN_SECTIONS = ["prerequisites", "contracts", "packages", "coverage", "operations"]
FORBIDDEN_KEYS = {
    "api_key",
    "authorization",
    "headers",
    "password",
    "secret",
    "token",
}
SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{8,}\b", re.IGNORECASE),
    re.compile(r"\bnpm_[A-Za-z0-9]{8,}\b"),
    re.compile(r"\bpypi-[A-Za-z0-9_-]{8,}\b", re.IGNORECASE),
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
            assert_true(normalized not in FORBIDDEN_KEYS, f"forbidden V1 checklist key {path}.{key}")
            walk_sanitized(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_sanitized(child, f"{path}[{index}]")
    elif isinstance(value, str):
        for pattern in SECRET_PATTERNS:
            assert_true(not pattern.search(value), f"secret-like value found in V1 checklist at {path}")


def validate_schema_contract(schema: dict[str, Any]) -> None:
    assert_true(schema.get("title") == "RunCost V1 Stabilization Checklist", "unexpected V1 schema title")
    evidence_types = set(schema.get("properties", {}).get("evidence_type", {}).get("enum", []))
    assert_true(evidence_types == {"template", "release_candidate_review"}, "V1 checklist evidence_type enum drifted")
    defs = schema.get("$defs")
    assert_true(isinstance(defs, dict), "V1 checklist schema missing $defs")
    assert_true(set(defs) == set(BOOLEAN_SECTIONS), "V1 checklist schema section definitions drifted")


def validate_boolean_section(checklist: dict[str, Any], section_name: str) -> list[str]:
    section = checklist.get(section_name)
    assert_true(isinstance(section, dict), f"{section_name} must be an object")
    false_fields: list[str] = []
    for key, value in section.items():
        assert_true(isinstance(value, bool), f"{section_name}.{key} must be boolean")
        if value is False:
            false_fields.append(f"{section_name}.{key}")
    return false_fields


def validate_checklist(checklist: dict[str, Any], *, require_real: bool) -> None:
    assert_true(checklist.get("schema_version") == "0.1", "V1 checklist must use schema_version 0.1")
    assert_true(checklist.get("safe_to_commit") is True, "V1 checklist must be safe_to_commit")
    assert_true(checklist.get("contains_secret_values") is False, "V1 checklist must not contain secret values")
    assert_true(checklist.get("evidence_type") in {"template", "release_candidate_review"}, "invalid V1 evidence_type")
    assert_true(isinstance(checklist.get("target_version"), str) and checklist["target_version"], "target_version required")
    assert_true(isinstance(checklist.get("reviewed_at"), str), "reviewed_at must be a string")
    assert_true(isinstance(checklist.get("reviewed_by"), str), "reviewed_by must be a string")
    walk_sanitized(checklist)

    false_fields: list[str] = []
    for section_name in BOOLEAN_SECTIONS:
        false_fields.extend(validate_boolean_section(checklist, section_name))

    holes = checklist.get("known_correctness_holes")
    assert_true(isinstance(holes, list) and all(isinstance(item, str) for item in holes), "known_correctness_holes must be a string list")
    notes = checklist.get("notes")
    assert_true(isinstance(notes, list) and all(isinstance(item, str) for item in notes), "notes must be a string list")

    if require_real:
        assert_true(
            checklist.get("evidence_type") == "release_candidate_review",
            "real V1 readiness must use evidence_type release_candidate_review",
        )
        assert_true(not false_fields, "real V1 readiness has incomplete fields: " + ", ".join(false_fields))
        assert_true(not holes, "real V1 readiness must have no known correctness holes")
        assert_true(checklist["reviewed_at"], "real V1 readiness requires reviewed_at")
        assert_true(checklist["reviewed_by"], "real V1 readiness requires reviewed_by")
    else:
        assert_true(
            checklist.get("evidence_type") == "template",
            "default V1 checklist should remain a template until release-candidate review",
        )


def self_check_rejections() -> None:
    template = load_json(DEFAULT_CHECKLIST)
    bad_secret = json.loads(json.dumps(template))
    bad_secret["notes"] = ["leaked sk-test-secret"]
    try:
        validate_checklist(bad_secret, require_real=False)
    except AssertionError as exc:
        assert_true("secret-like" in str(exc), "secret self-check should fail for token-like value")
    else:
        raise AssertionError("V1 checklist must reject secret-like values")

    bad_real = json.loads(json.dumps(template))
    bad_real["evidence_type"] = "release_candidate_review"
    try:
        validate_checklist(bad_real, require_real=True)
    except AssertionError as exc:
        assert_true("incomplete fields" in str(exc), "real self-check should require every boolean field")
    else:
        raise AssertionError("V1 release-candidate checklist must reject incomplete fields")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate RunCost V1 stabilization checklist evidence.")
    parser.add_argument("--checklist", default=str(DEFAULT_CHECKLIST), help="V1 stabilization checklist JSON.")
    parser.add_argument("--require-real", action="store_true", help="Require release-candidate V1 readiness evidence.")
    args = parser.parse_args()

    assert_true(SCHEMA.exists(), "missing V1 stabilization checklist schema")
    validate_schema_contract(load_json(SCHEMA))
    self_check_rejections()
    validate_checklist(load_json(Path(args.checklist)), require_real=args.require_real)
    print("V1 stabilization checklist checks passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"V1 stabilization checklist check failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
