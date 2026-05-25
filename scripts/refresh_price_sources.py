#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PYTHON_PACKAGE = ROOT / "packages" / "python"
if str(PYTHON_PACKAGE) not in sys.path:
    sys.path.insert(0, str(PYTHON_PACKAGE))

from runcost import (  # noqa: E402
    price_cards_from_helicone,
    price_cards_from_litellm,
    price_cards_from_llm_prices,
    price_cards_from_models_dev,
    price_cards_from_openrouter_models,
    price_cards_from_portkey,
    price_cards_from_user_pricing,
)

Adapter = Callable[[Any], list[dict[str, Any]]]

ADAPTERS: dict[str, Adapter] = {
    "llm-prices": price_cards_from_llm_prices,
    "litellm": price_cards_from_litellm,
    "models-dev": price_cards_from_models_dev,
    "openrouter-models": price_cards_from_openrouter_models,
    "portkey": price_cards_from_portkey,
    "user-pricing": price_cards_from_user_pricing,
    "helicone": price_cards_from_helicone,
}

PRESETS: dict[str, dict[str, str]] = {
    "llm-prices-current": {
        "source_type": "llm-prices",
        "url": "https://www.llm-prices.com/current-v1.json",
    },
    "llm-prices-historical": {
        "source_type": "llm-prices",
        "url": "https://www.llm-prices.com/historical-v1.json",
    },
    "openrouter-models": {
        "source_type": "openrouter-models",
        "url": "https://openrouter.ai/api/v1/models",
    },
    "models-dev": {
        "source_type": "models-dev",
        "url": "https://models.dev/api.json",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_snapshot(input_path: Path | None, url: str) -> bytes:
    if input_path:
        return input_path.read_bytes()
    request = Request(url, headers={"User-Agent": "runcost-price-source-refresh/0.1"})
    with urlopen(request, timeout=30) as response:
        return response.read()


def load_json_snapshot(raw: bytes, source_url: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source_url} did not return valid JSON: {exc}") from exc


def build_source_cache(
    raw: bytes,
    snapshot: Any,
    source_type: str,
    source_url: str,
    retrieved_at: str | None = None,
    generated_at: str | None = None,
    source_name: str | None = None,
) -> dict[str, Any]:
    if source_type not in ADAPTERS:
        supported = ", ".join(sorted(ADAPTERS))
        raise ValueError(f"Unsupported source type {source_type!r}; expected one of: {supported}")

    retrieved = retrieved_at or utc_now()
    generated = generated_at or retrieved
    cards = ADAPTERS[source_type](snapshot)
    source_info = {
        "name": source_name or source_type,
        "url": source_url,
        "retrieved_at": retrieved,
    }
    refreshed_cards = []
    for raw_card in cards:
        card = dict(raw_card)
        card["source"] = dict(source_info)
        refreshed_cards.append(card)
    source_entry: dict[str, Any] = {
        "type": source_type,
        "url": source_url,
        "retrieved_at": retrieved,
        "checksum": f"sha256:{hashlib.sha256(raw).hexdigest()}",
        "price_cards": refreshed_cards,
    }
    if source_name:
        source_entry["name"] = source_name
    return {
        "schema_version": "0.1",
        "generated_at": generated,
        "sources": [source_entry],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh a pricing source into a RunCost source-cache envelope.",
    )
    parser.add_argument("--preset", choices=sorted(PRESETS), help="known pricing source preset")
    parser.add_argument("--source-type", choices=sorted(ADAPTERS), help="source adapter to use")
    parser.add_argument("--url", help="source URL to fetch, or metadata URL when --input is used")
    parser.add_argument("--input", type=Path, help="local JSON snapshot to convert without network access")
    parser.add_argument("--output", type=Path, required=True, help="source-cache JSON file to write")
    parser.add_argument("--source-name", help="optional source display name")
    parser.add_argument("--retrieved-at", help="override retrieved_at timestamp for reproducible refreshes")
    parser.add_argument("--generated-at", help="override generated_at timestamp for reproducible refreshes")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    preset = PRESETS.get(args.preset or "", {})
    source_type = args.source_type or preset.get("source_type")
    if not source_type:
        raise SystemExit("--source-type is required unless --preset supplies it")

    input_path = args.input.resolve() if args.input else None
    source_url = args.url or preset.get("url")
    if not source_url:
        if not input_path:
            raise SystemExit("--url is required unless --preset or --input supplies it")
        source_url = input_path.as_uri()

    raw = read_snapshot(input_path, source_url)
    snapshot = load_json_snapshot(raw, source_url)
    envelope = build_source_cache(
        raw,
        snapshot,
        source_type,
        source_url,
        retrieved_at=args.retrieved_at,
        generated_at=args.generated_at,
        source_name=args.source_name,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(envelope['sources'][0]['price_cards'])} price cards to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
