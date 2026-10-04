#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON_PACKAGE = ROOT / "packages" / "python"
JAVASCRIPT_CORE = ROOT / "packages" / "javascript" / "core" / "index.js"
DEFAULT_FIXTURES = sorted((ROOT / "fixtures").glob("*.json"))

sys.path.insert(0, str(PYTHON_PACKAGE))

from runcost import (  # noqa: E402
    aggregate_cost_ledgers,
    calculate_cost,
    extract_usage_ledger,
    from_ag2_usage_summary,
    from_haystack_generator_result,
    from_langchain_message,
    from_langsmith_run,
    from_litellm_response,
    from_llamaindex_token_counter,
    from_openai_agents_usage,
    from_openrouter_sdk_response,
    from_response,
    from_semantic_kernel_telemetry,
    from_vercel_ai_sdk_result,
    from_vercel_ai_sdk_stream_finish,
    from_vercel_ai_sdk_stream_transcribe_finish,
    price_cards_from_helicone,
    price_cards_from_json_file,
    price_cards_from_litellm,
    price_cards_from_llm_prices,
    price_cards_from_models_dev,
    price_cards_from_official_snapshot,
    price_cards_from_openrouter_models,
    price_cards_from_portkey,
    price_cards_from_source_cache,
    price_cards_from_user_pricing,
    price_cards_from_yaml_file,
    track_langchain_costs,
)


def load_json(path: Path):
    return json.loads(path.read_text())


SCHEMA_PATHS = {
    "usage_ledger": ROOT / "schemas" / "usage-ledger.schema.json",
    "price_card": ROOT / "schemas" / "price-card.schema.json",
    "discount_policy": ROOT / "schemas" / "discount-policy.schema.json",
    "cost_ledger": ROOT / "schemas" / "cost-ledger.schema.json",
    "debug_trace": ROOT / "schemas" / "debug-trace.schema.json",
    "fixture": ROOT / "schemas" / "fixture.schema.json",
}
SCHEMAS = {name: load_json(path) for name, path in SCHEMA_PATHS.items()}
TAXONOMY = load_json(ROOT / "schemas" / "taxonomy.json")
COMPONENT_ORDER = {name: index for index, name in enumerate(TAXONOMY["component_names"])}
WARNING_METADATA_REQUIRED_KEYS = TAXONOMY["warning_metadata_required_keys"]
DATE_TIME_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})$"
)


def expected_languages(fixture):
    return fixture.get("metadata", {}).get("expected_languages", ["python", "javascript", "go"])


def validate_schema(value, schema, root=None, path="$"):
    """Validate Draft 2020-12, retaining root-local reference resolution."""
    from jsonschema import Draft202012Validator, FormatChecker
    root = root if root is not None else schema
    validator = Draft202012Validator(root, format_checker=Draft202012Validator.FORMAT_CHECKER).evolve(schema=schema)
    error = next(validator.iter_errors(value), None)
    if error is not None:
        location = path + "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in error.absolute_path)
        raise AssertionError(f"{location}: {error.message}")


def check_schema_validator_contract():
    priced_at_schema = SCHEMAS["usage_ledger"]["properties"]["context"]["properties"]["priced_at"]
    for valid in ("2026-08-08", "2026-08-08T12:34:56Z", "2026-08-08t12:34:56.123+05:30"):
        validate_schema(valid, priced_at_schema, SCHEMAS["usage_ledger"], "validator.valid")

    invalid_values = (
        "2026-02-30",
        "2026-08-08T12:34:56",
        "2026-08-08T25:00:00Z",
        "not-a-date",
    )
    for invalid in invalid_values:
        try:
            validate_schema(invalid, priced_at_schema, SCHEMAS["usage_ledger"], "validator.invalid")
        except AssertionError:
            pass
        else:
            raise AssertionError(f"validator.invalid: accepted invalid date/date-time {invalid!r}")

    ambiguous_schema = {"oneOf": [{"type": "string"}, {"type": "string", "minLength": 1}]}
    try:
        validate_schema("ambiguous", ambiguous_schema, path="validator.ambiguous")
    except AssertionError:
        pass
    else:
        raise AssertionError("validator.ambiguous: oneOf accepted more than one matching branch")

    tags_schema = SCHEMAS["discount_policy"]["properties"]["match"]["properties"]["tags"]
    validate_schema({"team": "platform"}, tags_schema, SCHEMAS["discount_policy"], "validator.tags.valid")
    try:
        validate_schema({"team": 42}, tags_schema, SCHEMAS["discount_policy"], "validator.tags.invalid")
    except AssertionError:
        pass
    else:
        raise AssertionError("validator.tags.invalid: accepted a non-string additional property")


