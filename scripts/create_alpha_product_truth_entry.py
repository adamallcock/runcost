#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTER = ROOT / "fixtures" / "source-files" / "alpha-smoke-product-truth-register.json"
DEFAULT_ARTIFACT = "docs/internal/reports/2026-05-26-alpha-smoke-live-no-credentials.md"

from check_alpha_product_truth import (  # noqa: E402
    ALLOWED_ARTIFACT_KINDS,
    ALLOWED_CLASSIFICATIONS,
    CLASSIFICATION_ARTIFACT_KINDS,
    generated_no_credentials_report,
    load_json,
    validate_register,
)
from check_alpha_smoke_contract import validate_report as validate_alpha_smoke_contract  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def normalize_artifact_path(value: str) -> str:
    if not value:
        return ""
    path = Path(value)
    if path.is_absolute():
        try:
            path = path.relative_to(ROOT)
        except ValueError as exc:
            raise AssertionError(f"artifact must live under the repository root: {value}") from exc
    normalized = path.as_posix()
    assert_true((ROOT / normalized).exists(), f"product-truth artifact does not exist: {normalized}")
    return normalized


def infer_artifact_kind(artifact: str, classification: str) -> str:
    if classification == "none":
        return "none" if not artifact else "sample_fixture"
    if artifact.startswith("schemas/"):
        return "schema"
    if artifact.startswith("docs/internal/reports/"):
        return "report"
    if artifact.startswith("docs/"):
        return "docs"
    if artifact.startswith("packages/") or artifact.startswith("scripts/"):
        return "code"
    if artifact.startswith("fixtures/source-files/"):
        return "source_data" if classification == "price_source_update" else "sample_fixture"
    if artifact.startswith("fixtures/"):
        return "fixture"
    raise AssertionError(
        "cannot infer artifact_kind for artifact; pass --artifact-kind explicitly "
        f"for {artifact!r}"
    )


def find_scenario(report: dict[str, Any], scenario: str, status: str | None) -> dict[str, Any]:
    validate_alpha_smoke_contract(report)
    candidates: list[dict[str, Any]]
    if isinstance(report.get("scenarios"), list):
        candidates = [item for item in report["scenarios"] if item.get("scenario") == scenario]
    else:
        candidates = [report] if report.get("scenario") == scenario else []
    if status is not None:
        candidates = [item for item in candidates if item.get("status") == status]
    if not candidates:
        suffix = f"/{status}" if status else ""
        raise AssertionError(f"smoke report does not contain scenario {scenario}{suffix}")
    if len(candidates) > 1:
        raise AssertionError(f"scenario {scenario} appears multiple times; pass --status to disambiguate")
    return candidates[0]


def build_entry(
    item: dict[str, Any],
    classification: str | None,
    artifact: str,
    artifact_kind: str | None,
    resolution: str,
    reason_contains: str | None,
) -> dict[str, Any]:
    scenario = item.get("scenario")
    status = item.get("status")
    next_action = item.get("next_action") or {}
    next_action_type = next_action.get("type")
    assert_true(isinstance(scenario, str) and scenario, "scenario is required")
    assert_true(isinstance(status, str) and status, "status is required")
    assert_true(isinstance(next_action_type, str) and next_action_type, "scenario next_action.type is required")

    if status == "passed":
        classification = classification or "none"
        if classification != "none":
            raise AssertionError("passed smoke entries must use classification none")
    elif not classification:
        raise AssertionError("non-passing smoke entries require --classification")
    assert_true(classification in ALLOWED_CLASSIFICATIONS, f"invalid classification {classification!r}")

    normalized_artifact = normalize_artifact_path(artifact) if artifact else ""
    if classification != "none" and not normalized_artifact:
        raise AssertionError("non-none classifications require --artifact")

    resolved_artifact_kind = artifact_kind or infer_artifact_kind(normalized_artifact, classification)
    assert_true(resolved_artifact_kind in ALLOWED_ARTIFACT_KINDS, f"invalid artifact_kind {resolved_artifact_kind!r}")
    if resolved_artifact_kind not in CLASSIFICATION_ARTIFACT_KINDS[classification]:
        raise AssertionError(
            f"classification {classification!r} is incompatible with artifact_kind {resolved_artifact_kind!r}"
        )

    if not reason_contains:
        reason_contains = str(next_action.get("reason") or "")
    if status != "passed":
        assert_true(reason_contains, "non-passing smoke entries require next_action.reason or --reason-contains")

    entry: dict[str, Any] = {
        "scenario": scenario,
        "status": status,
        "next_action_type": next_action_type,
        "classification": classification,
        "artifact": normalized_artifact,
        "artifact_kind": resolved_artifact_kind,
        "resolution": resolution,
    }
    if reason_contains:
        entry["reason_contains"] = reason_contains
    validate_register(
        {
            "schema_version": "0.1",
            "description": "Single-entry validation envelope.",
            "entries": [entry],
        }
    )
    return entry


