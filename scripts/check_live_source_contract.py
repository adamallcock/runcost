#!/usr/bin/env python3
"""Bounded, read-only live GenAI Prices v2 contract check. No provider API calls."""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
import urllib.request
from collections import Counter
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/python'))
from runcost.expansion import GENAI_PRICE_COMPONENTS
from runcost import price_cards_from_genai_prices
BASE = 'https://raw.githubusercontent.com/pydantic/genai-prices/main/prices/new_data/v2/'
# Recognized but deliberately unsupported unit semantics; new keys require review.
UNSUPPORTED = {'audio_hours', 'input_audio_hours', 'input_document_kpages', 'input_annotated_document_kpages', 'storage_searches_kcount', 'output_citation_mtok', 'input_text_messages_kcount'}

def read(url: str) -> bytes:
    request = urllib.request.Request(url, headers={'User-Agent': 'RunCost-source-contract-check', 'Accept': 'application/json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read(64 * 1024 * 1024 + 1)
    if len(body) > 64 * 1024 * 1024:
        raise ValueError('source exceeds 64 MiB contract limit')
    return body

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output')
    args = parser.parse_args()
    data_body, schema_body = read(BASE + 'data_slim.json'), read(BASE + 'data_slim.schema.json')
    data, schema = json.loads(data_body), json.loads(schema_body)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(data)
    fields = Counter()
    for provider in data:
        for model in provider['models']:
            prices = model.get('prices') or {}
            entries = prices if isinstance(prices, list) else [{'prices': prices}]
            for entry in entries:
                fields.update((entry.get('prices') or {}).keys())
    unknown = set(fields) - set(GENAI_PRICE_COMPONENTS) - UNSUPPORTED
    if unknown:
        raise AssertionError(f'unreviewed upstream price fields: {sorted(unknown)}')
    cards = price_cards_from_genai_prices(data, version=hashlib.sha256(data_body).hexdigest())
    if not cards:
        raise AssertionError('v2 source produced no supported cards')
    price_schema = json.loads((ROOT / 'schemas/price-card.schema.json').read_text())
    validator = Draft202012Validator(price_schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    for card in cards:
        validator.validate(card)
    result = {'contract': 'genai-prices/v2', 'source_url': BASE + 'data_slim.json', 'schema_url': BASE + 'data_slim.schema.json', 'catalog_revision': 'sha256:' + hashlib.sha256(data_body).hexdigest(), 'catalog_generated_at': None, 'providers': len(data), 'models': sum(len(p['models']) for p in data), 'supported_cards': len(cards), 'price_fields': dict(sorted(fields.items())), 'unsupported_fields': sorted(set(fields) & UNSUPPORTED)}
    encoded = json.dumps(result, sort_keys=True, indent=2) + '\n'
    if args.output:
        Path(args.output).write_text(encoded)
    print(encoded, end='')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
