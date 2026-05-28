#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "python"))
SAMPLE_FILE = ROOT / "fixtures" / "source-files" / "alpha-smoke-samples.json"
SAMPLE_RETRIEVED_AT = "2026-05-26T00:00:00Z"

from runcost import from_langchain_message  # noqa: E402
from check_alpha_smoke_contract import validate_report as validate_alpha_smoke_report  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def price_card(model: str, provider: str = "openai") -> dict[str, Any]:
    components = {
        "input_uncached_tokens": ("token", "1", "1000000"),
        "input_cache_read_tokens": ("token", "0.1", "1000000"),
        "input_cache_write_tokens": ("token", "1.25", "1000000"),
        "output_text_tokens": ("token", "2", "1000000"),
        "output_reasoning_tokens": ("token", "2", "1000000"),
    }
    return {
        "schema_version": "0.1",
        "id": f"{provider}:{model}:langchain-alpha-smoke-sample",
        "provider": provider,
        "surface": "framework.langchain.chat",
        "model": model,
        "components": [
            {
                "usage_component": name,
                "unit": unit,
                "price": {"amount": amount, "currency": "USD", "per": per},
            }
            for name, (unit, amount, per) in components.items()
        ],
        "source": {"name": "alpha-smoke-sample", "retrieved_at": SAMPLE_RETRIEVED_AT},
    }


def evidence(ledger: dict[str, Any], usage_fields: list[str], source: str, exactness: str = "synthetic_sample") -> dict[str, Any]:
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


def report(
    *,
    mode: str,
    status: str,
    ledger: dict[str, Any],
    usage_fields: list[str],
    source: str,
    next_action: dict[str, str],
    exactness: str = "synthetic_sample",
) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "generated_at": utc_now(),
        "mode": mode,
        "scenario": "langchain_agent_run",
        "status": status,
        "sanitized": True,
        "safe_to_attach_to_issue": True,
        "sample_prices": True,
        "evidence": evidence(ledger, usage_fields, source, exactness),
        "next_action": next_action,
    }


def skipped(reason: str) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "generated_at": utc_now(),
        "mode": "live",
        "scenario": "langchain_agent_run",
        "status": "skipped",
        "sanitized": True,
        "safe_to_attach_to_issue": True,
        "sample_prices": True,
        "evidence": {
            "component_names": [],
            "warning_codes": [],
            "total": "0",
            "usage_fields_present": [],
            "raw_response_retained": False,
            "exactness": "not_run",
            "source": "live",
        },
        "next_action": {"type": "documented_limitation", "reason": reason},
    }


def sample_report() -> dict[str, Any]:
    samples = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
    message = samples["scenarios"]["langchain_agent_run"]["message"]
    model = message["response_metadata"]["model_name"]
    ledger = from_langchain_message(
        message,
        provider="openai",
        surface="framework.langchain.chat",
        price_cards=[price_card(model)],
    )
    return report(
        mode="sample",
        status="passed",
        ledger=ledger,
        usage_fields=[
            "usage_metadata.input_tokens",
            "usage_metadata.input_token_details.cache_read",
            "usage_metadata.output_token_details.reasoning",
        ],
        source="sample",
        next_action={"type": "none", "reason": "Sanitized LangChain sample matched the chat-message extractor path."},
    )


def _message_to_mapping(message: Any, model: str) -> dict[str, Any]:
    usage = getattr(message, "usage_metadata", None) or {}
    metadata = getattr(message, "response_metadata", None) or {}
    if not isinstance(metadata, dict):
        metadata = {}
    metadata.setdefault("model_name", model)
    return {
        "usage_metadata": usage if isinstance(usage, dict) else {},
        "response_metadata": metadata,
    }


def live_report() -> dict[str, Any]:
    openai_key = os.environ.get("OPENAI_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if not openai_key and not openrouter_key:
        return skipped("OPENAI_API_KEY or OPENROUTER_API_KEY is not set.")
    try:
        from langchain_core.messages import HumanMessage
        from langchain_openai import ChatOpenAI
    except ImportError:
        return skipped("Install optional packages `langchain-openai` and `langchain-core` to run the live LangChain smoke.")

    provider = "openai" if openai_key else "openrouter"
    model = (
        os.environ.get("RUNCOST_SMOKE_OPENAI_MODEL", "gpt-4.1-mini")
        if openai_key
        else os.environ.get("RUNCOST_SMOKE_OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")
    )
    try:
        llm_kwargs = {"model": model, "max_tokens": 16}
        if openrouter_key and not openai_key:
            llm_kwargs.update({"api_key": openrouter_key, "base_url": "https://openrouter.ai/api/v1"})
        llm = ChatOpenAI(**llm_kwargs)
        message = llm.invoke([HumanMessage(content="Return exactly the word pong.")])
        payload = _message_to_mapping(message, model)
        ledger = from_langchain_message(
            payload,
            provider=provider,
            surface="framework.langchain.chat",
            price_cards=[price_card(payload["response_metadata"].get("model_name", model), provider)],
        )
        return report(
            mode="live",
            status="passed",
            ledger=ledger,
            usage_fields=sorted(payload["usage_metadata"].keys()),
            source="live",
            next_action={"type": "none", "reason": "Live LangChain invoke produced a sanitized RunCost ledger."},
            exactness="sample_prices_not_invoice_exact",
        )
    except Exception as exc:  # noqa: BLE001
        return report(
            mode="live",
            status="needs_product_truth",
            ledger={},
            usage_fields=[],
            source="live",
            next_action={
                "type": "fixture_or_warning_or_limitation",
                "reason": f"Live LangChain smoke failed with sanitized error type {type(exc).__name__}.",
            },
            exactness="requires_review",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run optional sanitized LangChain alpha smoke.")
    parser.add_argument("--mode", choices=["sample", "live"], default="sample")
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow-sample-prices", action="store_true")
    args = parser.parse_args()
    if not args.allow_sample_prices:
        raise SystemExit("--allow-sample-prices is required so smoke output is not mistaken for invoice-exact pricing.")

    result = sample_report() if args.mode == "sample" else live_report()
    validate_alpha_smoke_report(result)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote sanitized LangChain alpha smoke report to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
