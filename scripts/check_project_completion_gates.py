#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTER = ROOT / "fixtures" / "source-files" / "project-completion-gates.json"

ALLOWED_STATUSES = {
    "satisfied",
    "partial",
    "pending_external_evidence",
    "deferred_by_user",
    "not_started",
}
ALLOWED_AREAS = {
    "milestone8",
    "milestone9",
    "public_beta",
    "polyglot",
    "provider_framework_breadth",
    "v1",
}
ALLOWED_REQUIREMENTS = {"milestone8", "public_beta", "v1"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_evidence(gate_id: str, evidence: object) -> None:
    assert_true(isinstance(evidence, list), f"{gate_id}: current_evidence must be a list")
    for item in evidence:
        assert_true(isinstance(item, dict), f"{gate_id}: evidence entries must be objects")
        kind = item.get("kind")
        proves = item.get("proves")
        assert_true(isinstance(kind, str) and kind, f"{gate_id}: evidence entry missing kind")
        assert_true(isinstance(proves, str) and proves, f"{gate_id}: evidence entry missing proves")
        path = item.get("path")
        if path is not None:
            assert_true(isinstance(path, str) and path, f"{gate_id}: evidence path must be a non-empty string")
            assert_true((ROOT / path).exists(), f"{gate_id}: evidence path does not exist: {path}")


def validate_gate(gate: object, seen: set[str]) -> dict[str, Any]:
    assert_true(isinstance(gate, dict), "gate entries must be objects")
    gate_id = gate.get("id")
    assert_true(isinstance(gate_id, str) and re.fullmatch(r"[a-z0-9_]+", gate_id), f"invalid gate id: {gate_id!r}")
    assert_true(gate_id not in seen, f"duplicate gate id: {gate_id}")
    seen.add(gate_id)

    area = gate.get("area")
    status = gate.get("status")
    required_for = gate.get("required_for")
    required_evidence = gate.get("required_evidence")
    completion_check = gate.get("completion_check")

    assert_true(area in ALLOWED_AREAS, f"{gate_id}: invalid area {area!r}")
    assert_true(status in ALLOWED_STATUSES, f"{gate_id}: invalid status {status!r}")
    assert_true(isinstance(gate.get("requirement"), str) and gate["requirement"], f"{gate_id}: missing requirement")
    assert_true(isinstance(required_for, list) and required_for, f"{gate_id}: required_for must be a non-empty list")
    unknown_requirements = sorted(set(required_for) - ALLOWED_REQUIREMENTS)
    assert_true(not unknown_requirements, f"{gate_id}: unknown required_for values {unknown_requirements}")
    assert_true(
        isinstance(required_evidence, list)
        and required_evidence
        and all(isinstance(item, str) and item for item in required_evidence),
        f"{gate_id}: required_evidence must be a non-empty string list",
    )
    assert_true(
        isinstance(completion_check, str) and completion_check,
        f"{gate_id}: completion_check must be a non-empty string",
    )
    validate_evidence(gate_id, gate.get("current_evidence"))

    if status == "satisfied":
        assert_true(gate.get("current_evidence"), f"{gate_id}: satisfied gates must name current evidence")
    elif status == "deferred_by_user":
        assert_true(
            isinstance(gate.get("deferred_reason"), str) and gate["deferred_reason"],
            f"{gate_id}: deferred gates must include deferred_reason",
        )
        assert_true(
            isinstance(gate.get("remaining_action"), str) and gate["remaining_action"],
            f"{gate_id}: deferred gates must include remaining_action",
        )
    else:
        assert_true(
            isinstance(gate.get("remaining_action"), str) and gate["remaining_action"],
            f"{gate_id}: incomplete gates must include remaining_action",
        )
    return gate


def validate_register(register: dict[str, Any]) -> list[dict[str, Any]]:
    assert_true(register.get("schema_version") == "0.1", "completion gate register must use schema_version 0.1")
    assert_true(isinstance(register.get("updated_at"), str) and register["updated_at"], "register missing updated_at")
    status_scale = register.get("status_scale")
    assert_true(isinstance(status_scale, dict), "register missing status_scale")
    assert_true(set(status_scale) == ALLOWED_STATUSES, "status_scale must define every allowed status")

    gates = register.get("gates")
    assert_true(isinstance(gates, list) and gates, "register must contain gates")
    seen: set[str] = set()
    return [validate_gate(gate, seen) for gate in gates]


def require_complete(gates: list[dict[str, Any]], requirement: str) -> None:
    incomplete = [
        f"{gate['id']} ({gate['status']})"
        for gate in gates
        if requirement in gate["required_for"] and gate["status"] != "satisfied"
    ]
    if incomplete:
        joined = "\n  - ".join(incomplete)
        raise AssertionError(f"{requirement} is not complete. Incomplete gates:\n  - {joined}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate RunCost project completion gates.")
    parser.add_argument("--register", default=str(DEFAULT_REGISTER), help="Completion gate register JSON.")
    parser.add_argument("--require-milestone8", action="store_true", help="Fail unless every Milestone 8 gate is satisfied.")
    parser.add_argument("--require-public-beta", action="store_true", help="Fail unless every public beta gate is satisfied.")
    parser.add_argument("--require-v1", action="store_true", help="Fail unless every V1 gate is satisfied.")
    args = parser.parse_args()

    gates = validate_register(load_json(Path(args.register)))
    if args.require_milestone8:
        require_complete(gates, "milestone8")
    if args.require_public_beta:
        require_complete(gates, "public_beta")
    if args.require_v1:
        require_complete(gates, "v1")

    print("Project completion gate checks passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"Project completion gate check failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
