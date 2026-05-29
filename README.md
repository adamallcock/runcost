# RunCost

RunCost is a small alpha utility for answering one question:

> What did this LLM or agent API call cost, and why?

It turns provider responses, framework usage objects, or normalized usage into a
componentized cost ledger with input, cached input, output, reasoning, tool
units, discounts, price sources, and warnings.

## Install

Current alpha install paths:

```bash
# Python from the repo
python3 -m pip install git+https://github.com/adamallcock/runcost.git

# JavaScript/TypeScript from a checkout
npm pack ./packages/javascript/core
npm install ./runcost-0.1.2.tgz

# Go
go get github.com/adamallcock/runcost/packages/go/ledger
```

First registry release commands, once publishing is enabled:

```bash
pip install runcost-ai
npm install runcost
go get github.com/adamallcock/runcost/packages/go/ledger
```

The Python distribution name is `runcost-ai`; the import package and CLI are
`runcost`.

## One-Minute Examples

Python:

```python
from runcost import from_response

response = {
    "model": "gpt-4.1-mini-2025-04-14",
    "usage": {
        "input_tokens": 36,
        "input_tokens_details": {"cached_tokens": 6},
        "output_tokens": 87,
        "output_tokens_details": {"reasoning_tokens": 12},
    },
}

price_cards = [{
    "schema_version": "0.1",
    "id": "openai:gpt-4.1-mini:example",
    "provider": "openai",
    "surface": "openai.responses",
    "model": "gpt-4.1-mini",
    "aliases": ["gpt-4.1-mini-2025-04-14"],
    "components": [
        {"usage_component": "input_uncached_tokens", "unit": "token", "price": {"amount": "0.40", "currency": "USD", "per": "1000000"}},
        {"usage_component": "input_cache_read_tokens", "unit": "token", "price": {"amount": "0.10", "currency": "USD", "per": "1000000"}},
        {"usage_component": "output_text_tokens", "unit": "token", "price": {"amount": "1.60", "currency": "USD", "per": "1000000"}},
        {"usage_component": "output_reasoning_tokens", "unit": "token", "price": {"amount": "1.60", "currency": "USD", "per": "1000000"}},
    ],
    "source": {"name": "example"},
}]

ledger = from_response(
    response,
    provider="openai",
    surface="openai.responses",
    model="gpt-4.1-mini",
    price_cards=price_cards,
)

print(ledger["total"])
print(ledger["components"])
print(ledger["warnings"])
```

TypeScript:

```ts
import { fromResponse } from "runcost";

// Using the same response and priceCards shape as the Python example above.
const ledger = fromResponse(response, {
  provider: "openai",
  surface: "openai.responses",
  model: "gpt-4.1-mini",
  priceCards
});

console.log(ledger.total);
console.log(ledger.components);
console.log(ledger.warnings);
```

Go:

```go
package main

import (
    "fmt"

    ledger "github.com/adamallcock/runcost/packages/go/ledger"
)

func main() {
    cost := ledger.FromResponse(
        ledger.Object{
            "model": "gpt-4.1-mini-2025-04-14",
            "usage": ledger.Object{
                "input_tokens":  36,
                "output_tokens": 87,
            },
        },
        ledger.Object{
            "provider":    "openai",
            "surface":     "openai.responses",
            "model":       "gpt-4.1-mini",
            "price_cards": []any{
                ledger.Object{
                    "schema_version": "0.1",
                    "id":             "openai:gpt-4.1-mini:example",
                    "provider":       "openai",
                    "surface":        "openai.responses",
                    "model":          "gpt-4.1-mini",
                    "aliases":        []any{"gpt-4.1-mini-2025-04-14"},
                    "components": []any{
                        ledger.Object{
                            "usage_component": "input_uncached_tokens",
                            "unit":            "token",
                            "price": ledger.Object{"amount": "0.40", "currency": "USD", "per": "1000000"},
                        },
                        ledger.Object{
                            "usage_component": "output_text_tokens",
                            "unit":            "token",
                            "price": ledger.Object{"amount": "1.60", "currency": "USD", "per": "1000000"},
                        },
                    },
                    "source": ledger.Object{"name": "example"},
                },
            },
        },
    )

    fmt.Println(cost["total"])
}
```

Already have normalized usage? Use the deterministic calculator directly:

```python
from runcost import calculate_cost

ledger = calculate_cost(
    usage_ledger={
        "schema_version": "0.1",
        "provider": "openai",
        "surface": "openai.responses",
        "model": {"requested": "gpt-4.1-mini"},
        "components": [
            {"name": "input_uncached_tokens", "quantity": "30", "unit": "token"},
            {"name": "output_text_tokens", "quantity": "75", "unit": "token"},
        ],
    },
    price_cards=price_cards,
)
```

## Main APIs

