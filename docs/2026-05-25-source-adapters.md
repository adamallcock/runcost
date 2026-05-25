---
title: RunCost Source Adapters
date: 2026-05-25
type: reference
status: draft
---

# RunCost Source Adapters

Source adapters convert external pricing catalogs into RunCost price cards. They are useful for bootstrapping, but user overrides and fixture-backed validation remain the trust boundary.

## Supported Prototype Adapters

| Source | Current function | Notes |
|---|---|---|
| Simon Willison `llm-prices` | `price_cards_from_llm_prices` / `priceCardsFromLlmPrices` / `PriceCardsFromLlmPrices` | Handles simple current and historical pricing records. |
| LiteLLM model prices JSON | `price_cards_from_litellm` / `priceCardsFromLiteLLM` / `PriceCardsFromLiteLLM` | Handles token, cached token, and reasoning token fields that map cleanly to RunCost components. |
| OpenRouter models API | `price_cards_from_openrouter_models` / `priceCardsFromOpenRouterModels` / `PriceCardsFromOpenRouterModels` | Handles prompt, completion, cache, reasoning, request, image, web search, and tiered context fields covered by fixtures. |
| Portkey pricing data | `price_cards_from_portkey` / `priceCardsFromPortkey` / `PriceCardsFromPortkey` | Handles token, cache, reasoning, and web-search price fields covered by fixtures. |

## Adapter Contract

Every source adapter should:

- Return canonical `PriceCard` objects.
- Preserve source name, URL, and retrieval time when available.
- Drop records that cannot be safely converted.
- Avoid guessing units when a source field is ambiguous.
- Prefer warnings and fixture expansion over silent behavior changes.

## Source Priority

Use source priority when combining user overrides with public catalogs.

```js
const priceCards = [
  ...priceCardsFromLlmPrices(llmPricesData),
  ...priceCardsFromLiteLLM(liteLlmData),
  ...userCards
];

const ledger = fromResponse(response, {
  provider: "openai",
  surface: "openai.responses",
  priceCards,
  priceSourcePriority: ["user", "llm-prices", "litellm"]
});
```

If two sources match and disagree, RunCost can emit `price_source_disagreement` warnings while selecting the highest-priority source.

## Planned Source Adapters

High-value next adapters:

- User JSON and YAML files with schema validation.
- Helicone cost package snapshots.
- Official provider page snapshots where license and terms permit.
- Historical source bundles with effective dates.
- A refresh cache format that records retrieval time, URL, checksum, and generated price-card count.

## Maintenance Rules

Source adapters should stay thin. The project should avoid embedding complex provider scraping logic inside the calculator core.

Recommended pipeline:

1. Fetch or receive external pricing data.
2. Store raw source snapshot with retrieval metadata.
3. Convert snapshot into RunCost price cards.
4. Validate generated cards against schemas.
5. Run shared fixture tests.
6. Review source deltas before release.

## Known Limits

- Not every field in external catalogs has a direct pricing meaning.
- Some providers publish prices by marketing family, API surface, region, or tier rather than exact model ID.
- Tool-call pricing is often spread across product docs instead of model catalogs.
- The current adapters are prototypes; source coverage must be expanded fixture by fixture.
