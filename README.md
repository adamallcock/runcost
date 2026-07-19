# RunCost

[![CI](https://github.com/adamallcock/runcost/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/adamallcock/runcost/actions/workflows/ci.yml)
[![GitHub release](https://img.shields.io/github/v/release/adamallcock/runcost?include_prereleases)](https://github.com/adamallcock/runcost/releases)
[![npm](https://img.shields.io/npm/v/runcost)](https://www.npmjs.com/package/runcost)
[![PyPI](https://img.shields.io/pypi/v/runcost-ai)](https://pypi.org/project/runcost-ai/)
[![Go Reference](https://pkg.go.dev/badge/github.com/adamallcock/runcost/packages/go/ledger.svg)](https://pkg.go.dev/github.com/adamallcock/runcost/packages/go/ledger)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](pyproject.toml)
[![TypeScript types](https://img.shields.io/npm/types/runcost)](packages/javascript/core/index.d.ts)
[![Playground](https://img.shields.io/badge/try-playground-ff4f24)](https://adamallcock.github.io/runcost/playground/)

RunCost Ledger is an auditable LLM API cost calculator for answering one
question:

> What did this LLM or agent API call cost, and why?

It turns provider responses, framework usage objects, or normalized usage into a
componentized cost ledger with input, cached input, output, reasoning, tool
units, batch results, discounts, dated price sources, and warnings. It runs in
Python, JavaScript/TypeScript, Go, the CLI, browsers, and edge runtimes without
requiring a proxy or hosted account.

## Install

Install from package registries:

```bash
pip install runcost-ai
npm install runcost
go get github.com/adamallcock/runcost/packages/go/ledger
```

Source checkout development paths:

```bash
python3 -m pip install git+https://github.com/adamallcock/runcost.git
PKG_TGZ=$(npm pack ./packages/javascript/core --silent)
npm install "./$PKG_TGZ"
```

The Python distribution name is `runcost-ai`; the import package and CLI are
`runcost`. The npm package is `runcost`. The Go package is
`github.com/adamallcock/runcost/packages/go/ledger`.

## 60-Second Quickstart

The convenience APIs resolve current public pricing from `genai-prices`, then
`models.dev`, then LiteLLM, and cache the selected source for 24 hours. Pass the
response you already receive; RunCost never sends it to a pricing source.

Python:

```python
from runcost import from_response_auto

response = {
    "id": "resp_example",
    "object": "response",
    "model": "gpt-4.1-mini-2025-04-14",
    "usage": {
        "input_tokens": 36,
        "input_tokens_details": {"cached_tokens": 6},
        "output_tokens": 87,
        "output_tokens_details": {"reasoning_tokens": 12},
    },
}

ledger = from_response_auto(response, provider="openai")
print(ledger["total"], ledger["components"], ledger["warnings"])
```

JavaScript/TypeScript:

```js
import { fromResponseAuto } from "runcost";

const response = {
  id: "resp_example",
  object: "response",
  model: "gpt-4.1-mini-2025-04-14",
  usage: {
    input_tokens: 36,
    input_tokens_details: { cached_tokens: 6 },
    output_tokens: 87,
    output_tokens_details: { reasoning_tokens: 12 }
  }
};

const ledger = await fromResponseAuto(response, { provider: "openai" });
console.log(ledger.total, ledger.components, ledger.warnings);
```

CLI (Python install or `npx runcost`):

```bash
runcost quote response.json --provider openai
cat batch-results.jsonl | runcost quote - --jsonl --provider openai
```

Try the same flow without installing anything in the
[browser playground](https://adamallcock.github.io/runcost/playground/).

## External Price Resolution

Published RunCost packages contain no provider price database. The auto APIs
select exactly one upstream catalog per calculation, record attempted-source
and cache metadata, and fall back to the next source only when the earlier one
cannot price the requested model. OpenRouter-billed responses try OpenRouter's
models API first; direct-provider responses do not silently use OpenRouter
rates.

Python: `resolve_price_catalog(...)`, `from_response_auto(...)`

JavaScript/TypeScript: `resolvePriceCatalog(...)`, `fromResponseAuto(...)`

Go: `ResolvePriceCatalog(...)`, `FromResponseAuto(...)`

Node, Python, Go, and the CLIs use an OS cache with conditional refresh and a
last-known-good fallback. Browser/edge builds use an in-memory cache. Use
`runcost prices status|refresh|clear` to inspect or manage the CLI cache.

## Explicit Custom Prices

Explicit cards remain the deterministic, network-free path for negotiated
rates, unpublished models, reviewed snapshots, or fully self-contained tests.

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
    priceCards := []any{
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
    }

    cost := ledger.FromResponse(
        ledger.Object{
            "model": "gpt-4.1-mini-2025-04-14",
            "usage": ledger.Object{
                "input_tokens":  36,
                "output_tokens": 87,
            },
        },
        ledger.Object{
            "provider": "openai",
            "surface":  "openai.responses",
            "model":    "gpt-4.1-mini",
        },
        priceCards,
        nil,
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
| Price a provider response | `from_response(...)` | `fromResponse(response, options)` | `FromResponse(response, options, priceCards, discountPolicies)` |
| Normalize batch results | `from_batch_results(...)` | `fromBatchResults(items, options)` | `FromBatchResults(items, options)` |
| Adapt OpenTelemetry GenAI spans | `from_otel_genai_span(...)` | `fromOTelGenAISpan(span, options)` | `FromOTelGenAISpan(...)` |
| Adapt Pydantic `genai-prices` | `price_cards_from_genai_prices(...)` | `priceCardsFromGenAIPrices(...)` | `PriceCardsFromGenAIPrices(...)` |
| Estimate and check a budget | `estimate_cost(...)`, `evaluate_budget(...)` | `estimateCost(...)`, `evaluateBudget(...)` | `EstimateCost(...)`, `EvaluateBudget(...)` |
| Reconcile a provider total | `reconcile_cost(...)` | `reconcileCost(...)` | `ReconcileCost(...)` |
| Resolve and cache external prices | `resolve_price_catalog(...)` | `resolvePriceCatalog(options)` | `ResolvePriceCatalog(ctx, options)` |
| Price with automatic resolution | `from_response_auto(...)` | `fromResponseAuto(response, options)` | `FromResponseAuto(...)` |
| Aggregate call ledgers | `aggregate_cost_ledgers(...)` | `aggregateCostLedgers(options)` | `AggregateCostLedgers(...)` |
| Use framework outputs | `from_langsmith_run(...)`, `track_langchain_costs(...)`, and more | `fromVercelAISDKStreamFinish(...)`, `createRunCostVercelOnFinish(...)`, and more | `FromLangSmithRun(...)`, `FromSemanticKernelTelemetry(...)`, and more |
| Load price sources | `price_cards_from_json_file(...)`, `price_cards_from_openrouter_models(...)` | `priceCardsFromJSONFile(...)`, `priceCardsFromOpenRouterModels(...)` | `PriceCardsFromJSONFile(...)`, `PriceCardsFromOpenRouterModels(...)` |
| Add custom prices | Pass `price_cards` | Pass `priceCards` | Pass `price_cards` in options |
| Apply discounts | Pass `discount_policies` | Pass `discountPolicies` | Pass `discount_policies` in options |
| Audit decisions | `debug_trace=True` | `debugTrace: true` | `"debug_trace": true` |
| Fail on ambiguity | `mode="strict"` | `mode: "strict"` | `mode: "strict"` |
| CLI quote/checks | `runcost quote`, `runcost price-cards`, `runcost fixture-check` | `npx runcost quote` | N/A |

## Supported Inputs

Fixture-backed surfaces include OpenAI Responses, Chat Completions, Embeddings,
Images, and Batch; Anthropic Messages and Message Batches; Gemini Developer and
Vertex AI batch/generateContent; AWS Bedrock Converse and model-invocation batch;
Kimi and DashScope batch; OpenRouter;
Cohere Chat and Rerank, OpenAI-compatible providers such as Meta, Groq, xAI,
Mistral, DeepSeek, Azure OpenAI, Hugging Face Inference Providers, Tinker,
NVIDIA NIM, AI21, Arcee, DashScope, Inception, Poolside, Xiaomi, ZAI, and
MiniMax, plus selected
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
Use the external resolver, a caller-owned reviewed source-cache snapshot, or
explicit contract cards; see [price data strategy](docs/reference/price-data-strategy.md).

Python:

```python
from runcost import from_response_auto

ledger = from_response_auto(
    response,
    provider="openai",
    surface="openai.responses",
    model="gpt-4.1-mini",
    sources=["genai-prices", "models.dev", "litellm"],
)
```

TypeScript:

```ts
import { fromResponseAuto } from "runcost";

const ledger = await fromResponseAuto(response, {
  provider: "openai",
  surface: "openai.responses",
  model: "gpt-4.1-mini",
  sources: ["genai-prices", "models.dev", "litellm"]
});
```

## Warnings

RunCost is designed to be boring. When it cannot confidently price something, it
returns a structured warning such as `unknown_model`, `component_unpriced`,
`price_stale`, `stream_usage_missing`, or `provider_reported_cost_mismatch`.
Use strict mode in tests or reconciliation flows when warnings should fail.

## CLI

The Python and npm packages install equivalent quote CLIs:

```bash
runcost quote response.json --provider openai
runcost quote - --jsonl --provider openai < responses.jsonl
runcost price-cards --source-type user-pricing --input prices.json
runcost fixture-check fixtures/my-case.json
npx runcost quote response.json --provider openai
```

## Read Next

- [Quickstart](docs/guides/quickstart.md)
- [Product expansion quickstart](docs/guides/2026-07-18-product-expansion-quickstart.md)
- [External fixture contributions](docs/guides/external-fixture-contributions.md)
- [Integration case-study template](docs/guides/2026-07-18-integration-case-study-template.md)
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
JavaScript/TypeScript, and Go; the public conformance report inventories 200
cases without claiming unsupported behavior. Packages are published to PyPI,
npm, and Go module tags. Use provider exports or dashboard reconciliation before
treating any independent calculation as invoice-exact.
