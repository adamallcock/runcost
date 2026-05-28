---
title: RunCost Source Adapters
date: 2026-05-25
type: reference
status: active
---

# RunCost Source Adapters

Source adapters convert external pricing catalogs into RunCost price cards. They are useful for bootstrapping, but user overrides and fixture-backed validation remain the trust boundary.

## Supported Prototype Adapters

| Source | Current function | Notes |
|---|---|---|
| Simon Willison `llm-prices` | `price_cards_from_llm_prices` / `priceCardsFromLlmPrices` / `PriceCardsFromLlmPrices` | Handles current records and historical `from_date` / `to_date` windows, including historical source URL detection. |
| LiteLLM model prices JSON | `price_cards_from_litellm` / `priceCardsFromLiteLLM` / `PriceCardsFromLiteLLM` | Handles token, cached token, and reasoning token fields that map cleanly to RunCost components. |
| OpenRouter models API | `price_cards_from_openrouter_models` / `priceCardsFromOpenRouterModels` / `PriceCardsFromOpenRouterModels` | Handles prompt, completion, cache, reasoning, request, image, web search, and tiered context fields covered by fixtures. |
| models.dev API catalog | `price_cards_from_models_dev` / `priceCardsFromModelsDev` / `PriceCardsFromModelsDev` | Handles per-million token prices, cache read/write, reasoning, audio token fields, context tiers, capabilities, limits, and MIT source metadata covered by fixtures. |
| Reviewed official pricing snapshots | `price_cards_from_official_snapshot` / `priceCardsFromOfficialSnapshot` / `PriceCardsFromOfficialSnapshot` | Handles reviewed provider pricing page rows with source URL, retrieval time, version/license metadata, effective dates, aliases, token prices, and tool/search unit prices. |
| Portkey pricing data | `price_cards_from_portkey` / `priceCardsFromPortkey` / `PriceCardsFromPortkey` | Handles token, cache, reasoning, and web-search price fields covered by fixtures. |
| RunCost source-cache envelope | `price_cards_from_source_cache` / `priceCardsFromSourceCache` / `PriceCardsFromSourceCache` | Handles offline refresh/cache bundles that carry source URL, retrieval time, checksum, generated time, and canonical price cards. |
| Local JSON price-source file | `price_cards_from_json_file` / `priceCardsFromJSONFile` / `PriceCardsFromJSONFile` | Reads a local JSON file and maps it through one of the supported source adapters, defaulting to user compact pricing data. |
| Local YAML price-source file | `price_cards_from_yaml_file` / `priceCardsFromYAMLFile` / `PriceCardsFromYAMLFile` | Reads a strict YAML mapping/list/scalar price-source file and maps it through one of the supported source adapters, defaulting to user compact pricing data. |
| User compact pricing data | `price_cards_from_user_pricing` / `priceCardsFromUserPricing` / `PriceCardsFromUserPricing` | Handles compact JSON/YAML-shaped model records after callers parse them into objects. |
| Helicone model-registry endpoint data | `price_cards_from_helicone` / `priceCardsFromHelicone` / `PriceCardsFromHelicone` | Handles endpoint pricing arrays, cache multipliers, reasoning, request, web-search, and image/audio/video token modality prices covered by fixtures. |

## Explicit Refresh Command

Normal cost calculation never fetches live pricing data. To refresh a source explicitly, run `npm run prices:refresh --` and write a RunCost source-cache envelope:

```bash
npm run prices:refresh -- \
  --preset llm-prices-current \
  --output vendor/prices/llm-prices-current.source-cache.json
```

For offline or reviewed snapshots, pass `--input` and the source adapter type:

```bash
npm run prices:refresh -- \
  --source-type user-pricing \
  --input fixtures/source-files/user-pricing-file-basic.json \
  --output vendor/prices/user-pricing.source-cache.json
```

The command records the source URL, retrieval time, SHA-256 checksum, generated time, and converted canonical price cards. Load the generated file with the source-cache adapter or with the local JSON file loader using `source_type="source-cache"` / `sourceType: "source-cache"`.

Supported refresh presets are `llm-prices-current`, `llm-prices-historical`, `openrouter-models`, and `models-dev`. Reviewed official snapshots are refreshed with `--source-type official-snapshot --input path/to/snapshot.json`.

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

- Historical source bundles with effective dates.
- More refresh presets for live or vendored source snapshots.

## Maintenance Rules

Source adapters should stay thin. The project should avoid embedding complex provider scraping logic inside the calculator core.

The maintainer source-update process defines the source update owner, cadence,
review checklist, and product-truth loop for converting source findings into
fixtures, warnings, documented limitations, or adapter fixes.

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
- Local JSON and strict YAML file loading are supported. YAML anchors, tags, multi-document streams, block scalars, and other advanced YAML features are intentionally out of scope for the core package.
- The refresh command supports JSON snapshots only.
- The current adapters are prototypes; source coverage must be expanded fixture by fixture.
