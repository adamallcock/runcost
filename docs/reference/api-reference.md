---
title: RunCost API Reference
date: 2026-05-25
type: reference
status: active
---

# RunCost API Reference

This document describes the public API shape that currently exists across Python, JavaScript/TypeScript, and Go. The canonical behavior is defined by shared fixtures in `fixtures/` and schemas in `schemas/`.

## Core Calculation

| Capability | Python | JavaScript/TypeScript | Go |
|---|---|---|---|
| Calculate from canonical usage | `calculate_cost(...)` | `calculateCost(options)` | `CalculateCost(options)` |
| Calculate with explicit Go mode | N/A | N/A | `CalculateCostWithMode(options, mode)` |
| Calculate with Go options | N/A | N/A | `CalculateCostWithOptions(options)` |
| Calculate from typed Go structs | N/A | N/A | `CalculateCostTyped(...)`, `CalculateCostTypedWithOptions(...)` |
| Aggregate existing ledgers | `aggregate_cost_ledgers(...)` | `aggregateCostLedgers(options)` | `AggregateCostLedgers(costLedgers, options)` |
| Normalize batch results | `from_batch_results(...)` | `fromBatchResults(items, options)` | `FromBatchResults(items, options)` |
| Estimate expected components | `estimate_cost(...)` | `estimateCost(options)` | `EstimateCost(options, priceCards, policies)` |
| Evaluate a stateless budget | `evaluate_budget(...)` | `evaluateBudget(total, options)` | `EvaluateBudget(total, options)` |
| Reconcile provider cost | `reconcile_cost(...)` | `reconcileCost(ledger, reported, options)` | `ReconcileCost(ledger, reported, options)` |

Inputs:

- `usageLedger` / `usage_ledger`: canonical usage ledger.
- `priceCards` / `price_cards`: candidate price cards.
- `discountPolicies` / `discount_policies`: optional discounts and markups.
- `mode`: `compatibility` or `strict`.
- `priceSourcePriority` / `price_source_priority`: preferred source ordering for matching cards.
- `providerReportedCost` / `provider_reported_cost`: optional provider total for comparison or authoritative use.
- `providerReportedCostMode` / `provider_reported_cost_mode`: `compare` or `use`.
- `staleAfterDays` / `stale_after_days`: freshness warning threshold.
- `debugTrace` / `debug_trace`: include an optional decision trace in the returned cost ledger.
- `attribution`: passive run/session/workflow/tenant/feature metadata and string
  tags. Discount-policy `match.tags` entries match a required subset of those
  tags; attribution otherwise has no effect on price selection.

Output:

- `CostLedger` with `components`, `total`, `price_sources`, `applied_discounts`, `warnings`, and optional `debug_trace`.

Go also exposes typed wrappers for the normalized usage and price-card path:
`UsageLedger`, `ModelIdentity`, `UsageComponent`, `PriceCard`,
`PriceComponent`, `Price`, `Source`, `DiscountPolicy`, `DiscountMatch`,
`DiscountAdjustment`, and `CostOptions`. These structs convert to the canonical
schema-shaped objects and delegate to the same calculator as the map-backed API.

## Aggregation

Aggregation starts from already-calculated `CostLedger` objects and returns one combined ledger for a session, agent run, batch, or streaming wrapper.

Inputs:

- `cost_ledgers` / `costLedgers`: ledgers to merge.
- `provider`, `surface`, `model`: labels for the aggregate ledger. Defaults are `aggregate`, `aggregate.cost_ledgers`, and `multiple`.
- `expected_ledger_count` / `expectedLedgerCount`: optional count expected by the caller.
- `stream_final_usage_expected` / `streamFinalUsageExpected`: set when a streaming API should emit final usage.
- `stream_final_usage_present` / `streamFinalUsagePresent`: set false when that final usage was not observed.
- `mode`: `compatibility` or `strict`.

Output:

- `CostLedger` with summed totals, matching component groups, de-duplicated price sources, copied discounts, copied warnings, aggregate metadata, and `stream_usage_missing` when expected stream usage is absent.

## Raw Provider Extraction

