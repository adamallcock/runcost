#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures"
REPORT_PATH = ROOT / "docs" / "internal" / "reports" / "fixture-coverage.md"
FIXTURE_PATHS = sorted(FIXTURE_DIR.glob("*.json"))

EXPECTED_LANGUAGES = ["python", "javascript", "go"]
ALLOWED_SCENARIOS = {
    "aggregation",
    "debug_trace",
    "discount",
    "framework_adapter",
    "long_context",
    "normalized_usage",
    "provider_reported",
    "raw_provider_response",
    "service_mode",
    "service_tier",
    "source_adapter",
    "source_priority",
    "strict_error",
    "warning",
}
SCENARIO_REQUIREMENTS = {
    "aggregation": "RC-AGGREGATION",
    "debug_trace": "RC-DEBUG-TRACE",
    "discount": "RC-DISCOUNT-POLICY",
    "framework_adapter": "RC-FRAMEWORK-ADAPTER",
    "long_context": "RC-LONG-CONTEXT",
    "normalized_usage": "RC-CALC-CORE",
    "provider_reported": "RC-PROVIDER-REPORTED-COST",
    "raw_provider_response": "RC-RAW-EXTRACTOR",
    "service_mode": "RC-SERVICE-MODE",
    "service_tier": "RC-SERVICE-TIER",
    "source_adapter": "RC-SOURCE-ADAPTER",
    "source_priority": "RC-SOURCE-PRIORITY",
    "strict_error": "RC-STRICT-MODE",
    "warning": "RC-WARNING-MODE",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def cost_ledger(fixture: dict[str, Any]) -> dict[str, Any]:
    return fixture.get("expected", {}).get("cost_ledger", {})


def expected_warnings(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    ledger = cost_ledger(fixture)
    if ledger:
        return list(ledger.get("warnings", []))
    error = fixture.get("expected", {}).get("error")
    return [error] if isinstance(error, dict) else []


def infer_provider_surface(fixture: dict[str, Any]) -> tuple[str, str]:
    ledger = cost_ledger(fixture)
    if ledger:
        return ledger["provider"], ledger["surface"]
    input_data = fixture["input"]
    usage = input_data.get("usage_ledger")
    if usage:
        return usage["provider"], usage["surface"]
    extract = input_data.get("extract")
    if extract:
        return extract.get("provider", "unknown"), extract.get("surface", "unknown")
    return "unknown", "unknown"


def infer_scenario(fixture: dict[str, Any]) -> str:
    name = fixture["name"]
    input_data = fixture["input"]
    if "debug_trace" in cost_ledger(fixture):
        return "debug_trace"
    if "error" in fixture.get("expected", {}):
        return "strict_error"
    if name.startswith("service-mode"):
        return "service_mode"
    if name.startswith("service-tier"):
        return "service_tier"
    if name.startswith("long-context"):
        return "long_context"
    if name.startswith("provider-reported"):
        return "provider_reported"
    if name.startswith("price-source"):
        return "source_priority"
    if "cost_ledgers" in input_data:
        return "aggregation"
    if "price_source" in input_data:
        return "source_adapter"
    if input_data.get("helper") or input_data.get("extract", {}).get("adapter"):
        return "framework_adapter"
    if "raw_response" in input_data:
        return "raw_provider_response"
    if name.startswith("discount"):
        return "discount"
    if expected_warnings(fixture):
        return "warning"
    return "normalized_usage"


def fixture_components(fixture: dict[str, Any]) -> set[str]:
    components: set[str] = set()
    usage = fixture["input"].get("usage_ledger")
    if usage:
        components.update(component["name"] for component in usage.get("components", []))
    ledger = cost_ledger(fixture)
    components.update(component["name"] for component in ledger.get("components", []))
    for card in fixture["input"].get("price_cards", []):
        components.update(component["usage_component"] for component in card.get("components", []))
    return components


def fixture_warning_codes(fixture: dict[str, Any]) -> set[str]:
    codes = {warning["code"] for warning in expected_warnings(fixture) if "code" in warning}
    error = fixture.get("expected", {}).get("error")
    if isinstance(error, dict) and "code" in error:
        codes.add(error["code"])
    return codes


def infer_tags(fixture: dict[str, Any], scenario: str) -> list[str]:
    name = fixture["name"]
    input_data = fixture["input"]
    tags = {scenario}
    if "cache" in name:
        tags.add("cache")
    if "reasoning" in name:
        tags.add("reasoning")
    if "alias" in name:
        tags.add("alias")
    if "tool" in name:
        tags.add("tool_pricing")
    if "multimodal" in name:
        tags.add("multimodal")
    if "stale" in name:
        tags.add("stale_price")
    if "effective-date" in name:
        tags.add("effective_date")
    if input_data.get("price_source"):
        tags.add(f"source:{input_data['price_source']['type']}")
    if input_data.get("helper"):
        tags.add(f"helper:{input_data['helper']}")
    adapter = input_data.get("extract", {}).get("adapter")
    if adapter:
        tags.add(f"adapter:{adapter}")
    tags.update(f"component:{component}" for component in sorted(fixture_components(fixture)))
    tags.update(f"warning:{code}" for code in sorted(fixture_warning_codes(fixture)))
    return sorted(tags)


def infer_expected_languages(fixture: dict[str, Any]) -> list[str]:
    helper = fixture["input"].get("helper")
    if helper == "langchain_callback":
        return ["python"]
    if helper == "vercel_ai_sdk_middleware":
        return ["javascript"]
    return EXPECTED_LANGUAGES


def infer_metadata(fixture: dict[str, Any]) -> dict[str, Any]:
    provider, surface = infer_provider_surface(fixture)
    scenario = infer_scenario(fixture)
    return {
        "requirement_ids": sorted({"RC-FIXTURE-CONFORMANCE", SCENARIO_REQUIREMENTS[scenario]}),
        "provider": provider,
        "surface": surface,
        "scenario": scenario,
        "tags": infer_tags(fixture, scenario),
        "expected_languages": infer_expected_languages(fixture),
    }


def fixture_with_metadata(fixture: dict[str, Any]) -> dict[str, Any]:
    updated = {
        "name": fixture["name"],
        "description": fixture["description"],
        "metadata": infer_metadata(fixture),
        "input": fixture["input"],
        "expected": fixture["expected"],
    }
    return updated


def validate_metadata(path: Path, fixture: dict[str, Any]) -> None:
    metadata = fixture.get("metadata")
    if not isinstance(metadata, dict):
        raise AssertionError(f"{path.name}: missing metadata object")
    required = {"requirement_ids", "provider", "surface", "scenario", "tags", "expected_languages"}
    missing = sorted(required - set(metadata))
    if missing:
        raise AssertionError(f"{path.name}: metadata missing {missing}")
    if metadata["scenario"] not in ALLOWED_SCENARIOS:
        raise AssertionError(f"{path.name}: unknown scenario {metadata['scenario']!r}")
    for key in ("requirement_ids", "tags", "expected_languages"):
        if not isinstance(metadata[key], list) or not metadata[key]:
            raise AssertionError(f"{path.name}: metadata.{key} must be a non-empty array")
    unknown_languages = sorted(set(metadata["expected_languages"]) - set(EXPECTED_LANGUAGES))
    if unknown_languages:
        raise AssertionError(f"{path.name}: unknown expected languages {unknown_languages}")
    provider, surface = infer_provider_surface(fixture)
    if metadata["provider"] != provider:
        raise AssertionError(f"{path.name}: metadata.provider {metadata['provider']!r} should be {provider!r}")
    if metadata["surface"] != surface:
        raise AssertionError(f"{path.name}: metadata.surface {metadata['surface']!r} should be {surface!r}")


def table(counter: Counter[str], columns: tuple[str, str]) -> list[str]:
    lines = [f"| {columns[0]} | {columns[1]} |", "|---|---:|"]
    for key, count in sorted(counter.items()):
        lines.append(f"| `{key}` | {count} |")
    if not counter:
        lines.append("| None | 0 |")
    return lines


def provider_surface_table(counter: Counter[tuple[str, str]]) -> list[str]:
    lines = ["| Provider | Surface | Fixtures |", "|---|---|---:|"]
    for (provider, surface), count in sorted(counter.items()):
        lines.append(f"| `{provider}` | `{surface}` | {count} |")
    return lines


def build_report(fixtures: list[dict[str, Any]]) -> str:
    scenario_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()
    provider_surface_counts: Counter[tuple[str, str]] = Counter()
    component_counts: Counter[str] = Counter()
    warning_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    framework_counts: Counter[str] = Counter()
    requirement_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()

    for fixture in fixtures:
        metadata = fixture["metadata"]
        scenario_counts[metadata["scenario"]] += 1
        provider_surface_counts[(metadata["provider"], metadata["surface"])] += 1
        language_counts.update(metadata["expected_languages"])
        requirement_counts.update(metadata["requirement_ids"])
        tag_counts.update(metadata["tags"])
        component_counts.update(fixture_components(fixture))
        warning_counts.update(fixture_warning_codes(fixture))
        source = fixture["input"].get("price_source")
        if source:
            source_counts[source["type"]] += 1
        helper = fixture["input"].get("helper")
        adapter = fixture["input"].get("extract", {}).get("adapter")
        if helper:
            framework_counts[helper] += 1
        elif adapter:
            framework_counts[adapter] += 1

    lines = [
        "---",
        "title: RunCost Fixture Coverage",
        "date: 2026-05-25",
        "type: report",
        "status: generated",
        "---",
        "",
        "# RunCost Fixture Coverage",
        "",
        "Generated by `python3 scripts/check_fixture_coverage.py --write-report`.",
        "",
        "This report reflects fixture-backed coverage only. Missing entries are not supported claims.",
        "",
        "## Summary",
        "",
        f"- Fixtures: {len(fixtures)}",
        f"- Providers: {len({fixture['metadata']['provider'] for fixture in fixtures})}",
        f"- Provider surfaces: {len(provider_surface_counts)}",
        f"- Usage components covered: {len(component_counts)}",
        f"- Warning/error codes covered: {len(warning_counts)}",
        f"- Requirement IDs covered: {len(requirement_counts)}",
        "",
        "## Expected Languages",
        "",
        *table(language_counts, ("Language", "Fixtures")),
        "",
        "## Scenarios",
        "",
        *table(scenario_counts, ("Scenario", "Fixtures")),
        "",
        "## Provider Surfaces",
        "",
        *provider_surface_table(provider_surface_counts),
        "",
        "## Usage Components",
        "",
        *table(component_counts, ("Component", "Fixtures")),
        "",
        "## Warning And Error Codes",
        "",
        *table(warning_counts, ("Code", "Fixtures")),
        "",
        "## Price Source Adapters",
        "",
        *table(source_counts, ("Source", "Fixtures")),
        "",
        "## Framework Adapters",
        "",
        *table(framework_counts, ("Adapter", "Fixtures")),
        "",
        "## Requirement IDs",
        "",
        *table(requirement_counts, ("Requirement", "Fixtures")),
        "",
        "## Tags",
        "",
        *table(tag_counts, ("Tag", "Fixtures")),
        "",
    ]
    return "\n".join(lines)


def load_fixtures() -> list[tuple[Path, dict[str, Any]]]:
    return [(path, load_json(path)) for path in FIXTURE_PATHS]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-metadata", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    loaded = load_fixtures()
    if args.write_metadata:
        for path, fixture in loaded:
            write_json(path, fixture_with_metadata(fixture))
        loaded = load_fixtures()

    fixtures = []
    for path, fixture in loaded:
        validate_metadata(path, fixture)
        fixtures.append(fixture)

    report = build_report(fixtures)
    if args.write_report:
        REPORT_PATH.write_text(report, encoding="utf-8")
    else:
        if not REPORT_PATH.exists():
            raise AssertionError(f"coverage report missing: {REPORT_PATH.relative_to(ROOT)}")
        current = REPORT_PATH.read_text(encoding="utf-8")
        if current != report:
            raise AssertionError(
                "fixture coverage report is stale; run "
                "`python3 scripts/check_fixture_coverage.py --write-report`"
            )

    print(f"Fixture coverage checks passed for {len(fixtures)} fixtures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
