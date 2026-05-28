#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "docs/internal/project-plan.md",
    "docs/internal/progress-tracker.md",
    "docs/reference/api-reference.md",
    "docs/reference/aggregation-and-streaming.md",
    "docs/reference/custom-pricing-and-discounts.md",
    "docs/reference/debug-trace.md",
    "docs/internal/reports/fixture-coverage.md",
    "docs/generated/contract-taxonomy.md",
    "docs/generated/fixture-support-matrix.md",
    "docs/generated/warning-coverage.md",
    "docs/internal/reports/2026-05-26-invoice-dashboard-comparison-sample.md",
    "docs/internal/reports/2026-05-26-release-workflow-no-publish-blocked.md",
    "docs/internal/reports/2026-05-26-release-workflow-0-1-0-no-publish-rehearsal.md",
    "docs/internal/reports/2026-05-26-go-tag-verification-0-1-0.md",
    "docs/guides/package-installation.md",
    "docs/guides/2026-05-26-migration-from-hand-written-formulas.md",
    "docs/guides/quickstart.md",
    "docs/internal/process/release-process.md",
    "docs/internal/process/alpha-smoke-runbook.md",
    "docs/internal/process/invoice-dashboard-comparison.md",
    "docs/internal/process/2026-05-26-source-data-update-process.md",
    "docs/internal/process/2026-05-28-public-github-readiness.md",
    "docs/internal/process/beta-v1-hardening-roadmap.md",
    "docs/README.md",
    "docs/internal/README.md",
    "docs/reference/source-adapters.md",
    "docs/reference/supported-surfaces.md",
    "docs/reference/warnings-and-limitations.md",
    "docs/reference/price-data-strategy.md",
    "CODE_OF_CONDUCT.md",
    "SUPPORT.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/ISSUE_TEMPLATE/price_source_update.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/CODEOWNERS",
    ".github/dependabot.yml",
    "docs/internal/decisions/polyglot-toolchain-decision.md",
    "docs/internal/decisions/2026-05-27-python-distribution-name.md",
    "docs/internal/notes/api-parity-matrix.md",
    "docs/internal/notes/provider-extractor-notes.md",
    "docs/internal/notes/framework-adapter-notes.md",
    "scripts/check_fixture_coverage.py",
    "scripts/check_fixture_generator.py",
    "scripts/check_package_installs.py",
    "scripts/check_release_readiness.py",
    "scripts/check_schema_taxonomy.py",
    "scripts/check_source_refresh.py",
    "scripts/check_alpha_smoke.py",
    "scripts/check_go_fixtures.py",
    "scripts/check_alpha_evidence_collector.py",
    "scripts/check_invoice_comparison.py",
    "scripts/check_project_completion_gates.py",
    "scripts/check_generated_contract_docs.py",
    "scripts/check_public_api_registry.py",
    "scripts/check_public_github_readiness.py",
    "scripts/check_python_type_surface.py",
    "scripts/compare_invoice_dashboard.py",
    "scripts/collect_alpha_evidence_bundle.py",
    "scripts/create_openai_costs_comparison_input.py",
    "scripts/create_fixture.py",
    "scripts/run_langchain_alpha_smoke.py",
    "scripts/run_alpha_smoke.py",
    "scripts/run_openai_costs_invoice_comparison.py",
    "scripts/run_vercel_alpha_smoke.mjs",
    "scripts/generate_contract_docs.py",
    "scripts/refresh_price_sources.py",
    "examples/javascript_framework_adapters.mjs",
    "examples/python_framework_adapters.py",
    "fixtures/source-files/alpha-smoke-samples.json",
    "fixtures/source-files/invoice-dashboard-comparison-sample.json",
    "fixtures/source-files/openai-costs-comparison-source.json",
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
    "schemas/public-api-registry.schema.json",
    "schemas/taxonomy.json",
    "fixtures/source-files/public-api-registry.json",
    "docs/generated/public-api-registry.md",
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
    "extractCohereRerankUsage",
    "extract_cohere_rerank_usage",
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
    assert_true("check_go_fixtures.py" in scripts.get("test", ""), "root npm test must run explicit Go fixture checks")
    assert_true("check_go_fixtures.py" in scripts.get("check:fixtures:go", ""), "root check:fixtures:go must run explicit Go fixture checks")
    assert_true(
        "check_fixture_generator.py" in scripts.get("test", ""),
        "root npm test must run fixture generator checks",
    )
    assert_true(
        "check_schema_taxonomy.py" in scripts.get("test", ""),
        "root npm test must run schema taxonomy checks",
    )
    assert_true(
        "check_public_api_registry.py" in scripts.get("test", ""),
        "root npm test must run public API registry checks",
    )
    assert_true(
        "check_public_api_registry.py" in scripts.get("check:api-registry", ""),
        "root check:api-registry must run public API registry checks",
    )
    assert_true(
        "check_public_github_readiness.py" in scripts.get("test", ""),
        "root npm test must run public GitHub readiness checks",
    )
    assert_true(
        "check_public_github_readiness.py" in scripts.get("check:public-github", ""),
        "root check:public-github must run public GitHub readiness checks",
    )
    assert_true(
        "check_python_type_surface.py" in scripts.get("test", ""),
        "root npm test must run Python type surface checks",
    )
    assert_true(
        "check_python_type_surface.py" in scripts.get("check:types:python", ""),
        "root check:types:python must run Python type surface checks",
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
        "check_alpha_evidence_collector.py" in scripts.get("test", ""),
        "root npm test must run alpha evidence collector checks",
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
        "collect_alpha_evidence_bundle.py" in scripts.get("alpha:bundle", ""),
        "root alpha:bundle must run alpha evidence bundle collector",
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
    assert_true(
        "javascript_framework_adapters.mjs" in scripts.get("example:framework:js", ""),
        "root example:framework:js must run JavaScript framework examples",
    )
    assert_true(
        "python_framework_adapters.py" in scripts.get("example:framework:py", ""),
        "root example:framework:py must run Python framework examples",
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
    assert_true('name = "runcost-ai"' in pyproject, "Python distribution name must be runcost-ai")
    assert_true('runcost = "runcost.cli:main"' in pyproject, "Python package must install runcost CLI")


def check_public_api_artifacts() -> None:
    parity = (ROOT / "docs/internal/notes/api-parity-matrix.md").read_text(encoding="utf-8")
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
        "extractCohereRerankUsage",
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
        "extract_cohere_rerank_usage",
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
        "check_alpha_smoke_contract.py",
        "check_alpha_smoke_preflight.py",
        "check_alpha_evidence_bundle.py",
        "check_alpha_evidence_collector.py",
        "check_invoice_comparison_contract.py",
        "check_invoice_comparison.py",
        "check_project_completion_gates.py",
        "check_generated_contract_docs.py",
        "collect_alpha_evidence_bundle.py",
        "compare_invoice_dashboard.py",
        "create_openai_costs_comparison_input.py",
        "generate_contract_docs.py",
        "run_openai_costs_invoice_comparison.py",
        "run_langchain_alpha_smoke.py",
        "run_vercel_alpha_smoke.mjs",
        "check_schema_taxonomy.py",
        "refresh_price_sources.py",
        "npm run check:packages",
        "npm run check:release",
        "npm run example:js",
        "npm run example:py",
        "npm run example:framework:js",
        "npm run example:framework:py",
        "python3 -m py_compile",
    ]:
        assert_true(command in workflow, f"CI workflow missing command: {command}")


def check_packaging_docs() -> None:
    root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    npm_readme = (ROOT / "packages/javascript/core/README.md").read_text(encoding="utf-8")
    quickstart = (ROOT / "docs/guides/quickstart.md").read_text(encoding="utf-8")
    installation = (ROOT / "docs/guides/package-installation.md").read_text(encoding="utf-8")
    migration = (ROOT / "docs/guides/2026-05-26-migration-from-hand-written-formulas.md").read_text(encoding="utf-8")
    api_reference = (ROOT / "docs/reference/api-reference.md").read_text(encoding="utf-8")
    framework_notes = (ROOT / "docs/internal/notes/framework-adapter-notes.md").read_text(encoding="utf-8")
    release_process = (ROOT / "docs/internal/process/release-process.md").read_text(encoding="utf-8")
    beta_roadmap = (ROOT / "docs/internal/process/beta-v1-hardening-roadmap.md").read_text(encoding="utf-8")
    source_update = (ROOT / "docs/internal/process/2026-05-26-source-data-update-process.md").read_text(encoding="utf-8")
    warnings = (ROOT / "docs/reference/warnings-and-limitations.md").read_text(encoding="utf-8")
    gates = load_json(ROOT / "fixtures/source-files/project-completion-gates.json")

    for phrase in [
        "What did this LLM or agent API call cost, and why?",
        "pip install runcost-ai",
        "npm install runcost",
        "go get github.com/adamallcock/runcost/packages/go/ledger",
        "from_response",
        "fromResponse",
        "FromResponse",
        "calculate_cost",
        "Main APIs",
        "Custom Prices And Discounts",
        "Warnings",
    ]:
        assert_true(phrase in root_readme, f"README missing public user-facing phrase: {phrase}")
    assert_true("docs/guides/2026-05-26-migration-from-hand-written-formulas.md" in root_readme, "README must link to migration guide")
    assert_true("docs/internal/" not in root_readme, "README must not link to internal docs")
    for forbidden in ["Project State", "Project plan", "Progress tracker", "market-gap-validation", "docs/internal/process/", "docs/internal/reports/"]:
        assert_true(forbidden not in root_readme, f"README must not expose internal project state: {forbidden}")
    for phrase in ["What did this LLM or agent API call cost, and why?", "npm install runcost", "fromResponse", "calculateCost", "Main APIs"]:
        assert_true(phrase in npm_readme, f"npm README missing aligned package guidance: {phrase}")
    assert_true("prototype" not in npm_readme.lower(), "npm README must not use prototype positioning")
    assert_true("pre-alpha" not in root_readme.lower(), "README must not use pre-alpha positioning")
    assert_true("pre-alpha" not in npm_readme.lower(), "npm README must not use pre-alpha positioning")
    assert_true("npm test" in quickstart, "quickstart must mention npm test")
    assert_true("npm run check:packages" in installation, "package installation guide must mention package checks")
    assert_true("runcost.cli:main" in (ROOT / "pyproject.toml").read_text(encoding="utf-8"), "pyproject missing CLI entry")
    for phrase in ["runcost price-cards", "runcost fixture-check"]:
        assert_true(phrase in quickstart, f"quickstart missing CLI command: {phrase}")
        assert_true(phrase in installation, f"package installation guide missing CLI command: {phrase}")
        assert_true(phrase in api_reference, f"API reference missing CLI command: {phrase}")
        assert_true(phrase in migration, f"migration guide missing CLI command: {phrase}")
        assert_true(phrase in release_process, f"release process missing CLI command: {phrase}")
    for phrase in ["examples/python_framework_adapters.py", "examples/javascript_framework_adapters.mjs"]:
        assert_true(phrase in framework_notes, f"framework adapter notes missing framework example link: {phrase}")
    for phrase in ["Ownership", "Cadence", "Review Checklist", "Product Truth Loop"]:
        assert_true(phrase in source_update, f"source data update process missing section: {phrase}")
    assert_true(
        "2026-05-26-source-data-update-process.md" in release_process,
        "release process must link to source data update process",
    )
    assert_true(
        "warning-coverage.md" in warnings,
        "warnings and limitations docs must link generated warning coverage",
    )
    assert_true(
        "beta-v1-caveats.md" in warnings,
        "warnings and limitations docs must link generated beta/V1 caveats",
    )
    assert_true(
        "beta-v1-caveats.md" in beta_roadmap,
        "beta/V1 roadmap must link generated beta/V1 caveats",
    )
    assert_true(
        "2026-05-26-release-workflow-0-1-0-no-publish-rehearsal.md" in beta_roadmap,
        "beta/V1 roadmap must link the real-version no-publish rehearsal report",
    )
    assert_true(
        "2026-05-26-go-tag-verification-0-1-0.md" in beta_roadmap,
        "beta/V1 roadmap must link the real Go tag verification report",
    )
    gate_status = {gate["id"]: gate["status"] for gate in gates["gates"]}
    remaining_beta_text = beta_roadmap.lower().split("current release evidence:")[0]
    if gate_status.get("milestone9_real_version_no_publish_rehearsal") == "satisfied":
        assert_true(
            "real-version no-publish rehearsal" not in remaining_beta_text,
            "beta/V1 roadmap must not list satisfied no-publish rehearsal as a remaining strict-gate blocker",
        )
    if gate_status.get("milestone9_real_go_tag_verification") == "satisfied":
        assert_true(
            "real go tag verification" not in remaining_beta_text,
            "beta/V1 roadmap must not list satisfied Go tag verification as a remaining strict-gate blocker",
        )


def check_public_markdown_layout() -> None:
    public_paths = [
        ROOT / "README.md",
        ROOT / "packages/javascript/core/README.md",
        ROOT / "docs/README.md",
        *sorted((ROOT / "docs/guides").glob("*.md")),
        *sorted((ROOT / "docs/reference").glob("*.md")),
        *sorted((ROOT / "docs/generated").glob("*.md")),
    ]
    forbidden_public_patterns = [
        "PROJECT_PLAN.md",
        "PROGRESS_TRACKER.md",
        "VALIDATION_REPORT.md",
        "PRODUCT_REQUIREMENTS.md",
        "ARCHITECTURE.md",
        "LIVE_EVALUATION_PROTOCOL.md",
        "RESULTS_MATRIX.md",
        "2026-05-25-",
    ]
    root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for forbidden in ["docs/internal/", "docs/process/", "docs/notes/", "docs/reports/"]:
        assert_true(forbidden not in root_readme, f"root README must not link internal path {forbidden}")

    for path in public_paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT)
        for forbidden in forbidden_public_patterns:
            assert_true(forbidden not in text, f"{relative} contains stale public-doc reference {forbidden}")
        for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
            target = match.group(1).strip()
            if (
                not target
                or target.startswith("#")
                or "://" in target
                or target.startswith("mailto:")
                or target.startswith("<")
            ):
                continue
            link_path = target.split("#", 1)[0]
            if not link_path:
                continue
            candidate = (path.parent / link_path).resolve()
            assert_true(
                candidate.exists(),
                f"{relative} has broken markdown link {target}",
            )


def check_framework_adapter_paths() -> None:
    framework_notes = (ROOT / "docs/internal/notes/framework-adapter-notes.md").read_text(encoding="utf-8")
    supported_surfaces = (ROOT / "docs/reference/supported-surfaces.md").read_text(encoding="utf-8")
    parity = (ROOT / "docs/internal/notes/api-parity-matrix.md").read_text(encoding="utf-8")

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
    check_public_markdown_layout()
    check_framework_adapter_paths()
    print("Project hygiene checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
