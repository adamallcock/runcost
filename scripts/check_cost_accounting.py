#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures"
REPORT_PATH = ROOT / "docs" / "internal" / "reports" / "2026-06-06-cost-accounting-coverage.md"
PUBLIC_API_REGISTRY = ROOT / "fixtures" / "source-files" / "public-api-registry.json"
TAXONOMY = ROOT / "schemas" / "taxonomy.json"
FIXTURE_PATHS = sorted(FIXTURE_DIR.glob("*.json"))

COMPONENT_WARNING_CODES = {
    "component_unpriced",
    "tool_component_unpriced",
    "source_capability_unsupported",
    "long_context_rule_missing",
}
LEDGER_LEVEL_NO_PRICE_WARNING_CODES = {
    "historical_price_missing",
    "price_not_found",
    "service_tier_unsupported",
    "unknown_model",
    "unknown_provider",
    "unknown_surface",
}
SOURCE_COMPONENT_REQUIREMENTS = {
    "helicone": {
        "input_cache_read_tokens",
        "output_reasoning_tokens",
        "web_search_units",
    },
    "json-file": {
        "input_cache_read_tokens",
        "output_reasoning_tokens",
        "web_search_units",
    },
    "litellm": {
        "input_cache_read_tokens",
        "input_cache_write_tokens",
        "output_reasoning_tokens",
    },
    "models-dev": {
        "input_cache_read_tokens",
        "input_cache_write_tokens",
        "output_reasoning_tokens",
    },
    "official-snapshot": {
        "input_cache_read_tokens",
        "input_cache_write_tokens",
        "output_reasoning_tokens",
        "web_search_units",
    },
    "openrouter-models": {
        "input_cache_read_tokens",
        "output_reasoning_tokens",
        "web_search_units",
    },
    "portkey": {
        "input_cache_read_tokens",
        "input_cache_write_tokens",
        "output_reasoning_tokens",
        "web_search_units",
    },
    "user-pricing": {
        "input_cache_read_tokens",
        "output_reasoning_tokens",
        "web_search_units",
    },
    "yaml-file": {
        "input_cache_read_tokens",
        "output_reasoning_tokens",
        "web_search_units",
    },
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def is_positive(value: Any) -> bool:
    return decimal(value) > 0


def component_tags(fixture: dict[str, Any]) -> set[str]:
    tags = fixture.get("metadata", {}).get("tags", [])
    prefix = "component:"
    return {tag[len(prefix) :] for tag in tags if tag.startswith(prefix)}


def usage_components(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    usage = fixture.get("input", {}).get("usage_ledger")
    if not usage:
        return []
    return [component for component in usage.get("components", []) if is_positive(component.get("quantity", "0"))]


def ledger_components(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    return [component for component in ledger.get("components", []) if is_positive(component.get("quantity", "0"))]


def component_key(component: dict[str, Any]) -> tuple[str, str]:
    return str(component.get("name", "")), str(component.get("unit", ""))


def warning_component_key(warning: dict[str, Any]) -> tuple[str, str] | None:
    metadata = warning.get("metadata") or {}
    component = metadata.get("component")
    unit = metadata.get("unit")
    if not component or not unit:
        return None
    return str(component), str(unit)


def ledger_has_ledger_level_no_price_warning(ledger: dict[str, Any]) -> bool:
    return any(warning.get("code") in LEDGER_LEVEL_NO_PRICE_WARNING_CODES for warning in ledger.get("warnings", []))


def component_treatments(ledger: dict[str, Any]) -> set[tuple[str, str]]:
    treatments = {component_key(component) for component in ledger_components(ledger)}
    for warning in ledger.get("warnings", []):
        if warning.get("code") not in COMPONENT_WARNING_CODES:
            continue
        key = warning_component_key(warning)
        if key:
            treatments.add(key)
    return treatments


def fixture_components(fixture: dict[str, Any]) -> set[str]:
    components = set(component_tags(fixture))
    usage = fixture.get("input", {}).get("usage_ledger") or {}
    components.update(component.get("name", "") for component in usage.get("components", []))
    ledger = fixture.get("expected", {}).get("cost_ledger") or {}
    components.update(component.get("name", "") for component in ledger.get("components", []))
    for warning in ledger.get("warnings", []):
        metadata = warning.get("metadata") or {}
        if metadata.get("component"):
            components.add(metadata["component"])
    for card in fixture.get("input", {}).get("price_cards", []):
        components.update(component.get("usage_component", "") for component in card.get("components", []))
    return {component for component in components if component}


def source_type(fixture: dict[str, Any]) -> str | None:
    source = fixture.get("input", {}).get("price_source")
    if not isinstance(source, dict):
        return None
    return source.get("type")


def check_component_warning_metadata(path: Path, fixture: dict[str, Any]) -> list[str]:
    errors = []
    ledger = fixture.get("expected", {}).get("cost_ledger") or {}
    for index, warning in enumerate(ledger.get("warnings", [])):
        if warning.get("code") not in COMPONENT_WARNING_CODES:
            continue
        metadata = warning.get("metadata") or {}
        for key in ("component", "unit"):
            if not metadata.get(key):
                errors.append(f"{path.name}: expected.cost_ledger.warnings[{index}].metadata.{key} is required for {warning.get('code')}")
    return errors


def check_normalized_usage_accounting(path: Path, fixture: dict[str, Any]) -> list[str]:
    errors = []
    ledger = fixture.get("expected", {}).get("cost_ledger")
    if not ledger:
        return errors
    if ledger_has_ledger_level_no_price_warning(ledger):
        return errors
    treatments = component_treatments(ledger)
    for component in usage_components(fixture):
        key = component_key(component)
        if key not in treatments:
            errors.append(
                f"{path.name}: nonzero usage component {key[0]} ({key[1]}) is neither priced nor explicitly warned"
            )
    return errors


def check_component_tags_accounted(path: Path, fixture: dict[str, Any]) -> list[str]:
    errors = []
    ledger = fixture.get("expected", {}).get("cost_ledger")
    if not ledger:
        return errors
    priced = {component["name"] for component in ledger_components(ledger)}
    warned = {
        (warning.get("metadata") or {}).get("component")
        for warning in ledger.get("warnings", [])
        if warning.get("code") in COMPONENT_WARNING_CODES
    }
    if ledger_has_ledger_level_no_price_warning(ledger):
        return errors
    for component in sorted(component_tags(fixture) - priced - warned):
        errors.append(f"{path.name}: metadata tag component:{component} is not priced or explicitly warned")
    return errors


def check_source_component_requirements(fixtures: list[dict[str, Any]]) -> list[str]:
    by_source: dict[str, set[str]] = defaultdict(set)
    for fixture in fixtures:
        fixture_source = source_type(fixture)
        if fixture_source:
            by_source[fixture_source].update(fixture_components(fixture))
    errors = []
    for fixture_source, required_components in sorted(SOURCE_COMPONENT_REQUIREMENTS.items()):
        missing = sorted(required_components - by_source.get(fixture_source, set()))
        if missing:
            errors.append(f"source adapter {fixture_source!r} lacks fixture accounting coverage for: {', '.join(missing)}")
    return errors


def check_public_api_evidence(registry: dict[str, Any], fixture_names: set[str]) -> list[str]:
    errors = []
    checked_categories = {"core", "provider_extractor", "framework_adapter", "source_adapter"}
    for capability in registry.get("capabilities", []):
        if capability.get("category") not in checked_categories:
            continue
        fixture_evidence = []
        for evidence in capability.get("evidence", []):
            evidence_path = Path(evidence)
            if evidence_path.parts[:1] != ("fixtures",):
                continue
            fixture_evidence.append(evidence_path.name)
            if evidence_path.name not in fixture_names:
                errors.append(f"{capability['id']}: fixture evidence missing from accounting scan: {evidence}")
        if not fixture_evidence:
            errors.append(f"{capability['id']}: checked public API capability has no fixture-backed accounting evidence")
    return errors


def table(counter: Counter[str], columns: tuple[str, str]) -> list[str]:
    lines = [f"| {columns[0]} | {columns[1]} |", "|---|---:|"]
    for key, count in sorted(counter.items()):
        lines.append(f"| `{key}` | {count} |")
    if not counter:
        lines.append("| None | 0 |")
    return lines


def source_component_table(source_components: dict[str, set[str]]) -> list[str]:
    lines = ["| Source | Components |", "|---|---|"]
    for source, components in sorted(source_components.items()):
        component_text = ", ".join(f"`{component}`" for component in sorted(components)) or "None"
        lines.append(f"| `{source}` | {component_text} |")
    return lines


def surface_component_table(surface_components: dict[tuple[str, str], set[str]]) -> list[str]:
    lines = ["| Provider | Surface | Components |", "|---|---|---|"]
    for (provider, surface), components in sorted(surface_components.items()):
        component_text = ", ".join(f"`{component}`" for component in sorted(components)) or "None"
        lines.append(f"| `{provider}` | `{surface}` | {component_text} |")
    return lines


def build_report(fixtures: list[dict[str, Any]], registry: dict[str, Any]) -> str:
    component_counts: Counter[str] = Counter()
    scenario_counts: Counter[str] = Counter()
    source_components: dict[str, set[str]] = defaultdict(set)
    surface_components: dict[tuple[str, str], set[str]] = defaultdict(set)
    public_api_categories: Counter[str] = Counter()

    for fixture in fixtures:
        metadata = fixture["metadata"]
        components = fixture_components(fixture)
        component_counts.update(components)
        scenario_counts[metadata["scenario"]] += 1
        surface_components[(metadata["provider"], metadata["surface"])].update(components)
        fixture_source = source_type(fixture)
        if fixture_source:
            source_components[fixture_source].update(components)

    for capability in registry.get("capabilities", []):
        public_api_categories[capability.get("category", "unknown")] += 1

    lines = [
        "---",
        "title: RunCost Cost Accounting Coverage",
        "date: 2026-06-06",
        "type: report",
        "status: generated",
        "---",
        "",
        "# RunCost Cost Accounting Coverage",
        "",
        "Generated by `python3 scripts/check_cost_accounting.py --write-report`.",
        "",
        "This report tracks fixture-backed safeguards against silent nonzero usage-component omissions.",
        "",
        "## Summary",
        "",
        f"- Fixtures scanned: {len(fixtures)}",
        f"- Public API capabilities scanned: {len(registry.get('capabilities', []))}",
        f"- Provider/surface component rows: {len(surface_components)}",
        f"- Price-source component rows: {len(source_components)}",
        "",
        "## Scenarios",
        "",
        *table(scenario_counts, ("Scenario", "Fixtures")),
        "",
        "## Components",
        "",
        *table(component_counts, ("Component", "Fixtures")),
        "",
        "## Price Source Component Coverage",
        "",
        *source_component_table(source_components),
        "",
        "## Provider Surface Component Coverage",
        "",
        *surface_component_table(surface_components),
        "",
        "## Public API Categories",
        "",
        *table(public_api_categories, ("Category", "Capabilities")),
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    loaded = [(path, load_json(path)) for path in FIXTURE_PATHS]
    fixtures = [fixture for _, fixture in loaded]
    registry = load_json(PUBLIC_API_REGISTRY)
    taxonomy = load_json(TAXONOMY)

    if "source_capability_unsupported" not in taxonomy["warning_metadata_required_keys"]:
        raise AssertionError("taxonomy missing warning metadata keys for source_capability_unsupported")

    errors = []
    for path, fixture in loaded:
        errors.extend(check_component_warning_metadata(path, fixture))
        errors.extend(check_normalized_usage_accounting(path, fixture))
        errors.extend(check_component_tags_accounted(path, fixture))
    errors.extend(check_source_component_requirements(fixtures))
    errors.extend(check_public_api_evidence(registry, {path.name for path, _ in loaded}))

    report = build_report(fixtures, registry)
    if args.write_report:
        REPORT_PATH.write_text(report, encoding="utf-8")
    elif not REPORT_PATH.exists():
        errors.append(f"cost accounting coverage report missing: {REPORT_PATH.relative_to(ROOT)}")
    elif REPORT_PATH.read_text(encoding="utf-8") != report:
        errors.append(
            "cost accounting coverage report is stale; run "
            "`python3 scripts/check_cost_accounting.py --write-report`"
        )

    if errors:
        raise AssertionError("\n".join(errors))

    print(f"Cost accounting checks passed for {len(fixtures)} fixtures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
