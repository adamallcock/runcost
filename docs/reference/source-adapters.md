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
| Simon Willison `llm-prices` | `price_cards_from_llm_prices` / `priceCardsFromLlmPrices` / `PriceCardsFromLlmPrices` | Handles current records and historical `from_date` / `to_date` windows, including historical source URL detection. |
| LiteLLM model prices JSON | `price_cards_from_litellm` / `priceCardsFromLiteLLM` / `PriceCardsFromLiteLLM` | Handles token, cached token, and reasoning token fields that map cleanly to RunCost components. |
| OpenRouter models API | `price_cards_from_openrouter_models` / `priceCardsFromOpenRouterModels` / `PriceCardsFromOpenRouterModels` | Handles prompt, completion, cache, reasoning, request, image, web search, and tiered context fields covered by fixtures. |
| Portkey pricing data | `price_cards_from_portkey` / `priceCardsFromPortkey` / `PriceCardsFromPortkey` | Handles token, cache, reasoning, and web-search price fields covered by fixtures. |
| RunCost source-cache envelope | `price_cards_from_source_cache` / `priceCardsFromSourceCache` / `PriceCardsFromSourceCache` | Handles offline refresh/cache bundles that carry source URL, retrieval time, checksum, generated time, and canonical price cards. |
| User compact pricing data | `price_cards_from_user_pricing` / `priceCardsFromUserPricing` / `PriceCardsFromUserPricing` | Handles compact JSON/YAML-shaped model records after callers parse them into objects. |
| Helicone model-registry endpoint data | `price_cards_from_helicone` / `priceCardsFromHelicone` / `PriceCardsFromHelicone` | Handles endpoint pricing arrays, cache multipliers, reasoning, request, web-search, and image/audio/video token modality prices covered by fixtures. |

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
  ...priceCardsFromUserPricing(userPricingData),
  ...userCards
];

const ledger = fromResponse(response, {
  provider: "openai",
  surface: "openai.responses",
  priceCards,
  priceSourcePriority: ["user-pricing", "llm-prices", "litellm"]
});
```

If two sources match and disagree, RunCost can emit `price_source_disagreement` warnings while selecting the highest-priority source.

## Planned Source Adapters

High-value next adapters:

- Official provider page snapshots where license and terms permit.
- Historical source bundles with effective dates.
- A file-reading refresh command that writes source-cache envelopes from live or vendored source snapshots.

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
- User JSON/YAML support currently means parsed objects, not a file-reading YAML parser in the core package.
- The current adapters are prototypes; source coverage must be expanded fixture by fixture.
