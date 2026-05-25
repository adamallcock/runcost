#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "LICENSE",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "docs/2026-05-25-release-process.md",
    ".github/workflows/release.yml",
]


def read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def read_toml(relative: str) -> dict:
    return tomllib.loads((ROOT / relative).read_text(encoding="utf-8"))


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check_required_files() -> None:
    for relative in REQUIRED_FILES:
        assert_true((ROOT / relative).exists(), f"missing release readiness file: {relative}")


def check_versions_and_license() -> None:
    root_package = read_json("package.json")
    js_package = read_json("packages/javascript/core/package.json")
    pyproject = read_toml("pyproject.toml")
    python_project = pyproject["project"]

    version = root_package["version"]
    assert_true(js_package["version"] == version, "JavaScript package version must match root package version")
    assert_true(python_project["version"] == version, "Python package version must match root package version")
    expected_version = os.environ.get("EXPECTED_VERSION")
    if expected_version:
        assert_true(version == expected_version, f"package version {version} must match EXPECTED_VERSION {expected_version}")

    assert_true(js_package.get("license") == "MIT", "JavaScript package must declare MIT license")
    license_value = python_project.get("license")
    assert_true(
        license_value == {"text": "MIT"} or license_value == "MIT",
        "Python package must declare MIT license",
    )
    assert_true((ROOT / "LICENSE").read_text(encoding="utf-8").startswith("MIT License"), "LICENSE must be MIT")

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert_true("## Unreleased" in changelog, "CHANGELOG.md must include Unreleased section")
    assert_true(f"## {version}" in changelog, f"CHANGELOG.md must include current version {version}")


def check_release_workflow() -> None:
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    required_snippets = [
        "workflow_dispatch:",
        "EXPECTED_VERSION: ${{ inputs.version }}",
        "npm run check:release",
        "python3 -m build",
        "npm pack ./packages/javascript/core",
        "id-token: write",
        "pypa/gh-action-pypi-publish@release/v1",
        "npm publish --provenance --access public",
        "environment: release",
    ]
    for snippet in required_snippets:
        assert_true(snippet in workflow, f"release workflow missing {snippet!r}")


def check_release_docs() -> None:
    release_doc = (ROOT / "docs/2026-05-25-release-process.md").read_text(encoding="utf-8")
    for phrase in [
        "trusted publishing",
        "Go module",
        "semantic version",
        "PyPI",
        "npm",
        "provenance",
    ]:
        assert_true(re.search(re.escape(phrase), release_doc, re.IGNORECASE), f"release process missing {phrase}")

    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert_true("fixture" in contributing.lower(), "CONTRIBUTING.md must describe fixture-first workflow")
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert_true("OIDC" in security, "SECURITY.md must mention OIDC publishing")


def main() -> int:
    check_required_files()
    check_versions_and_license()
    check_release_workflow()
    check_release_docs()
    print("Release readiness checks passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"Release readiness check failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
