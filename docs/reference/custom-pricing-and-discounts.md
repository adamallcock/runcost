---
title: RunCost Custom Pricing And Discounts
date: 2026-05-25
type: guide
status: draft
---

# RunCost Custom Pricing And Discounts

RunCost treats provider prices, user overrides, and discounts as data. The calculator should not need a code change when a customer wants to override one model, add a private contract rate, or apply a provider-level discount.

## Price Cards

A price card describes one priced model variant for a provider, surface, service tier, region, and optional effective date range.

```json
{
  "schema_version": "0.1",
  "id": "openai:gpt-5.4:standard:2026-05-01",
  "provider": "openai",
  "surface": "openai.responses",
  "model": "gpt-5.4",
  "aliases": ["gpt-5.4-2026-05-01"],
  "service_tier": "standard",
  "effective": {"from": "2026-05-01"},
  "components": [
    {
      "usage_component": "input_uncached_tokens",
      "unit": "token",
      "price": {"amount": "1.25", "currency": "USD", "per": "1000000"}
    },
    {
      "usage_component": "input_cache_read_tokens",
      "unit": "token",
      "price": {"amount": "0.125", "currency": "USD", "per": "1000000"}
    },
    {
      "usage_component": "output_text_tokens",
      "unit": "token",
      "price": {"amount": "10", "currency": "USD", "per": "1000000"}
    }
  ],
  "source": {
    "name": "user",
    "retrieved_at": "2026-05-25T00:00:00Z"
  }
}
```

## Component Names

Common token components:

- `input_uncached_tokens`
- `input_cache_read_tokens`
- `input_cache_write_tokens`
- `input_cache_write_1h_tokens`
- `output_text_tokens`
- `output_reasoning_tokens`
- `embedding_tokens`

Common tool or feature components:

- `request_units`
- `web_search_units`
- `file_search_units`
- `code_interpreter_session_units`
- `code_interpreter_call_units`
- `computer_use_action_units`
- `tool_call_units`
- `image_generation_units`
- `video_generation_units`
- `audio_generation_units`
- `endpoint_runtime_seconds`
- `endpoint_instance_hours`

The schema also supports `custom_units` for contract-specific billing that RunCost does not yet model directly.

## Aliases

Put provider-returned dated model names in `aliases` when the billing model is stable but the API returns a dated name.

Example:

```json
{
  "model": "gpt-5.4",
  "aliases": ["gpt-5.4-2026-05-01"]
}
```

Aliases are exact strings in the current implementation. Avoid broad regex-style aliases until the package has explicit validation and collision behavior.

## Long Context Pricing

Use component `conditions` to model context-dependent pricing.

```json
{
  "usage_component": "input_uncached_tokens",
  "unit": "token",
  "price": {"amount": "2.50", "currency": "USD", "per": "1000000"},
  "conditions": {"min_total_input_tokens": "200000"}
}
```

Supported conditions today:

- `min_total_input_tokens`
- `max_total_input_tokens`

## Discounts And Markups

A discount policy applies after component costs are calculated.

```json
{
  "schema_version": "0.1",
  "id": "openai-contract-4pct",
  "description": "Contract discount for OpenAI usage",
  "match": {"provider": "openai"},
  "adjustment": {
    "type": "percentage_discount",
    "value": "4"
  }
}
```

Adjustment types:

- `percentage_discount`
- `percentage_markup`
- `multiplier`

Match fields:

- `provider`
- `surface`
- `model`
- `service_tier`
- `region`
- `components`
- `exclude_components`

Use `components` for component-specific discounts, such as discounted input tokens but full-price tool calls.

## User Overrides

When multiple price sources can match, pass a priority list.

Python:

```python
ledger = from_response(
    response,
    provider="openai",
    surface="openai.responses",
    price_cards=user_cards + source_cards,
    price_source_priority=["user", "llm-prices", "litellm"],
)
```

JavaScript:

```js
const ledger = fromResponse(response, {
  provider: "openai",
  surface: "openai.responses",
  priceCards: [...userCards, ...sourceCards],
  priceSourcePriority: ["user", "llm-prices", "litellm"]
});
```

The chosen price source is included in the returned cost ledger.
