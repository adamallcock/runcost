#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "fixtures" / "source-files" / "public-api-registry.json"
CORE = ROOT / "packages" / "python" / "runcost" / "core.py"
TYPES = ROOT / "packages" / "python" / "runcost" / "types.py"
GENERATED_TAXONOMY = ROOT / "packages" / "python" / "runcost" / "generated" / "taxonomy.py"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def public_python_runtime_names() -> set[str]:
    registry = load_json(REGISTRY)
    names: set[str] = set()
    for capability in registry["capabilities"]:
        names.update(capability["languages"]["python"]["runtime"])
    return names


def public_python_type_names() -> set[str]:
    registry = load_json(REGISTRY)
    names: set[str] = set()
    for capability in registry["capabilities"]:
        names.update(capability["languages"]["python"]["types"])
    return names


def module_defs(path: Path) -> dict[str, ast.AST]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    definitions: dict[str, ast.AST] = {}
    for statement in tree.body:
        if isinstance(statement, (ast.FunctionDef, ast.ClassDef, ast.Assign)):
            if isinstance(statement, ast.Assign):
                for target in statement.targets:
                    if isinstance(target, ast.Name):
                        definitions[target.id] = statement
            else:
                definitions[statement.name] = statement
    return definitions


def check_function_annotations(name: str, node: ast.FunctionDef) -> None:
    if node.returns is None:
        raise AssertionError(f"Python public function {name} is missing a return annotation")
    for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]:
        if arg.arg == "self":
            continue
        if arg.annotation is None:
            raise AssertionError(f"Python public function {name} parameter {arg.arg} is missing an annotation")
    if node.args.vararg and node.args.vararg.annotation is None:
        raise AssertionError(f"Python public function {name} *{node.args.vararg.arg} is missing an annotation")
    if node.args.kwarg and node.args.kwarg.annotation is None:
        raise AssertionError(f"Python public function {name} **{node.args.kwarg.arg} is missing an annotation")


def main() -> int:
    core_defs = module_defs(CORE)
    type_defs = {**module_defs(TYPES), **module_defs(GENERATED_TAXONOMY)}

    for name in sorted(public_python_runtime_names()):
        node = core_defs.get(name)
        if node is None:
            raise AssertionError(f"Python public runtime API {name} is missing from core.py")
        if isinstance(node, ast.FunctionDef):
            check_function_annotations(name, node)

    for name in sorted(public_python_type_names()):
        if name not in type_defs:
            raise AssertionError(f"Python public type API {name} is missing from types.py or generated taxonomy")

    print("Python public type surface checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
