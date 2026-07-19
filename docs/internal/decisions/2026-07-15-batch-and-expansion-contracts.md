---
title: Batch and Product Expansion Contracts
date: 2026-07-15
type: decision-record
status: accepted
---

# Batch and Product Expansion Contracts

## Decision

RunCost will expose one canonical batch ledger while preserving each provider's
native result envelope. A batch item is either `succeeded` with a normal
`CostLedger`, or a visible terminal/non-terminal error state with no fabricated
zero-cost success. Batch aggregation is keyed by provider IDs and never relies
on output order.

Normal endpoint extraction remains the source of truth. Batch adapters only:

1. identify the provider item and terminal state;
2. unwrap the nested normal response;
3. attach `service_tier=batch`, batch/item IDs, and caller attribution;
4. call the existing normal-response extractor and calculator; and
5. aggregate successful ledgers without dropping failed items.

## Provider envelopes

| Provider | Native success envelope | Native failure signal | Canonical surface |
| --- | --- | --- | --- |
| OpenAI Batch | `response.body` plus `custom_id` | top-level `error` or non-2xx `response.status_code` | endpoint inferred from the batch request URL or explicit `surface` |
| Anthropic Message Batches | `result.type=succeeded` and `result.message` | `errored`, `canceled`, or `expired` result | `anthropic.messages` |
| Gemini Developer API | inline `response`, or a file response record carrying `key` | inline/file `error` or status object | `google.gemini.generate_content` |
| Vertex Gemini batch prediction | top-level `response`, with `status`, `request`, and `processed_time` retained | non-empty `status` and no usable response | `vertex.gemini.generate_content` |
| Amazon Bedrock batch inference | `modelOutput` plus `recordId` | `error` replacing `modelOutput` | caller-selected Converse or InvokeModel surface |

The adapters set `service_tier=batch`; they do not apply an arithmetic 50%
discount. A batch price is selected only when a matching batch price card exists.
This is necessary because provider eligibility and cache treatment differ.

## One-call behavior

- Deterministic functions never fetch or select package pricing implicitly.
- Auto convenience functions resolve one named external source through the
  managed cache when cards are omitted.
- Explicit cards always win; an explicit empty list means intentionally
  unpriced and performs no network request.
- Surface inference is conservative. Distinctive provider shapes may be
  inferred; generic OpenAI-compatible `usage` objects require provider/surface
  context unless the object type makes the endpoint unambiguous.

## Attribution

`UsageLedger`, `CostLedger`, aggregate ledgers, and batch items may carry:

- `run_id`
- `session_id`
- `workflow`
- `tenant_id`
- `feature`
- string-valued `tags`

Attribution is passive. It cannot affect price selection unless a caller
explicitly supplies a discount policy whose tag match uses the same values.

## OpenTelemetry GenAI mapping

The adapter consumes the current OpenTelemetry GenAI attributes:

- `gen_ai.provider.name`
- `gen_ai.operation.name`
- `gen_ai.request.model`
- `gen_ai.response.model`
- `gen_ai.usage.input_tokens`
- `gen_ai.usage.output_tokens`
- `gen_ai.usage.cache_creation.input_tokens`
- `gen_ai.usage.cache_read.input_tokens`
- `gen_ai.usage.reasoning.output_tokens`

The inclusive input/output totals are netted against cache and reasoning
sub-counts so components do not double count. Unknown `gen_ai.*` and
provider-specific attributes remain in metadata. OpenAI request/response
service-tier attributes are mapped to context without promoting them to a
generic OpenTelemetry standard.

## Catalog source and integrity behavior

Pydantic `genai-prices` source features are converted when they map exactly to
RunCost contracts. Match clauses and schedules that cannot be represented as a
static alias/card are retained in metadata and surfaced as adapter warnings.
Catalog manifests are deterministic JSON, include provider shards, and sign
each artifact with SHA-256. The signature proves byte identity, not publisher
identity or freshness.

## Product boundary

Estimation, budget evaluation, reconciliation, conformance, and telemetry
enrichment are stateless pure helpers. RunCost does not store spend, proxy
requests, route models, emit telemetry to a backend, or become a billing system.

## Primary sources

- [OpenAI Batch API](https://developers.openai.com/api/docs/guides/batch)
- [Anthropic Message Batches](https://platform.claude.com/docs/en/build-with-claude/batch-processing)
- [Gemini Batch API](https://ai.google.dev/gemini-api/docs/batch-api)
- [Vertex AI Gemini batch samples](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/samples/generativeaionvertexai-batch-predict-gemini-createjob-gcs)
- [Amazon Bedrock batch output](https://docs.aws.amazon.com/bedrock/latest/userguide/batch-inference-results.html)
- [OpenTelemetry GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai)
- [Pydantic `genai-prices`](https://github.com/pydantic/genai-prices)
