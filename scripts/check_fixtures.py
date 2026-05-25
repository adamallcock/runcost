#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON_PACKAGE = ROOT / "packages" / "python"
JAVASCRIPT_CORE = ROOT / "packages" / "javascript" / "core" / "index.js"
FIXTURES = sorted((ROOT / "fixtures").glob("*.json"))

sys.path.insert(0, str(PYTHON_PACKAGE))

from runcost import (  # noqa: E402
    calculate_cost,
    extract_usage_ledger,
    from_langchain_message,
    from_llamaindex_token_counter,
    from_response,
    from_vercel_ai_sdk_result,
    price_cards_from_litellm,
    price_cards_from_llm_prices,
    price_cards_from_openrouter_models,
    price_cards_from_portkey,
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


def _type_matches(value, expected_type):
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "null":
        return value is None
    return True


def _resolve_ref(schema, root):
    ref = schema.get("$ref")
    if not ref:
        return schema
    if not ref.startswith("#/"):
        raise AssertionError(f"Unsupported schema ref: {ref}")
    current = root
    for part in ref[2:].split("/"):
        current = current[part]
    return current


def validate_schema(value, schema, root=None, path="$"):
    root = root or schema
    schema = _resolve_ref(schema, root)

    if "const" in schema and value != schema["const"]:
        raise AssertionError(f"{path}: expected const {schema['const']!r}, got {value!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise AssertionError(f"{path}: expected one of {schema['enum']!r}, got {value!r}")

    expected_type = schema.get("type")
    if isinstance(expected_type, list):
        if not any(_type_matches(value, candidate) for candidate in expected_type):
            raise AssertionError(f"{path}: expected type {expected_type!r}, got {type(value).__name__}")
    elif expected_type and not _type_matches(value, expected_type):
        raise AssertionError(f"{path}: expected type {expected_type!r}, got {type(value).__name__}")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise AssertionError(f"{path}: shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise AssertionError(f"{path}: longer than maxLength {schema['maxLength']}")
        if "pattern" in schema:
            import re

            if not re.match(schema["pattern"], value):
                raise AssertionError(f"{path}: does not match pattern {schema['pattern']!r}")

    if isinstance(value, int) and "minimum" in schema and value < schema["minimum"]:
        raise AssertionError(f"{path}: below minimum {schema['minimum']}")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise AssertionError(f"{path}: fewer than minItems {schema['minItems']}")
        if "items" in schema:
            for index, item in enumerate(value):
                validate_schema(item, schema["items"], root, f"{path}[{index}]")

    if isinstance(value, dict):
        for required in schema.get("required", []):
            if required not in value:
                raise AssertionError(f"{path}.{required}: missing required property")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(properties))
            if extra:
                raise AssertionError(f"{path}: unexpected properties {extra!r}")
        for key, child in value.items():
            if key in properties:
                validate_schema(child, properties[key], root, f"{path}.{key}")


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


def resolve_python_price_cards(fixture):
    input_data = fixture["input"]
    if "price_cards" in input_data:
        return input_data["price_cards"]

    source = input_data["price_source"]
    if source["type"] == "llm-prices":
        return price_cards_from_llm_prices(source["data"])
    if source["type"] == "litellm":
        return price_cards_from_litellm(source["data"])
    if source["type"] == "openrouter-models":
        return price_cards_from_openrouter_models(source["data"])
    if source["type"] == "portkey":
        return price_cards_from_portkey(source["data"])
    raise AssertionError(f"Unsupported price source: {source['type']}")


def run_python_fixture(fixture):
    input_data = fixture["input"]
    price_cards = resolve_python_price_cards(fixture)
    validate_price_cards(price_cards, f"{fixture['name']}.price_cards")
    validate_discount_policies(input_data.get("discount_policies", []), f"{fixture['name']}.discount_policies")
    if "raw_response" in input_data:
        if input_data["extract"].get("adapter") in {
            "langchain.chat_message",
            "vercel_ai_sdk.generate_text",
            "llamaindex.token_counter",
        } or input_data["extract"].get("surface") in {
            "openai.responses",
            "openai.chat_completions",
            "anthropic.messages",
            "openrouter.chat_completions",
            "groq.chat_completions",
            "xai.chat_completions",
            "mistral.chat_completions",
            "deepseek.chat_completions",
            "azure.openai.chat_completions",
            "huggingface.chat_completions",
            "google.gemini.generate_content",
            "vertex.gemini.generate_content",
            "aws.bedrock.converse",
            "cohere.chat",
        }:
            usage_ledger = extract_usage_ledger(input_data["raw_response"], **input_data["extract"])
            validate_schema(usage_ledger, SCHEMAS["usage_ledger"], path=f"{fixture['name']}.extracted_usage_ledger")
        helper = input_data.get("helper")
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
        if helper == "from_llamaindex_token_counter":
            return from_llamaindex_token_counter(input_data["raw_response"], **helper_options)
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
      import {{ calculateCost }} from {json.dumps(JAVASCRIPT_CORE.as_uri())};
      import {{ fromResponse, fromLangChainMessage, fromVercelAISDKResult, fromLlamaIndexTokenCounter, priceCardsFromLlmPrices }} from {json.dumps(JAVASCRIPT_CORE.as_uri())};
      import fs from "node:fs";
      const fixture = JSON.parse(fs.readFileSync({json.dumps(str(path))}, "utf8"));
      const input = fixture.input;
      let priceCards = input.price_cards;
      if (!priceCards && input.price_source.type === "llm-prices") priceCards = priceCardsFromLlmPrices(input.price_source.data);
      if (!priceCards && input.price_source.type === "litellm") {{
        const module = await import({json.dumps(JAVASCRIPT_CORE.as_uri())});
        priceCards = module.priceCardsFromLiteLLM(input.price_source.data);
      }}
      if (!priceCards && input.price_source.type === "portkey") {{
        const module = await import({json.dumps(JAVASCRIPT_CORE.as_uri())});
        priceCards = module.priceCardsFromPortkey(input.price_source.data);
      }}
      if (!priceCards && input.price_source.type === "openrouter-models") {{
        const module = await import({json.dumps(JAVASCRIPT_CORE.as_uri())});
        priceCards = module.priceCardsFromOpenRouterModels(input.price_source.data);
      }}
      const responseOptions = {{
            ...input.extract,
            ...(input.options || {{}}),
            priceCards,
            discountPolicies: input.discount_policies || [],
            mode: input.mode || "compatibility"
          }};
      const result = input.raw_response
        ? input.helper === "from_langchain_message"
          ? fromLangChainMessage(input.raw_response, responseOptions)
          : input.helper === "from_vercel_ai_sdk_result"
            ? fromVercelAISDKResult(input.raw_response, responseOptions)
            : input.helper === "from_llamaindex_token_counter"
              ? fromLlamaIndexTokenCounter(input.raw_response, responseOptions)
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


def main() -> int:
    for path in FIXTURES:
        fixture = load_json(path)
        validate_schema(fixture, SCHEMAS["fixture"], path=f"{path.name}:fixture")
        if "error" in fixture["expected"]:
            expected_code = fixture["expected"]["error"]["code"]
            for label, runner in (("python", lambda: run_python_fixture(fixture)), ("javascript", lambda: run_javascript_fixture(path))):
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
        if "debug_trace" in expected:
            validate_schema(expected["debug_trace"], SCHEMAS["debug_trace"], path=f"{path.name}:expected.debug_trace")

        python_result = run_python_fixture(fixture)
        validate_schema(python_result, SCHEMAS["cost_ledger"], path=f"{path.name}:python")
        if "debug_trace" in python_result:
            validate_schema(python_result["debug_trace"], SCHEMAS["debug_trace"], path=f"{path.name}:python.debug_trace")
        assert_total_matches_components(python_result, f"{path.name}:python")
        assert_subset(python_result, expected, f"{path.name}:python")

        javascript_result = run_javascript_fixture(path)
        validate_schema(javascript_result, SCHEMAS["cost_ledger"], path=f"{path.name}:javascript")
        if "debug_trace" in javascript_result:
            validate_schema(javascript_result["debug_trace"], SCHEMAS["debug_trace"], path=f"{path.name}:javascript.debug_trace")
        assert_total_matches_components(javascript_result, f"{path.name}:javascript")
        assert_subset(javascript_result, expected, f"{path.name}:javascript")

    print(f"Checked {len(FIXTURES)} fixtures against Python and JavaScript cores.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
