---
title: RunCost Warnings And Limitations
date: 2026-05-25
type: reference
status: draft
---

# RunCost Warnings And Limitations

RunCost should be boring and trustworthy. When it cannot fully explain a cost, it should say so in the returned ledger.

## Modes

Compatibility mode:

- Best effort.
- Returns a cost ledger when possible.
- Includes warnings for unknown or ambiguous pricing behavior.

Strict mode:

- Intended for tests, CI, reconciliation, and production guardrails.
- Fails when compatibility mode would return warnings.

## Warning Codes

Current warning codes:

- `unknown_provider`
- `unknown_surface`
- `unknown_model`
- `alias_inferred`
- `price_not_found`
- `price_stale`
- `price_source_disagreement`
- `usage_field_ignored`
- `inclusive_usage_ambiguous`
- `component_unpriced`
- `service_tier_unsupported`
- `long_context_rule_missing`
- `discount_not_applied`
- `stream_usage_missing`
- `historical_price_missing`
- `tool_component_unpriced`
- `provider_reported_cost_used`
- `provider_reported_cost_mismatch`

Warnings include a message, and may include a `path` and `metadata`.

## Common Causes

`unknown_surface`: RunCost does not know how to extract usage for the supplied provider surface.

`unknown_model`: usage was extracted, but no matching price card was available.

`component_unpriced`: one or more usage components did not have a matching price component.

`tool_component_unpriced`: a tool or feature unit was present but not priced.

`price_stale`: a matching price card exists, but its source retrieval timestamp is older than the freshness threshold.

`price_source_disagreement`: multiple matching sources disagree.

`provider_reported_cost_mismatch`: RunCost's computed total differs from a provider-reported total.

`stream_usage_missing`: aggregation expected final streaming usage, or a specific number of call ledgers, but did not observe enough cost ledgers. The aggregate total may be incomplete.

## Current Limitations

- Registry publishing is not complete.
- Go types are still map-backed prototype types.
- Source adapters are prototypes, not a comprehensive provider price database.
- Aggregation is first-class only for already-calculated cost ledgers.
- Streaming support covers selected final-usage event envelopes for OpenAI Responses, Anthropic Messages, and Gemini generateContent, plus warnings for missing expected final usage. It does not estimate usage from arbitrary partial text chunks.
- Debug trace exists for core calculator decisions, but provider extractor and framework middleware traces are still shallow.
- Official price-page monitoring and pull-request automation are not implemented.
- Tool-call pricing coverage exists only for selected fixtures and provider shapes.
- Historical point-in-time pricing exists in the model but is not comprehensive.
- Framework adapters cover selected usage metadata objects plus initial LangChain callback/context-manager and Vercel `wrapGenerate` middleware helpers, not every framework callback or streaming pattern.
- Semantic Kernel, AutoGen/AG2, LangSmith, and OpenRouter-compatible SDK paths are documented as partial integration paths only; they still need fixture-backed adapters before they are supported.
- Haystack and LiteLLM proxy metadata now have fixture-backed adapters, but only for selected OpenAI-compatible metadata shapes.

## Production Guidance

- Pin price-card snapshots used for billing.
- Prefer user overrides for contract rates.
- Run strict mode in tests.
- Review warnings before using totals for customer-visible billing.
- Keep provider-reported totals when providers expose authoritative billing data.
- Store the returned cost ledger with the request trace if you need auditability.
