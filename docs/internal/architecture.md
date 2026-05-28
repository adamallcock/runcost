---
title: RunCost Architecture
date: 2026-05-25
type: spec
status: draft
---

# RunCost Architecture

Status: Draft
Last updated: 2026-05-24

## Design Goal

Build the smallest reliable core that can answer:

> What did this LLM or agent call cost, and why?

The system should be boring in the best way: deterministic, schema-driven, offline by default, easy to test, and explicit when it cannot know something.

## Core Shape

```text
raw response or framework metadata
  -> extractor
  -> normalized usage ledger
  -> alias resolver
  -> price source resolver
  -> modifier engine
  -> discount engine
  -> cost calculator
  -> cost ledger
```

The core must not know about provider SDK classes, framework classes, HTTP clients, databases, or dashboards. Provider and framework adapters translate external shapes into the core schemas.

## Package Boundaries

Recommended package layout:

```text
schemas/
  usage-ledger.schema.json
  price-card.schema.json
  discount-policy.schema.json
  cost-ledger.schema.json
fixtures/
  README.md
  openai-responses-basic.json
  tool-call-units-basic.json
packages/
  typescript/
    core/
    providers/
    langchain/
    vercel-ai/
  python/
    core/
    providers/
    langchain/
    llamaindex/
```

The `schemas/` and `fixtures/` directories are the source of truth. Language packages should pass the same fixture suite.

## Canonical Data Contracts

### UsageLedger

A provider-neutral, disjoint ledger of usage quantities.

Rules:

- Never price inclusive totals directly.
- Separate uncached input from cache read and cache write.
- Treat reasoning/thinking as a separate output component even when it later bills at normal output price.
- Treat tool calls as billable units with explicit unit types.
- Preserve unknown billable units instead of dropping them.

### PriceCard

A normalized price definition for one provider/model/surface/tier/date condition.

Rules:

- Prices must declare their unit, currency, and source.
- Component names should match usage ledger component names where possible.
- Price cards may contain multiple components for the same model.
- Source provenance is mandatory.
- Effective-date fields are supported even when a source has only current prices.

### DiscountPolicy

A deterministic adjustment layer.

Rules:

- Discounts are component-aware.
- A policy can include or exclude tools, pass-through charges, and provider-reported costs.
- Precedence must be explicit.
- Applied policies must appear in the output ledger.

### CostLedger

The result returned to the caller.

Rules:

- Component sum must equal total.
- Warnings are structured.
- Debug mode can show extraction, alias, price, modifier, and discount decisions.
- Provider-reported cost can be returned, recalculated, or compared.

## Tool Call Pricing

Tool pricing is a first-class problem, not an edge case.

The library should model tool usage through generic billable components:

- `web_search_units`
- `file_search_units`
- `code_interpreter_session_units`
- `code_interpreter_call_units`
- `computer_use_action_units`
- `tool_call_units`
- `tool_execution_seconds`
- `custom_units`

Provider-specific examples should compile down to these components:

- Web search priced per search, per context size, or pass-through cost.
- File search priced per call, per storage GB-day, or pass-through cost.
- Code interpreter priced per session, per call, or per execution duration.
- Computer use priced by token, action, duration, or model output.
- Hosted framework tools priced by gateway-reported cost.
- User-defined internal tools priced by custom price cards.

This lets the calculator stay simple while providers remain free to invent new billing shapes.

## Source Adapter Strategy

The project should not maintain a giant hand-authored pricing table first.

Adapters should normalize upstream sources into `PriceCard`:

- Portkey Models for broad provider/model price rows.
- LiteLLM for deep provider pricing keys, service tiers, and edge cases.
- Helicone cost package for registry, endpoint, deployment, PTB/BYOK, and component breakdown concepts.
- Simon Willison `llm-prices` for simple current/historical input/output/cached-input prices.
- OpenRouter `/api/v1/models` for OpenRouter-specific live model catalog and pricing.
- models.dev for catalog/context/alias enrichment.
- User JSON/YAML for internal prices and contract overrides.

Every adapter must preserve what the source can prove and warn about what it cannot represent.

## V0 Implementation Path

### Step 1: Schema and Fixtures

Create JSON Schemas and golden fixtures before language code.

Deliverables:

- `UsageLedger` schema.
- `PriceCard` schema.
- `DiscountPolicy` schema.
- `CostLedger` schema.
- Basic OpenAI Responses fixture.
- Basic tool-call fixture.

### Step 2: TypeScript Core

Implement the smallest calculator:

- Load normalized usage.
- Load in-memory price cards.
- Apply one discount policy.
- Return a cost ledger.
- No provider SDK dependency.
- No network.

### Step 3: Python Core

Port the same behavior using shared fixtures.

### Step 4: First Extractors

Add raw extractors:

- OpenAI Responses.
- OpenAI Chat Completions.
- Anthropic Messages.

### Step 5: First Source Adapters

Add source adapters:

- Simon Willison `llm-prices`, because it is simple and historical.
- LiteLLM or Portkey Models next, because they expose richer components.

### Step 6: Framework Adapters

Add thin wrappers:

- LangChain callback.
- Vercel AI SDK middleware/onFinish helper.
- LlamaIndex callback handler.

## Strictness Modes

### Strict

Fail when:

- Model is unknown.
- Billable component has no price.
- Alias is inferred.
- Price data is stale.
- Service tier is ambiguous.

### Compatibility

Return best-effort cost with warnings.

## Engineering Rules

- Decimal-safe arithmetic only.
- Offline by default.
- No hidden source fallback.
- No silent unit conversion.
- No dependency on provider SDKs in core.
- No prompt text required for pricing.
- Every warning must be stable and testable.
- Every language implementation must pass the same fixtures.

## First Public API Target

TypeScript:

```ts
const ledger = calculateCost({
  usage,
  priceCards,
  discounts,
  context: {
    provider: "openai",
    surface: "responses",
    model: "gpt-5.4"
  }
});
```

Python:

```py
ledger = calculate_cost(
    usage=usage,
    price_cards=price_cards,
    discounts=discounts,
    context={
        "provider": "openai",
        "surface": "responses",
        "model": "gpt-5.4",
    },
)
```

Provider-response convenience APIs can wrap this later. The normalized API should be the first thing that works.
