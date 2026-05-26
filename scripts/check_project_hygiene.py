#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "PROJECT_PLAN.md",
    "PROGRESS_TRACKER.md",
    "docs/reference/api-reference.md",
    "docs/reference/aggregation-and-streaming.md",
    "docs/reference/custom-pricing-and-discounts.md",
    "docs/reference/debug-trace.md",
    "docs/reports/fixture-coverage.md",
    "docs/generated/contract-taxonomy.md",
    "docs/generated/fixture-support-matrix.md",
    "docs/reports/2026-05-26-invoice-dashboard-comparison-sample.md",
    "docs/reports/2026-05-26-release-workflow-no-publish-blocked.md",
    "docs/guides/package-installation.md",
    "docs/guides/2026-05-26-migration-from-hand-written-formulas.md",
    "docs/guides/quickstart.md",
    "docs/process/release-process.md",
    "docs/process/alpha-smoke-runbook.md",
    "docs/process/invoice-dashboard-comparison.md",
    "docs/process/2026-05-26-source-data-update-process.md",
    "docs/process/beta-v1-hardening-roadmap.md",
    "docs/reference/source-adapters.md",
    "docs/reference/supported-surfaces.md",
    "docs/reference/warnings-and-limitations.md",
    "docs/decisions/polyglot-toolchain-decision.md",
    "docs/notes/api-parity-matrix.md",
    "docs/notes/provider-extractor-notes.md",
    "docs/notes/framework-adapter-notes.md",
    "scripts/check_fixture_coverage.py",
    "scripts/check_fixture_generator.py",
    "scripts/check_package_installs.py",
    "scripts/check_release_readiness.py",
    "scripts/check_schema_taxonomy.py",
    "scripts/check_source_refresh.py",
    "scripts/check_alpha_smoke.py",
    "scripts/check_invoice_comparison.py",
    "scripts/check_project_completion_gates.py",
    "scripts/check_generated_contract_docs.py",
    "scripts/compare_invoice_dashboard.py",
    "scripts/create_fixture.py",
    "scripts/run_langchain_alpha_smoke.py",
    "scripts/run_alpha_smoke.py",
    "scripts/run_vercel_alpha_smoke.mjs",
    "scripts/generate_contract_docs.py",
    "scripts/refresh_price_sources.py",
    "fixtures/source-files/alpha-smoke-samples.json",
    "fixtures/source-files/invoice-dashboard-comparison-sample.json",
    "fixtures/source-files/project-completion-gates.json",
    "packages/python/runcost/cli.py",
    "LICENSE",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "packages/javascript/core/index.d.ts",
    "packages/python/runcost/types.py",
    "schemas/debug-trace.schema.json",
    "schemas/fixture.schema.json",
    "schemas/taxonomy.json",
    "packages/go/ledger/example_test.go",
    ".github/workflows/ci.yml",
    ".github/workflows/release.yml",
]