def validate_price_cards(price_cards, path):
    for index, card in enumerate(price_cards):
        validate_schema(card, SCHEMAS["price_card"], path=f"{path}[{index}]")


def validate_discount_policies(discount_policies, path):
    for index, policy in enumerate(discount_policies):
        validate_schema(policy, SCHEMAS["discount_policy"], path=f"{path}[{index}]")


def assert_subset(actual, expected, path=""):
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            raise AssertionError(f"{path}: expected object, got {type(actual).__name__}")
        for key, expected_value in expected.items():
            if key not in actual:
                raise AssertionError(f"{path}.{key}: missing")
            assert_subset(actual[key], expected_value, f"{path}.{key}")
        return

    if isinstance(expected, list):
        if all(isinstance(item, dict) for item in expected):
            if not isinstance(actual, list):
                raise AssertionError(f"{path}: expected array, got {type(actual).__name__}")
            if len(actual) != len(expected):
                raise AssertionError(f"{path}: expected {len(expected)} items, got {len(actual)}")
            for index, expected_item in enumerate(expected):
                assert_subset(actual[index], expected_item, f"{path}[{index}]")
            return
        if actual != expected:
            raise AssertionError(f"{path}: expected {expected!r}, got {actual!r}")
        return

    if actual != expected:
        raise AssertionError(f"{path}: expected {expected!r}, got {actual!r}")


def assert_total_matches_components(cost_ledger, path):
    total = sum(Decimal(component["cost"]) for component in cost_ledger["components"])
    expected = Decimal(cost_ledger["total"])
    if total != expected:
        raise AssertionError(f"{path}: component costs sum to {total}, total is {expected}")


def component_sort_key(component):
    name = component.get("name", "")
    return (
        COMPONENT_ORDER.get(name, len(COMPONENT_ORDER)),
        name,
        component.get("unit", ""),
        component.get("unit_price", ""),
        component.get("price_card_id", ""),
        component.get("quantity", ""),
        component.get("cost", ""),
    )


def source_sort_key(source):
    return (
        source.get("name", ""),
        source.get("url", ""),
        source.get("retrieved_at", ""),
        source.get("version", ""),
    )


def discount_sort_key(discount):
    return (
        discount.get("component", ""),
        discount.get("policy_id", ""),
        discount.get("amount", ""),
    )


def warning_sort_key(warning):
    return (
        warning.get("code", ""),
        warning.get("path", ""),
        warning.get("message", ""),
        json.dumps(warning.get("metadata", {}), sort_keys=True, separators=(",", ":")),
    )


def assert_ordered(values, key, path):
    expected = sorted(values, key=key)
    if values != expected:
        raise AssertionError(f"{path}: output order is not byte-stable")


def assert_cost_ledger_ordering(cost_ledger, path):
    assert_ordered(cost_ledger.get("components", []), component_sort_key, f"{path}.components")
    assert_ordered(cost_ledger.get("price_sources", []), source_sort_key, f"{path}.price_sources")
    assert_ordered(cost_ledger.get("applied_discounts", []), discount_sort_key, f"{path}.applied_discounts")
    assert_ordered(cost_ledger.get("warnings", []), warning_sort_key, f"{path}.warnings")


