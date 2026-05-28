#!/usr/bin/env python3
from __future__ import annotations

import json

from check_alpha_smoke_contract import validate_report
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
    validate_report(report)
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
        assert_true("required_inputs" in item, f"{item['scenario']} missing required_inputs")
        assert_true("inputs_present" in item, f"{item['scenario']} missing inputs_present")
        assert_true("inputs_missing" in item, f"{item['scenario']} missing inputs_missing")
        assert_true("next_action" in item, f"{item['scenario']} missing next_action")
        assert_true(
            item["next_action"]["type"] in {"run_live_smoke", "prepare_live_smoke"},
            f"{item['scenario']} has invalid next_action type",
        )
        joined_names = " ".join(item["required_env"] + item["env_present"] + item["env_missing"])
        assert_true("sk-test-secret" not in item["next_action"]["reason"], f"{item['scenario']} leaked secret in next_action")
        assert_true(
            all(name in joined_names or name not in item["next_action"]["reason"] for name in fake_env.values()),
            f"{item['scenario']} leaked secret value in next_action",
        )
    costs_item = next(item for item in report["scenarios"] if item["scenario"] == "openai_costs_invoice_comparison")
    assert_true(costs_item["status"] == "not_ready", "OpenAI Costs preflight must require explicit comparison inputs")
    assert_true(
        costs_item["inputs_missing"] == ["openai_costs_start_time", "openai_costs_runcost_ledger"],
        "OpenAI Costs preflight must report missing sanitized input names",
    )
    ready_costs = run_alpha_smoke_preflight.build_report(
        {**fake_env, "OPENAI_ADMIN_KEY": "sk-admin-secret"},
        {
            "openai_costs_start_time": "1741476542",
            "openai_costs_runcost_ledger": "/private/path/ledger.json",
        },
    )
    validate_report(ready_costs)
    ready_costs_item = next(item for item in ready_costs["scenarios"] if item["scenario"] == "openai_costs_invoice_comparison")
    assert_true(ready_costs_item["status"] == "ready", "OpenAI Costs preflight should be ready when env and input names are present")
    ready_serialized = json.dumps(ready_costs, sort_keys=True)
    assert_true("sk-admin-secret" not in ready_serialized, "OpenAI Costs preflight leaked admin secret")
    assert_true("/private/path/ledger.json" not in ready_serialized, "OpenAI Costs preflight leaked local ledger path")
    assert_true(report["next_action"]["type"] in {"run_live_smoke", "prepare_live_smoke"}, "preflight report missing top-level next action")
    print("Alpha smoke preflight checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