PUBLIC_API_NAMES = [
    "calculate_cost",
    "calculateCost",
    "CalculateCost",
    "CalculateCostWithOptions",
    "CalculateCostTyped",
    "CalculateCostTypedWithOptions",
    "from_response",
    "fromResponse",
    "FromResponse",
    "aggregate_cost_ledgers",
    "aggregateCostLedgers",
    "AggregateCostLedgers",
    "from_langchain_message",
    "fromLangChainMessage",
    "FromLangChainMessage",
    "track_langchain_costs",
    "RunCostLangChainCallback",
    "from_vercel_ai_sdk_result",
    "fromVercelAISDKResult",
    "FromVercelAISDKResult",
    "createRunCostVercelMiddleware",
    "from_llamaindex_token_counter",
    "fromLlamaIndexTokenCounter",
    "FromLlamaIndexTokenCounter",
    "from_haystack_generator_result",
    "fromHaystackGeneratorResult",
    "FromHaystackGeneratorResult",
    "from_litellm_response",
    "fromLiteLLMResponse",
    "FromLiteLLMResponse",
    "from_ag2_usage_summary",
    "fromAG2UsageSummary",
    "FromAG2UsageSummary",
    "DebugTrace",
    "debug_trace",
    "debugTrace",
    "extract_gemini_generate_content_usage",
    "extractGeminiGenerateContentUsage",
    "extractBedrockConverseUsage",
    "extract_bedrock_converse_usage",
    "extractBedrockInvokeModelUsage",
    "extract_bedrock_invoke_model_usage",
    "extractCohereChatUsage",
    "extract_cohere_chat_usage",
    "extractLangChainChatUsage",
    "extract_langchain_chat_usage",
    "extractVercelAISDKUsage",
    "extract_vercel_ai_sdk_usage",
    "extractLlamaIndexTokenCounterUsage",
    "extract_llamaindex_token_counter_usage",
    "extractHaystackGeneratorUsage",
    "extract_haystack_generator_usage",
    "extractLiteLLMProxyResponseUsage",
    "extract_litellm_proxy_response_usage",
    "extractAG2UsageSummaryUsage",
    "extract_ag2_usage_summary_usage",
    "extractOpenRouterChatCompletionsUsage",
    "extract_openrouter_chat_completions_usage",
    "extractOpenAICompatibleChatCompletionsUsage",
    "extract_openai_compatible_chat_completions_usage",
    "extractOpenAIEmbeddingsUsage",
    "extract_openai_embeddings_usage",
    "price_cards_from_litellm",
    "priceCardsFromLiteLLM",
    "PriceCardsFromLiteLLM",
    "price_cards_from_models_dev",
    "priceCardsFromModelsDev",
    "PriceCardsFromModelsDev",
    "price_cards_from_official_snapshot",
    "priceCardsFromOfficialSnapshot",
    "PriceCardsFromOfficialSnapshot",
    "price_cards_from_openrouter_models",
    "priceCardsFromOpenRouterModels",
    "PriceCardsFromOpenRouterModels",
    "price_cards_from_portkey",
    "priceCardsFromPortkey",
    "PriceCardsFromPortkey",
    "price_cards_from_source_cache",
    "priceCardsFromSourceCache",
    "PriceCardsFromSourceCache",
    "price_cards_from_user_pricing",
    "priceCardsFromUserPricing",
    "PriceCardsFromUserPricing",
    "price_cards_from_helicone",
    "priceCardsFromHelicone",
    "PriceCardsFromHelicone",
    "price_cards_from_json_file",
    "priceCardsFromJSONFile",
    "PriceCardsFromJSONFile",
    "price_cards_from_yaml_file",
    "priceCardsFromYAMLFile",
    "PriceCardsFromYAMLFile",
]


def load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check_required_files() -> None:
    for relative in REQUIRED_FILES:
        path = ROOT / relative
        assert_true(path.exists(), f"required file is missing: {relative}")


def check_json_files() -> None:
    for path in sorted(ROOT.rglob("*.json")):
        if "node_modules" in path.parts:
            continue
        try:
            load_json(path)
        except json.JSONDecodeError as exc:
            relative = path.relative_to(ROOT)
            raise AssertionError(f"{relative}: invalid JSON: {exc}") from exc