def assert_warning_metadata(cost_ledger, path):
    for index, warning in enumerate(cost_ledger.get("warnings", [])):
        warning_path = f"{path}.warnings[{index}]"
        if "metadata" not in warning:
            raise AssertionError(f"{warning_path}.metadata: missing required warning metadata")
        metadata = warning["metadata"]
        if not isinstance(metadata, dict):
            raise AssertionError(f"{warning_path}.metadata: expected object, got {type(metadata).__name__}")
        required_keys = WARNING_METADATA_REQUIRED_KEYS.get(warning.get("code"), [])
        missing = sorted(key for key in required_keys if key not in metadata)
        if missing:
            raise AssertionError(f"{warning_path}.metadata: missing required keys {missing!r}")


def resolve_python_price_cards(fixture):
    input_data = fixture["input"]
    if "cost_ledgers" in input_data:
        return []
    if "price_cards" in input_data:
        return input_data["price_cards"]

    source = input_data["price_source"]
    if source["type"] == "llm-prices":
        return price_cards_from_llm_prices(source["data"])
    if source["type"] == "litellm":
        return price_cards_from_litellm(source["data"])
    if source["type"] == "openrouter-models":
        return price_cards_from_openrouter_models(source["data"])
    if source["type"] == "models-dev":
        return price_cards_from_models_dev(source["data"])
    if source["type"] == "official-snapshot":
        return price_cards_from_official_snapshot(source["data"])
    if source["type"] == "portkey":
        return price_cards_from_portkey(source["data"])
    if source["type"] == "source-cache":
        return price_cards_from_source_cache(source["data"])
    if source["type"] == "user-pricing":
        return price_cards_from_user_pricing(source["data"])
    if source["type"] == "helicone":
        return price_cards_from_helicone(source["data"])
    if source["type"] == "json-file":
        return price_cards_from_json_file(ROOT / source["path"], source.get("source_type", "user-pricing"))
    if source["type"] == "yaml-file":
        return price_cards_from_yaml_file(ROOT / source["path"], source.get("source_type", "user-pricing"))
    raise AssertionError(f"Unsupported price source: {source['type']}")


