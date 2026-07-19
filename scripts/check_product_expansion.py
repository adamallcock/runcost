#!/usr/bin/env python3
"""Run shared product-expansion conformance cases in Python and JavaScript."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "expansion" / "cases.json"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "packages" / "python"))

from runcost import (  # noqa: E402
    attach_price_resolution,
    estimate_cost,
    evaluate_budget,
    from_batch_results,
    from_otel_genai_span,
    from_response,
    price_cards_from_genai_prices,
    reconcile_cost,
    usage_ledger_from_otel_genai_span,
)
from scripts.check_fixtures import validate_schema  # noqa: E402

SCHEMAS = {
    name: json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
    for name, filename in {
        "batch": "batch-ledger.schema.json",
        "budget": "budget-evaluation.schema.json",
        "cost": "cost-ledger.schema.json",
        "price": "price-card.schema.json",
        "reconciliation": "reconciliation.schema.json",
        "usage": "usage-ledger.schema.json",
    }.items()
}


def assert_subset(expected: Any, actual: Any, path: str = "$") -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            raise AssertionError(f"{path}: expected object, got {type(actual).__name__}")
        for key, value in expected.items():
            if key not in actual:
                raise AssertionError(f"{path}.{key}: missing")
            assert_subset(value, actual[key], f"{path}.{key}")
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise AssertionError(f"{path}: expected {len(expected)} items, got {len(actual) if isinstance(actual, list) else type(actual).__name__}")
        for index, value in enumerate(expected):
            assert_subset(value, actual[index], f"{path}[{index}]")
        return
    if expected != actual:
        raise AssertionError(f"{path}: expected {expected!r}, got {actual!r}")


def resolve_input(raw: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    value = dict(raw)
    reference = value.pop("price_cards_ref", None)
    if reference:
        value["price_cards"] = fixture["price_card_sets"][reference]
    return value


def run_python_case(case: dict[str, Any], fixture: dict[str, Any]) -> Any:
    value = resolve_input(case["input"], fixture)
    operation = case["operation"]
    if operation == "from_response":
        response = value.pop("response")
        return from_response(response, **value)
    if operation == "from_batch_results":
        items = value.pop("items")
        return from_batch_results(items, **value)
    if operation == "price_cards_from_genai_prices":
        data = value.pop("data")
        return price_cards_from_genai_prices(data, **value)
    if operation == "usage_ledger_from_otel":
        span = value.pop("span")
        return usage_ledger_from_otel_genai_span(span, **value)
    if operation == "from_otel":
        span = value.pop("span")
        return from_otel_genai_span(span, **value)
    if operation == "estimate_cost":
        return estimate_cost(**value)
    if operation == "attach_price_resolution":
        return attach_price_resolution(value["ledger"], value["resolution"])
    if operation == "evaluate_budget":
        total = value.pop("ledger_or_total")
        return evaluate_budget(total, **value)
    if operation == "reconcile_cost":
        total = value.pop("ledger_or_total")
        reported = value.pop("reported_total")
        return reconcile_cost(total, reported, **value)
    raise AssertionError(f"unsupported operation: {operation}")


def validate_result(case: dict[str, Any], result: Any, language: str) -> None:
    operation = case["operation"]
    path = f"{language}:{case['id']}"
    if operation == "from_batch_results":
        validate_schema(result, SCHEMAS["batch"], path=path)
    elif operation in {"from_response", "from_otel", "estimate_cost", "attach_price_resolution"}:
        validate_schema(result, SCHEMAS["cost"], path=path)
    elif operation == "usage_ledger_from_otel":
        validate_schema(result, SCHEMAS["usage"], path=path)
    elif operation == "price_cards_from_genai_prices":
        for index, price_card in enumerate(result):
            validate_schema(price_card, SCHEMAS["price"], path=f"{path}[{index}]")
    elif operation == "evaluate_budget":
        validate_schema(result, SCHEMAS["budget"], path=path)
    elif operation == "reconcile_cost":
        validate_schema(result, SCHEMAS["reconciliation"], path=path)


def check_python_edges() -> None:
    empty = from_batch_results([], provider="openai")
    if empty["summary"] != {"total": 0, "succeeded": 0, "failed": 0, "pending": 0, "total_cost": "0"}:
        raise AssertionError(f"empty batch summary is unstable: {empty['summary']}")
    if empty["warnings"]:
        raise AssertionError("empty batch must not emit failure or pending warnings")

    try:
        from_batch_results([], provider="unsupported")
    except ValueError as exc:
        if "unsupported batch provider" not in str(exc):
            raise
    else:
        raise AssertionError("unsupported empty batch provider was accepted")

    if evaluate_budget("0", budget="0")["status"] != "within_budget":
        raise AssertionError("an unspent zero budget must remain within budget")
    for kwargs, message in [
        ({"budget": "-1"}, "budget must be non-negative"),
        ({"budget": "1", "warning_threshold": "1.1"}, "warning_threshold must be between 0 and 1"),
    ]:
        try:
            evaluate_budget("0", **kwargs)
        except ValueError as exc:
            if message not in str(exc):
                raise
        else:
            raise AssertionError(f"invalid budget policy was accepted: {kwargs}")
    try:
        reconcile_cost("1", "1", tolerance="-0.01")
    except ValueError as exc:
        if "tolerance must be non-negative" not in str(exc):
            raise
    else:
        raise AssertionError("negative reconciliation tolerance was accepted")

    unknown = from_response({"unexpected": True})
    if [warning.get("code") for warning in unknown.get("warnings", [])] != ["unknown_surface"]:
        raise AssertionError(f"ambiguous response did not preserve unknown_surface: {unknown}")

    duplicate_cards = price_cards_from_genai_prices(
        {
            "providers": [
                {
                    "id": "duplicate-fixture",
                    "models": [
                        {
                            "id": "model",
                            "prices": [
                                {"constraint": {"start_date": "2026-01-01"}, "prices": {"input_mtok": "1"}},
                                {"constraint": {"start_date": "2026-01-01"}, "prices": {"input_mtok": "2"}},
                            ],
                        }
                    ],
                }
            ]
        }
    )
    ids = [card["id"] for card in duplicate_cards]
    if len(ids) != 2 or len(set(ids)) != 2:
        raise AssertionError(f"genai-prices duplicate IDs were not disambiguated: {ids}")


def main() -> int:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if fixture.get("schema_version") != "0.1" or not isinstance(fixture.get("price_card_sets"), dict) or not isinstance(fixture.get("cases"), list):
        raise AssertionError("expansion fixture envelope is invalid")
    for set_name, price_cards in fixture["price_card_sets"].items():
        for index, price_card in enumerate(price_cards):
            validate_schema(price_card, SCHEMAS["price"], path=f"price_card_sets.{set_name}[{index}]")
    check_python_edges()
    python_results = {}
    for case in fixture["cases"]:
        if "python" not in case.get("expected_languages", ["python", "javascript", "go"]):
            continue
        result = run_python_case(case, fixture)
        assert_subset(case["expected"], result, f"python:{case['id']}")
        validate_result(case, result, "python")
        python_results[case["id"]] = result

    completed = subprocess.run(
        ["node", "scripts/check_product_expansion.mjs", "--json"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    javascript_results = json.loads(completed.stdout)
    for case in fixture["cases"]:
        if "javascript" not in case.get("expected_languages", ["python", "javascript", "go"]):
            continue
        assert_subset(case["expected"], javascript_results[case["id"]], f"javascript:{case['id']}")
        validate_result(case, javascript_results[case["id"]], "javascript")
        if case["id"] in python_results and javascript_results[case["id"]] != python_results[case["id"]]:
            raise AssertionError(f"{case['id']}: Python and JavaScript outputs differ")
    print(f"product expansion conformance passed ({len(fixture['cases'])} cases; Python/JavaScript parity)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
