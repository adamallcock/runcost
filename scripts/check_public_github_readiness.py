#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
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
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/CODEOWNERS",
    ".github/dependabot.yml",
    ".github/workflows/ci.yml",
    ".github/workflows/release.yml",
    "docs/README.md",
    "docs/reference/price-data-strategy.md",
    "docs/internal/process/2026-05-28-public-github-readiness.md",
    "packages/javascript/core/README.md",
]

FORBIDDEN_PUBLIC_README_PHRASES = [
    "PROJECT_PLAN.md",
    "PROGRESS_TRACKER.md",
    "VALIDATION_REPORT.md",
    "docs/internal/",
    "docs/process/",
    "docs/reports/",
]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def read_json(relative: str) -> dict:
    return json.loads(read_text(relative))


def read_toml(relative: str) -> dict:
    return tomllib.loads(read_text(relative))


def check_required_files() -> None:
    for relative in REQUIRED_FILES:
        assert_true((ROOT / relative).exists(), f"missing public readiness file: {relative}")


def check_readmes() -> None:
    root_readme = read_text("README.md")
    npm_readme = read_text("packages/javascript/core/README.md")
    docs_index = read_text("docs/README.md")
    price_strategy = read_text("docs/reference/price-data-strategy.md")

    for phrase in [
        "What did this LLM or agent API call cost, and why?",
        "pip install runcost-ai",
        "npm install runcost",
        "Price data strategy",
        "Fixtures are behavioral conformance tests, not a complete model-price database.",
    ]:
        assert_true(phrase in root_readme, f"root README missing public readiness phrase: {phrase}")

    for forbidden in FORBIDDEN_PUBLIC_README_PHRASES:
        assert_true(forbidden not in root_readme, f"root README exposes internal path or planning doc: {forbidden}")

    for phrase in ["npm install runcost", "fromResponse", "calculateCost", "github.com/adamallcock/runcost"]:
        assert_true(phrase in npm_readme, f"npm README missing package readiness phrase: {phrase}")

    assert_true("reference/price-data-strategy.md" in docs_index, "docs index must link price data strategy")
    for phrase in ["Source Adapters Convert Catalogs", "Source Cache Is The Offline Boundary", "optional reviewed default source-cache catalog"]:
        assert_true(phrase in price_strategy, f"price data strategy missing phrase: {phrase}")


def check_package_metadata() -> None:
    root_package = read_json("package.json")
    js_package = read_json("packages/javascript/core/package.json")
    pyproject = read_toml("pyproject.toml")

    assert_true(root_package.get("private") is True, "workspace package must remain private")
    assert_true(js_package.get("name") == "runcost", "npm package name must be runcost")
    assert_true(js_package.get("description") == "Alpha cost ledger utility for LLM and agent API responses.", "npm description must be public-ready")
    assert_true("README.md" in js_package.get("files", []), "npm package must include README")
    assert_true(pyproject["project"].get("name") == "runcost-ai", "Python distribution must be runcost-ai")
    assert_true(pyproject["project"].get("description") == "Alpha cost ledger utility for LLM and agent API responses.", "Python description must be public-ready")
    assert_true("Development Status :: 3 - Alpha" in pyproject["project"].get("classifiers", []), "Python classifier must be alpha")


def check_github_templates() -> None:
    pr_template = read_text(".github/PULL_REQUEST_TEMPLATE.md")
    assert_true("No API keys" in pr_template, "PR template must include secret-safety reminder")

    issue_dir = ROOT / ".github" / "ISSUE_TEMPLATE"
    issue_files = {path.name for path in issue_dir.glob("*.yml")}
    assert_true(
        {"bug_report.yml", "feature_request.yml", "price_source_update.yml", "config.yml"}.issubset(issue_files),
        "issue templates must include bug, feature, price-source, and config files",
    )

    dependabot = read_text(".github/dependabot.yml")
    for ecosystem in ["github-actions", "npm", "pip", "gomod"]:
        assert_true(ecosystem in dependabot, f"Dependabot config missing {ecosystem}")

    codeowners = read_text(".github/CODEOWNERS")
    for owned_path in ["/packages/python/", "/packages/javascript/", "/packages/go/", "/schemas/", "/fixtures/"]:
        assert_true(owned_path in codeowners, f"CODEOWNERS missing {owned_path}")


def check_public_markdown_links() -> None:
    paths = [
        ROOT / "README.md",
        ROOT / "CODE_OF_CONDUCT.md",
        ROOT / "SUPPORT.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "SECURITY.md",
        ROOT / "docs" / "README.md",
        *sorted((ROOT / "docs" / "guides").glob("*.md")),
        *sorted((ROOT / "docs" / "reference").glob("*.md")),
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT)
        for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
            target = match.group(1).strip()
            if not target or target.startswith("#") or "://" in target or target.startswith("mailto:"):
                continue
            link_path = target.split("#", 1)[0]
            if not link_path:
                continue
            candidate = (path.parent / link_path).resolve()
            assert_true(candidate.exists(), f"{relative} has broken markdown link {target}")


def main() -> int:
    check_required_files()
    check_readmes()
    check_package_metadata()
    check_github_templates()
    check_public_markdown_links()
    print("Public GitHub readiness checks passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"Public GitHub readiness check failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
