---
title: RunCost Price Data Strategy
date: 2026-05-28
type: reference
status: active
---

# RunCost Price Data Strategy

RunCost separates pricing behavior from pricing catalogs.

## Fixtures Are Behavioral Tests

Fixtures under `fixtures/` are not meant to be a complete public price database.
They are small, reviewable conformance cases that prove how RunCost handles a
provider response, framework usage object, warning, discount, source adapter, or
edge case across Python, JavaScript/TypeScript, and Go.

A fixture should answer:

- Did we extract the right usage components?
- Did we select the right price-card component?
- Did aliases, tiers, regions, discounts, long-context rules, or effective dates
  behave correctly?
- Did unsupported or ambiguous billing fields produce structured warnings?

## Source Adapters Convert Catalogs

Price catalogs should come from explicit source adapters or user overrides, not
from hidden formulas in the calculator core. Current source adapters cover:

- Simon Willison `llm-prices` current and historical JSON.
- LiteLLM model pricing JSON.
- OpenRouter models API.
- models.dev API catalog.
- Reviewed official pricing snapshots.
- Portkey pricing data.
- Helicone model-registry data.
- User compact JSON/YAML pricing.
- RunCost source-cache envelopes.

These adapters convert source-specific data into canonical RunCost `PriceCard`
objects. The source adapter fixtures prove representative mappings; they do not
vend every upstream model row.

## External Resolution And The Offline Boundary

The deterministic calculation APIs never fetch the network. The separate auto
resolver downloads public catalog data, adapts it to canonical cards, and keeps
a checksummed last-known-good cache. To create a caller-owned reviewed envelope
instead, refresh it explicitly:

```bash
npm run prices:refresh -- \
  --preset llm-prices-current \
  --output vendor/prices/llm-prices-current.source-cache.json
```

The envelope records source URL, retrieval time, checksum, generated time, and
canonical price cards. Applications can commit their own reviewed source-cache
files, pin them by checksum, and combine them with user overrides.

Published RunCost packages contain no provider price catalog. Node, Python, and
Go use the operating system's persistent cache; browsers and edge runtimes use
an in-memory cache. The default freshness window is 24 hours. A stale entry is
conditionally refreshed with `ETag` or `Last-Modified` when available. If that
refresh fails, RunCost may use the last-known-good cards with a structured
`price_source_refresh_failed` warning. Offline cache misses stay visible as
`price_source_unavailable`.

Targeted official snapshots in this repository prove pricing behavior such as
service tiers, long-context boundaries, and cache-write components. They are
test evidence, not production package data.

## Trust Order

Recommended production order:

1. User or contract price cards.
2. Caller-owned reviewed source-cache snapshots.
3. `genai-prices`.
4. models.dev.
5. LiteLLM pricing data.
6. Provider-reported cost comparison when the provider exposes an authoritative
   cost field.

OpenRouter-billed responses try the OpenRouter models API before the general
external profile. A resolver calculation selects exactly one catalog and never
silently combines rates from multiple sources. When callers deliberately pass
a merged set of explicit cards, `price_source_priority` /
`priceSourcePriority` controls matching within that caller-owned set.

## Maintenance Rule

When a source adapter cannot safely map a billable field, add a fixture that
shows either the correct mapping or the structured warning. Do not silently turn
unknown source fields into prices.
