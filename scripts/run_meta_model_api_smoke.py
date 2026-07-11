#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "python"))

from runcost import (  # noqa: E402
    from_response,
    price_cards_from_official_snapshot,
)

DEFAULT_BASE_URL = "https://api.meta.ai/v1"
DEFAULT_MODEL = "muse-spark-1.1"
SAMPLE_RETRIEVED_AT = "2026-07-09T00:00:00Z"
META_PREVIEW_SNAPSHOT = ROOT / "fixtures" / "source-files" / "meta-reviewed-preview-pricing-snapshot.json"
META_PREVIEW_SOURCE_NAME = "Meta Model API reviewed public-preview pricing snapshot"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def request_json(
    method: str,
    url: str,
    *,
    api_key: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def sample_models(model: str) -> tuple[int, dict[str, Any]]:
    return 200, {
        "object": "list",
        "data": [
            {
                "id": model,
                "object": "model",
            }
        ],
    }


def sample_chat_completion(model: str) -> tuple[int, dict[str, Any]]:
    return 200, {
        "id": "chatcmpl-sanitized-meta-smoke",
        "object": "chat.completion",
        "created": 1783627200,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": None, "refusal": None},
                "finish_reason": "length",
                "logprobs": None,
            }
        ],
        "usage": {
            "prompt_tokens": 15,
            "prompt_tokens_details": {"cached_tokens": 11},
            "completion_tokens": 8,
            "completion_tokens_details": {"reasoning_tokens": 5},
            "total_tokens": 23,
        },
    }


def sample_responses(model: str) -> tuple[int, dict[str, Any]]:
    return 200, {
        "id": "resp_sanitized_meta_smoke",
        "object": "response",
        "created_at": 1783627200,
        "status": "completed",
        "model": model,
        "output": [],
        "usage": {
            "input_tokens": 15,
            "input_tokens_details": {"cached_tokens": 11},
            "output_tokens": 16,
            "output_tokens_details": {"reasoning_tokens": 13},
            "total_tokens": 31,
        },
    }


def summarize_models(status: int, response: dict[str, Any]) -> dict[str, Any]:
    models = response.get("data") if isinstance(response.get("data"), list) else []
    model_ids = []
    for item in models:
        if isinstance(item, dict):
            model_id = item.get("id") or item.get("model") or item.get("name")
            if model_id:
                model_ids.append(str(model_id))
    return {
        "status": status,
        "object": response.get("object"),
        "model_count": len(models),
        "model_ids": model_ids[:20],
        "raw_response_retained": False,
    }


def summarize_chat(status: int, response: dict[str, Any]) -> dict[str, Any]:
    choices = response.get("choices") if isinstance(response.get("choices"), list) else []
    first_choice = choices[0] if choices and isinstance(choices[0], dict) else {}
    message = first_choice.get("message") if isinstance(first_choice.get("message"), dict) else {}
    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    prompt_details = usage.get("prompt_tokens_details") if isinstance(usage.get("prompt_tokens_details"), dict) else {}
    completion_details = usage.get("completion_tokens_details") if isinstance(usage.get("completion_tokens_details"), dict) else {}
    return {
        "status": status,
        "object": response.get("object"),
        "model": response.get("model"),
        "choice_count": len(choices),
        "finish_reason": first_choice.get("finish_reason"),
        "message_role": message.get("role"),
        "message_content_present": message.get("content") is not None,
        "message_refusal_present": message.get("refusal") is not None,
        "usage_keys": sorted(usage),
        "prompt_detail_keys": sorted(prompt_details),
        "completion_detail_keys": sorted(completion_details),
        "raw_response_retained": False,
    }


def summarize_responses(status: int, response: dict[str, Any]) -> dict[str, Any]:
    output = response.get("output") if isinstance(response.get("output"), list) else []
    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    input_details = usage.get("input_tokens_details") if isinstance(usage.get("input_tokens_details"), dict) else {}
    output_details = usage.get("output_tokens_details") if isinstance(usage.get("output_tokens_details"), dict) else {}
    return {
        "status": status,
        "object": response.get("object"),
        "model": response.get("model"),
        "response_status": response.get("status"),
        "output_count": len(output),
        "usage_keys": sorted(usage),
        "input_detail_keys": sorted(input_details),
        "output_detail_keys": sorted(output_details),
        "raw_response_retained": False,
    }


def ledger_evidence(response: dict[str, Any], *, surface: str) -> dict[str, Any]:
    preview_snapshot = json.loads(META_PREVIEW_SNAPSHOT.read_text(encoding="utf-8"))
    preview_cards = price_cards_from_official_snapshot(preview_snapshot)
    ledger = from_response(
        response,
        provider="meta",
        surface=surface,
        model=response.get("model") or DEFAULT_MODEL,
        price_cards=preview_cards,
        price_source_priority=[META_PREVIEW_SOURCE_NAME],
    )
    return {
        "provider": ledger.get("provider"),
        "surface": ledger.get("surface"),
        "model": ledger.get("model", {}),
        "component_names": [component.get("name") for component in ledger.get("components", [])],
        "warning_codes": [warning.get("code") for warning in ledger.get("warnings", [])],
        "total": ledger.get("total"),
        "price_source_names": [source.get("name") for source in ledger.get("price_sources", [])],
        "raw_response_retained": False,
    }


