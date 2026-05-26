#!/usr/bin/env python3
from __future__ import annotations

import json

import run_alpha_smoke_preflight


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    fake_env = {
        "OPENAI_API_KEY": "sk-test-secret-openai",
        "ANTHROPIC_API_KEY": "sk-ant-test-secret",
        "OPENROUTER_API_KEY": "sk-or-test-secret",
    }
    report = run_alpha_smoke_preflight.build_report(fake_env)
    serialized = json.dumps(report, sort_keys=True)
    for secret in fake_env.values():
        assert_true(secret not in serialized, f"preflight leaked secret value {secret}")
    assert_true(report["sanitized"] is True, "preflight report must be marked sanitized")
    assert_true(report["safe_to_attach_to_issue"] is True, "preflight report must be issue-safe")
    for item in report["scenarios"]:
        assert_true(item["secret_values_emitted"] is False, f"{item['scenario']} emitted secret values")
        assert_true("required_env" in item, f"{item['scenario']} missing required_env")
        assert_true("env_present" in item, f"{item['scenario']} missing env_present")
        assert_true("env_missing" in item, f"{item['scenario']} missing env_missing")
    print("Alpha smoke preflight checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
