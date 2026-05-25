#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_json(relative: str) -> dict[str, Any]:
    with (ROOT / relative).open("r", encoding="utf-8") as file:
        return json.load(file)


def at(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        current = current[part]
    return current


def assert_unique(values: list[str], label: str) -> None:
    duplicates = sorted({value for value in values if values.count(value) > 1})
    if duplicates:
        raise AssertionError(f"{label} contains duplicate values: {duplicates}")


def assert_equal(actual: list[str], expected: list[str], label: str) -> None:
    if actual != expected:
        raise AssertionError(
            f"{label} drifted.\n"
            f"actual:   {actual}\n"
            f"expected: {expected}"
        )


def main() -> int:
    taxonomy = load_json("schemas/taxonomy.json")
    usage = load_json("schemas/usage-ledger.schema.json")
    price = load_json("schemas/price-card.schema.json")
    cost = load_json("schemas/cost-ledger.schema.json")
    fixture = load_json("schemas/fixture.schema.json")

    if taxonomy.get("schema_version") != "0.1":
        raise AssertionError("schemas/taxonomy.json must use schema_version 0.1")
    if taxonomy.get("status") != "locked":
        raise AssertionError("schemas/taxonomy.json must declare status locked")

    for key in [
        "component_names",
        "units",
        "warning_codes",
        "alias_resolution_values",
        "fixture_scenarios",
        "expected_languages",
        "debug_decision_types",
    ]:
        values = taxonomy.get(key)
        if not isinstance(values, list) or not values:
            raise AssertionError(f"taxonomy {key} must be a non-empty array")
        assert_unique(values, key)

    assert_equal(
        at(taxonomy, "component_names"),
        at(usage, "$defs.usage_component.properties.name.enum"),
        "usage component taxonomy",
    )
    assert_equal(
        at(taxonomy, "component_names"),
        at(price, "$defs.price_component.properties.usage_component.enum"),
        "price component taxonomy",
    )
    assert_equal(
        at(taxonomy, "units"),
        at(usage, "$defs.usage_component.properties.unit.enum"),
        "usage unit taxonomy",
    )
    assert_equal(
        at(taxonomy, "units"),
        at(price, "$defs.price_component.properties.unit.enum"),
        "price unit taxonomy",
    )
    assert_equal(
        at(taxonomy, "warning_codes"),
        at(cost, "$defs.warning.properties.code.enum"),
        "warning code taxonomy",
    )
    assert_equal(
        at(taxonomy, "alias_resolution_values"),
        at(usage, "properties.model.properties.alias_resolution.enum"),
        "alias resolution taxonomy",
    )
    assert_equal(
        at(taxonomy, "fixture_scenarios"),
        at(fixture, "properties.metadata.properties.scenario.enum"),
        "fixture scenario taxonomy",
    )
    assert_equal(
        at(taxonomy, "expected_languages"),
        at(fixture, "properties.metadata.properties.expected_languages.items.enum"),
        "expected language taxonomy",
    )
    assert_equal(
        at(taxonomy, "debug_decision_types"),
        at(cost, "$defs.debug_decision.properties.type.enum"),
        "debug decision taxonomy",
    )

    print("Schema taxonomy checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
