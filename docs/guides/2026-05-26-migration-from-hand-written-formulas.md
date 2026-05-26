---
title: Migration From Hand-Written Formulas
date: 2026-05-26
type: guide
status: draft
---

# Migration From Hand-Written Formulas

RunCost is meant to replace small, scattered snippets like:

```python
cost = input_tokens * 0.000001 + output_tokens * 0.000004
```

Those snippets are easy to start with, but they usually miss cached input,
reasoning tokens, aliases, service modes, source freshness, discounts, and
provider-reported cost comparisons.

## Step 1: Name The Billing Surface

Record the provider, surface, and model alongside the usage:

```json
{
  "provider": "openai",
  "surface": "openai.responses",
  "model": "gpt-5-nano"
}
```

Do not collapse provider and surface into only a model string. The same model
can have different pricing depending on API surface, service mode, batch mode,
region, or gateway.

## Step 2: Move Prices Into Price Cards

Replace inline constants with a price card:

```json
{
  "schema_version": "0.1",
  "id": "openai:gpt-5-nano:internal",
  "provider": "openai",
  "surface": "openai.responses",
  "model": "gpt-5-nano",
  "aliases": ["gpt-5-nano-2026-05-24"],
  "components": [
    {
      "usage_component": "input_uncached_tokens",
      "unit": "token",
      "price": {"amount": "1", "currency": "USD", "per": "1000000"}
    },
    {
      "usage_component": "input_cache_read_tokens",
      "unit": "token",
      "price": {"amount": "0.1", "currency": "USD", "per": "1000000"}
    },
    {
      "usage_component": "output_text_tokens",
      "unit": "token",
      "price": {"amount": "4", "currency": "USD", "per": "1000000"}
    }
  ],
  "source": {"name": "internal"}
}
```

Use string amounts for prices and quantities when exact decimal behavior
matters.

## Step 3: Normalize Usage Once

If you already have token counts, call the calculator directly:

```python
from runcost import calculate_cost

ledger = calculate_cost(
    usage_ledger={
        "schema_version": "0.1",
        "provider": "openai",
        "surface": "openai.responses",
        "model": {
            "requested": "gpt-5-nano",
            "billed": "gpt-5-nano",
            "alias_resolution": "none",
        },
        "components": [
            {"name": "input_uncached_tokens", "quantity": "1000", "unit": "token"},
            {"name": "output_text_tokens", "quantity": "250", "unit": "token"},
        ],
    },
    price_cards=price_cards,
)
```

If you have a raw SDK response, use `from_response` or a framework helper so
RunCost extracts the canonical usage ledger first.

## Step 4: Preserve The Explanation

Store the full returned cost ledger, not only `total`. The ledger explains:

- which components were priced;
- which price card matched;
- how aliases resolved;
- which discounts applied;
- which warnings need attention.

That explanation is what makes future invoice comparison and debugging possible.

## Step 5: Replace Formula Tests With Fixtures

Turn important hand-written formula cases into fixtures:

```bash
runcost fixture-check fixtures/my-case.json
```

For source data conversion, use:

```bash
runcost price-cards --source-type user-pricing --input prices.json
```

The repository conformance runner is still the stronger multi-language gate.
The installed CLI is a lightweight package-user check for one fixture or one
price-source conversion.