def run_python_fixture(fixture):
    input_data = fixture["input"]
    if "cost_ledgers" in input_data:
        return aggregate_cost_ledgers(
            input_data["cost_ledgers"],
            mode=input_data.get("mode", "compatibility"),
            **input_data.get("options", {}),
        )

    price_cards = resolve_python_price_cards(fixture)
    validate_price_cards(price_cards, f"{fixture['name']}.price_cards")
    validate_discount_policies(input_data.get("discount_policies", []), f"{fixture['name']}.discount_policies")
    if "raw_response" in input_data:
        helper = input_data.get("helper")
        expected_warning_codes = {
            warning.get("code")
            for warning in fixture.get("expected", {}).get("cost_ledger", {}).get("warnings", [])
        }
        expected_error_code = fixture.get("expected", {}).get("error", {}).get("code")
        if (
            "invalid_usage" not in expected_warning_codes
            and expected_error_code != "invalid_usage"
            and helper != "langchain_callback"
            and (
            input_data["extract"].get("adapter") in {
                "langchain.chat_message",
                "vercel_ai_sdk.generate_text",
                "llamaindex.token_counter",
                "haystack.generator_result",
                "litellm.proxy_response",
                "ag2.usage_summary",
                "openai_agents.usage",
                "vercel_ai_sdk.stream_text",
                "vercel_ai_sdk.stream_transcribe",
                "langsmith.run_usage",
                "semantic_kernel.telemetry",
                "openrouter.sdk_response",
            } or input_data["extract"].get("surface") in {
                "openai.responses",
                "xai.responses",
                "openai.embeddings",
                "openai.audio_transcriptions",
                "openai.images",
                "openai.usage.images",
                "openai.usage.completions",
                "openai.usage.audio_speeches",
                "openai.usage.audio_transcriptions",
                "openai.usage.embeddings",
                "openai.vector_stores",
                "openai.usage.code_interpreter_sessions",
                "openai.chat_completions",
                "meta.chat_completions",
                "meta.responses",
                "anthropic.messages",
                "openrouter.chat_completions",
                "groq.chat_completions",
                "xai.chat_completions",
                "mistral.chat_completions",
                "deepseek.chat_completions",
                "azure.openai.chat_completions",
                "huggingface.chat_completions",
                "google.gemini.generate_content",
                "google.gemini.live",
                "google.gemini.interactions",
                "vertex.gemini.generate_content",
                "aws.bedrock.converse",
                "aws.bedrock.invoke_model",
                "cohere.chat",
                "cohere.rerank",
            }
        )):
            usage_ledger = extract_usage_ledger(input_data["raw_response"], **input_data["extract"])
            validate_schema(usage_ledger, SCHEMAS["usage_ledger"], path=f"{fixture['name']}.extracted_usage_ledger")
        helper_options = {
            "price_cards": price_cards,
            "discount_policies": input_data.get("discount_policies", []),
            "mode": input_data.get("mode", "compatibility"),
            **input_data.get("options", {}),
            **input_data["extract"],
        }
        if helper == "from_langchain_message":
            return from_langchain_message(input_data["raw_response"], **helper_options)
        if helper == "from_vercel_ai_sdk_result":
            return from_vercel_ai_sdk_result(input_data["raw_response"], **helper_options)
        if helper == "from_vercel_ai_sdk_stream_finish":
            return from_vercel_ai_sdk_stream_finish(input_data["raw_response"], **helper_options)
        if helper == "from_vercel_ai_sdk_stream_transcribe_finish":
            return from_vercel_ai_sdk_stream_transcribe_finish(input_data["raw_response"], **helper_options)
        if helper == "from_llamaindex_token_counter":
            return from_llamaindex_token_counter(input_data["raw_response"], **helper_options)
        if helper == "from_haystack_generator_result":
            return from_haystack_generator_result(input_data["raw_response"], **helper_options)
        if helper == "from_litellm_response":
            return from_litellm_response(input_data["raw_response"], **helper_options)
        if helper == "from_ag2_usage_summary":
            return from_ag2_usage_summary(input_data["raw_response"], **helper_options)
        if helper == "from_openai_agents_usage":
            return from_openai_agents_usage(input_data["raw_response"], **helper_options)
        if helper == "from_langsmith_run":
            return from_langsmith_run(input_data["raw_response"], **helper_options)
        if helper == "from_semantic_kernel_telemetry":
            return from_semantic_kernel_telemetry(input_data["raw_response"], **helper_options)
        if helper == "from_openrouter_sdk_response":
            return from_openrouter_sdk_response(input_data["raw_response"], **helper_options)
        if helper == "langchain_callback":
            with track_langchain_costs(**helper_options) as callback:
                callback.on_llm_end(input_data["raw_response"])
                if not callback.latest:
                    raise AssertionError(f"{fixture['name']}: LangChain callback recorded no cost ledgers")
                return callback.latest
        return from_response(
            input_data["raw_response"],
            **helper_options,
        )

    validate_schema(input_data["usage_ledger"], SCHEMAS["usage_ledger"], path=f"{fixture['name']}.usage_ledger")
    return calculate_cost(
        usage_ledger=input_data["usage_ledger"],
        price_cards=price_cards,
        discount_policies=input_data.get("discount_policies", []),
        mode=input_data.get("mode", "compatibility"),
        **input_data.get("options", {}),
    )