| Job | Python | JavaScript/TypeScript | Go |
|---|---|---|---|
| Price normalized usage | `calculate_cost(...)` | `calculateCost(options)` | `CalculateCost(options)` |
| Price a provider response | `from_response(...)` | `fromResponse(response, options)` | `FromResponse(response, options)` |
| Aggregate call ledgers | `aggregate_cost_ledgers(...)` | `aggregateCostLedgers(options)` | `AggregateCostLedgers(...)` |
| Use framework outputs | `from_langsmith_run(...)`, `track_langchain_costs(...)`, and more | `fromVercelAISDKStreamFinish(...)`, `createRunCostVercelOnFinish(...)`, and more | `FromLangSmithRun(...)`, `FromSemanticKernelTelemetry(...)`, and more |
| Load price sources | `price_cards_from_json_file(...)`, `price_cards_from_openrouter_models(...)` | `priceCardsFromJSONFile(...)`, `priceCardsFromOpenRouterModels(...)` | `PriceCardsFromJSONFile(...)`, `PriceCardsFromOpenRouterModels(...)` |
| Use bundled default catalog | `default_price_cards()` | `defaultPriceCards()` | `DefaultPriceCards()` |
| Add custom prices | Pass `price_cards` | Pass `priceCards` | Pass `price_cards` in options |
| Apply discounts | Pass `discount_policies` | Pass `discountPolicies` | Pass `discount_policies` in options |
| Audit decisions | `debug_trace=True` | `debugTrace: true` | `"debug_trace": true` |
| Fail on ambiguity | `mode="strict"` | `mode: "strict"` | `mode: "strict"` |
| CLI checks | `runcost price-cards`, `runcost fixture-check` | N/A | N/A |

## Supported Inputs

Fixture-backed surfaces include OpenAI Responses and Chat Completions, Anthropic
Messages, OpenRouter, Gemini and Vertex `generateContent`, AWS Bedrock Converse,
Cohere Chat and Rerank, OpenAI-compatible providers such as Groq, xAI, Mistral,
DeepSeek, Azure OpenAI, and Hugging Face Inference Providers, plus selected
framework objects from LangChain, Vercel AI SDK, OpenAI Agents SDK, LlamaIndex,
Haystack, LiteLLM, AutoGen/AG2, LangSmith, Semantic Kernel, and OpenRouter SDK
paths.

See [supported surfaces](docs/reference/supported-surfaces.md) for the current
matrix.

## Custom Prices And Discounts

RunCost treats provider pricing as data. You can pass user price cards for
private rates, exact aliases, service tiers, long-context prices, historical
effective dates, tool units, or internal billing units.

```python
discounts = [{
    "schema_version": "0.1",
    "id": "openai-contract-4pct",
    "match": {"provider": "openai"},
    "adjustment": {"type": "percentage_discount", "value": "4"},
}]
```

The returned ledger records selected price sources, applied discounts, and any
warning that prevents the total from being fully explained.

Fixtures are behavioral conformance tests, not a complete model-price database.
Use source adapters, reviewed source-cache snapshots, or the optional bundled
default catalog for upstream catalog data; see [price data strategy](docs/reference/price-data-strategy.md).

Python:

```python
from runcost import DEFAULT_PRICE_SOURCE_PRIORITY, default_price_cards, from_response

ledger = from_response(
    response,
    provider="openai",
    surface="openai.responses",
    model="gpt-4.1-mini",
    price_cards=default_price_cards(),
    price_source_priority=DEFAULT_PRICE_SOURCE_PRIORITY,
)
```

TypeScript:

```ts
import { DEFAULT_PRICE_SOURCE_PRIORITY, defaultPriceCards, fromResponse } from "runcost";

const ledger = fromResponse(response, {
  provider: "openai",
  surface: "openai.responses",
  model: "gpt-4.1-mini",
  priceCards: defaultPriceCards(),
  priceSourcePriority: DEFAULT_PRICE_SOURCE_PRIORITY
});
```

## Warnings

RunCost is designed to be boring. When it cannot confidently price something, it
returns a structured warning such as `unknown_model`, `component_unpriced`,
`price_stale`, `stream_usage_missing`, or `provider_reported_cost_mismatch`.
Use strict mode in tests or reconciliation flows when warnings should fail.

## CLI

The Python package installs a lightweight CLI:

```bash
runcost price-cards --source-type user-pricing --input prices.json
runcost fixture-check fixtures/my-case.json
```

## Read Next

- [Quickstart](docs/guides/quickstart.md)
- [Package installation](docs/guides/package-installation.md)
- [Migration from hand-written formulas](docs/guides/2026-05-26-migration-from-hand-written-formulas.md)
- [API reference](docs/reference/api-reference.md)
- [Supported surfaces](docs/reference/supported-surfaces.md)
- [Custom pricing and discounts](docs/reference/custom-pricing-and-discounts.md)
- [Source adapters](docs/reference/source-adapters.md)
- [Price data strategy](docs/reference/price-data-strategy.md)
- [Aggregation and streaming](docs/reference/aggregation-and-streaming.md)
- [Warnings and limitations](docs/reference/warnings-and-limitations.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)
- [Changelog](CHANGELOG.md)

## Status

RunCost is alpha software. The core behavior is fixture-backed across Python,
JavaScript/TypeScript, and Go, but registry publishing is still held until the
release gates are complete. Smoke costs may use sample price cards; use provider
exports or dashboard reconciliation before treating a total as invoice-exact.
