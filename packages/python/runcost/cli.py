from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .core import (
    aggregate_cost_ledgers,
    calculate_cost,
    from_response,
    price_cards_from_helicone,
    price_cards_from_json_file,
    price_cards_from_litellm,
    price_cards_from_llm_prices,
    price_cards_from_models_dev,
    price_cards_from_official_snapshot,
    price_cards_from_openrouter_models,
    price_cards_from_portkey,
    price_cards_from_source_cache,
    price_cards_from_user_pricing,
    price_cards_from_yaml_file,
)


def _load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_json(data: Any, output: str | None) -> None:
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    if output:
        Path(output).write_text(text, encoding="utf-8")
        return
    sys.stdout.write(text)


def _price_cards_from_source(source_type: str, data: Any, input_path: str | None = None) -> List[Dict[str, Any]]:
    if source_type == "llm-prices":
        return price_cards_from_llm_prices(data)
    if source_type == "litellm":
        return price_cards_from_litellm(data)
    if source_type == "openrouter-models":
        return price_cards_from_openrouter_models(data)
    if source_type == "models-dev":
        return price_cards_from_models_dev(data)
    if source_type == "official-snapshot":
        return price_cards_from_official_snapshot(data)
    if source_type == "portkey":
        return price_cards_from_portkey(data)
    if source_type == "source-cache":
        return price_cards_from_source_cache(data)
    if source_type == "user-pricing":
        return price_cards_from_user_pricing(data)
    if source_type == "helicone":
        return price_cards_from_helicone(data)
    if source_type == "json-file":
        if not input_path:
            raise ValueError("json-file source requires --input")
        return price_cards_from_json_file(Path(input_path), "user-pricing")
    if source_type == "yaml-file":
        if not input_path:
            raise ValueError("yaml-file source requires --input")
        return price_cards_from_yaml_file(Path(input_path), "user-pricing")
    raise ValueError(f"unsupported source type: {source_type}")


def _resolve_fixture_price_cards(fixture: Dict[str, Any]) -> List[Dict[str, Any]]:
    input_data = fixture.get("input", {})
    if "price_cards" in input_data:
        return input_data["price_cards"]
    source = input_data.get("price_source")
    if isinstance(source, dict):
        if "data" in source:
            return _price_cards_from_source(source["type"], source["data"])
        if "path" in source:
            return _price_cards_from_source(source["type"], _load_json(source["path"]), source["path"])
    return []


def _fixture_result(fixture: Dict[str, Any]) -> Dict[str, Any]:
    input_data = fixture["input"]
    options = {
        **input_data.get("options", {}),
        "mode": input_data.get("mode", "compatibility"),
    }
    price_cards = _resolve_fixture_price_cards(fixture)
    discount_policies = input_data.get("discount_policies", [])

    if "cost_ledgers" in input_data:
        return aggregate_cost_ledgers(input_data["cost_ledgers"], **options)
    if "raw_response" in input_data:
        return from_response(
            input_data["raw_response"],
            **{
                **input_data.get("extract", {}),
                **options,
                "price_cards": price_cards,
                "discount_policies": discount_policies,
            },
        )
    return calculate_cost(
        usage_ledger=input_data["usage_ledger"],
        price_cards=price_cards,
        discount_policies=discount_policies,
        **options,
    )


def _assert_subset(expected: Any, actual: Any, path: str = "$") -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            raise AssertionError(f"{path}: expected object, got {type(actual).__name__}")
        for key, value in expected.items():
            if key not in actual:
                raise AssertionError(f"{path}.{key}: missing key")
            _assert_subset(value, actual[key], f"{path}.{key}")
        return
    if isinstance(expected, list):
        if expected != actual:
            raise AssertionError(f"{path}: expected {expected!r}, got {actual!r}")
        return
    if expected != actual:
        raise AssertionError(f"{path}: expected {expected!r}, got {actual!r}")


def command_price_cards(args: argparse.Namespace) -> int:
    data = _load_json(args.input)
    price_cards = _price_cards_from_source(args.source_type, data, args.input)
    _write_json(price_cards, args.output)
    return 0


def command_fixture_check(args: argparse.Namespace) -> int:
    fixture = _load_json(args.fixture)
    actual = _fixture_result(fixture)
    expected = fixture.get("expected", {}).get("cost_ledger")
    if expected is not None:
        _assert_subset(expected, actual)
    _write_json(actual, args.output)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="runcost", description="RunCost package utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    price_cards = subparsers.add_parser("price-cards", help="Convert a pricing source JSON file to price cards.")
    price_cards.add_argument("--source-type", required=True)
    price_cards.add_argument("--input", required=True)
    price_cards.add_argument("--output")
    price_cards.set_defaults(func=command_price_cards)

    fixture_check = subparsers.add_parser("fixture-check", help="Calculate and optionally verify one RunCost fixture.")
    fixture_check.add_argument("fixture")
    fixture_check.add_argument("--output")
    fixture_check.set_defaults(func=command_fixture_check)

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        return args.func(args)
    except (AssertionError, ValueError, KeyError) as exc:
        print(f"runcost: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