def run_javascript_fixture(path: Path):
    script = f"""
      import {{ aggregateCostLedgers, calculateCost }} from {json.dumps(JAVASCRIPT_CORE.as_uri())};
      import {{ fromResponse, fromLangChainMessage, fromVercelAISDKResult, fromVercelAISDKStreamFinish, fromVercelAISDKStreamTranscribeFinish, fromLlamaIndexTokenCounter, fromHaystackGeneratorResult, fromLiteLLMResponse, fromAG2UsageSummary, fromOpenAIAgentsUsage, fromLangSmithRun, fromSemanticKernelTelemetry, fromOpenRouterSDKResponse, createRunCostVercelMiddleware, createRunCostVercelOnFinish, priceCardsFromLlmPrices, priceCardsFromSourceCache, priceCardsFromJSONFile, priceCardsFromYAMLFile, priceCardsFromModelsDev, priceCardsFromOfficialSnapshot }} from {json.dumps(JAVASCRIPT_CORE.as_uri())};
      import fs from "node:fs";
      const fixture = JSON.parse(fs.readFileSync({json.dumps(str(path))}, "utf8"));
      const input = fixture.input;
      let priceCards = input.price_cards;
      const priceSource = input.price_source || null;
      const root = {json.dumps(str(ROOT))};
      if (!priceCards && priceSource && priceSource.type === "llm-prices") priceCards = priceCardsFromLlmPrices(priceSource.data);
      if (!priceCards && priceSource && priceSource.type === "litellm") {{
        const module = await import({json.dumps(JAVASCRIPT_CORE.as_uri())});
        priceCards = module.priceCardsFromLiteLLM(priceSource.data);
      }}
      if (!priceCards && priceSource && priceSource.type === "portkey") {{
        const module = await import({json.dumps(JAVASCRIPT_CORE.as_uri())});
        priceCards = module.priceCardsFromPortkey(priceSource.data);
      }}
      if (!priceCards && priceSource && priceSource.type === "source-cache") priceCards = priceCardsFromSourceCache(priceSource.data);
      if (!priceCards && priceSource && priceSource.type === "openrouter-models") {{
        const module = await import({json.dumps(JAVASCRIPT_CORE.as_uri())});
        priceCards = module.priceCardsFromOpenRouterModels(priceSource.data);
      }}
      if (!priceCards && priceSource && priceSource.type === "models-dev") priceCards = priceCardsFromModelsDev(priceSource.data);
      if (!priceCards && priceSource && priceSource.type === "official-snapshot") priceCards = priceCardsFromOfficialSnapshot(priceSource.data);
      if (!priceCards && priceSource && priceSource.type === "user-pricing") {{
        const module = await import({json.dumps(JAVASCRIPT_CORE.as_uri())});
        priceCards = module.priceCardsFromUserPricing(priceSource.data);
      }}
      if (!priceCards && priceSource && priceSource.type === "helicone") {{
        const module = await import({json.dumps(JAVASCRIPT_CORE.as_uri())});
        priceCards = module.priceCardsFromHelicone(priceSource.data);
      }}
      if (!priceCards && priceSource && priceSource.type === "json-file") {{
        const filePath = priceSource.path.startsWith("/") ? priceSource.path : `${{root}}/${{priceSource.path}}`;
        priceCards = priceCardsFromJSONFile(filePath, {{ sourceType: priceSource.source_type || "user-pricing" }});
      }}
      if (!priceCards && priceSource && priceSource.type === "yaml-file") {{
        const filePath = priceSource.path.startsWith("/") ? priceSource.path : `${{root}}/${{priceSource.path}}`;
        priceCards = priceCardsFromYAMLFile(filePath, {{ sourceType: priceSource.source_type || "user-pricing" }});
      }}
      const responseOptions = {{
            ...input.extract,
            ...(input.options || {{}}),
            priceCards,
            discountPolicies: input.discount_policies || [],
            mode: input.mode || "compatibility"
          }};
      const result = input.cost_ledgers
        ? aggregateCostLedgers({{
            costLedgers: input.cost_ledgers,
            mode: input.mode || "compatibility",
            ...(input.options || {{}})
          }})
        : input.raw_response
        ? input.helper === "from_langchain_message"
          ? fromLangChainMessage(input.raw_response, responseOptions)
          : input.helper === "from_vercel_ai_sdk_result"
            ? fromVercelAISDKResult(input.raw_response, responseOptions)
            : input.helper === "from_vercel_ai_sdk_stream_finish"
              ? fromVercelAISDKStreamFinish(input.raw_response, responseOptions)
              : input.helper === "from_vercel_ai_sdk_stream_transcribe_finish"
                ? fromVercelAISDKStreamTranscribeFinish(input.raw_response, responseOptions)
                : input.helper === "from_llamaindex_token_counter"
                  ? fromLlamaIndexTokenCounter(input.raw_response, responseOptions)
                  : input.helper === "from_haystack_generator_result"
                    ? fromHaystackGeneratorResult(input.raw_response, responseOptions)
                    : input.helper === "from_litellm_response"
                      ? fromLiteLLMResponse(input.raw_response, responseOptions)
                      : input.helper === "from_ag2_usage_summary"
                        ? fromAG2UsageSummary(input.raw_response, responseOptions)
                        : input.helper === "from_openai_agents_usage"
                          ? fromOpenAIAgentsUsage(input.raw_response, responseOptions)
                          : input.helper === "from_langsmith_run"
                            ? fromLangSmithRun(input.raw_response, responseOptions)
                            : input.helper === "from_semantic_kernel_telemetry"
                              ? fromSemanticKernelTelemetry(input.raw_response, responseOptions)
                              : input.helper === "from_openrouter_sdk_response"
                                ? fromOpenRouterSDKResponse(input.raw_response, responseOptions)
                                : input.helper === "vercel_ai_sdk_on_finish"
                                  ? await createRunCostVercelOnFinish(responseOptions)(input.raw_response)
                                  : input.helper === "vercel_ai_sdk_middleware"
                                    ? (await createRunCostVercelMiddleware(responseOptions).wrapGenerate({{ doGenerate: async () => input.raw_response }})).runCost
                                    : fromResponse(input.raw_response, responseOptions)
        : calculateCost({{
            usageLedger: input.usage_ledger,
            priceCards,
            discountPolicies: input.discount_policies || [],
            mode: input.mode || "compatibility",
            ...(input.options || {{}})
          }});
      process.stdout.write(JSON.stringify(result));
    """
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return json.loads(completed.stdout)