| Surface | Python | JavaScript/TypeScript | Go |
|---|---|---|---|
| Generic dispatch | `extract_usage_ledger` | `extractUsageLedger` | `ExtractUsageLedger` |
| OpenAI Responses | `extract_openai_responses_usage` | `extractOpenAIResponsesUsage` | via dispatch |
| OpenAI Embeddings | `extract_openai_embeddings_usage` | `extractOpenAIEmbeddingsUsage` | via dispatch |
| xAI Responses | via `extract_usage_ledger(..., surface="xai.responses")` | via `extractUsageLedger(..., { surface: "xai.responses" })` | via dispatch |
| OpenAI Chat Completions | `extract_openai_chat_completions_usage` | `extractOpenAIChatCompletionsUsage` | via dispatch |
| OpenAI-compatible Chat Completions | `extract_openai_compatible_chat_completions_usage` | `extractOpenAICompatibleChatCompletionsUsage` | via dispatch |
| OpenRouter Chat Completions | `extract_openrouter_chat_completions_usage` | `extractOpenRouterChatCompletionsUsage` | via dispatch |
| Meta Model API Responses | `extract_meta_responses_usage` | `extractMetaResponsesUsage` | via dispatch |
| Meta Model API Chat Completions | `extract_meta_chat_completions_usage` | `extractMetaChatCompletionsUsage` | via dispatch |
| Anthropic Messages | `extract_anthropic_messages_usage` | `extractAnthropicMessagesUsage` | via dispatch |
| Gemini or Vertex `generateContent` | `extract_gemini_generate_content_usage` | `extractGeminiGenerateContentUsage` | via dispatch |
| Gemini Live API | `extract_gemini_live_usage` | `extractGeminiLiveUsage` | via dispatch |
| Google Gemini Interactions | `extract_google_interactions_usage` | `extractGoogleInteractionsUsage` | via dispatch |
| AWS Bedrock Converse | `extract_bedrock_converse_usage` | `extractBedrockConverseUsage` | via dispatch |
| AWS Bedrock InvokeModel | `extract_bedrock_invoke_model_usage` | `extractBedrockInvokeModelUsage` | via dispatch |
| Cohere Chat | `extract_cohere_chat_usage` | `extractCohereChatUsage` | via dispatch |
| Cohere Rerank | `extract_cohere_rerank_usage` | `extractCohereRerankUsage` | via dispatch |

OpenAI-compatible dispatch also has explicit provider routes for Tinker,
NVIDIA, AI21, Arcee, Cohere-compatible chat, DashScope, Inception, Poolside,
Xiaomi, and ZAI. MiniMax uses its explicit Anthropic-compatible Messages route.

Common one-call helper:

| Language | Function |
|---|---|
| Python | `from_response(response, ...)` |
| JavaScript/TypeScript | `fromResponse(response, options)` |
| Go | `FromResponse(response, options, priceCards, discountPolicies)` |

Python `from_response` and `from_batch_results` also accept Anthropic SDK/Pydantic
objects exposing `model_dump()` or `dict()`; callers do not need to serialize
them to JSON first.

For an Anthropic fallback, render attribution from
`ledger.metadata.anthropic_fallback`. `utilized` says whether a fallback served
the response; `requested_model`, `attempted_models`, and `serving_model` describe
the route; and `pricing_models` lists the models whose reported usage produced
billable components. A UI can therefore state, for example, “Fallback utilized;
`claude-opus-5` was used for pricing.” Individual components retain
`metadata.billing_model` and `metadata.usage_iteration_index` for audit detail.

For Message Batches, inspect each item even when provider status is `succeeded`.
RunCost marks refusal results with `metadata.refusal` and
`metadata.requires_retry`; server-side fallback is not available in Anthropic
Message Batches, so a later retry result is a separate priced item/batch.

For OpenAI, preserve caller request intent by supplying `service_tier: "fast"`
in extraction context when Fast was requested. Fast and Priority are independent
canonical request and price-card tiers. The calculator selects an applicable
Fast card first; only when none exists may it use a Priority card. That one-way
compatibility fallback records `metadata.service_tier_resolution` with
`requested: "fast"`, `priced_as: "priority"`, `fallback: true`, and the selected
price-card IDs. Priority never falls back to Fast. This distinction matters for
GPT-5.6 and earlier responses that may report `priority` after a Fast request.

Auto-resolving convenience helper (may read or refresh the public price cache):

| Language | Function |
|---|---|
| Python | `from_response_auto(response, ...)` |
| JavaScript/TypeScript | `await fromResponseAuto(response, options)` |
| Go | `FromResponseAuto(ctx, response, options, priceCards, discountPolicies)` |

## Framework Adapters

