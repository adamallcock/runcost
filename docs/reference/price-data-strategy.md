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

## Source Cache Is The Offline Boundary

Normal cost calculation never fetches the network. To use public catalog data in
an application or release, refresh an explicit source-cache envelope:

```bash
npm run prices:refresh -- \
  --preset llm-prices-current \
  --output vendor/prices/llm-prices-current.source-cache.json
```

The envelope records source URL, retrieval time, checksum, generated time, and
canonical price cards. Applications can commit their own reviewed source-cache
files, pin them by checksum, and combine them with user overrides.

RunCost also ships an optional reviewed default source-cache catalog in each
package. It is generated from `llm-prices`, LiteLLM, OpenRouter, and
`models.dev`, and can be loaded without network access through
`default_price_cards()` / `defaultPriceCards()` / `DefaultPriceCards()`.
Applications with stricter review requirements can still commit their own
source-cache files and pass those cards explicitly.

## Trust Order

Recommended production order:

1. User contract price cards.
2. Reviewed source-cache snapshots pinned in your app.
3. The bundled reviewed default catalog.
4. Public catalog adapters such as `llm-prices`, LiteLLM, OpenRouter, or
   models.dev.
5. Provider-reported cost comparison when the provider exposes an authoritative
   cost field.

Use `price_source_priority` / `priceSourcePriority` to make this deterministic.

## Maintenance Rule

When a source adapter cannot safely map a billable field, add a fixture that
shows either the correct mapping or the structured warning. Do not silently turn
unknown source fields into prices.
