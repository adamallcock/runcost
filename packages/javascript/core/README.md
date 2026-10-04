# RunCost

**Provider response in. Itemized USD cost ledger out.**

RunCost turns the LLM or agent response you already receive into a local,
auditable cost estimate with separate billing components, rates, sources,
assumptions, and warnings. No proxy, hosted account, or usage database is
required.

> What did this LLM or agent API call cost, and why?

This is the JavaScript/TypeScript package. Python and Go implement the same
ledger contract and run the same shared conformance fixtures.

## First Success

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

Illustrative output using rates selected on 2026-08-08 (auto-selected public
rates can change):

```text
input_uncached_tokens    30   0.000012
input_cache_read_tokens   6   0.0000006
output_text_tokens       75   0.00012
output_reasoning_tokens  12   0.0000192
total 0.0001518 USD
```

The auto helper selects one current external pricing source, caches it, and
records its provenance. It never sends your response or usage data to that
source. Published RunCost packages contain no provider price database.

Try the same flow without installing anything in the
[browser playground](https://adamallcock.github.io/runcost/playground/).

## CLI

```bash
npx runcost quote response.json --provider openai
cat responses.jsonl | npx runcost quote - --jsonl --provider openai
```

## When To Use RunCost

Use RunCost when cached input, reasoning output, tools, media, tiers, batches,
discounts, rate provenance, or reconciliation matter. A simpler input/output
calculator may be enough when you only need a rough total.

RunCost calculates USD ledgers. Arithmetic is deterministic, but an independent
estimate is only as accurate as the response fields and selected rates. Reconcile
against provider-reported cost or an export before treating it as invoice-exact.

## Main APIs

| Job | API |
|---|---|
| Price a provider response | `fromResponse(response, options)` |
| Resolve prices and price a response | `fromResponseAuto(response, options)` |
| Price normalized usage | `calculateCost(options)` |
| Normalize provider batch results | `fromBatchResults(items, options)` |
| Aggregate call ledgers | `aggregateCostLedgers(options)` |
| Reconcile a provider total | `reconcileCost(ledger, reportedTotal)` |
| Adapt OpenTelemetry GenAI spans | `fromOTelGenAISpan(span, options)` |
| Estimate and check a budget | `estimateCost(options)`, `evaluateBudget(total, options)` |
| Use a browser/edge-safe core | `import { fromResponse } from "runcost/browser"` |

Pass `priceCards` for negotiated rates or self-contained tests,
`discountPolicies` for visible adjustments, `debugTrace: true` to inspect
decisions, and `mode: "strict"` to fail on ambiguity.

Full documentation, supported inputs, Python and Go examples, and caveats:

- [Quickstart](https://github.com/adamallcock/runcost/blob/main/docs/guides/quickstart.md)
- [API reference](https://github.com/adamallcock/runcost/blob/main/docs/reference/api-reference.md)
- [Supported surfaces](https://github.com/adamallcock/runcost/blob/main/docs/reference/supported-surfaces.md)
- [Warnings and limitations](https://github.com/adamallcock/runcost/blob/main/docs/reference/warnings-and-limitations.md)
- [RunCost repository](https://github.com/adamallcock/runcost)

## Status

RunCost `0.2.x` is public beta. If you have a sanitized billing case that
ordinary calculators mishandle, add it to the
[public fixture call](https://github.com/adamallcock/runcost/issues/57).


Compiled catalogs own recursively read-only snapshots. Default GenAI Prices resolution uses the maintained v2 feed, and retrieval time is separate from rate freshness. Direct DeepSeek official pricing requires an independently confirmed `pricing_period` because Chinese public holidays are not inferred. See the repository's [source adapter contract](../../../docs/reference/source-adapters.md#genai-prices-v2-contract).

For independent JSONL quotes, `runcost quote - --jsonl` processes rows incrementally and preserves canonical JSON-array output. Add `--output-jsonl` for one ledger per line. `exportCostLedger` creates an allowlisted sharing document; review retained model/rate identifiers and amounts before sharing it.
