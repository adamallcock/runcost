# RunCost

[![CI](https://github.com/adamallcock/runcost/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/adamallcock/runcost/actions/workflows/ci.yml)
[![GitHub release](https://img.shields.io/github/v/release/adamallcock/runcost?include_prereleases)](https://github.com/adamallcock/runcost/releases)
[![npm](https://img.shields.io/npm/v/runcost)](https://www.npmjs.com/package/runcost)
[![PyPI](https://img.shields.io/pypi/v/runcost-ai)](https://pypi.org/project/runcost-ai/)
[![Go Reference](https://pkg.go.dev/badge/github.com/adamallcock/runcost/packages/go/ledger.svg)](https://pkg.go.dev/github.com/adamallcock/runcost/packages/go/ledger)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/adamallcock/runcost/blob/main/LICENSE)
[![Playground](https://img.shields.io/badge/try-playground-ff4f24)](https://adamallcock.github.io/runcost/playground/)

**Provider response in. Itemized USD cost ledger out.**

RunCost turns the LLM or agent response you already receive into a local,
auditable cost estimate. It separates cached input, uncached input, output,
reasoning, tools, media, tiers, batches, and discounts, then records the rates,
sources, assumptions, and warnings behind the total.

No proxy, hosted account, or usage database is required.

> What did this LLM or agent API call cost, and why?

[Try the browser playground](https://adamallcock.github.io/runcost/playground/)
or get a first result below.

## First Success: Python

The Python **distribution** is `runcost-ai`. The import package and installed
CLI are both `runcost`.

```bash
pip install runcost-ai
```

```python
from runcost import from_response_auto

response = {
    "id": "resp_example",
    "object": "response",
    "model": "gpt-4.1-mini",
    "usage": {
        "input_tokens": 36,
        "input_tokens_details": {"cached_tokens": 6},
        "output_tokens": 87,
        "output_tokens_details": {"reasoning_tokens": 12},
    },
}

ledger = from_response_auto(response, provider="openai")

for component in ledger["components"]:
    print(component["name"], component["quantity"], component["cost"])
print("total", ledger["total"], ledger["currency"])
print("source", ledger["price_sources"][0]["name"])
print("warnings", ledger["warnings"])
```

The result is a structured ledger, not just a number:

```text
input_uncached_tokens    30   0.000012
input_cache_read_tokens   6   0.0000006
output_text_tokens       75   0.00012
output_reasoning_tokens  12   0.0000192
total 0.0001518 USD
```

This is example output using rates selected on 2026-08-08. Auto-selected public
rates can change; the ledger records the source and exact rates used for each
calculation.

The selected source is recorded alongside the result. RunCost downloads public
pricing data, but never sends your response or usage data to the pricing source.

## JavaScript And TypeScript

```bash
npm install runcost
```

```js
import { fromResponseAuto } from "runcost";

const response = {
  id: "resp_example",
  object: "response",
  model: "gpt-4.1-mini",
  usage: {
    input_tokens: 36,
    input_tokens_details: { cached_tokens: 6 },
    output_tokens: 87,
    output_tokens_details: { reasoning_tokens: 12 }
  }
};

const ledger = await fromResponseAuto(response, { provider: "openai" });
console.log(ledger.total, ledger.currency);
console.table(ledger.components);
console.log(ledger.price_sources, ledger.warnings);
```

The npm package includes TypeScript declarations and an equivalent CLI:

```bash
npx runcost quote response.json --provider openai
```

## CLI And Go

The Python CLI prices one JSON response or a JSONL stream:

```bash
runcost quote response.json --provider openai
runcost quote - --jsonl --provider openai < responses.jsonl
```

The Go implementation uses the same shared conformance fixtures:

```bash
go get github.com/adamallcock/runcost/packages/go/ledger
```

See the [multi-language quickstart](https://github.com/adamallcock/runcost/blob/main/docs/guides/quickstart.md)
for Go and explicit-price examples.

## When To Use RunCost

Use RunCost when you need to:

- Explain a total as separate billing components instead of `tokens × rate`.
- Keep pricing provenance, effective dates, assumptions, and warnings with the result.
- Reconcile an independent estimate against provider-reported cost or an export.
- Use the same ledger contract in Python, JavaScript/TypeScript, Go, a CLI, or a browser.
- Run locally without placing a proxy or telemetry service in the request path.

RunCost is probably unnecessary when a rough input/output estimate is enough,
or when an existing gateway or observability platform already provides the
billing record you trust.

## How Pricing Works

Published RunCost packages contain no provider price database. The auto APIs
select one upstream catalog—normally `genai-prices`, `models.dev`, or LiteLLM—
cache it, and record the selected source. OpenRouter-billed responses try
OpenRouter first; direct-provider responses do not silently use OpenRouter rates.

Pass explicit price cards for negotiated rates, historical snapshots, or
network-free tests. See the [Price data strategy](https://github.com/adamallcock/runcost/blob/main/docs/reference/price-data-strategy.md)
and [custom pricing guide](https://github.com/adamallcock/runcost/blob/main/docs/reference/custom-pricing-and-discounts.md).

RunCost currently calculates USD ledgers only. Arithmetic is deterministic;
the estimate is only as accurate as the response fields and selected rates.
Reconcile with provider-reported costs, exports, or invoices before treating a
result as invoice-exact.

Fixtures are behavioral conformance tests, not a complete model-price database.

## Main APIs

| Job | Python | JavaScript/TypeScript | Go |
|---|---|---|---|
| Price a provider response | `from_response(...)` | `fromResponse(...)` | `FromResponse(...)` |
| Resolve prices and price a response | `from_response_auto(...)` | `fromResponseAuto(...)` | `FromResponseAuto(...)` |
| Price normalized usage | `calculate_cost(...)` | `calculateCost(...)` | `CalculateCost(...)` |
| Aggregate call ledgers | `aggregate_cost_ledgers(...)` | `aggregateCostLedgers(...)` | `AggregateCostLedgers(...)` |
| Reconcile a provider total | `reconcile_cost(...)` | `reconcileCost(...)` | `ReconcileCost(...)` |

Batch APIs, OpenTelemetry GenAI spans, framework adapters, budgets, streaming,
discounts, and debug traces are also supported. Browse the [API reference](https://github.com/adamallcock/runcost/blob/main/docs/reference/api-reference.md)
or [supported surfaces](https://github.com/adamallcock/runcost/blob/main/docs/reference/supported-surfaces.md)
instead of starting with the full surface area.

## Custom Prices And Discounts

Use caller-owned price cards for private contracts, exact aliases, service tiers,
long-context rates, historical dates, tool units, or self-contained tests. Use
discount policies for explicit adjustments that should remain visible as ledger
entries. The [custom pricing guide](https://github.com/adamallcock/runcost/blob/main/docs/reference/custom-pricing-and-discounts.md)
contains complete Python, JavaScript, and Go examples.

## Warnings

RunCost preserves uncertainty rather than hiding it. Unknown models, unpriced
components, stale sources, ambiguous usage, missing stream usage, and
provider-reported cost mismatches appear as structured warnings. Use strict mode
when those conditions should fail a test or reconciliation workflow.

See [warnings and limitations](https://github.com/adamallcock/runcost/blob/main/docs/reference/warnings-and-limitations.md).

## Bring RunCost Into A Project

- Replace a hand-written formula with the [migration guide](https://github.com/adamallcock/runcost/blob/main/docs/guides/2026-05-26-migration-from-hand-written-formulas.md).
- Add one sanitized real-world case through the [external fixture guide](https://github.com/adamallcock/runcost/blob/main/docs/guides/external-fixture-contributions.md).
- Share a billing edge case that ordinary calculators mishandle in [issue #57](https://github.com/adamallcock/runcost/issues/57).
- Start with the [quickstart](https://github.com/adamallcock/runcost/blob/main/docs/guides/quickstart.md), then browse the [documentation index](https://github.com/adamallcock/runcost/blob/main/docs/README.md).

## Status

RunCost `0.2.x` is public beta and published on PyPI, npm, and the Go module
proxy. Python, JavaScript/TypeScript, and Go are checked against shared fixtures;
the [generated conformance report](https://github.com/adamallcock/runcost/blob/main/docs/generated/conformance-report.md)
is the source of truth for the current case count and pathway status.

[Contributing](https://github.com/adamallcock/runcost/blob/main/CONTRIBUTING.md) ·
[Security](https://github.com/adamallcock/runcost/blob/main/SECURITY.md) ·
[Changelog](https://github.com/adamallcock/runcost/blob/main/CHANGELOG.md) ·
[MIT License](https://github.com/adamallcock/runcost/blob/main/LICENSE)
