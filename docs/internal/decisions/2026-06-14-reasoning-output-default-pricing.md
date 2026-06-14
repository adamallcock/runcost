---
title: Reasoning Output Default Pricing
date: 2026-06-14
type: decision-record
status: accepted
---

# Reasoning Output Default Pricing

## Decision

When a matching price card publishes output-token pricing but omits a separate
`output_reasoning_tokens` component, RunCost prices `output_reasoning_tokens`
at the matching output-token rate by default.

The default is applied only after direct matching fails:

- A direct `output_reasoning_tokens` price wins.
- A source card that explicitly marks `output_reasoning_tokens` unsupported
  still emits `source_capability_unsupported`.
- If no applicable output-token price exists, RunCost keeps the existing
  unpriced-component warning behavior.

Fallback-priced components include metadata:

```json
{
  "pricing_policy": "reasoning_tokens_priced_as_output_tokens",
  "priced_as_component": "output_text_tokens",
  "fallback_reason": "no_separate_reasoning_price"
}
```

Provider-specific policies for Gemini and xAI keep their existing metadata
labels when they apply.

## Rationale

Providers and upstream price catalogs often publish a single output-token rate
even when usage payloads split visible output and reasoning or thinking tokens.
Leaving those reasoning tokens unpriced makes default cost estimates
systematically low. Pricing them at the same matched output-token rate is the
most useful compatibility-mode default, as long as the cost ledger records that
the price was inferred rather than directly published.

## Implementation Contract

- The fallback must use a price component from the same matched price-card set
  and request context as the missing reasoning component.
- For multimodal output, prefer output components present in the usage ledger
  before falling back to `output_text_tokens`.
- The fallback must not override source capability metadata that explicitly
  declares `output_reasoning_tokens` unsupported.
- The behavior must be covered across Python, JavaScript, and Go by
  `fixtures/reasoning-output-default-pricing.json` and
  `fixtures/gemini-live-translate-audio-thinking-preferred.json`.
