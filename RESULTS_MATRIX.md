# LLM Pricing Package Results Matrix

Research date: 2026-05-24

Legend:

- Strong: directly supported and source-verified or smoke-tested.
- Partial: supported only for some providers, surfaces, or fields.
- Weak: claimed or adjacent, but not sufficient for precise accounting.
- Missing: not found during validation.
- Unknown: not validated deeply enough.

## Capability Matrix

| Candidate | Type | Provider coverage | Raw response extraction | Component cost ledger | Cache read/write | Reasoning/thinking | Long-context tiers | Batch/flex/priority/service tiers | Custom prices | Discounts | Point-in-time | Multi-language path | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| LiteLLM | Python SDK/gateway and pricing map | Strong | Partial | Partial | Strong | Strong | Strong | Strong | Partial | Missing | Partial/unknown | Weak | Best reference source, too large and Python-centric for the desired package. |
| Portkey Models | Open pricing data API | Strong | Missing | Missing | Strong | Strong | Strong | Strong | Missing | Missing | Unknown | Strong data, no SDK | Best upstream pricing-data source, not a cost calculator. |
| Simon Willison `llm-prices` | Static JSON pricing API | Partial | Missing | Missing | Partial | Missing | Partial | Missing | Missing | Missing | Strong/simple | Strong data, no SDK | Excellent simple current/historical source for input/output/cached input, but intentionally not a full billing engine. |
| Helicone `@helicone-package/cost` | TypeScript cost package and registry | Strong/partial | Partial | Strong | Strong | Strong | Strong | Partial/strong | Partial | Missing | Partial | Node-first | Strong registry and cost-breakdown reference, tied to Helicone PTB/BYOK and observability needs. |
| OpenRouter `/api/v1/models` | Live model catalog/pricing endpoint | OpenRouter-scoped | Missing | Missing | Partial | Partial | Partial | Missing/partial | Missing | Missing | Current-only/unknown | Strong data, no SDK | Useful live source for OpenRouter model pricing and provider routing, not a generic calculator. |
| `genai-prices` | Python library | Strong | Partial | Partial | Strong | Weak/partial | Strong | Missing/partial | Partial | Missing | Strong | Weak | Best small Python baseline, but misses service tiers, reasoning extraction, aliases, and portable core. |
| `ai-sdk-cost-calculator` | Node/Vercel AI SDK library | Partial/strong | Partial | Strong | Strong | Strong | Strong | Missing/weak | Strong | Partial | Missing | Weak | Closest Node ergonomic competitor, but not broad/provider-neutral enough. |
| TokenLens / models.dev | Model catalog and helper library | Strong catalog | Partial | Weak/partial | Partial | Partial | Missing/partial | Missing | Missing/partial | Missing | Missing | Node-first | Good catalog/alias source, not precise billing. |
| `token-costs` | Node pricing-data client | Partial | Missing | Weak | Partial | Missing | Missing/partial | Missing | Strong | Missing | Missing | Weak | Freshness idea is good, but live data was stale and feature depth is limited. |
| `ai-cost-meter` | Node tracking/helper package | Weak/partial | Partial | Weak | Weak | Weak | Missing | Missing | Partial | Missing | Missing | Weak | Good response-in UX idea, but inspected calculator ignored cache/reasoning costs. |
| `tokentally` | TypeScript cost helper | Partial | Partial | Weak | Weak/partial | Weak | Missing | Missing | Partial | Missing | Missing | Weak | Tiny and useful, but explicitly not perfect accounting. |
| AgentOps `tokencost` | Python cost helper | Partial | Missing | Weak | Missing | Missing | Missing | Missing | Partial | Missing | Missing | Weak | Older input/output calculator. |
| `llm-tokencost` | Python SDK wrappers/tracker | Weak/partial | Partial | Weak | Missing/weak | Missing/weak | Missing | Missing | Partial | Missing | Missing | Weak | SDK wrapper and tracking pattern only. |
| Langfuse | Hosted/self-hosted observability | Strong | Strong through instrumentation | Partial | Partial | Partial | Partial | Partial | Partial | Partial | Unknown | API product | Solves observability, not a tiny embeddable cost kernel. |
| Helicone | Hosted/self-hosted observability/gateway | Strong | Strong through gateway/instrumentation | Partial | Partial | Partial | Partial | Partial | Partial | Partial | Unknown | API product | Spend tracking competitor, not the desired package shape. |
| Portkey Gateway | Gateway/observability | Strong | Strong through gateway | Partial | Strong | Strong | Strong | Strong | Partial | Partial | Unknown | API product | Strong gateway product, but heavier than the desired local primitive. |

## Closest Competitors

### Closest for correctness

1. LiteLLM
2. Portkey Models plus custom calculator
3. `genai-prices`

Why they matter:

- LiteLLM and Portkey already encode hard vendor pricing dimensions.
- `genai-prices` has a clean local-library mental model and conditional pricing.

Why they do not close the gap:

- None gives a small cross-language "raw response in, exact component ledger out" abstraction with discount policies and surface/service-tier handling.

### Closest for developer ergonomics

1. `ai-sdk-cost-calculator`
2. `ai-cost-meter`
3. `tokentally`

