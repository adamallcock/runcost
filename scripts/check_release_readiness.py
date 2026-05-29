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
    "CODE_OF_CONDUCT.md",
    "SUPPORT.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/ISSUE_TEMPLATE/price_source_update.yml",
    ".github/CODEOWNERS",
    ".github/dependabot.yml",
    "docs/internal/process/release-process.md",
    "docs/internal/process/2026-05-26-source-data-update-process.md",
    "docs/internal/process/2026-05-28-public-github-readiness.md",
    "docs/internal/reports/2026-05-28-default-price-catalog-review.md",
    "docs/reference/price-data-strategy.md",
    "docs/guides/2026-05-26-migration-from-hand-written-formulas.md",
    ".github/workflows/release.yml",
    "scripts/check_release_dry_run.py",
    "scripts/check_project_completion_gates.py",
    "scripts/check_trusted_publishing_verification.py",
    "scripts/check_default_price_catalog.py",
    "scripts/build_default_price_catalog.py",
    "packages/python/runcost/data/default-source-cache.json",
    "packages/javascript/core/data/default-source-cache.json",
    "packages/go/ledger/data/default-source-cache.json",
    "packages/javascript/core/README.md",
    "schemas/trusted-publishing-verification.schema.json",
    "fixtures/source-files/trusted-publishing-verification-template.json",
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
    assert_true(
        python_project.get("name") == "runcost-ai",
        "Python distribution name must be runcost-ai while PyPI runcost is occupied",
    )
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


def check_registry_metadata() -> None:
    js_package = read_json("packages/javascript/core/package.json")
    pyproject = read_toml("pyproject.toml")
    python_project = pyproject["project"]

    assert_true(python_project.get("readme") == "README.md", "Python package must publish the root README")
    assert_true(python_project.get("name") == "runcost-ai", "Python distribution name must be runcost-ai")
    assert_true("README.md" in js_package.get("files", []), "npm package files must include README.md")
    assert_true(js_package.get("homepage") == "https://github.com/adamallcock/runcost#readme", "npm homepage must point at the project README")
    assert_true(
        js_package.get("repository", {}).get("url") == "git+https://github.com/adamallcock/runcost.git",
        "npm repository URL must point at adamallcock/runcost",
    )

    npm_readme = (ROOT / "packages/javascript/core/README.md").read_text(encoding="utf-8")
    assert_true("github.com/adamallcock/runcost" in npm_readme, "npm README must link to full repository docs")
    root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert_true("pip install runcost-ai" in root_readme, "root README must include Python registry install command")
    assert_true("npm install runcost" in root_readme, "root README must include npm registry install command")
    assert_true("docs/internal/" not in root_readme, "root README must not expose internal docs")
    assert_true("fromResponse" in npm_readme, "npm README must include JavaScript usage")
    assert_true("pre-alpha" not in root_readme.lower(), "root README must use alpha positioning")


def check_release_workflow() -> None:
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    required_snippets = [
        "workflow_dispatch:",
        "EXPECTED_VERSION: ${{ inputs.version }}",
        "publish:",
        "default: false",
        "publish_approval:",
        "publish=true requires publish_approval=publish-runcost",
        "Verify Go module from published tag",
        "go list -m -versions github.com/adamallcock/runcost",
        "go get github.com/adamallcock/runcost/packages/go/ledger@v${{ inputs.version }}",
        "No-publish artifact review checklist",
        "npm run check:release",
        "npm run check:release-dry-run",
        "npm run example:framework:js",
        "npm run example:framework:py",
        "python3 -m build",
        "npm pack ./packages/javascript/core",
        "id-token: write",
        "pypa/gh-action-pypi-publish@release/v1",
        "npm publish --provenance --access public",
        "environment: release",
        "registry-url: \"https://registry.npmjs.org\"",
    ]
    for snippet in required_snippets:
        assert_true(snippet in workflow, f"release workflow missing {snippet!r}")

    forbidden_registry_tokens = [
        "PYPI_API_TOKEN",
        "NPM_TOKEN",
        "NODE_AUTH_TOKEN",
        "TWINE_USERNAME",
        "TWINE_PASSWORD",
        "password:",
        "api-token:",
        "secrets.PYPI",
        "secrets.NPM",
    ]
    for snippet in forbidden_registry_tokens:
        assert_true(snippet not in workflow, f"release workflow must not depend on stored registry token {snippet!r}")

    publish_section = workflow.split("  publish:", 1)[1]
    assert_true("id-token: write" in publish_section, "publish job must request OIDC id-token permission")
    assert_true("pypa/gh-action-pypi-publish@release/v1" in publish_section, "publish job must use PyPI trusted publishing action")
    assert_true("npm publish --provenance --access public" in publish_section, "publish job must publish npm with provenance")
    assert_true(
        "inputs.publish && inputs.publish_approval != 'publish-runcost'" in workflow,
        "release workflow must require typed publish approval before publish=true can proceed",
    )


def check_release_docs() -> None:
    release_doc = (ROOT / "docs/internal/process/release-process.md").read_text(encoding="utf-8")
    source_update_doc = (ROOT / "docs/internal/process/2026-05-26-source-data-update-process.md").read_text(encoding="utf-8")
    for phrase in [
        "trusted publishing",
        "Go module",
        "semantic version",
        "PyPI",
        "npm",
        "runcost price-cards",
        "runcost fixture-check",
        "provenance",
        "check:release-dry-run",
        "check:gates",
        "Registry README Policy",
        "Workflow filename",
        "Allowed action",
        "publishing disabled",
        "real Go tag",
        "artifact review",
        "source-data-update-process",
        "check:trusted-publishing",
        "trusted-publishing-verification",
        "runcost-ai",
        "public-github",
    ]:
        assert_true(re.search(re.escape(phrase), release_doc, re.IGNORECASE), f"release process missing {phrase}")

    for phrase in [
        "Ownership",
        "Cadence",
        "Review Checklist",
        "Product Truth Loop",
        "price-source update",
        "fixture",
        "structured warning",
        "documented limitation",
        "source-adapter fix",
    ]:
        assert_true(
            re.search(re.escape(phrase), source_update_doc, re.IGNORECASE),
            f"source data update process missing {phrase}",
        )

    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert_true("fixture" in contributing.lower(), "CONTRIBUTING.md must describe fixture-first workflow")
    assert_true(
        "2026-05-26-source-data-update-process.md" in contributing,
        "CONTRIBUTING.md must link source data update process",
    )
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert_true("OIDC" in security, "SECURITY.md must mention OIDC publishing")
    migration = (ROOT / "docs/guides/2026-05-26-migration-from-hand-written-formulas.md").read_text(encoding="utf-8")
    assert_true("hand-written" in migration.lower(), "migration guide must cover hand-written formulas")
    assert_true("fixture-check" in migration, "migration guide must mention fixture checks")


def main() -> int:
    check_required_files()
    check_versions_and_license()
    check_registry_metadata()
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
