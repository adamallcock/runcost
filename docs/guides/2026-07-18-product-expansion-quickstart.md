---
title: RunCost Batch, Telemetry, and Provider Quickstart
date: 2026-07-18
type: guide
status: active
---

# RunCost Batch, Telemetry, and Provider Quickstart

This guide covers the expansion APIs that sit beside the normal
`from_response` / `fromResponse` / `FromResponse` path. All examples are local,
stateless, and dependency-free beyond RunCost itself.

## Batch results

`from_batch_results` normalizes provider result rows into one itemized contract.
It retains stable item IDs, succeeded/failed/pending status, endpoint metadata,
per-item ledgers, an aggregate ledger, and summary counts. Failed items are not
silently converted into zero-cost successes.

Supported fixture-backed families are:

- OpenAI Batch results for Responses, Chat Completions, Embeddings, and Images;
- Anthropic Message Batches;
- Gemini Developer API batches and Vertex Gemini batch prediction;
- Amazon Bedrock model-invocation batches;
- Kimi and DashScope batches.

Python:

```python
from runcost import from_batch_results_auto

ledger = from_batch_results_auto(
    result_rows,
    provider="openai",
    endpoint="/v1/responses",
    batch_id="batch_public_example",
)
print(ledger["summary"])
```

JavaScript/TypeScript:

```js
import { fromBatchResultsAuto } from "runcost";

const ledger = await fromBatchResultsAuto(resultRows, {
  provider: "openai",
  endpoint: "/v1/responses",
  batchId: "batch_public_example"
});
console.log(ledger.summary);
```

Run the complete examples with `python3 examples/python_batch_endpoints.py` and
`node examples/javascript_batch_endpoints.mjs`.

## Direct and compatible providers

The generic response path has explicit provider/surface routes for Tinker,
NVIDIA NIM, AI21, Arcee, Cohere-compatible chat, DashScope, Inception,
Poolside, Xiaomi, ZAI/Zhipu, and MiniMax's Anthropic-compatible Messages API.
Their provider namespaces remain distinct even where the wire format is
OpenAI- or Anthropic-compatible.

See `examples/python_direct_providers.py` and
`examples/javascript_direct_providers.mjs` for runnable fixtures covering all
eleven routes.

## Pydantic genai-prices

RunCost can adapt the Pydantic `genai-prices` catalog shape while preserving the
upstream provider/model identity, date boundaries, constraints, cache prices,
and unsupported source capabilities in metadata.

```python
from runcost import price_cards_from_genai_prices

cards = price_cards_from_genai_prices(catalog, version="pinned-version")
```

This is an adapter, not a bundled dependency. You decide how and when to obtain
or pin the upstream catalog.

## OpenTelemetry GenAI spans

Use a standard GenAI span as usage input, or return cost attributes for an
existing telemetry pipeline:

```python
from runcost import from_otel_genai_span_auto, otel_cost_attributes

ledger = from_otel_genai_span_auto(span)
attributes = otel_cost_attributes(ledger)
```

The enricher returns data; it does not export spans or require a telemetry
backend. Unknown experimental attributes remain available in raw metadata.

## Pre-call estimates and budgets

Estimation uses the same component names, price selection, exact decimal
arithmetic, and warnings as post-call pricing:

```python
from runcost import estimate_cost_auto, evaluate_budget

estimate = estimate_cost_auto(
    provider="openai",
    surface="openai.responses",
    model="gpt-4.1-mini-2025-04-14",
    components={"input_uncached_tokens": 2_000, "output_text_tokens": 500},
)
decision = evaluate_budget(estimate, budget="0.01", warning_threshold="0.8")
```

The budget helper is side-effect free. It reports `within_budget`, `warning`,
or `exceeded`; it does not persist spend or route a request.

### Attribution-aware policies

Passive `run_id`, `session_id`, `workflow`, `tenant_id`, `feature`, and `tags`
metadata follows usage into cost and aggregate ledgers. A discount can opt in to
matching a subset of string tags:

```python
estimate = estimate_cost_auto(
    provider="openai",
    surface="openai.responses",
    model="gpt-4.1-mini-2025-04-14",
    components={"input_uncached_tokens": 2_000},
    attribution={"feature": "search", "tags": {"plan": "pilot"}},
    discount_policies=[{
        "schema_version": "0.1",
        "id": "pilot-plan",
        "match": {"tags": {"plan": "pilot"}},
        "adjustment": {"type": "percentage_discount", "value": "10"},
    }],
)
```

Attribution never changes price selection by itself. Only an explicit matching
policy can alter the calculated total.

## Reconciliation

Keep independent and provider-reported numbers visible:

```python
from runcost import reconcile_cost

result = reconcile_cost(ledger, reported_total="0.0042", tolerance="0.000001")
```

The result includes signed and absolute residuals. It never replaces the
calculated ledger with the provider number.

## Browser and edge entrypoint

Browser and edge apps import the browser-safe core. Auto helpers resolve public
catalog data into an in-memory cache; deterministic helpers accept explicit
caller-owned cards:

```js
import { fromResponseAuto } from "runcost/browser";

const ledger = await fromResponseAuto(response, { provider: "openai" });
```

The public playground demonstrates this path, labels its dated offline demo
fallback, and never uploads pasted response JSON.

## Validate the examples

From a checkout:

```bash
npm run check:expansion
npm run check:playground
```

For the exact machine-readable contract, use the schemas and the generated
[conformance report](../generated/conformance-report.md).
