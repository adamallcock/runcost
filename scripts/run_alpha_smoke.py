#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "python"))
SAMPLE_FILE = ROOT / "fixtures" / "source-files" / "alpha-smoke-samples.json"
VERCEL_SMOKE_COMMAND = ROOT / "scripts" / "run_vercel_alpha_smoke.mjs"
LANGCHAIN_SMOKE_COMMAND = ROOT / "scripts" / "run_langchain_alpha_smoke.py"

from runcost import (  # noqa: E402
    aggregate_cost_ledgers,
    calculate_cost,
    from_langchain_message,
    from_openrouter_sdk_response,
    from_response,
    from_vercel_ai_sdk_stream_finish,
)
from check_alpha_smoke_contract import validate_report as validate_alpha_smoke_report  # noqa: E402

ScenarioResult = dict[str, Any]

SAMPLE_RETRIEVED_AT = "2026-05-26T00:00:00Z"
_SAMPLES: dict[str, Any] | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sample_payload(scenario: str, key: str) -> dict[str, Any]:
    global _SAMPLES
    if _SAMPLES is None:
        _SAMPLES = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
    return _SAMPLES["scenarios"][scenario][key]


def price_card(provider: str, surface: str, model: str, components: dict[str, tuple[str, str, str]]) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "id": f"{provider}:{model}:alpha-smoke-sample",
        "provider": provider,
        "surface": surface,
        "model": model,
        "components": [
            {
                "usage_component": name,
                "unit": unit,
                "price": {"amount": amount, "currency": "USD", "per": per},
            }
            for name, (unit, amount, per) in components.items()
        ],
        "source": {
            "name": "alpha-smoke-sample",
            "retrieved_at": SAMPLE_RETRIEVED_AT,
        },
    }


def token_components(input_price: str = "1", output_price: str = "2") -> dict[str, tuple[str, str, str]]:
    return {
        "input_uncached_tokens": ("token", input_price, "1000000"),
        "input_cache_read_tokens": ("token", "0.1", "1000000"),
        "input_cache_write_tokens": ("token", "1.25", "1000000"),
        "input_cache_write_1h_tokens": ("token", "2", "1000000"),
        "output_text_tokens": ("token", output_price, "1000000"),
        "output_reasoning_tokens": ("token", output_price, "1000000"),
    }


def evidence(
    ledger: dict[str, Any],
    *,
    usage_fields: list[str],
    source: str,
    exactness: str = "synthetic_sample",
) -> dict[str, Any]:
    return {
        "provider": ledger.get("provider"),
        "surface": ledger.get("surface"),
        "model": ledger.get("model", {}),
        "component_names": [component["name"] for component in ledger.get("components", [])],
        "warning_codes": [warning["code"] for warning in ledger.get("warnings", [])],
        "total": ledger.get("total"),
        "price_source_names": [source.get("name") for source in ledger.get("price_sources", [])],
        "usage_fields_present": sorted(usage_fields),
        "raw_response_retained": False,
        "exactness": exactness,
        "source": source,
    }


def passed(
    scenario: str,
    ledger: dict[str, Any],
    *,
    usage_fields: list[str],
    source: str,
    exactness: str = "synthetic_sample",
) -> ScenarioResult:
    return {
        "scenario": scenario,
        "status": "passed",
        "evidence": evidence(ledger, usage_fields=usage_fields, source=source, exactness=exactness),
        "next_action": {
            "type": "none",
            "reason": "Sanitized smoke output matched an existing extractor path.",
        },
    }


def skipped(scenario: str, reason: str) -> ScenarioResult:
    return {
        "scenario": scenario,
        "status": "skipped",
        "evidence": {
            "component_names": [],
            "warning_codes": [],
            "total": "0",
            "usage_fields_present": [],
            "raw_response_retained": False,
            "exactness": "not_run",
            "source": "live",
        },
        "next_action": {
            "type": "documented_limitation",
            "reason": reason,
        },
    }


def needs_product_truth(scenario: str, reason: str, ledger: dict[str, Any] | None = None) -> ScenarioResult:
    return {
        "scenario": scenario,
        "status": "needs_product_truth",
        "evidence": evidence(ledger or {}, usage_fields=[], source="live", exactness="requires_review"),
        "next_action": {
            "type": "fixture_or_warning_or_limitation",
            "reason": reason,
        },
    }


