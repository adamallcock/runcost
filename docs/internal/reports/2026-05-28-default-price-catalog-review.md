---
title: Default Price Catalog Review
date: 2026-05-28
type: review
status: active
---

# Default Price Catalog Review

RunCost now ships a generated default source-cache catalog as package data. The
catalog is data, not behavioral fixture coverage.

## Generated Artifact

- Path: `packages/python/runcost/data/default-source-cache.json`
- Mirrored paths:
  - `packages/javascript/core/data/default-source-cache.json`
  - `packages/go/ledger/data/default-source-cache.json`
- SHA-256 for all copies:
  `158849ad0a2fe99bc513d7e7e77aff2c1030b29af7c9cd2cee13fd7a58c8f6f4`
- Generated at: `2026-05-29T00:19:51Z`
- Source entries: 4
- Canonical price cards: 7,480

## Source Inputs

| Source | Adapter | Cards | Raw checksum | URL |
| --- | --- | ---: | --- | --- |
| `llm-prices` | `llm-prices` | 112 | `sha256:872376de2cfb471357559a388b9e8f60be8aa58417467fa48439465167e60e45` | `https://www.llm-prices.com/current-v1.json` |
| `litellm` | `litellm` | 2,283 | `sha256:799deb47015eef4eeca6a058830cd42b775bc8b6a45fb4ebdacce36ce4f9e541` | `https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json` |
| `openrouter` | `openrouter-models` | 358 | `sha256:2eb04dfe0ccca3a6bf88215d04dbb4754bb227b9c8ec9800a86f0530404a1319` | `https://openrouter.ai/api/v1/models` |
| `models.dev` | `models-dev` | 4,727 | `sha256:429a376c19a9a3a11254eb0703babb7fca8b804e547fc748f4c7fb921d26da5b` | `https://models.dev/api.json` |

## Review Notes

- Normal cost calculation remains offline. The bundled catalog is loaded only
  when callers opt in through the default catalog helpers.
- The catalog preserves each source URL, retrieval time, source type, and raw
  checksum in source-cache metadata.
- Recommended source priority is `llm-prices`, `models.dev`, `litellm`,
  `openrouter`.
- User custom price cards should still take precedence over the bundled catalog
  when users have contract pricing.

## Verification

Run:

```bash
python3 scripts/check_default_price_catalog.py
```

This verifies byte-identical package copies, source shape, total price-card
count, and Python/JavaScript loader behavior. Go loader behavior is verified by
`go test ./packages/go/...`.