def check_package_metadata() -> None:
    root_package = load_json(ROOT / "package.json")
    scripts = root_package.get("scripts", {})
    assert_true("check_fixtures.py" in scripts.get("test", ""), "root npm test must run fixture checks")
    assert_true(
        "check_fixture_generator.py" in scripts.get("test", ""),
        "root npm test must run fixture generator checks",
    )
    assert_true(
        "check_schema_taxonomy.py" in scripts.get("test", ""),
        "root npm test must run schema taxonomy checks",
    )
    assert_true(
        "check_source_refresh.py" in scripts.get("test", ""),
        "root npm test must run source refresh command checks",
    )
    assert_true(
        "check_alpha_smoke.py" in scripts.get("test", ""),
        "root npm test must run alpha smoke sample checks",
    )
    assert_true(
        "check_invoice_comparison.py" in scripts.get("test", ""),
        "root npm test must run invoice/dashboard comparison checks",
    )
    assert_true(
        "check_project_completion_gates.py" in scripts.get("test", ""),
        "root npm test must run project completion gate checks",
    )
    assert_true(
        "check_generated_contract_docs.py" in scripts.get("test", ""),
        "root npm test must run generated contract docs drift checks",
    )
    assert_true("check_fixture_coverage.py" in scripts.get("test", ""), "root npm test must run fixture coverage checks")
    assert_true(
        "check_fixture_coverage.py" in scripts.get("check:coverage", ""),
        "root check:coverage must run fixture coverage checks",
    )
    assert_true("go test ./packages/go/..." in scripts.get("test", ""), "root npm test must run Go tests")
    assert_true(
        "check_project_hygiene.py" in scripts.get("test", ""),
        "root npm test must run project hygiene checks",
    )
    assert_true(
        "check_package_installs.py" in scripts.get("check:packages", ""),
        "root check:packages must run clean package install checks",
    )
    assert_true(
        "check_release_readiness.py" in scripts.get("check:release", ""),
        "root check:release must run release readiness checks",
    )
    assert_true(
        "check_schema_taxonomy.py" in scripts.get("check:taxonomy", ""),
        "root check:taxonomy must run schema taxonomy checks",
    )
    assert_true("create_fixture.py" in scripts.get("fixture:new", ""), "root fixture:new must run fixture generator")
    assert_true(
        "refresh_price_sources.py" in scripts.get("prices:refresh", ""),
        "root prices:refresh must run source refresh command",
    )
    assert_true(
        "run_alpha_smoke.py" in scripts.get("smoke:alpha", ""),
        "root smoke:alpha must run alpha smoke harness",
    )
    assert_true(
        "compare_invoice_dashboard.py" in scripts.get("compare:invoice", ""),
        "root compare:invoice must run invoice/dashboard comparison command",
    )
    assert_true(
        "check_project_completion_gates.py" in scripts.get("check:gates", ""),
        "root check:gates must run project completion gate checks",
    )
    assert_true(
        "generate_contract_docs.py --write" in scripts.get("generate:contracts", ""),
        "root generate:contracts must regenerate contract docs",
    )

    js_package_path = ROOT / "packages/javascript/core/package.json"
    js_package = load_json(js_package_path)
    types_path = ROOT / "packages/javascript/core" / js_package.get("types", "")
    assert_true(types_path.exists(), "JavaScript package types field must point to an existing file")
    exports = js_package.get("exports", {}).get(".", {})
    assert_true(exports.get("types") == "./index.d.ts", "JavaScript package exports must expose index.d.ts")
    assert_true(not js_package.get("private", False), "JavaScript package must be publishable")
    assert_true("files" in js_package, "JavaScript package must define a publish file allowlist")
    assert_true(js_package.get("license") == "MIT", "JavaScript package must declare MIT license")

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert_true('runcost = "runcost.cli:main"' in pyproject, "Python package must install runcost CLI")


