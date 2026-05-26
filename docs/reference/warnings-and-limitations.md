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
- `source_capability_unsupported`
- `service_tier_unsupported`
- `long_context_rule_missing`
- `discount_not_applied`
- `stream_usage_missing`
- `historical_price_missing`
- `tool_component_unpriced`
- `provider_reported_cost_used`
- `provider_reported_cost_mismatch`

Warnings include a stable code, a message, and typed metadata. They may include
a `path` when a warning points to a specific provider or ledger field.

Warning metadata is intentionally required so downstream billing, reconciliation,
and alerting code can group warnings without parsing human-readable messages.
The current metadata contract is locked in `schemas/taxonomy.json` under
`warning_metadata_required_keys` and enforced by the shared fixture runner.
For fixture-backed warning coverage and V1 warning-code support status, see
[Generated Warning Coverage](../generated/warning-coverage.md).

| Warning code | Required metadata keys |
|---|---|
| `unknown_provider` | `provider`, `surface`, `model` |
| `unknown_surface` | `provider`, `surface`, `model` |
| `unknown_model` | `provider`, `surface`, `model` |
| `alias_inferred` | `requested_model`, `billed_model` |
| `price_not_found` | `provider`, `surface`, `model` |
| `price_stale` | `source`, `age_days`, `threshold_days`, `retrieved_at` |
| `price_source_disagreement` | `component`, `selected_price_card_id`, `candidate_price_card_ids` |
| `usage_field_ignored` | `field` |
| `inclusive_usage_ambiguous` | `field` |
| `component_unpriced` | `component`, `unit`, `model` |
| `source_capability_unsupported` | `component`, `price_card_id`, `source` |
| `service_tier_unsupported` | `model`, `service_tier` |
| `long_context_rule_missing` | `component`, `unit`, `total_input_tokens` |
| `discount_not_applied` | `policy_id` |
| `stream_usage_missing` | `actual_ledger_count` |
| `historical_price_missing` | `model`, `priced_at` |
| `tool_component_unpriced` | `component`, `unit`, `model` |
| `provider_reported_cost_used` | `provider_reported_cost`, `calculated_total` |
| `provider_reported_cost_mismatch` | `provider_reported_cost`, `calculated_total` |

## Common Causes

`unknown_surface`: RunCost does not know how to extract usage for the supplied provider surface.

`unknown_provider`: usage was extracted for a model and surface that appear in price data, but not for the requested provider.

`unknown_model`: usage was extracted, but no matching price card was available.

`usage_field_ignored`: a normalized usage ledger explicitly marked a raw field as intentionally not mapped to a cost component.

`inclusive_usage_ambiguous`: a normalized usage ledger explicitly marked a raw field as an inclusive total while RunCost priced the component fields instead.

`component_unpriced`: one or more usage components did not have a matching price component.

`source_capability_unsupported`: a matching price source explicitly states that it does not price the usage component.

`tool_component_unpriced`: a tool or feature unit, such as hosted search, file search, code interpreter, computer-use actions, function calls, rerank, generation, transcription, execution seconds, or GB-day storage, was present but not priced.

`price_stale`: a matching price card exists, but its source retrieval timestamp is older than the freshness threshold.

`price_source_disagreement`: multiple matching sources disagree.

`provider_reported_cost_mismatch`: RunCost's computed total differs from a provider-reported total.

`stream_usage_missing`: aggregation expected final streaming usage, or a specific number of call ledgers, but did not observe enough cost ledgers. The aggregate total may be incomplete.

## Current Limitations

- Registry publishing is not complete.
- Go now has typed wrappers for normalized usage, price cards, discounts, and
  core calculation, but raw provider and framework adapter paths are still
  map-backed prototype objects.
- Source adapters are prototypes, not a comprehensive provider price database.
- Aggregation is first-class only for already-calculated cost ledgers.
- Streaming support covers selected final-usage event envelopes for OpenAI Responses, Anthropic Messages, and Gemini generateContent, plus warnings for missing expected final usage. It does not estimate usage from arbitrary partial text chunks.
- Debug trace exists for core calculator decisions, but provider extractor and framework middleware traces are still shallow.
- Official price-page monitoring and pull-request automation are not implemented.
- Tool-call pricing coverage exists only for selected fixtures and provider shapes.
- Historical point-in-time pricing exists in the model but is not comprehensive.
- Framework adapters cover selected usage metadata objects plus initial LangChain callback/context-manager and Vercel `wrapGenerate` / `onFinish` helpers, not every framework callback or streaming pattern.
- Semantic Kernel, LangSmith, OpenRouter-compatible SDK paths, OpenAI Agents SDK usage objects, and Vercel `streamText` finish objects now have fixture-backed plain-object adapters. A sanitized Milestone 8 smoke harness exists, but live run evidence and real app validation are still incomplete.
- Haystack, LiteLLM proxy metadata, AutoGen/AG2 usage summaries, LangSmith exports, and Semantic Kernel telemetry are covered only for selected metadata or summary shapes.
- AutoGen/AG2 support compares AG2-reported cost from usage summaries as framework-reported cost; AG2 custom-price and Azure model-version behavior can make that value differ from RunCost price cards.

## Production Guidance

- Pin price-card snapshots used for billing.
- Prefer user overrides for contract rates.
- Run strict mode in tests.
- Review warnings before using totals for customer-visible billing.
- Keep provider-reported totals when providers expose authoritative billing data.
- Store the returned cost ledger with the request trace if you need auditability.
