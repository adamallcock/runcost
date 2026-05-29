# RunCost

RunCost is a small alpha utility for answering:

> What did this LLM or agent API call cost, and why?

This npm package exposes the JavaScript/TypeScript implementation. It is
validated against the same shared fixtures as the Python and Go packages.

## Install

```bash
npm install runcost
```

Until the first registry release is published, install from a checkout:

```bash
npm pack ./packages/javascript/core
npm install ./runcost-0.1.2.tgz
```

## Basic Usage

```ts
import { fromResponse } from "runcost";

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

## Main APIs

| Job | API |
|---|---|
| Price normalized usage | `calculateCost(options)` |
| Price a provider response | `fromResponse(response, options)` |
| Aggregate call ledgers | `aggregateCostLedgers(options)` |
| Use framework outputs | `fromVercelAISDKStreamFinish(...)`, `fromLangSmithRun(...)`, `createRunCostVercelOnFinish(...)`, and more |
| Load price sources | `priceCardsFromJSONFile(...)`, `priceCardsFromOpenRouterModels(...)`, and more |
| Use bundled default catalog | `defaultPriceCards()` |
| Add custom prices | Pass `priceCards` |
| Apply discounts | Pass `discountPolicies` |
| Audit decisions | `debugTrace: true` |
| Fail on ambiguity | `mode: "strict"` |

Full documentation, Python and Go examples, supported surfaces, and caveats:

<https://github.com/adamallcock/runcost>