def check_public_api_artifacts() -> None:
    parity = (ROOT / "docs/notes/api-parity-matrix.md").read_text(encoding="utf-8")
    typescript = (ROOT / "packages/javascript/core/index.d.ts").read_text(encoding="utf-8")
    python_init = (ROOT / "packages/python/runcost/__init__.py").read_text(encoding="utf-8")
    python_types = (ROOT / "packages/python/runcost/types.py").read_text(encoding="utf-8")
    go_source = (ROOT / "packages/go/ledger/ledger.go").read_text(encoding="utf-8")
    go_examples = (ROOT / "packages/go/ledger/example_test.go").read_text(encoding="utf-8")

    for name in PUBLIC_API_NAMES:
        assert_true(name in parity, f"API parity matrix missing {name}")

    for exported in [
        "calculateCost",
        "aggregateCostLedgers",
        "fromResponse",
        "fromLangChainMessage",
        "createRunCostVercelMiddleware",
        "fromVercelAISDKResult",
        "fromLlamaIndexTokenCounter",
        "fromHaystackGeneratorResult",
        "fromLiteLLMResponse",
        "fromAG2UsageSummary",
        "priceCardsFromLlmPrices",
        "priceCardsFromLiteLLM",
        "priceCardsFromModelsDev",
        "priceCardsFromOfficialSnapshot",
        "priceCardsFromOpenRouterModels",
        "priceCardsFromPortkey",
        "priceCardsFromSourceCache",
        "priceCardsFromUserPricing",
        "priceCardsFromHelicone",
        "priceCardsFromJSONFile",
        "priceCardsFromYAMLFile",
        "extractOpenAICompatibleChatCompletionsUsage",
        "extractOpenAIEmbeddingsUsage",
        "extractBedrockInvokeModelUsage",
        "extractCohereChatUsage",
        "extractLangChainChatUsage",
        "extractVercelAISDKUsage",
        "extractLlamaIndexTokenCounterUsage",
        "extractHaystackGeneratorUsage",
        "extractLiteLLMProxyResponseUsage",
        "extractAG2UsageSummaryUsage",
        "UsageLedger",
        "PriceCard",
        "CostLedger",
        "DebugTrace",
    ]:
        assert_true(exported in typescript, f"TypeScript declarations missing {exported}")

    for exported in [
        "UsageLedger",
        "PriceCard",
        "DiscountPolicy",
        "CostLedger",
        "DebugTrace",
        "calculate_cost",
        "aggregate_cost_ledgers",
        "from_response",
        "from_langchain_message",
        "track_langchain_costs",
        "RunCostLangChainCallback",
        "from_vercel_ai_sdk_result",
        "from_llamaindex_token_counter",
        "from_haystack_generator_result",
        "from_litellm_response",
        "from_ag2_usage_summary",
        "price_cards_from_litellm",
        "price_cards_from_models_dev",
        "price_cards_from_official_snapshot",
        "price_cards_from_openrouter_models",
        "price_cards_from_portkey",
        "price_cards_from_source_cache",
        "price_cards_from_user_pricing",
        "price_cards_from_helicone",
        "price_cards_from_json_file",
        "price_cards_from_yaml_file",
        "extract_openai_compatible_chat_completions_usage",
        "extract_openai_embeddings_usage",
        "extract_bedrock_invoke_model_usage",
        "extract_cohere_chat_usage",
        "extract_langchain_chat_usage",
        "extract_vercel_ai_sdk_usage",
        "extract_llamaindex_token_counter_usage",
        "extract_haystack_generator_usage",
        "extract_litellm_proxy_response_usage",
        "extract_ag2_usage_summary_usage",
    ]:
        assert_true(exported in python_init or exported in python_types, f"Python package missing {exported}")

    for exported in [
        "CalculateCost",
        "CalculateCostWithMode",
        "CalculateCostWithOptions",
        "CalculateCostTyped",
        "CalculateCostTypedWithMode",
        "CalculateCostTypedWithOptions",
        "AggregateCostLedgers",
        "ExtractUsageLedger",
        "PriceCardsFromLlmPrices",
        "PriceCardsFromLiteLLM",
        "PriceCardsFromModelsDev",
        "PriceCardsFromOfficialSnapshot",
        "PriceCardsFromOpenRouterModels",
        "PriceCardsFromPortkey",
        "PriceCardsFromSourceCache",
        "PriceCardsFromUserPricing",
        "PriceCardsFromHelicone",
        "PriceCardsFromJSONFile",
        "PriceCardsFromYAMLFile",
        "FromResponse",
        "FromLangChainMessage",
        "FromVercelAISDKResult",
        "FromLlamaIndexTokenCounter",
        "FromHaystackGeneratorResult",
        "FromLiteLLMResponse",
        "FromAG2UsageSummary",
    ]:
        assert_true(
            re.search(rf"// {exported}\b", go_source) is not None,
            f"Go exported function {exported} must have a doc comment",
        )

    assert_true("ExampleCalculateCost" in go_examples, "Go example test must include ExampleCalculateCost")
    assert_true("ExampleCalculateCostTyped" in go_examples, "Go example test must include ExampleCalculateCostTyped")
    assert_true("ExampleFromResponse" in go_examples, "Go example test must include ExampleFromResponse")


def check_fixture_floor() -> None:
    fixtures = sorted((ROOT / "fixtures").glob("*.json"))
    assert_true(len(fixtures) >= 68, f"expected at least 68 fixtures, found {len(fixtures)}")
    for path in fixtures:
        fixture = load_json(path)
        metadata = fixture.get("metadata")
        assert_true(isinstance(metadata, dict), f"{path.name} must include metadata")
        for key in ["requirement_ids", "provider", "surface", "scenario", "tags", "expected_languages"]:
            assert_true(key in metadata, f"{path.name} metadata missing {key}")
        languages = metadata.get("expected_languages")
        assert_true(isinstance(languages, list) and languages, f"{path.name} must declare expected languages")
        unknown = sorted(set(languages) - {"python", "javascript", "go"})
        assert_true(not unknown, f"{path.name} declares unknown expected languages: {unknown}")


def check_ci_workflow() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for command in [
        "npm test",
        "check_fixture_coverage.py",
        "check_fixture_generator.py",
        "check_source_refresh.py",
        "check_alpha_smoke.py",
        "check_invoice_comparison.py",
        "check_project_completion_gates.py",
        "check_generated_contract_docs.py",
        "compare_invoice_dashboard.py",
        "generate_contract_docs.py",
        "run_langchain_alpha_smoke.py",
        "run_vercel_alpha_smoke.mjs",
        "check_schema_taxonomy.py",
        "refresh_price_sources.py",
        "npm run check:packages",
        "npm run check:release",
        "npm run example:js",
        "npm run example:py",
        "python3 -m py_compile",
    ]:
        assert_true(command in workflow, f"CI workflow missing command: {command}")