def check_fixture_paths(paths: list[Path]) -> None:
    for path in paths:
        fixture = load_json(path)
        validate_schema(fixture, SCHEMAS["fixture"], path=f"{path.name}:fixture")
        if "error" in fixture["expected"]:
            expected_code = fixture["expected"]["error"]["code"]
            runners = []
            languages = expected_languages(fixture)
            if "python" in languages:
                runners.append(("python", lambda: run_python_fixture(fixture)))
            if "javascript" in languages:
                runners.append(("javascript", lambda: run_javascript_fixture(path)))
            for label, runner in runners:
                try:
                    runner()
                except Exception as exc:
                    detail = str(exc)
                    if isinstance(exc, subprocess.CalledProcessError):
                        detail = f"{exc}\nstdout={exc.stdout}\nstderr={exc.stderr}"
                    if expected_code not in detail:
                        raise AssertionError(f"{path.name}:{label}: expected error containing {expected_code!r}, got {detail}")
                else:
                    raise AssertionError(f"{path.name}:{label}: expected error containing {expected_code!r}")
            continue

        expected = fixture["expected"]["cost_ledger"]
        validate_schema(expected, SCHEMAS["cost_ledger"], path=f"{path.name}:expected")
        assert_warning_metadata(expected, f"{path.name}:expected")
        assert_cost_ledger_ordering(expected, f"{path.name}:expected")
        if "debug_trace" in expected:
            validate_schema(expected["debug_trace"], SCHEMAS["debug_trace"], path=f"{path.name}:expected.debug_trace")

        languages = expected_languages(fixture)
        if "python" in languages:
            python_result = run_python_fixture(fixture)
            validate_schema(python_result, SCHEMAS["cost_ledger"], path=f"{path.name}:python")
            assert_warning_metadata(python_result, f"{path.name}:python")
            if "debug_trace" in python_result:
                validate_schema(python_result["debug_trace"], SCHEMAS["debug_trace"], path=f"{path.name}:python.debug_trace")
            assert_total_matches_components(python_result, f"{path.name}:python")
            assert_cost_ledger_ordering(python_result, f"{path.name}:python")
            assert_subset(python_result, expected, f"{path.name}:python")

        if "javascript" in languages:
            javascript_result = run_javascript_fixture(path)
            validate_schema(javascript_result, SCHEMAS["cost_ledger"], path=f"{path.name}:javascript")
            assert_warning_metadata(javascript_result, f"{path.name}:javascript")
            if "debug_trace" in javascript_result:
                validate_schema(javascript_result["debug_trace"], SCHEMAS["debug_trace"], path=f"{path.name}:javascript.debug_trace")
            assert_total_matches_components(javascript_result, f"{path.name}:javascript")
            assert_cost_ledger_ordering(javascript_result, f"{path.name}:javascript")
            assert_subset(javascript_result, expected, f"{path.name}:javascript")


