# RunCost

RunCost Ledger is an auditable LLM API cost calculator for answering:

> What did this LLM or agent API call cost, and why?

This npm package exposes the JavaScript/TypeScript implementation. It is
validated against the same shared fixtures as the Python and Go packages.

## Install

```bash
npm install runcost
```

For local checkout development, pack and install the checkout tarball:

```bash
PKG_TGZ=$(npm pack ./packages/javascript/core --silent)
npm install "./$PKG_TGZ"
```

## 60-Second Usage

```ts
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

const ledger = await fromResponseAuto(response, {
  provider: "openai"
});

console.log(ledger.total);
console.log(ledger.components);
console.log(ledger.warnings);
```

The auto helper selects one current external source (`genai-prices`,
`models.dev`, then LiteLLM), records its provenance, and caches it for 24 hours.
It never sends your response or usage data to those sources. Published RunCost
packages contain no provider pricing database. For a zero-code demo or
browser/edge proof, open the
[RunCost playground](https://adamallcock.github.io/runcost/playground/).

Quote JSON or JSONL from the command line:

```bash
npx runcost quote response.json --provider openai
cat responses.jsonl | npx runcost quote - --jsonl --provider openai
```

## Main APIs

| Job | API |
|---|---|
| Price normalized usage | `calculateCost(options)` |
| Price a provider response | `fromResponse(response, options)` |
| Normalize provider batch results | `fromBatchResults(items, options)` |
| Adapt OpenTelemetry GenAI spans | `fromOTelGenAISpan(span, options)` |
| Adapt Pydantic `genai-prices` | `priceCardsFromGenAIPrices(data)` |
| Estimate and evaluate a budget | `estimateCost(options)`, `evaluateBudget(total, options)` |
| Reconcile a provider total | `reconcileCost(ledger, reportedTotal)` |
| Resolve external prices | `resolvePriceCatalog(options)` |
| Price with external resolution | `fromResponseAuto(response, options)` |
| Aggregate call ledgers | `aggregateCostLedgers(options)` |
| Use framework outputs | `fromVercelAISDKStreamFinish(...)`, `fromLangSmithRun(...)`, `createRunCostVercelOnFinish(...)`, and more |
| Load price sources | `priceCardsFromJSONFile(...)`, `priceCardsFromOpenRouterModels(...)`, and more |
| Use a browser/edge-safe core | `import { fromResponse } from "runcost/browser"` |
| Add custom prices | Pass `priceCards` |
| Apply discounts | Pass `discountPolicies` |
| Audit decisions | `debugTrace: true` |
| Fail on ambiguity | `mode: "strict"` |

Full documentation, Python and Go examples, supported surfaces, and caveats:

<https://github.com/adamallcock/runcost>

## Status

RunCost `0.2.x` is public beta. Use provider-reported costs or a matching export
before treating an independent ledger as invoice-exact. If you have a sanitized
billing case that ordinary calculators mishandle, add it to the
[public fixture call](https://github.com/adamallcock/runcost/issues/57).
