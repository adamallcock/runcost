#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "trusted-publishing-verification.schema.json"
DEFAULT_VERIFICATION = ROOT / "fixtures" / "source-files" / "trusted-publishing-verification-template.json"

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
            assert_true(normalized not in FORBIDDEN_KEYS, f"forbidden trusted-publishing key {path}.{key}")
            walk_sanitized(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_sanitized(child, f"{path}[{index}]")
    elif isinstance(value, str):
        for pattern in SECRET_PATTERNS:
            assert_true(not pattern.search(value), f"secret-like value found in trusted-publishing evidence at {path}")


def validate_schema_contract(schema: dict[str, Any]) -> None:
    assert_true(schema.get("title") == "RunCost Trusted Publishing Verification", "unexpected trusted publishing schema title")
    assert_true(schema.get("properties", {}).get("repository", {}).get("const") == "adamallcock/runcost", "repository const drifted")
    assert_true(
        schema.get("properties", {}).get("workflow", {}).get("const") == ".github/workflows/release.yml",
        "workflow const drifted",
    )
    assert_true(schema.get("properties", {}).get("environment", {}).get("const") == "release", "environment const drifted")
    evidence_types = set(schema.get("properties", {}).get("evidence_type", {}).get("enum", []))
    assert_true(evidence_types == {"template", "manual_verified"}, "evidence_type enum drifted")
    pypi_rules = schema.get("properties", {}).get("pypi", {}).get("allOf", [])
    npm_rules = schema.get("properties", {}).get("npm", {}).get("allOf", [])
    assert_true(
        any(rule.get("properties", {}).get("package", {}).get("const") == "runcost-ai" for rule in pypi_rules),
        "PyPI package const must be runcost-ai",
    )
    assert_true(
        any(rule.get("properties", {}).get("package", {}).get("const") == "runcost" for rule in npm_rules),
        "npm package const must be runcost",
    )


def validate_publisher(name: str, publisher: object, *, require_real: bool) -> None:
    assert_true(isinstance(publisher, dict), f"{name} publisher evidence must be an object")
    expected_registry = name
    expected_package = "runcost-ai" if name == "pypi" else "runcost"
    assert_true(publisher.get("package") == expected_package, f"{name} package must be {expected_package}")
    assert_true(publisher.get("registry") == expected_registry, f"{name} registry must be {expected_registry}")
    assert_true(
        publisher.get("stored_registry_token_required") is False,
        f"{name} trusted publishing must not require a stored registry token",
    )
    for key in ["configured_by", "verified_at", "verification_method", "evidence_url"]:
        assert_true(isinstance(publisher.get(key), str), f"{name}.{key} must be a string")

    if require_real:
        assert_true(publisher.get("trusted_publisher_configured") is True, f"{name} trusted publisher is not configured")
        assert_true(
            publisher.get("provenance_or_oidc_configured") is True,
            f"{name} provenance/OIDC configuration is not verified",
        )
        for key in ["configured_by", "verified_at", "verification_method", "evidence_url"]:
            assert_true(publisher[key], f"{name}.{key} is required for real trusted-publishing evidence")
    else:
        assert_true(
            isinstance(publisher.get("trusted_publisher_configured"), bool),
            f"{name}.trusted_publisher_configured must be boolean",
        )
        assert_true(
            isinstance(publisher.get("provenance_or_oidc_configured"), bool),
            f"{name}.provenance_or_oidc_configured must be boolean",
        )


def validate_verification(evidence: dict[str, Any], *, require_real: bool) -> None:
    assert_true(evidence.get("schema_version") == "0.1", "trusted publishing evidence must use schema_version 0.1")
    assert_true(isinstance(evidence.get("generated_at"), str) and evidence["generated_at"], "generated_at is required")
    assert_true(evidence.get("safe_to_commit") is True, "trusted publishing evidence must be safe_to_commit")
    assert_true(evidence.get("contains_secret_values") is False, "trusted publishing evidence must not contain secret values")
    assert_true(evidence.get("repository") == "adamallcock/runcost", "repository must be adamallcock/runcost")
    assert_true(evidence.get("workflow") == ".github/workflows/release.yml", "workflow must be release.yml")
    assert_true(evidence.get("environment") == "release", "environment must be release")
    assert_true(evidence.get("evidence_type") in {"template", "manual_verified"}, "invalid evidence_type")
    walk_sanitized(evidence)
    validate_publisher("pypi", evidence.get("pypi"), require_real=require_real)
    validate_publisher("npm", evidence.get("npm"), require_real=require_real)
    assert_true(isinstance(evidence.get("notes"), list), "notes must be a list")
    if require_real:
        assert_true(evidence.get("evidence_type") == "manual_verified", "real evidence must use evidence_type manual_verified")
    else:
        assert_true(
            evidence.get("evidence_type") == "template",
            "default trusted publishing evidence should remain a template until registry setup is manually verified",
        )


def self_check_rejections() -> None:
    template = load_json(DEFAULT_VERIFICATION)
    bad_token = json.loads(json.dumps(template))
    bad_token["notes"] = ["leaked npm_1234567890abcdef"]
    try:
        validate_verification(bad_token, require_real=False)
    except AssertionError as exc:
        assert_true("secret-like" in str(exc), "secret self-check should reject token-like values")
    else:
        raise AssertionError("trusted publishing verification must reject token-like values")

    bad_real = json.loads(json.dumps(template))
    bad_real["evidence_type"] = "manual_verified"
    try:
        validate_verification(bad_real, require_real=True)
    except AssertionError as exc:
        assert_true("not configured" in str(exc), "real self-check should require configured publishers")
    else:
        raise AssertionError("real trusted publishing verification must require configured publishers")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate sanitized PyPI/npm trusted publishing verification evidence.")
    parser.add_argument("--verification", default=str(DEFAULT_VERIFICATION), help="Trusted publishing verification JSON.")
    parser.add_argument("--require-real", action="store_true", help="Require registry-side PyPI and npm setup to be manually verified.")
    args = parser.parse_args()

    assert_true(SCHEMA.exists(), "missing trusted publishing verification schema")
    validate_schema_contract(load_json(SCHEMA))
    self_check_rejections()
    validate_verification(load_json(Path(args.verification)), require_real=args.require_real)
    print("Trusted publishing verification checks passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"Trusted publishing verification check failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
