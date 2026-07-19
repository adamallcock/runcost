#!/usr/bin/env python3
"""Generate the public machine-readable and rendered conformance inventory."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
JSON_OUTPUT = ROOT / "docs" / "generated" / "conformance-report.json"
MARKDOWN_OUTPUT = ROOT / "docs" / "generated" / "conformance-report.md"
UNSUPPORTED_WARNING_CODES = {
    "component_unpriced",
    "source_capability_unsupported",
    "tool_component_unpriced",
    "unknown_surface",
}


def outcome(expected: dict[str, Any]) -> tuple[str, list[str]]:
    if not isinstance(expected, dict):
        return "preserved", []
    if "error" in expected:
        return "warned", [str(expected["error"].get("code", "expected_error"))]
    ledger = expected.get("cost_ledger", expected)
    warnings = ledger.get("warnings", []) if isinstance(ledger, dict) else []
    codes = sorted({str(warning.get("code")) for warning in warnings if isinstance(warning, dict)})
    if any(code in UNSUPPORTED_WARNING_CODES for code in codes):
        return "unsupported", codes
    if codes:
        return "warned", codes
    return "preserved", []


def standard_cases() -> list[dict[str, Any]]:
    cases = []
    for path in sorted((ROOT / "fixtures").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        languages = data.get("metadata", {}).get("expected_languages", ["python", "javascript", "go"])
        status, warnings = outcome(data.get("expected", {}))
        cases.append(
            {
                "id": data.get("name", path.stem),
                "fixture": str(path.relative_to(ROOT)),
                "provider": data.get("metadata", {}).get("provider", "unknown"),
                "surface": data.get("metadata", {}).get("surface", "unknown"),
                "scenario": data.get("metadata", {}).get("scenario", "unknown"),
                "outcome": status,
                "warning_codes": warnings,
                "languages": {language: status if language in languages else "not_tested" for language in ("python", "javascript", "go")},
            }
        )
    return cases


def expansion_cases() -> list[dict[str, Any]]:
    path = ROOT / "fixtures" / "expansion" / "cases.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = []
    for raw in data["cases"]:
        languages = raw.get("expected_languages", ["python", "javascript", "go"])
        status, warnings = outcome(raw.get("expected", {}))
        input_data = raw.get("input", {})
        provider = input_data.get("provider") or input_data.get("batch_provider") or "cross-provider"
        cases.append(
            {
                "id": raw["id"],
                "fixture": str(path.relative_to(ROOT)),
                "provider": provider,
                "surface": input_data.get("surface", raw["operation"]),
                "scenario": raw["operation"],
                "outcome": status,
                "warning_codes": warnings,
                "languages": {language: status if language in languages else "not_tested" for language in ("python", "javascript", "go")},
            }
        )
    return cases


def build_report() -> dict[str, Any]:
    cases = standard_cases() + expansion_cases()
    counts = Counter(case["outcome"] for case in cases)
    language_counts = {
        language: dict(sorted(Counter(case["languages"][language] for case in cases).items()))
        for language in ("python", "javascript", "go")
    }
    return {
        "schema_version": "0.1",
        "generated_on": "2026-07-18",
        "methodology": {
            "preserved": "The expected billing semantics are asserted without warning.",
            "warned": "The implementation preserves a visible caveat or expected error.",
            "unsupported": "The implementation explicitly reports that a billing semantic is not priced or supported.",
            "not_tested": "The case does not request that language implementation.",
            "scope": "RunCost behavior only; this report makes no claim about competing calculators.",
        },
        "summary": {"case_count": len(cases), "outcomes": dict(sorted(counts.items())), "languages": language_counts},
        "cases": cases,
    }


def markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "---",
        "title: RunCost Conformance Report",
        "date: 2026-07-18",
        "type: report",
        "status: generated",
        "---",
        "",
        "# RunCost Conformance Report",
        "",
        "This report describes RunCost's own fixture-backed behavior. It does not score or infer the behavior of competitors.",
        "",
        "## Outcome definitions",
        "",
    ]
    for name in ("preserved", "warned", "unsupported", "not_tested"):
        lines.append(f"- **{name.replace('_', ' ').title()}:** {report['methodology'][name]}")
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"{summary['case_count']} cases are inventoried.",
            "",
            "| Outcome | Cases |",
            "| --- | ---: |",
        ]
    )
    for name in ("preserved", "warned", "unsupported", "not_tested"):
        lines.append(f"| {name.replace('_', ' ').title()} | {summary['outcomes'].get(name, 0)} |")
    lines.extend(["", "## Cases", "", "| Case | Provider | Surface or operation | Outcome | Languages |", "| --- | --- | --- | --- | --- |"])
    for case in report["cases"]:
        language_text = ", ".join(f"{name}: {status}" for name, status in case["languages"].items())
        lines.append(f"| `{case['id']}` | {case['provider']} | `{case['surface']}` | {case['outcome']} | {language_text} |")
    lines.extend(["", "The canonical machine-readable form is [`conformance-report.json`](./conformance-report.json).", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = build_report()
    encoded_json = json.dumps(report, indent=2, sort_keys=True) + "\n"
    encoded_markdown = markdown(report)
    if args.check:
        if not JSON_OUTPUT.is_file() or JSON_OUTPUT.read_text(encoding="utf-8") != encoded_json:
            raise SystemExit("conformance-report.json is stale")
        if not MARKDOWN_OUTPUT.is_file() or MARKDOWN_OUTPUT.read_text(encoding="utf-8") != encoded_markdown:
            raise SystemExit("conformance-report.md is stale")
        print("generated conformance reports are current")
        return 0
    JSON_OUTPUT.write_text(encoded_json, encoding="utf-8")
    MARKDOWN_OUTPUT.write_text(encoded_markdown, encoding="utf-8")
    print(f"Wrote {report['summary']['case_count']} conformance cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
