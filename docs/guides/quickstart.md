---
title: RunCost Quickstart
date: 2026-05-25
type: guide
status: active
---

# RunCost Quickstart

RunCost answers one narrow question:

> What did this LLM or agent API call cost, and why?

The package accepts normalized usage, raw provider responses, or selected framework objects. It returns a componentized cost ledger with line items, totals, price sources, applied discounts, and warnings.

## Install

Python:

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

The package is alpha. Registry packages are the normal install path; repository
and tarball paths are for development and release verification.

## Price A Real Response

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
print(ledger["total"])
print(ledger["components"])
print(ledger["warnings"])
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

The convenience APIs select one named external source—normally
`genai-prices`, models.dev, or LiteLLM—and expose its provenance and cache state
in the ledger. RunCost does not bundle a provider price database. Pass explicit
`price_cards` / `priceCards` when you need negotiated rates or a self-contained
test; an explicitly empty list disables network resolution. Open the
[browser playground](https://adamallcock.github.io/runcost/playground/) to see
the same ledger without installing the package.

## Python With Explicit Prices

```python
from runcost import from_response

response = {
    "model": "gpt-5.4-2026-05-01",
    "usage": {
        "input_tokens": 36,
        "input_tokens_details": {"cached_tokens": 0},
        "output_tokens": 87,
        "output_tokens_details": {"reasoning_tokens": 0},
    },
}

price_cards = [{
    "schema_version": "0.1",
    "id": "openai:gpt-5.4:example",
    "provider": "openai",
    "surface": "openai.responses",
    "model": "gpt-5.4",
    "aliases": ["gpt-5.4-2026-05-01"],
    "components": [
        {
            "usage_component": "input_uncached_tokens",
            "unit": "token",
            "price": {"amount": "1.25", "currency": "USD", "per": "1000000"},
        },
        {
            "usage_component": "output_text_tokens",
            "unit": "token",
            "price": {"amount": "10", "currency": "USD", "per": "1000000"},
        },
    ],
    "source": {"name": "user"},
}]

ledger = from_response(
    response,
    provider="openai",
    surface="openai.responses",
    model="gpt-5.4",
    price_cards=price_cards,
)

print(ledger["total"])
print(ledger["components"])
```

## JavaScript With Explicit Prices

```js
import { fromResponse } from "runcost";

const ledger = fromResponse(response, {
  provider: "openai",
  surface: "openai.responses",
  model: "gpt-5.4",
  priceCards
});

console.log(ledger.total);
console.log(ledger.components);
```

## Go

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
            "id":             "openai:gpt-5.4:example",
            "provider":       "openai",
            "surface":        "openai.responses",
            "model":          "gpt-5.4",
            "aliases":        []any{"gpt-5.4-2026-05-01"},
            "components": []any{
                ledger.Object{
                    "usage_component": "input_uncached_tokens",
                    "unit":            "token",
                    "price": ledger.Object{
                        "amount": "1.25",
                        "currency": "USD",
                        "per": "1000000",
                    },
                },
                ledger.Object{
                    "usage_component": "output_text_tokens",
                    "unit":            "token",
                    "price": ledger.Object{
                        "amount": "10",
                        "currency": "USD",
                        "per": "1000000",
                    },
                },
            },
            "source": ledger.Object{"name": "user"},
        },
    }

    cost := ledger.FromResponse(
        ledger.Object{
            "model": "gpt-5.4-2026-05-01",
            "usage": ledger.Object{
                "input_tokens":  36,
                "output_tokens": 87,
            },
        },
        ledger.Object{
            "provider": "openai",
            "surface":  "openai.responses",
            "model":    "gpt-5.4",
        },
        priceCards,
        nil,
    )

    fmt.Println(cost["total"])
}
```

## Choosing The Entry Point

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
- [Batch, OTel, budgets, and direct providers](2026-07-18-product-expansion-quickstart.md)
- [Migration From Hand-Written Formulas](2026-05-26-migration-from-hand-written-formulas.md)
- [API Reference](../reference/api-reference.md)
- [Custom Pricing And Discounts](../reference/custom-pricing-and-discounts.md)
- [Source Adapters](../reference/source-adapters.md)
- [Warnings And Limitations](../reference/warnings-and-limitations.md)