Why they matter:

- They validate the ergonomic demand for cost helpers near SDK calls.
- `ai-sdk-cost-calculator` already returns a component-like breakdown.

Why they do not close the gap:

- They are Node or Vercel AI SDK-centric.
- Provider coverage and billing dimensions are not complete enough for the proposed project.

### Closest data sources

1. Portkey Models
2. LiteLLM `model_prices_and_context_window.json`
3. Helicone `@helicone-package/cost`
4. Simon Willison `llm-prices`
5. OpenRouter `/api/v1/models`
6. models.dev

Recommended use:

- Treat Portkey, LiteLLM, Helicone, Simon Willison `llm-prices`, and OpenRouter as upstream references with different tradeoffs.
- Do not manually maintain a full pricing catalog until the upstream adapters and conformance tests prove this is unavoidable.

## Required Differentiators

A new package must beat the existing set on these dimensions:

| Differentiator | Why it matters | Existing state |
|---|---|---|
| Provider-neutral disjoint usage ledger | Prevents double counting inclusive usage fields. | Partially handled by `genai-prices`, not universal. |
| Raw response extractors for official SDKs | Enables one- or two-line integration. | Fragmented across packages. |
| Componentized cost result | Users need to see input/output/cache/thinking, not only total. | Strong in `ai-sdk-cost-calculator`, partial elsewhere. |
| Service tier and surface modifiers | Modern pricing varies by batch, priority, flex, API surface, region, and deployment. | Strong in data maps, weak in small public APIs. |
| Custom discount policy | Real customers have negotiated provider discounts. | Mostly global multipliers or ad hoc custom prices. |
| Alias and version resolution | Providers return dated or canonical model names inconsistently. | Partial and inconsistent. |
| Point-in-time pricing | Audits and historical usage need old prices. | Strongest in `genai-prices`, mostly absent elsewhere. |
| Multi-language conformance | LLM apps are Python, Node, Go, and more. | Existing packages are mostly single-language. |
| Price provenance and staleness | Pricing changes often and source disagreement is normal. | Partial in `token-costs`, otherwise inconsistent. |

## Suggested Competitive Positioning

Short description:

> A tiny, provider-neutral cost ledger for LLM API responses.

Longer positioning:

> It is not a gateway, tracker, tokenizer, or pricing database. It is a deterministic library that turns raw LLM SDK responses plus provider/model/surface context into a precise, explainable cost breakdown.

Do not compete head-on with:

- Langfuse, Helicone, or Portkey Gateway for observability.
- LiteLLM for model routing or unified calling.
- models.dev for catalog browsing.
- Tokenizers for token estimation.

Compete against:

- Copy-pasted pricing tables.
- Hand-written cost formulas in application code.
- Rough AI SDK helpers that miss cache, thinking, or service tier billing.
- Internal spreadsheets for negotiated discounts.

## Decision Matrix

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| Stop | Avoids duplicating mature projects. | No existing package closes the full gap. | Do not stop. |
| Contribute to LiteLLM | Leverages best pricing map. | Heavy Python/gateway context, not portable. | Contribute tests/data as useful, but not sole path. |
| Contribute to `genai-prices` | Strong small Python baseline and point-in-time model. | Python-only and missing service tier/discount abstraction. | Good targeted PR path. |
| Extend `ai-sdk-cost-calculator` | Closest Node UX. | Vercel AI SDK-centric and not portable. | Useful reference, not enough. |
| Wrap Portkey Models | Fastest way to good price data. | Still need extractors, modifiers, aliases, discounts, and ledgers. | Recommended core data strategy. |
| Build from scratch with scrapers | Full control. | High maintenance burden and slow time to value. | Avoid initially. |
| Build thin portable cost kernel | Reuses existing data, fills actual gap. | Requires rigorous schema and fixtures. | Recommended. |

## Initial Provider Priority

| Priority | Provider/surface | Reason |
|---:|---|---|
| 1 | OpenAI Responses and Chat Completions | User's motivating example, aliases, reasoning, cached input, service tiers. |
| 2 | Anthropic Messages | Cache creation/read/TTL and batch pricing are core hard cases. |
| 3 | Gemini API and Vertex AI | Thinking tokens, cached content, context thresholds, surface differences. |
| 4 | AWS Bedrock Converse | Surface-specific usage and deployment/pricing modes. |
| 5 | DeepSeek | Cache hit/miss and conditional discounts. |
| 6 | xAI | OpenAI-compatible shape with cached-token edge cases. |
| 7 | OpenRouter | Aggregator/provider-routing ambiguity. |
| 8 | Vercel AI SDK | High-leverage integration surface for Node users. |

## Evidence Quality Notes

- Registry download counts are useful demand signals, not proof of active production adoption.
- Some provider pages, especially OpenAI platform docs, can be hard to scrape directly from shell due bot protection. Public official URLs should still be cited, but implementation details should be verified against official docs or live SDK fixtures before release.
- Source-visible package code is more reliable than README claims. This validation weighted source and smoke checks higher than marketing claims.
- Pricing data changes frequently. Every release should include a data date, source URL, and stale-data behavior.