| Framework object | Python | JavaScript/TypeScript | Go |
|---|---|---|---|
| LangChain AIMessage | `from_langchain_message` | `fromLangChainMessage` | `FromLangChainMessage` |
| OpenAI Agents SDK usage | `from_openai_agents_usage` | `fromOpenAIAgentsUsage` | `FromOpenAIAgentsUsage` |
| Vercel AI SDK `generateText` result | `from_vercel_ai_sdk_result` | `fromVercelAISDKResult` | `FromVercelAISDKResult` |
| Vercel AI SDK `streamText` finish result | `from_vercel_ai_sdk_stream_finish` | `fromVercelAISDKStreamFinish` | `FromVercelAISDKStreamFinish` |
| LlamaIndex token counter | `from_llamaindex_token_counter` | `fromLlamaIndexTokenCounter` | `FromLlamaIndexTokenCounter` |
| Haystack generator result | `from_haystack_generator_result` | `fromHaystackGeneratorResult` | `FromHaystackGeneratorResult` |
| LiteLLM proxy / SDK response | `from_litellm_response` | `fromLiteLLMResponse` | `FromLiteLLMResponse` |
| AutoGen / AG2 usage summary | `from_ag2_usage_summary` | `fromAG2UsageSummary` | `FromAG2UsageSummary` |
| LangSmith run/export usage | `from_langsmith_run` | `fromLangSmithRun` | `FromLangSmithRun` |
| Semantic Kernel telemetry | `from_semantic_kernel_telemetry` | `fromSemanticKernelTelemetry` | `FromSemanticKernelTelemetry` |
| OpenRouter SDK response | `from_openrouter_sdk_response` | `fromOpenRouterSDKResponse` | `FromOpenRouterSDKResponse` |
| LangChain callback/context manager | `track_langchain_costs` / `RunCostLangChainCallback` | N/A | N/A |
| Vercel AI SDK middleware | N/A | `createRunCostVercelMiddleware` | N/A |
| Vercel AI SDK `onFinish` helper | N/A | `createRunCostVercelOnFinish` | N/A |
| OpenRouter Agent SDK result | N/A | `fromOpenRouterAgentResult` | N/A |
| OpenTelemetry GenAI span | `usage_ledger_from_otel_genai_span` / `from_otel_genai_span` | `usageLedgerFromOTelGenAISpan` / `fromOTelGenAISpan` | `UsageLedgerFromOTelGenAISpan` / `FromOTelGenAISpan` |
| OpenTelemetry cost attributes | `otel_cost_attributes` | `otelCostAttributes` | `OTelCostAttributes` |

The framework helpers route through the same cost calculator after extracting canonical usage.

Streaming final usage:

- OpenAI Responses accepts the final `response.completed` event envelope.
- Anthropic Messages accepts an object with `events` containing `message_start`, `content_block_start`, `message_delta`, and `message_stop` SSE payloads. It accumulates final usage and follows a final fallback block/iteration when `message_start` still names the primary model.
- Gemini / Vertex generateContent accepts an object with `chunks` or `stream` and uses the last chunk carrying `usageMetadata`.
- Gemini Live API accepts top-level `usageMetadata`, or a `chunks` / `stream` collection where the final server message carries `usageMetadata`.
- Google Gemini Interactions accepts top-level/event `metadata.total_usage`, camelCase `metadata.totalUsage`, legacy `metadata.usage`, or `chunks` / `stream` / `events` collections and uses the last event carrying usage metadata.
- These are final-usage extraction paths, not arbitrary partial-token estimation.
- Meta Model API support is fixture-backed and credentialed-smoke-backed for
  `/models`, `/chat/completions`, and `/responses` on
  `https://api.meta.ai/v1`. A reviewed public-preview snapshot supports opt-in
  compatibility estimates, but Meta prices are excluded from the default
  catalog until exact rates are verified from a primary Meta pricing source.

## Price Source Adapters