def merge_entry(register: dict[str, Any], entry: dict[str, Any], replace_existing: bool) -> dict[str, Any]:
    merged = json.loads(json.dumps(register))
    entries = merged.get("entries")
    assert_true(isinstance(entries, list), "register entries must be a list")
    key = (entry["scenario"], entry["status"])
    replaced = False
    for index, existing in enumerate(entries):
        if (existing.get("scenario"), existing.get("status")) == key:
            if not replace_existing:
                raise AssertionError(f"register already has an entry for {key}; pass --replace-existing")
            entries[index] = entry
            replaced = True
            break
    if not replaced:
        entries.append(entry)
    validate_register(merged)
    return merged


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def self_check() -> None:
    report = generated_no_credentials_report()
    item = find_scenario(report, "openai_responses", "skipped")
    entry = build_entry(
        item,
        classification="documented_limitation",
        artifact=DEFAULT_ARTIFACT,
        artifact_kind=None,
        resolution="Self-check entry for a sanitized no-credential smoke finding.",
        reason_contains=None,
    )
    assert_true(entry["artifact_kind"] == "report", "self-check should infer docs/reports artifacts as report")

    try:
        build_entry(
            item,
            classification="none",
            artifact="fixtures/source-files/alpha-smoke-samples.json",
            artifact_kind="sample_fixture",
            resolution="Invalid self-check entry.",
            reason_contains=None,
        )
    except AssertionError as exc:
        assert_true("must resolve to product truth" in str(exc), "non-passing none classification should fail")
    else:
        raise AssertionError("non-passing entries with classification none must be rejected")

    try:
        build_entry(
            item,
            classification="documented_limitation",
            artifact=DEFAULT_ARTIFACT,
            artifact_kind="fixture",
            resolution="Invalid self-check entry.",
            reason_contains=None,
        )
    except AssertionError as exc:
        assert_true("incompatible" in str(exc), "classification/artifact_kind mismatch should fail")
    else:
        raise AssertionError("incompatible classification/artifact_kind pairs must be rejected")

    register = load_json(DEFAULT_REGISTER)
    merge_entry(register, entry, replace_existing=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create or append one alpha smoke product-truth register entry from a sanitized smoke report."
    )
    parser.add_argument("--smoke-report", help="Sanitized alpha smoke JSON report to read.")
    parser.add_argument("--scenario", help="Scenario id to convert into a register entry.")
    parser.add_argument("--status", help="Optional status to disambiguate repeated scenarios.")
    parser.add_argument("--classification", choices=sorted(ALLOWED_CLASSIFICATIONS), help="Product-truth classification.")
    parser.add_argument("--artifact", default="", help="Repository-relative product-truth artifact path.")
    parser.add_argument("--artifact-kind", choices=sorted(ALLOWED_ARTIFACT_KINDS), help="Artifact kind; inferred when omitted.")
    parser.add_argument("--resolution", help="Human-readable resolution text for the register entry.")
    parser.add_argument("--reason-contains", help="Substring expected in the smoke finding next_action.reason.")
    parser.add_argument("--register", default=str(DEFAULT_REGISTER), help="Register to validate or update.")
    parser.add_argument("--write-register", action="store_true", help="Write the merged entry back to --register.")
    parser.add_argument("--replace-existing", action="store_true", help="Replace an existing scenario/status entry.")
    parser.add_argument("--self-check", action="store_true", help="Run helper self-checks.")
    args = parser.parse_args()

    if args.self_check:
        self_check()
        print("Alpha smoke product-truth entry helper checks passed.")
        return 0

    for field in ["smoke_report", "scenario", "resolution"]:
        if not getattr(args, field):
            parser.error(f"--{field.replace('_', '-')} is required unless --self-check is used")

    report = load_json(Path(args.smoke_report))
    item = find_scenario(report, args.scenario, args.status)
    entry = build_entry(
        item,
        classification=args.classification,
        artifact=args.artifact,
        artifact_kind=args.artifact_kind,
        resolution=args.resolution,
        reason_contains=args.reason_contains,
    )
    if args.write_register:
        register_path = Path(args.register)
        register = load_json(register_path)
        merged = merge_entry(register, entry, args.replace_existing)
        write_json(register_path, merged)
    else:
        json.dump(entry, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
