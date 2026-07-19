#!/usr/bin/env python3
"""Price OpenAI-compatible and Anthropic-compatible provider responses."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "python"))

from runcost import from_response  # noqa: E402


PROVIDERS = {
    "tinker": ("tinker.chat_completions", "thinkingmachines/Inkling", "chat"),
    "nvidia": ("nvidia.chat_completions", "nvidia-fixture", "chat"),
    "ai21": ("ai21.chat_completions", "jamba-fixture", "chat"),
    "arcee": ("arcee.chat_completions", "arcee-fixture", "chat"),
    "cohere": ("cohere.chat_completions_compatible", "command-fixture", "chat"),
    "dashscope": ("dashscope.chat_completions", "qwen-fixture", "chat"),
    "inception": ("inception.chat_completions", "mercury-fixture", "chat"),
    "poolside": ("poolside.chat_completions", "poolside-fixture", "chat"),
    "xiaomi": ("xiaomi.chat_completions", "mimo-fixture", "chat"),
    "zai": ("zai.chat_completions", "glm-fixture", "chat"),
    "minimax": ("minimax.messages", "minimax-fixture", "message"),
}


def price_card(provider: str, surface: str, model: str) -> dict[str, object]:
    return {
        "schema_version": "0.1",
        "id": f"example:{provider}:{model}",
        "provider": provider,
        "surface": surface,
        "model": model,
        "components": [
            {"usage_component": "input_uncached_tokens", "unit": "token", "price": {"amount": "1", "currency": "USD", "per": "1000000"}},
            {"usage_component": "output_text_tokens", "unit": "token", "price": {"amount": "2", "currency": "USD", "per": "1000000"}},
        ],
        "source": {"name": "example"},
    }


totals: dict[str, str] = {}
for provider, (surface, model, shape) in PROVIDERS.items():
    response = (
        {"id": "msg_example", "type": "message", "model": model, "usage": {"input_tokens": 100, "output_tokens": 40}}
        if shape == "message"
        else {"object": "chat.completion", "model": model, "choices": [], "usage": {"prompt_tokens": 100, "completion_tokens": 40}}
    )
    ledger = from_response(response, provider=provider, price_cards=[price_card(provider, surface, model)])
    totals[provider] = ledger["total"]

print(json.dumps(totals, sort_keys=True))