| Source | Python | JavaScript/TypeScript | Go |
|---|---|---|---|
| Simon Willison `llm-prices` | `price_cards_from_llm_prices` | `priceCardsFromLlmPrices` | `PriceCardsFromLlmPrices` |
| LiteLLM model price JSON | `price_cards_from_litellm` | `priceCardsFromLiteLLM` | `PriceCardsFromLiteLLM` |
| OpenRouter models API | `price_cards_from_openrouter_models` | `priceCardsFromOpenRouterModels` | `PriceCardsFromOpenRouterModels` |
| models.dev API catalog | `price_cards_from_models_dev` | `priceCardsFromModelsDev` | `PriceCardsFromModelsDev` |
| Reviewed official pricing snapshots | `price_cards_from_official_snapshot` | `priceCardsFromOfficialSnapshot` | `PriceCardsFromOfficialSnapshot` |
| Portkey pricing data | `price_cards_from_portkey` | `priceCardsFromPortkey` | `PriceCardsFromPortkey` |
| Local JSON price-source file | `price_cards_from_json_file` | `priceCardsFromJSONFile` | `PriceCardsFromJSONFile` |
| Local YAML price-source file | `price_cards_from_yaml_file` | `priceCardsFromYAMLFile` | `PriceCardsFromYAMLFile` |
| User compact pricing data | `price_cards_from_user_pricing` | `priceCardsFromUserPricing` | `PriceCardsFromUserPricing` |
| Helicone model-registry data | `price_cards_from_helicone` | `priceCardsFromHelicone` | `PriceCardsFromHelicone` |
| Pydantic `genai-prices` | `price_cards_from_genai_prices` | `priceCardsFromGenAIPrices` | `PriceCardsFromGenAIPrices` |

Adapters return canonical `PriceCard` objects. Users can merge these with their own custom cards and then use `priceSourcePriority` to make overrides deterministic.

## External Price Resolver

| Capability | Python | JavaScript/TypeScript | Go |
|---|---|---|---|
| Select one source | `resolve_price_catalog` | `resolvePriceCatalog` | `ResolvePriceCatalog` |
| Auto-price a response | `from_response_auto` | `fromResponseAuto` | `FromResponseAuto` |
| Auto-price batch results | `from_batch_results_auto` | `fromBatchResultsAuto` | `FromBatchResultsAuto` |
| Auto-price an OTel span | `from_otel_genai_span_auto` | `fromOTelGenAISpanAuto` | `FromOTelGenAISpanAuto` |
| Auto-price an estimate | `estimate_cost_auto` | `estimateCostAuto` | `EstimateCostAuto` |
| Inspect/clear cache | `price_cache_status`, `clear_price_cache` | `priceCacheStatus`, `clearPriceCache` | `PriceCacheStatus`, `ClearPriceCache` |

Explicit cards always win, including an explicitly empty list. Otherwise the
general source order is `genai-prices`, models.dev, then LiteLLM. OpenRouter
usage tries the OpenRouter models API first. Results include `price_resolution`
metadata with the selected source, attempted sources, cache status, timestamps,
and operational warnings. Sources are never silently merged.

## CLI

The Python and npm packages install matching quote commands. Python also keeps
the source/fixture maintenance commands:

| Command | Purpose |
|---|---|
| `runcost quote PATH --provider PROVIDER` | Price one provider-response JSON object using external resolution and cache. Use `-` for stdin. |
| `runcost quote - --jsonl --provider PROVIDER` | Price a JSONL stream with one canonical JSON ledger per input row. |
| `npx runcost quote PATH --provider PROVIDER` | Run the equivalent npm CLI. |
| `runcost prices refresh|status|clear` | Refresh, inspect, or clear managed external price-cache entries. |
| `runcost price-cards --source-type TYPE --input PATH` | Convert one pricing source JSON file to canonical price cards. |
| `runcost fixture-check PATH` | Calculate one fixture and compare the expected cost-ledger subset when present. |

The CLI is dependency-free and intentionally narrower than the repository test
runner. Use `npm test` for the full Python, JavaScript/TypeScript, and Go
conformance suite.

## Modes

Compatibility mode returns a ledger with warnings when possible.

Strict mode raises or fails fixture validation when the calculator would otherwise emit warnings. This is useful for tests, billing reconciliation, and production cost controls.

## Debug Trace

Set `debug_trace=True` in Python, `debugTrace: true` or `debug_trace: true` in JavaScript, or `"debug_trace": true` in Go options to include `debug_trace` in the returned ledger.

The trace records price-card candidates, selected component prices, alias resolution, discount applications, and warnings. See [Debug Trace](debug-trace.md).

## Canonical Schemas

- `schemas/usage-ledger.schema.json`
- `schemas/price-card.schema.json`
- `schemas/discount-policy.schema.json`
- `schemas/cost-ledger.schema.json`
- `schemas/debug-trace.schema.json`
- `schemas/batch-ledger.schema.json`
- `schemas/catalog-manifest.schema.json`
- `schemas/budget-evaluation.schema.json`
- `schemas/reconciliation.schema.json`

The schemas are language-neutral and should remain the source of truth for future generated types.