def check_packaging_docs() -> None:
    root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    quickstart = (ROOT / "docs/guides/quickstart.md").read_text(encoding="utf-8")
    installation = (ROOT / "docs/guides/package-installation.md").read_text(encoding="utf-8")
    migration = (ROOT / "docs/guides/2026-05-26-migration-from-hand-written-formulas.md").read_text(encoding="utf-8")
    api_reference = (ROOT / "docs/reference/api-reference.md").read_text(encoding="utf-8")
    release_process = (ROOT / "docs/process/release-process.md").read_text(encoding="utf-8")
    source_update = (ROOT / "docs/process/2026-05-26-source-data-update-process.md").read_text(encoding="utf-8")

    assert_true(
        "2026-05-26-migration-from-hand-written-formulas.md" in root_readme,
        "README must link to migration guide",
    )
    assert_true("npm test" in quickstart, "quickstart must mention npm test")
    assert_true("npm run check:packages" in installation, "package installation guide must mention package checks")
    assert_true("runcost.cli:main" in (ROOT / "pyproject.toml").read_text(encoding="utf-8"), "pyproject missing CLI entry")
    for phrase in ["runcost price-cards", "runcost fixture-check"]:
        assert_true(phrase in quickstart, f"quickstart missing CLI command: {phrase}")
        assert_true(phrase in installation, f"package installation guide missing CLI command: {phrase}")
        assert_true(phrase in api_reference, f"API reference missing CLI command: {phrase}")
        assert_true(phrase in migration, f"migration guide missing CLI command: {phrase}")
        assert_true(phrase in release_process, f"release process missing CLI command: {phrase}")
    for phrase in ["Ownership", "Cadence", "Review Checklist", "Product Truth Loop"]:
        assert_true(phrase in source_update, f"source data update process missing section: {phrase}")
    assert_true(
        "2026-05-26-source-data-update-process.md" in root_readme,
        "README must link to source data update process",
    )
    assert_true(
        "2026-05-26-source-data-update-process.md" in release_process,
        "release process must link to source data update process",
    )


def check_framework_adapter_paths() -> None:
    framework_notes = (ROOT / "docs/notes/framework-adapter-notes.md").read_text(encoding="utf-8")
    supported_surfaces = (ROOT / "docs/reference/supported-surfaces.md").read_text(encoding="utf-8")
    parity = (ROOT / "docs/notes/api-parity-matrix.md").read_text(encoding="utf-8")

    framework_note_terms = [
        "OpenAI Agents SDK Usage",
        "Vercel AI SDK",
        "Semantic Kernel",
        "Haystack",
        "AutoGen / AG2",
        "LangSmith",
        "LiteLLM Proxy Response Metadata",
        "OpenRouter-Compatible SDK Paths",
    ]
    for term in framework_note_terms:
        assert_true(term in framework_notes, f"framework adapter notes missing framework path: {term}")

    for term in [
        "OpenAI Agents SDK",
        "Vercel AI SDK",
        "Semantic Kernel",
        "Haystack",
        "AutoGen / AG2",
        "LangSmith",
        "LiteLLM proxy",
        "OpenRouter-compatible SDK paths",
    ]:
        assert_true(term in supported_surfaces, f"supported surfaces missing framework path: {term}")
        assert_true(term in parity, f"API parity matrix missing framework path: {term}")

    assert_true(
        "fixture-support-matrix.md" in supported_surfaces,
        "supported surfaces must link generated fixture support matrix",
    )

    for term in [
        "openai-agents-sdk-usage.json",
        "vercel-ai-sdk-stream-text-finish.json",
        "langsmith-run-usage-metadata.json",
        "langsmith-export-cost-compare.json",
        "semantic-kernel-telemetry-basic.json",
        "openrouter-openai-sdk-response.json",
        "openrouter-agent-sdk-response.json",
    ]:
        assert_true(term in parity, f"API parity matrix missing framework fixture: {term}")


def main() -> int:
    check_required_files()
    check_json_files()
    check_package_metadata()
    check_public_api_artifacts()
    check_fixture_floor()
    check_ci_workflow()
    check_packaging_docs()
    check_framework_adapter_paths()
    print("Project hygiene checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
