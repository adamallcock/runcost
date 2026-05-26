#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TAXONOMY = ROOT / "schemas" / "taxonomy.json"
PYTHON_TYPES = ROOT / "packages" / "python" / "runcost" / "types.py"
TYPESCRIPT_TYPES = ROOT / "packages" / "javascript" / "core" / "index.d.ts"
GO_CORE = ROOT / "packages" / "go" / "ledger" / "ledger.go"


def load_taxonomy() -> dict[str, Any]:
    return json.loads(TAXONOMY.read_text(encoding="utf-8"))


def assert_equal(actual: list[str], expected: list[str], label: str) -> None:
    if actual != expected:
        raise AssertionError(
            f"{label} drifted from schemas/taxonomy.json.\n"
            f"actual:   {actual}\n"
            f"expected: {expected}"
        )


def string_literals(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.Tuple):
        values: list[str] = []
        for item in node.elts:
            values.extend(string_literals(item))
        return values
    if isinstance(node, ast.Subscript):
        return string_literals(node.slice)
    return []


def python_literal_values(type_name: str) -> list[str]:
    tree = ast.parse(PYTHON_TYPES.read_text(encoding="utf-8"), filename=str(PYTHON_TYPES))
    for statement in tree.body:
        if not isinstance(statement, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == type_name for target in statement.targets):
            continue
        return string_literals(statement.value)
    raise AssertionError(f"missing Python type alias {type_name}")


def typescript_literal_values(type_name: str) -> list[str]:
    source = TYPESCRIPT_TYPES.read_text(encoding="utf-8")
    pattern = re.compile(rf"export type {re.escape(type_name)}\s*=([\s\S]*?);", re.MULTILINE)
    match = pattern.search(source)
    if not match:
        raise AssertionError(f"missing TypeScript type alias {type_name}")
    return re.findall(r'"([^"]+)"', match.group(1))


def go_string_slice(var_name: str) -> list[str]:
    source = GO_CORE.read_text(encoding="utf-8")
    pattern = re.compile(rf"var {re.escape(var_name)}\s*=\s*\[\]string\s*\{{([\s\S]*?)\}}", re.MULTILINE)
    match = pattern.search(source)
    if not match:
        raise AssertionError(f"missing Go string slice {var_name}")
    return re.findall(r'"([^"]+)"', match.group(1))


def main() -> int:
    taxonomy = load_taxonomy()
    checks = [
        ("component_names", "UsageComponentName"),
        ("units", "UsageUnit"),
        ("warning_codes", "WarningCode"),
        ("alias_resolution_values", "AliasResolution"),
        ("debug_decision_types", "DebugDecisionType"),
    ]
    for taxonomy_key, type_name in checks:
        expected = taxonomy[taxonomy_key]
        assert_equal(python_literal_values(type_name), expected, f"Python {type_name}")
        assert_equal(typescript_literal_values(type_name), expected, f"TypeScript {type_name}")

    assert_equal(go_string_slice("componentOrderNames"), taxonomy["component_names"], "Go componentOrderNames")

    print("Type taxonomy parity checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
