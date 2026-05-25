#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
DEFAULT_LANGUAGES = ["python", "javascript", "go"]
SCENARIOS = [
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
]


def ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def load_json_value(value: str | None) -> Any:
    if value is None:
        return None
    candidate = value[1:] if value.startswith("@") else value
    path = Path(candidate)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON or missing path for {value!r}: {exc}") from exc


def validate_name(name: str) -> None:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise SystemExit("Fixture name must be lowercase kebab-case, for example openai-responses-basic")


def build_fixture(
    *,
    name: str,
    description: str,
    requirement_ids: list[str],
    provider: str,
    surface: str,
    scenario: str,
    tags: list[str],
    expected_languages: list[str],
    input_data: dict[str, Any],
    expected: dict[str, Any],
) -> dict[str, Any]:
    validate_name(name)
    return {
        "name": name,
        "description": description,
        "metadata": {
            "requirement_ids": ordered_unique(requirement_ids),
            "provider": provider,
            "surface": surface,
            "scenario": scenario,
            "tags": ordered_unique([scenario, *tags]),
            "expected_languages": expected_languages,
        },
        "input": input_data,
        "expected": expected,
    }


def example_normalized_usage_fixture() -> dict[str, Any]:
    usage_ledger = {
        "schema_version": "0.1",
        "provider": "openai",
        "surface": "openai.responses",
        "model": {
            "requested": "gpt-5-nano",
            "returned": "gpt-5-nano",
            "billed": "gpt-5-nano",
            "alias_resolution": "none",
        },
        "components": [
            {
                "name": "input_uncached_tokens",
                "quantity": "1",
                "unit": "token",
                "source_path": "$.usage.input_tokens",
            }
        ],
        "raw_usage": {
            "input_tokens": 1,
            "total_tokens": 1,
        },
    }
    price_card = {
        "schema_version": "0.1",
        "id": "openai:gpt-5-nano:fixture-generator",
        "provider": "openai",
        "surface": "openai.responses",
        "model": "gpt-5-nano",
        "components": [
            {
                "usage_component": "input_uncached_tokens",
                "unit": "token",
                "price": {
                    "amount": "1",
                    "currency": "USD",
                    "per": "1000000",
                },
            }
        ],
        "source": {
            "name": "fixture-generator",
            "retrieved_at": "2026-05-25T00:00:00Z",
        },
    }
    cost_ledger = {
        "schema_version": "0.1",
        "provider": "openai",
        "surface": "openai.responses",
        "model": {
            "requested": "gpt-5-nano",
            "returned": "gpt-5-nano",
            "billed": "gpt-5-nano",
            "alias_resolution": "none",
        },
        "currency": "USD",
        "components": [
            {
                "name": "input_uncached_tokens",
                "quantity": "1",
                "unit": "token",
                "unit_price": "0.000001",
                "cost": "0.000001",
                "price_card_id": "openai:gpt-5-nano:fixture-generator",
                "discount_eligible": True,
            }
        ],
        "total": "0.000001",
        "price_sources": [
            {
                "name": "fixture-generator",
                "retrieved_at": "2026-05-25T00:00:00Z",
            }
        ],
        "applied_discounts": [],
        "warnings": [],
    }
    return build_fixture(
        name="fixture-generator-normalized-usage",
        description="Generated smoke fixture for normalized usage fixture scaffolding.",
        requirement_ids=["RC-FIXTURE-CONFORMANCE"],
        provider="openai",
        surface="openai.responses",
        scenario="normalized_usage",
        tags=["component:input_uncached_tokens", "generated"],
        expected_languages=DEFAULT_LANGUAGES,
        input_data={"usage_ledger": usage_ledger, "price_cards": [price_card]},
        expected={"cost_ledger": cost_ledger},
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create schema-shaped RunCost fixture JSON.")
    parser.add_argument("--example", choices=["normalized_usage"], help="Emit a complete example fixture.")
    parser.add_argument("--name", help="Fixture name in lowercase kebab-case.")
    parser.add_argument("--description", help="Human-readable fixture description.")
    parser.add_argument("--requirement-id", action="append", dest="requirement_ids", default=[])
    parser.add_argument("--provider", help="Provider metadata value, for example openai.")
    parser.add_argument("--surface", help="Surface metadata value, for example openai.responses.")
    parser.add_argument("--scenario", choices=SCENARIOS)
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--language", action="append", choices=DEFAULT_LANGUAGES, default=[])
    parser.add_argument("--input-json", help="Full input object as JSON or @path.")
    parser.add_argument("--expected-json", help="Full expected object as JSON or @path.")
    parser.add_argument("--usage-ledger-json", help="input.usage_ledger as JSON or @path.")
    parser.add_argument("--raw-response-json", help="input.raw_response as JSON or @path.")
    parser.add_argument("--price-cards-json", help="input.price_cards as JSON array or @path.")
    parser.add_argument("--price-source-json", help="input.price_source as JSON object or @path.")
    parser.add_argument("--discount-policies-json", help="input.discount_policies as JSON array or @path.")
    parser.add_argument("--options-json", help="input.options as JSON object or @path.")
    parser.add_argument("--extract-json", help="input.extract as JSON object or @path.")
    parser.add_argument("--helper", help="input.helper value for one-call helper fixtures.")
    parser.add_argument("--mode", help="input.mode value, for example compatibility or strict.")
    parser.add_argument("--expected-cost-ledger-json", help="expected.cost_ledger as JSON or @path.")
    parser.add_argument("--expected-error-json", help="expected.error as JSON or @path.")
    parser.add_argument("--write", help="Write path. If a directory is supplied, writes <name>.json there.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing --write target.")
    return parser.parse_args()


def fixture_from_args(args: argparse.Namespace) -> dict[str, Any]:
    if args.example == "normalized_usage":
        return example_normalized_usage_fixture()
    required = {
        "--name": args.name,
        "--description": args.description,
        "--provider": args.provider,
        "--surface": args.surface,
        "--scenario": args.scenario,
    }
    missing = [flag for flag, value in required.items() if not value]
    if missing:
        raise SystemExit(f"Missing required arguments: {', '.join(missing)}")
    if not args.requirement_ids:
        raise SystemExit("At least one --requirement-id is required")

    input_data = load_json_value(args.input_json) or {}
    if not isinstance(input_data, dict):
        raise SystemExit("--input-json must be a JSON object")
    for key, value in [
        ("usage_ledger", args.usage_ledger_json),
        ("raw_response", args.raw_response_json),
        ("price_cards", args.price_cards_json),
        ("price_source", args.price_source_json),
        ("discount_policies", args.discount_policies_json),
        ("options", args.options_json),
        ("extract", args.extract_json),
    ]:
        loaded = load_json_value(value)
        if loaded is not None:
            input_data[key] = loaded
    if args.helper:
        input_data["helper"] = args.helper
    if args.mode:
        input_data["mode"] = args.mode

    expected = load_json_value(args.expected_json) or {}
    if not isinstance(expected, dict):
        raise SystemExit("--expected-json must be a JSON object")
    expected_cost_ledger = load_json_value(args.expected_cost_ledger_json)
    expected_error = load_json_value(args.expected_error_json)
    if expected_cost_ledger is not None:
        expected["cost_ledger"] = expected_cost_ledger
    if expected_error is not None:
        expected["error"] = expected_error

    return build_fixture(
        name=args.name,
        description=args.description,
        requirement_ids=args.requirement_ids,
        provider=args.provider,
        surface=args.surface,
        scenario=args.scenario,
        tags=args.tag,
        expected_languages=args.language or DEFAULT_LANGUAGES,
        input_data=input_data,
        expected=expected,
    )


def write_or_print(fixture: dict[str, Any], destination: str | None, force: bool) -> Path | None:
    output = json.dumps(fixture, indent=2) + "\n"
    if not destination:
        sys.stdout.write(output)
        return None
    path = Path(destination)
    if path.is_dir():
        path = path / f"{fixture['name']}.json"
    if path.exists() and not force:
        raise SystemExit(f"Refusing to overwrite existing file without --force: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(output, encoding="utf-8")
    return path


def main() -> int:
    args = parse_args()
    fixture = fixture_from_args(args)
    write_or_print(fixture, args.write, args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
