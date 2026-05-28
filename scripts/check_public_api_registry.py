#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "fixtures" / "source-files" / "public-api-registry.json"
SCHEMA = ROOT / "schemas" / "public-api-registry.schema.json"
PYTHON_INIT = ROOT / "packages" / "python" / "runcost" / "__init__.py"
PYTHON_TYPES = ROOT / "packages" / "python" / "runcost" / "types.py"
PYTHON_GENERATED = ROOT / "packages" / "python" / "runcost" / "generated" / "taxonomy.py"
TYPESCRIPT_DECLARATIONS = ROOT / "packages" / "javascript" / "core" / "index.d.ts"
TYPESCRIPT_RUNTIME = ROOT / "packages" / "javascript" / "core" / "index.js"
TYPESCRIPT_GENERATED = ROOT / "packages" / "javascript" / "core" / "generated" / "taxonomy.d.ts"
GO_SOURCE = ROOT / "packages" / "go" / "ledger" / "ledger.go"
PARITY_MATRIX = ROOT / "docs" / "internal" / "notes" / "api-parity-matrix.md"
GENERATED_API_DOCS = ROOT / "docs" / "generated" / "public-api-registry.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_registry_shape(registry: dict[str, Any], schema: dict[str, Any]) -> None:
    assert_true(registry.get("schema_version") == schema["properties"]["schema_version"]["const"], "public API registry schema_version mismatch")
    allowed_categories = set(schema["$defs"]["capability"]["properties"]["category"]["enum"])
    allowed_statuses = set(schema["$defs"]["capability"]["properties"]["status"]["enum"])
    seen_ids: set[str] = set()
    for index, capability in enumerate(registry.get("capabilities", [])):
        location = f"capabilities[{index}]"
        capability_id = capability.get("id")
        assert_true(isinstance(capability_id, str) and re.match(r"^[a-z0-9_]+$", capability_id), f"{location}.id is invalid")
        assert_true(capability_id not in seen_ids, f"duplicate public API capability id: {capability_id}")
        seen_ids.add(capability_id)
        assert_true(capability.get("category") in allowed_categories, f"{capability_id}: invalid category")
        assert_true(capability.get("status") in allowed_statuses, f"{capability_id}: invalid status")
        assert_true(capability.get("evidence"), f"{capability_id}: missing evidence")
        for evidence in capability.get("evidence", []):
            assert_true((ROOT / evidence).exists(), f"{capability_id}: referenced evidence does not exist: {evidence}")
        languages = capability.get("languages")
        assert_true(isinstance(languages, dict), f"{capability_id}: languages must be an object")
        for language in ["python", "javascript", "go"]:
            api = languages.get(language)
            assert_true(isinstance(api, dict), f"{capability_id}: missing {language} API entry")
            assert_true(isinstance(api.get("runtime"), list), f"{capability_id}: {language}.runtime must be a list")
            assert_true(isinstance(api.get("types"), list), f"{capability_id}: {language}.types must be a list")


def check_python_name(name: str, kind: str, sources: dict[str, str]) -> None:
    if kind == "runtime":
        assert_true(name in sources["init"], f"Python runtime API missing from __init__.py: {name}")
        return
    assert_true(
        name in sources["types"] or name in sources["generated"],
        f"Python type API missing from types.py or generated taxonomy: {name}",
    )


def check_javascript_name(name: str, kind: str, sources: dict[str, str]) -> None:
    assert_true(name in sources["declarations"] or name in sources["generated"], f"TypeScript declaration missing: {name}")
    if kind == "runtime":
        assert_true(
            re.search(rf"export (async )?function {re.escape(name)}\b", sources["runtime"]) is not None,
            f"JavaScript runtime export missing: {name}",
        )


def check_go_name(name: str, kind: str, sources: dict[str, str]) -> None:
    pattern = rf"\bfunc {re.escape(name)}\b" if kind == "runtime" else rf"\btype {re.escape(name)}\b"
    assert_true(re.search(pattern, sources["source"]) is not None, f"Go {kind} API missing: {name}")


def check_api_exports(registry: dict[str, Any]) -> None:
    python_sources = {
        "init": text(PYTHON_INIT),
        "types": text(PYTHON_TYPES),
        "generated": text(PYTHON_GENERATED),
    }
    javascript_sources = {
        "declarations": text(TYPESCRIPT_DECLARATIONS),
        "generated": text(TYPESCRIPT_GENERATED),
        "runtime": text(TYPESCRIPT_RUNTIME),
    }
    go_sources = {"source": text(GO_SOURCE)}
    parity_matrix = text(PARITY_MATRIX)
    generated_api_docs = text(GENERATED_API_DOCS)
    assert_true("public-api-registry.json" in parity_matrix, "API parity matrix must link the public API registry")

    checkers = {
        "python": check_python_name,
        "javascript": check_javascript_name,
        "go": check_go_name,
    }
    sources = {
        "python": python_sources,
        "javascript": javascript_sources,
        "go": go_sources,
    }
    for capability in registry["capabilities"]:
        capability_id = capability["id"]
        assert_true(capability_id in generated_api_docs, f"generated public API docs missing capability id: {capability_id}")
        for language, api in capability["languages"].items():
            for kind in ["runtime", "types"]:
                for name in api[kind]:
                    checkers[language](name, kind, sources[language])
                    assert_true(name in generated_api_docs, f"generated public API docs missing public API name: {name}")


def main() -> int:
    registry = load_json(REGISTRY)
    schema = load_json(SCHEMA)
    check_registry_shape(registry, schema)
    check_api_exports(registry)
    print("Public API registry checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