def smoke_openai_responses_sample(_args: argparse.Namespace) -> ScenarioResult:
    model = "gpt-alpha-smoke"
    response = sample_payload("openai_responses", "response")
    cards = [
        price_card(
            "openai",
            "openai.responses",
            model,
            {
                **token_components(),
                "web_search_units": ("search", "0.01", "1"),
                "tool_call_units": ("call", "0.001", "1"),
            },
        )
    ]
    ledger = from_response(response, provider="openai", surface="openai.responses", price_cards=cards)
    return passed(
        "openai_responses",
        ledger,
        usage_fields=["input_tokens", "input_tokens_details.cached_tokens", "output_tokens", "output_tokens_details.reasoning_tokens"],
        source="sample",
    )


def smoke_anthropic_prompt_caching_sample(_args: argparse.Namespace) -> ScenarioResult:
    model = "claude-alpha-smoke"
    response = sample_payload("anthropic_prompt_caching", "response")
    cards = [price_card("anthropic", "anthropic.messages", model, token_components("3", "15"))]
    ledger = from_response(response, provider="anthropic", surface="anthropic.messages", price_cards=cards)
    return passed(
        "anthropic_prompt_caching",
        ledger,
        usage_fields=[
            "cache_creation_input_tokens",
            "cache_creation_input_tokens_1h",
            "cache_read_input_tokens",
            "input_tokens",
            "output_tokens",
        ],
        source="sample",
    )


def smoke_vercel_stream_sample(_args: argparse.Namespace) -> ScenarioResult:
    model = "gpt-alpha-smoke"
    finish = sample_payload("vercel_ai_sdk_stream_text", "finish")
    cards = [price_card("openai", "framework.vercel_ai_sdk", model, token_components())]
    ledger = from_vercel_ai_sdk_stream_finish(finish, provider="openai", surface="framework.vercel_ai_sdk", price_cards=cards)
    return passed(
        "vercel_ai_sdk_stream_text",
        ledger,
        usage_fields=[
            "totalUsage.inputTokens",
            "totalUsage.inputTokenDetails.cacheReadTokens",
            "totalUsage.inputTokenDetails.cacheWriteTokens",
            "totalUsage.outputTokenDetails.reasoningTokens",
        ],
        source="sample",
    )


def smoke_langchain_agent_sample(_args: argparse.Namespace) -> ScenarioResult:
    model = "gpt-alpha-smoke"
    message = sample_payload("langchain_agent_run", "message")
    cards = [price_card("openai", "framework.langchain.chat", model, token_components())]
    ledger = from_langchain_message(message, provider="openai", surface="framework.langchain.chat", price_cards=cards)
    return passed(
        "langchain_agent_run",
        ledger,
        usage_fields=[
            "usage_metadata.input_tokens",
            "usage_metadata.input_token_details.cache_read",
            "usage_metadata.output_token_details.reasoning",
        ],
        source="sample",
    )


def smoke_openrouter_cost_compare_sample(_args: argparse.Namespace) -> ScenarioResult:
    model = "openai/gpt-alpha-smoke"
    response = sample_payload("openrouter_cost_compare", "response")
    cards = [price_card("openrouter", "openrouter.chat_completions", model, token_components("2", "8"))]
    ledger = from_openrouter_sdk_response(response, surface="openrouter.chat_completions", price_cards=cards)
    return passed(
        "openrouter_cost_compare",
        ledger,
        usage_fields=["usage.prompt_tokens", "usage.completion_tokens", "usage.cost"],
        source="sample",
    )


def smoke_multi_provider_discount_sample(_args: argparse.Namespace) -> ScenarioResult:
    openai_usage = {
        "schema_version": "0.1",
        "provider": "openai",
        "surface": "openai.responses",
        "model": {"requested": "gpt-alpha-smoke", "billed": "gpt-alpha-smoke", "alias_resolution": "none"},
        "components": [{"name": "input_uncached_tokens", "quantity": "100", "unit": "token"}],
    }
    anthropic_usage = {
        "schema_version": "0.1",
        "provider": "anthropic",
        "surface": "anthropic.messages",
        "model": {"requested": "claude-alpha-smoke", "billed": "claude-alpha-smoke", "alias_resolution": "none"},
        "components": [{"name": "output_text_tokens", "quantity": "50", "unit": "token"}],
    }
    cards = [
        price_card("openai", "openai.responses", "gpt-alpha-smoke", {"input_uncached_tokens": ("token", "1", "1000000")}),
        price_card("anthropic", "anthropic.messages", "claude-alpha-smoke", {"output_text_tokens": ("token", "15", "1000000")}),
    ]
    discount_policies = [
        {
            "schema_version": "0.1",
            "id": "alpha-openai-discount",
            "match": {"provider": "openai"},
            "adjustment": {"type": "percentage_discount", "value": "4"},
        }
    ]
    ledgers = [
        calculate_cost(usage_ledger=openai_usage, price_cards=cards, discount_policies=discount_policies),
        calculate_cost(usage_ledger=anthropic_usage, price_cards=cards, discount_policies=discount_policies),
    ]
    ledger = aggregate_cost_ledgers(ledgers)
    return passed(
        "multi_provider_discount",
        ledger,
        usage_fields=["usage_ledger.components", "discount_policies.match.provider"],
        source="sample",
    )


