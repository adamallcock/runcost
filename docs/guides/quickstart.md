---
title: RunCost Quickstart
date: 2026-05-25
type: guide
status: active
---

# RunCost Quickstart

RunCost has one job:

> What did this LLM or agent API call cost, and why?

Give it the provider response you already receive. It returns an itemized USD
estimate with billing components, rates, price sources, assumptions, and
warnings. Calculation runs locally; no proxy, hosted account, or usage database
is required. RunCost may download public pricing data, but it does not send the
response to a pricing source.

Arithmetic is deterministic. The estimate still depends on the completeness of
the response and the selected rates, so reconcile important results against
provider-reported costs or billing exports.

## Choose An Install

Python distribution (`runcost-ai`), import package, and CLI (`runcost`):

```bash
pip install runcost-ai
```

JavaScript and TypeScript:

```bash
npm install runcost
```

For a cloned checkout:

```bash
python3 -m pip install git+https://github.com/adamallcock/runcost.git
PKG_TGZ=$(npm pack ./packages/javascript/core --silent)
npm install "./$PKG_TGZ"
```

Go:

```bash
go get github.com/adamallcock/runcost/packages/go/ledger
```

RunCost `0.2.x` is public beta. Registry packages are the normal install path;
repository and tarball paths are for development and release verification.

## First Success: Price A Real Response

Python:

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

JavaScript/TypeScript:

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

Success means you receive a USD total, one line per priced usage component, the
selected source, and an explicit warnings array. For the example above, the
current public rates produce separate uncached input, cached input, text output,
and reasoning output lines.

The convenience APIs select one named external source—normally
`genai-prices`, models.dev, or LiteLLM—and expose its provenance and cache state
in the ledger. RunCost does not bundle a provider price database. Pass explicit
`price_cards` / `priceCards` when you need negotiated rates or a self-contained
test; an explicitly empty list disables network resolution. Open the
[browser playground](https://adamallcock.github.io/runcost/playground/) to see
the same ledger without installing the package.

## Deterministic Custom Prices

Pass `price_cards` in Python or `priceCards` in JavaScript when you have
negotiated rates, need a reviewed historical snapshot, or want a network-free
test. RunCost records the caller-owned source in the same ledger shape. See
[Custom Pricing And Discounts](../reference/custom-pricing-and-discounts.md) for
complete examples instead of copying a large price card into the first-run path.

## Go

```go
package main

import (
    "context"
    "fmt"
    "log"

    ledger "github.com/adamallcock/runcost/packages/go/ledger"
)

func main() {
    result, err := ledger.FromResponseAuto(
        context.Background(),
        ledger.Object{
            "model": "gpt-4.1-mini",
            "usage": ledger.Object{"input_tokens": 36, "output_tokens": 87},
        },
        ledger.Object{
            "provider": "openai",
            "surface":  "openai.responses",
            "model":    "gpt-4.1-mini",
        },
        nil,
        nil,
    )
    if err != nil {
        log.Fatal(err)
    }
    fmt.Println(result["total"], result["currency"])
}
```

## Choosing The Entry Point

Use `from_response_auto` / `fromResponseAuto` / `FromResponseAuto` for the
shortest path from a provider response to a sourced estimate.

Use `calculate_cost` / `calculateCost` / `CalculateCost` when you already have canonical usage and price cards. This is the most deterministic path.

Use `from_response` / `fromResponse` / `FromResponse` when you want RunCost to extract usage from a raw provider SDK response.

Use the framework helpers when the object came from LangChain, OpenAI Agents SDK, Vercel AI SDK, LlamaIndex, Haystack, LiteLLM, AutoGen/AG2, LangSmith, Semantic Kernel, or an OpenRouter-compatible SDK response.

## CLI Checks

The Python package installs a small `runcost` command for lightweight local
checks:

```bash
runcost quote response.json --provider openai
runcost quote - --jsonl --provider openai < responses.jsonl
npx runcost quote response.json --provider openai
runcost price-cards --source-type user-pricing --input prices.json
runcost fixture-check fixtures/my-case.json
```

Use the CLI for one fixture or one price-source conversion. Use `npm test` for
the full multi-language conformance suite.

## Read Next

- [Package Installation](package-installation.md)
- [Supported provider and framework surfaces](../reference/supported-surfaces.md)
- [Batch, OTel, budgets, and direct providers](2026-07-18-product-expansion-quickstart.md)
- [Migration From Hand-Written Formulas](2026-05-26-migration-from-hand-written-formulas.md)
- [API Reference](../reference/api-reference.md)
- [Custom Pricing And Discounts](../reference/custom-pricing-and-discounts.md)
- [Source Adapters](../reference/source-adapters.md)
- [Warnings And Limitations](../reference/warnings-and-limitations.md)