def skipped_report(args: argparse.Namespace, reason: str) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "generated_at": utc_now(),
        "mode": args.mode,
        "provider": "meta",
        "base_url": args.base_url,
        "model": args.model,
        "sanitized": True,
        "safe_to_attach_to_issue": True,
        "secret_values_emitted": False,
        "raw_response_retained": False,
        "status": "skipped",
        "reason": reason,
        "product_truth_policy": {
            "privacy": "The report omits prompts, messages, response content, headers, account identifiers, and raw provider responses.",
        },
    }


def failed_report(args: argparse.Namespace, reason: str) -> dict[str, Any]:
    report = skipped_report(args, reason)
    report["status"] = "needs_product_truth"
    return report


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    if args.mode == "live":
        api_key = os.environ.get("META_API_KEY")
        if not api_key:
            return skipped_report(args, "META_API_KEY is not set.")
        try:
            models_status, models_response = request_json("GET", f"{args.base_url.rstrip('/')}/models", api_key=api_key)
            chat_status, chat_response = request_json(
                "POST",
                f"{args.base_url.rstrip('/')}/chat/completions",
                api_key=api_key,
                payload={
                    "model": args.model,
                    "messages": [{"role": "user", "content": "Reply with exactly: runcost-ok"}],
                    "max_tokens": args.max_tokens,
                    "temperature": 0,
                },
            )
            responses_status, responses_response = request_json(
                "POST",
                f"{args.base_url.rstrip('/')}/responses",
                api_key=api_key,
                payload={
                    "model": args.model,
                    "input": "Reply with exactly: runcost-ok",
                    "max_output_tokens": args.max_output_tokens,
                    "temperature": 0,
                },
            )
        except urllib.error.HTTPError as exc:
            return failed_report(args, f"Meta Model API smoke failed with HTTP {exc.code}.")
        except (TimeoutError, urllib.error.URLError, ValueError) as exc:
            return failed_report(args, f"Meta Model API smoke failed with sanitized error type {type(exc).__name__}.")
        exactness = "live_provider_response_catalog_prices_not_invoice_exact"
    else:
        models_status, models_response = sample_models(args.model)
        chat_status, chat_response = sample_chat_completion(args.model)
        responses_status, responses_response = sample_responses(args.model)
        exactness = "sanitized_sample_catalog_prices_not_invoice_exact"

    chat_ledger = ledger_evidence(chat_response, surface="meta.chat_completions")
    responses_ledger = ledger_evidence(responses_response, surface="meta.responses")
    status = "passed"
    for ledger in [chat_ledger, responses_ledger]:
        if ledger["warning_codes"]:
            status = "needs_product_truth"

    return {
        "schema_version": "0.1",
        "generated_at": utc_now(),
        "mode": args.mode,
        "provider": "meta",
        "base_url": args.base_url,
        "model": args.model,
        "sanitized": True,
        "safe_to_attach_to_issue": True,
        "secret_values_emitted": False,
        "raw_response_retained": False,
        "status": status,
        "exactness": exactness,
        "pricing_authority": "reviewed_preview_not_primary_source_verified",
        "models": summarize_models(models_status, models_response),
        "chat_completions": {
            "surface": "meta.chat_completions",
            "response": summarize_chat(chat_status, chat_response),
            "ledger": chat_ledger,
        },
        "responses": {
            "surface": "meta.responses",
            "response": summarize_responses(responses_status, responses_response),
            "ledger": responses_ledger,
        },
        "source": {
            "name": "meta-model-api-live-smoke" if args.mode == "live" else "meta-model-api-sample-smoke",
            "url": "https://developer.meta.com/ai/resources/blog/build-with-muse-spark/",
            "retrieved_at": SAMPLE_RETRIEVED_AT,
        },
        "product_truth_policy": {
            "needs_product_truth": "Convert any live discrepancy into a fixture, structured warning, documented limitation, or extractor/source-adapter fix.",
            "privacy": "The report omits prompts, messages, response content, headers, account identifiers, and raw provider responses.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a sanitized Meta Model API pricing smoke.")
    parser.add_argument("--mode", choices=["sample", "live"], default="sample")
    parser.add_argument("--output", required=True, help="Path to write sanitized JSON evidence.")
    parser.add_argument("--base-url", default=os.environ.get("RUNCOST_META_API_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--model", default=os.environ.get("RUNCOST_SMOKE_META_MODEL", DEFAULT_MODEL))
    parser.add_argument("--max-tokens", type=int, default=32)
    parser.add_argument("--max-output-tokens", type=int, default=32)
    parser.add_argument("--require-passed", action="store_true")
    args = parser.parse_args()

    report = build_report(args)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote sanitized Meta Model API smoke report to {output}")
    if args.require_passed and report.get("status") != "passed":
        raise SystemExit(f"Meta Model API smoke status was {report.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