def check_runtime_boundary_contracts() -> None:
    context_probe = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from decimal import getcontext; "
                "getcontext().prec = 17; before = (getcontext().prec, getcontext().rounding); "
                "import runcost; "
                "assert (getcontext().prec, getcontext().rounding) == before"
            ),
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(PYTHON_PACKAGE)},
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if context_probe.stderr:
        raise AssertionError(f"Python decimal-context probe wrote stderr: {context_probe.stderr}")

    usage = {
        "schema_version": "0.1",
        "provider": "openai",
        "surface": "openai.responses",
        "model": {"requested": "m", "returned": "m", "billed": "m", "alias_resolution": "none"},
        "components": [{"name": "input_uncached_tokens", "quantity": "1", "unit": "token"}],
    }
    eur_card = {
        "schema_version": "0.1",
        "id": "eur-card",
        "provider": "openai",
        "surface": "openai.responses",
        "model": "m",
        "components": [{
            "usage_component": "input_uncached_tokens",
            "unit": "token",
            "price": {"amount": "1", "currency": "EUR", "per": "1"},
        }],
        "source": {"name": "test"},
    }
    try:
        calculate_cost(usage_ledger=usage, price_cards=[eur_card])
    except ValueError as error:
        if "RunCost supports USD only" not in str(error):
            raise
    else:
        raise AssertionError("Python calculator accepted a non-USD price card")
    try:
        aggregate_cost_ledgers([{"currency": "EUR", "total": "1"}])
    except ValueError as error:
        if "aggregation supports USD only" not in str(error):
            raise
    else:
        raise AssertionError("Python aggregation accepted a non-USD ledger")

    malformed_usage_cases = [
        (
            "openai",
            "openai.responses",
            {"object": "response", "model": "probe", "usage": {"input_tokens_details": {"cached_tokens": "oops"}}},
            "$.usage.input_tokens_details.cached_tokens",
        ),
        (
            "openai",
            "openai.chat_completions",
            {"model": "probe", "usage": {"completion_tokens_details": {"reasoning_tokens": "oops"}}},
            "$.usage.completion_tokens_details.reasoning_tokens",
        ),
        (
            "anthropic",
            "anthropic.messages",
            {"type": "message", "model": "claude-test", "usage": {"input_tokens": "oops", "output_tokens": 0}},
            "$.usage.input_tokens",
        ),
        (
            "google",
            "google.gemini.generate_content",
            {
                "modelVersion": "gemini-test",
                "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": "oops"},
            },
            "$.usageMetadata.candidatesTokenCount",
        ),
        (
            "bedrock",
            "aws.bedrock.converse",
            {"modelId": "bedrock-test", "usage": {"inputTokens": "oops", "outputTokens": 0}},
            "$.usage.inputTokens",
        ),
    ]
    for provider, surface, response, path in malformed_usage_cases:
        result = from_response(response, provider=provider, surface=surface, price_cards=[])
        warnings = result.get("warnings", [])
        if result.get("total") != "0" or result.get("components") != [] or len(warnings) != 1:
            raise AssertionError(f"Python malformed supported usage did not fail closed: {result!r}")
        warning = warnings[0]
        if (
            warning.get("code") != "invalid_usage"
            or warning.get("path") != path
            or warning.get("metadata", {}).get("reason") != "malformed_decimal"
        ):
            raise AssertionError(f"Python malformed supported usage was misclassified: {warning!r}")
        try:
            from_response(response, provider=provider, surface=surface, price_cards=[], mode="strict")
        except ValueError as error:
            if "invalid_usage" not in str(error):
                raise
        else:
            raise AssertionError("Python strict mode accepted malformed supported usage")

    javascript_probe = f"""
      import {{ aggregateCostLedgers, calculateCost, fromResponse }} from {json.dumps(JAVASCRIPT_CORE.as_uri())};
      const usageLedger = {json.dumps(usage)};
      const priceCards = [{json.dumps(eur_card)}];
      let cardRejected = false;
      try {{ calculateCost({{ usageLedger, priceCards }}); }}
      catch (error) {{ cardRejected = error.message.includes("RunCost supports USD only"); }}
      if (!cardRejected) throw new Error("JavaScript calculator accepted a non-USD price card");
      let ledgerRejected = false;
      try {{ aggregateCostLedgers({{ costLedgers: [{{ currency: "EUR", total: "1" }}] }}); }}
      catch (error) {{ ledgerRejected = error.message.includes("aggregation supports USD only"); }}
      if (!ledgerRejected) throw new Error("JavaScript aggregation accepted a non-USD ledger");
      const malformedUsageCases = [
        [
          "openai",
          "openai.responses",
          {{ object: "response", model: "probe", usage: {{ input_tokens_details: {{ cached_tokens: "oops" }} }} }},
          "$.usage.input_tokens_details.cached_tokens"
        ],
        [
          "openai",
          "openai.chat_completions",
          {{ model: "probe", usage: {{ completion_tokens_details: {{ reasoning_tokens: "oops" }} }} }},
          "$.usage.completion_tokens_details.reasoning_tokens"
        ],
        [
          "anthropic",
          "anthropic.messages",
          {{ type: "message", model: "claude-test", usage: {{ input_tokens: "oops", output_tokens: 0 }} }},
          "$.usage.input_tokens"
        ],
        [
          "google",
          "google.gemini.generate_content",
          {{ modelVersion: "gemini-test", usageMetadata: {{ promptTokenCount: 1, candidatesTokenCount: "oops" }} }},
          "$.usageMetadata.candidatesTokenCount"
        ],
        [
          "bedrock",
          "aws.bedrock.converse",
          {{ modelId: "bedrock-test", usage: {{ inputTokens: "oops", outputTokens: 0 }} }},
          "$.usage.inputTokens"
        ]
      ];
      for (const [provider, surface, response, path] of malformedUsageCases) {{
        const result = fromResponse(response, {{ provider, surface, priceCards: [] }});
        const warning = result.warnings?.[0];
        if (result.total !== "0" || result.components?.length !== 0 || result.warnings?.length !== 1) {{
          throw new Error(`JavaScript malformed supported usage did not fail closed: ${{JSON.stringify(result)}}`);
        }}
        if (warning.code !== "invalid_usage" || warning.path !== path || warning.metadata?.reason !== "malformed_decimal") {{
          throw new Error(`JavaScript malformed supported usage was misclassified: ${{JSON.stringify(warning)}}`);
        }}
        let strictRejected = false;
        try {{ fromResponse(response, {{ provider, surface, priceCards: [], mode: "strict" }}); }}
        catch (error) {{ strictRejected = error.message.includes("invalid_usage"); }}
        if (!strictRejected) throw new Error("JavaScript strict mode accepted malformed supported usage");
      }}
    """
    subprocess.run(
        ["node", "--input-type=module", "-e", javascript_probe],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run shared RunCost fixture conformance checks.")
    parser.add_argument(
        "--fixture",
        action="append",
        default=[],
        help="Specific fixture path to check. May be passed more than once. Defaults to fixtures/*.json.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = [Path(value) for value in args.fixture] if args.fixture else DEFAULT_FIXTURES
    check_schema_validator_contract()
    check_runtime_boundary_contracts()
    check_fixture_paths(paths)
    print(f"Checked {len(paths)} fixtures against Python and JavaScript cores.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
