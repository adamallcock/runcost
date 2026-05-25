---
title: RunCost Quickstart
date: 2026-05-25
type: guide
status: draft
---

# RunCost Quickstart

RunCost answers one narrow question:

> What did this LLM or agent API call cost, and why?

The package accepts normalized usage, raw provider responses, or selected framework objects. It returns a componentized cost ledger with line items, totals, price sources, applied discounts, and warnings.

## Install From This Repo

Python:

```bash
python3 -m pip install git+https://github.com/adamallcock/runcost.git
```

JavaScript and TypeScript from a cloned checkout:

```bash
npm pack ./packages/javascript/core
npm install ./runcost-0.0.0.tgz
```

Go:

```bash
go get github.com/adamallcock/runcost/packages/go/ledger
```

The package is pre-alpha. Until registry publishing is wired, the repo and tarball install paths are the supported validation path.

## Python

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

## JavaScript

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
            "price_cards": []any{
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
            },
        },
    )

    fmt.Println(cost["total"])
}
```

## Choosing The Entry Point

Use `calculate_cost` / `calculateCost` / `CalculateCost` when you already have canonical usage and price cards. This is the most deterministic path.

Use `from_response` / `fromResponse` / `FromResponse` when you want RunCost to extract usage from a raw provider SDK response.

Use the framework helpers when the object came from LangChain, Vercel AI SDK, or LlamaIndex.

## Read Next

- [Package Installation](2026-05-25-package-installation.md)
- [API Reference](2026-05-25-api-reference.md)
- [Custom Pricing And Discounts](2026-05-25-custom-pricing-and-discounts.md)
- [Source Adapters](2026-05-25-source-adapters.md)
- [Warnings And Limitations](2026-05-25-warnings-and-limitations.md)
