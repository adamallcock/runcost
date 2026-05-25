---
title: RunCost Debug Trace
date: 2026-05-25
type: reference
status: draft
---

# RunCost Debug Trace

RunCost can include an optional `debug_trace` field in the returned cost ledger. Use it when you need to answer why a model alias, price card, component price, source override, discount, or warning appeared in the final total.

## Enable It

Python:

```python
ledger = from_response(
    response,
    provider="openai",
    surface="openai.responses",
    price_cards=price_cards,
    debug_trace=True,
)
```

JavaScript:

```js
const ledger = fromResponse(response, {
  provider: "openai",
  surface: "openai.responses",
  priceCards,
  debugTrace: true
});
```

Go:

```go
ledger := ledger.CalculateCostWithOptions(usage, priceCards, discounts, ledger.Object{
    "debug_trace": true,
})
```

## Shape

```json
{
  "schema_version": "0.1",
  "decisions": [
    {
      "type": "price_card_candidates",
      "model": "gpt-trace-2026",
      "candidate_price_card_ids": ["openai:gpt-trace:user"],
      "source_priority": ["user-overrides", "vendor-feed"]
    },
    {
      "type": "price_component_match",
      "component": "input_uncached_tokens",
      "selected_price_card_id": "openai:gpt-trace:user",
      "selected_source": "user-overrides"
    },
    {
      "type": "model_alias_resolution",
      "from": "gpt-trace-2026",
      "to": "gpt-trace",
      "resolution": "source_exact"
    }
  ],
  "summary": {
    "priced_components": 1,
    "unpriced_components": 0,
    "warnings": 0,
    "applied_discounts": 1
  }
}
```

## Decision Types

- `price_card_candidates`: records matching price cards after provider, surface, model, context, effective-date, and source-priority selection.
- `price_component_match`: records which price card priced a usage component.
- `model_alias_resolution`: records exact alias resolution, such as a dated provider-returned model mapping to a billing model.
- `discount_application`: records the discount policy and amount applied to a component.
- `warning`: mirrors returned warnings into the trace so warning decisions are visible in the same explain object.

## Contract

The trace is optional and should not appear unless requested. The current schema lives in `schemas/debug-trace.schema.json`, and the fixture `debug-trace-explain-decisions.json` proves behavior across Python, JavaScript/TypeScript, and Go.

Debug trace is for observability and auditability. It should not be treated as a separate billing output; the canonical billing output remains `CostLedger.components`, `CostLedger.total`, `CostLedger.price_sources`, `CostLedger.applied_discounts`, and `CostLedger.warnings`.