def post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def live_openai_responses(args: argparse.Namespace) -> ScenarioResult:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return skipped("openai_responses", "OPENAI_API_KEY is not set.")
    model = os.environ.get("RUNCOST_SMOKE_OPENAI_MODEL", "gpt-4.1-mini")
    try:
        response = post_json(
            "https://api.openai.com/v1/responses",
            {"Authorization": f"Bearer {api_key}"},
            {
                "model": model,
                "input": "Return exactly the word pong.",
                "max_output_tokens": 16,
            },
        )
        cards = [price_card("openai", "openai.responses", response.get("model", model), token_components())]
        ledger = from_response(response, provider="openai", surface="openai.responses", price_cards=cards)
        return passed(
            "openai_responses",
            ledger,
            usage_fields=sorted((response.get("usage") or {}).keys()),
            source="live",
            exactness="sample_prices_not_invoice_exact",
        )
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
        return needs_product_truth("openai_responses", f"Live OpenAI smoke failed with sanitized error type {type(exc).__name__}.")


def live_anthropic_prompt_caching(args: argparse.Namespace) -> ScenarioResult:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return skipped("anthropic_prompt_caching", "ANTHROPIC_API_KEY is not set.")
    model = os.environ.get("RUNCOST_SMOKE_ANTHROPIC_MODEL", "claude-sonnet-4-5")
    try:
        response = post_json(
            "https://api.anthropic.com/v1/messages",
            {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            {
                "model": model,
                "max_tokens": 16,
                "system": [
                    {
                        "type": "text",
                        "text": "You are a smoke-test assistant. Return short answers.",
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                "messages": [{"role": "user", "content": "Return exactly the word pong."}],
            },
        )
        cards = [price_card("anthropic", "anthropic.messages", response.get("model", model), token_components("3", "15"))]
        ledger = from_response(response, provider="anthropic", surface="anthropic.messages", price_cards=cards)
        return passed(
            "anthropic_prompt_caching",
            ledger,
            usage_fields=sorted((response.get("usage") or {}).keys()),
            source="live",
            exactness="sample_prices_not_invoice_exact",
        )
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
        return needs_product_truth("anthropic_prompt_caching", f"Live Anthropic smoke failed with sanitized error type {type(exc).__name__}.")


def live_openrouter_cost_compare(args: argparse.Namespace) -> ScenarioResult:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return skipped("openrouter_cost_compare", "OPENROUTER_API_KEY is not set.")
    model = os.environ.get("RUNCOST_SMOKE_OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")
    try:
        response = post_json(
            "https://openrouter.ai/api/v1/chat/completions",
            {"Authorization": f"Bearer {api_key}"},
            {
                "model": model,
                "messages": [{"role": "user", "content": "Return exactly the word pong."}],
                "max_tokens": 16,
            },
        )
        cards = [price_card("openrouter", "openrouter.chat_completions", response.get("model", model), token_components("2", "8"))]
        ledger = from_openrouter_sdk_response(response, surface="openrouter.chat_completions", price_cards=cards)
        return passed(
            "openrouter_cost_compare",
            ledger,
            usage_fields=sorted((response.get("usage") or {}).keys()),
            source="live",
            exactness="sample_prices_not_invoice_exact",
        )
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
        return needs_product_truth("openrouter_cost_compare", f"Live OpenRouter smoke failed with sanitized error type {type(exc).__name__}.")


def framework_smoke_result(scenario: str, command: list[str]) -> ScenarioResult:
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / f"{scenario}.json"
            subprocess.run(
                [
                    *command,
                    "--mode",
                    "live",
                    "--output",
                    str(output),
                    "--allow-sample-prices",
                ],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            report = json.loads(output.read_text(encoding="utf-8"))
        return {
            "scenario": report["scenario"],
            "status": report["status"],
            "evidence": report["evidence"],
            "next_action": report["next_action"],
        }
    except (
        FileNotFoundError,
        json.JSONDecodeError,
        KeyError,
        OSError,
        subprocess.CalledProcessError,
    ) as exc:
        return needs_product_truth(
            scenario,
            f"Framework smoke child process failed with sanitized error type {type(exc).__name__}.",
        )


def live_vercel_ai_sdk_stream_text(_args: argparse.Namespace) -> ScenarioResult:
    return framework_smoke_result("vercel_ai_sdk_stream_text", ["node", str(VERCEL_SMOKE_COMMAND)])


def live_langchain_agent_run(_args: argparse.Namespace) -> ScenarioResult:
    return framework_smoke_result("langchain_agent_run", [sys.executable, str(LANGCHAIN_SMOKE_COMMAND)])


SAMPLE_SCENARIOS: dict[str, Callable[[argparse.Namespace], ScenarioResult]] = {
    "openai_responses": smoke_openai_responses_sample,
    "anthropic_prompt_caching": smoke_anthropic_prompt_caching_sample,
    "vercel_ai_sdk_stream_text": smoke_vercel_stream_sample,
    "langchain_agent_run": smoke_langchain_agent_sample,
    "openrouter_cost_compare": smoke_openrouter_cost_compare_sample,
    "multi_provider_discount": smoke_multi_provider_discount_sample,
}

LIVE_SCENARIOS: dict[str, Callable[[argparse.Namespace], ScenarioResult]] = {
    "openai_responses": live_openai_responses,
    "anthropic_prompt_caching": live_anthropic_prompt_caching,
    "openrouter_cost_compare": live_openrouter_cost_compare,
    "vercel_ai_sdk_stream_text": live_vercel_ai_sdk_stream_text,
    "langchain_agent_run": live_langchain_agent_run,
    "multi_provider_discount": smoke_multi_provider_discount_sample,
}


def selected_scenarios(raw: str | None, available: dict[str, Callable[[argparse.Namespace], ScenarioResult]]) -> list[str]:
    if not raw:
        return list(available.keys())
    requested = [item.strip() for item in raw.split(",") if item.strip()]
    unknown = sorted(set(requested) - set(available))
    if unknown:
        raise SystemExit(f"Unknown alpha smoke scenario(s): {', '.join(unknown)}")
    return requested


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    available = SAMPLE_SCENARIOS if args.mode == "sample" else LIVE_SCENARIOS
    results = [available[name](args) for name in selected_scenarios(args.scenarios, available)]
    summary = {
        "total": len(results),
        "passed": sum(1 for result in results if result["status"] == "passed"),
        "skipped": sum(1 for result in results if result["status"] == "skipped"),
        "needs_product_truth": sum(1 for result in results if result["status"] == "needs_product_truth"),
        "failed": sum(1 for result in results if result["status"] == "failed"),
    }
    return {
        "schema_version": "0.1",
        "generated_at": utc_now(),
        "mode": args.mode,
        "sanitized": True,
        "safe_to_attach_to_issue": True,
        "sample_prices": args.allow_sample_prices,
        "summary": summary,
        "scenarios": results,
        "product_truth_policy": {
            "needs_product_truth": "Convert every live discrepancy into a fixture, structured warning, documented limitation, or extractor/source-adapter fix.",
            "privacy": "The report intentionally omits prompts, messages, response content, headers, account identifiers, and raw provider responses.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run optional sanitized RunCost alpha smoke scenarios.")
    parser.add_argument("--mode", choices=["sample", "live"], default="sample")
    parser.add_argument("--scenarios", help="Comma-separated scenario names. Defaults to all scenarios for the selected mode.")
    parser.add_argument("--output", required=True, help="Path to write sanitized JSON evidence.")
    parser.add_argument(
        "--allow-sample-prices",
        action="store_true",
        help="Acknowledge that smoke ledgers use sample price cards and are not invoice-exact.",
    )
    args = parser.parse_args()

    if not args.allow_sample_prices:
        raise SystemExit("--allow-sample-prices is required so smoke output is not mistaken for invoice-exact pricing.")

    report = build_report(args)
    validate_alpha_smoke_report(report)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote sanitized alpha smoke report to {output}")
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
