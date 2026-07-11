---
title: Default Price Catalog Review
date: 2026-07-09
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
  `77fc583e3bdf67fd62c9fdd95af8f8a392bba39184c176d46debda4e2e8f8db9`
- Generated at: `2026-07-10T19:29:43Z`
- Source entries: 8
- Canonical price cards: 7,763

## Source Inputs

| Source | Adapter | Cards | Raw checksum | URL |
| --- | --- | ---: | --- | --- |
| `openai-official` | `official-snapshot` | 12 | `sha256:d83078ea40228067d84d8b47c02e1121150e9401c2378640dfa531464236caea` | `https://developers.openai.com/api/docs/pricing` |
| `anthropic-official` | `official-snapshot` | 9 | `sha256:36a1f8df3ca6799d2450fcff5c58a8f0b54d894d618eb6a606d05c25c9c5692b` | `https://platform.claude.com/docs/en/about-claude/pricing` |
| `google-official` | `official-snapshot` | 22 | `sha256:88f23af8bda551ce0af0e76d7e09dfab3d5f923672eed33495fc2f724d757b34` | `https://ai.google.dev/gemini-api/docs/pricing` |
| `llm-prices` | `llm-prices` | 117 | `sha256:de9671021f9687eed96d12d228f80d03a706e71120f6f6643731055be54d7bf4` | `https://www.llm-prices.com/current-v1.json` |
| `litellm` | `litellm` | 2,330 | `sha256:3ceb8bff5ba6e98c074fb4b459a986b7d5d7f6fd983c2c5a0f3bd039cfc8215c` | `https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json` |
| `openrouter` | `openrouter-models` | 341 | `sha256:2f2a1c9a1f34d36b08390f2f3cd2da53c3b9b31147241a79454e55573c77f637` | `https://openrouter.ai/api/v1/models` |
| `models.dev` | `models-dev` | 4,902 | `sha256:45a7ac57d6583a92e0e865f4c53dfdc7d57d88359dd67196012acc3f8074fc6a` | `https://models.dev/api.json` |
| `xai-official` | `official-snapshot` | 30 | `sha256:61db8c8464a034cc815ba20f329fde60ffe5ded98d44ea6c6de27ef996756391` | `https://docs.x.ai/developers/models/grok-4.3` |

## Review Notes

- Normal cost calculation remains offline. The bundled catalog is loaded only
  when callers opt in through the default catalog helpers.
- The catalog preserves each source URL, retrieval time, source type, and raw
  checksum in source-cache metadata.
- Recommended source priority is `openai-official`, `anthropic-official`,
  `google-official`, `xai-official`, `llm-prices`, `models.dev`, `litellm`,
  `openrouter`.
- The Anthropic official snapshot was refreshed against the current Anthropic
  pricing page and model/deprecation docs. Only active/current Claude API IDs
  whose names and rates were verified from those primary sources are included;
  retired rows, batch pricing, fast mode, partner-platform premiums, and
  data-residency multipliers remain intentionally unmodeled in the bundled
  default catalog until those matching dimensions are represented explicitly.
- Google Gemini and xAI official snapshot values were spot-checked against
  their current primary pricing pages before rebuilding the catalog.
- Meta Model API preview prices remain in an opt-in fixture only. The SDK docs
  are login-gated and the authenticated `/models` response does not expose
  prices, so media-corroborated rates are deliberately excluded from default
  package data until primary-source verification is possible.
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
