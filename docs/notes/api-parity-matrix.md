---
title: RunCost Public API Parity Matrix
date: 2026-05-25
type: reference
status: draft
---

# RunCost Public API Parity Matrix

Status: v0.x prototype
Date: 2026-05-25

This matrix tracks whether the Python, JavaScript/TypeScript, and Go packages expose the same developer-facing capabilities. It is a release gate: public APIs should not drift silently between languages.

## Legend

- `Yes`: implemented and covered by shared fixtures or language tests.
- `Partial`: implemented but missing type coverage, docs, or provider breadth.
- `No`: not implemented.
- `Planned`: intentionally deferred.

## Core APIs

| Capability | Python | JavaScript/TypeScript | Go | Evidence |
|---|---:|---:|---:|---|
| Calculate cost from normalized usage and price cards | Yes | Yes | Yes | `calculate_cost`, `calculateCost`, `CalculateCost`; shared fixtures |
| Calculate cost with advanced options | Yes | Yes | Yes | `calculate_cost` keyword options, `calculateCost` options object, `CalculateCostWithOptions`; stale/provider-reported fixtures |
| Extract usage and calculate from raw response | Yes | Yes | Yes | `from_response`, `fromResponse`, `FromResponse`; raw response fixtures |
| Aggregate already-calculated cost ledgers | Yes | Yes | Yes | `aggregate_cost_ledgers`, `aggregateCostLedgers`, `AggregateCostLedgers`; `cost-ledger-aggregation-basic.json`, `stream-final-usage-missing-warning.json` |
| Calculate with discount policies | Yes | Yes | Yes | `discount-policy-openai-basic.json` |
| Strict mode | Yes | Yes | Yes | `strict-unknown-model.json` |
| Compatibility mode with warnings | Yes | Yes | Yes | unknown model, unpriced component, unknown surface fixtures |
| Decimal-safe money arithmetic | Yes | Yes | Yes | Python `Decimal`, JS `BigInt` decimal helpers, Go `big.Rat` |
| Alias resolution through price-card aliases | Yes | Yes | Yes | `openai-responses-raw-dated-alias.json` |
| Effective-date price-card selection | Yes | Yes | Yes | `effective-date-selection.json` |
| Service-tier and region price-card matching | Yes | Yes | Yes | `service-tier-region-selection.json` |
| Unsupported service-tier warning | Yes | Yes | Yes | `service-tier-unsupported-compatibility.json` |
| Stale price-source warning | Yes | Yes | Yes | `stale-price-warning.json` |
| Provider-reported cost comparison warning | Yes | Yes | Yes | `provider-reported-cost-mismatch.json` |
| Provider-reported cost authoritative use mode | Yes | Yes | Yes | `provider-reported-cost-used.json` |
| Price source priority for user overrides | Yes | Yes | Yes | `price-source-priority-user-override.json` |
| Price source disagreement warning | Yes | Yes | Yes | `price-source-disagreement-warning.json` |
| Streaming final-usage missing warning | Yes | Yes | Yes | `stream_usage_missing`; `stream-final-usage-missing-warning.json` |
| Streaming final-usage event extraction | Yes | Yes | Yes | OpenAI `response.completed`, Anthropic Messages SSE events, and Gemini stream chunk fixtures |
| Debug trace / explain mode | Yes | Yes | Yes | `debug-trace-explain-decisions.json`; optional `debug_trace` / `debugTrace` output |
| Long-context threshold price component selection | Yes | Yes | Yes | `long-context-threshold-selection.json` |
| Missing long-context rule warning | Yes | Yes | Yes | `long-context-rule-missing.json` |
| Batch service-mode pricing through service tier | Yes | Yes | Yes | `service-mode-batch-selection.json` |
| Priority service-mode pricing through service tier | Yes | Yes | Yes | `service-mode-priority-selection.json` |
| Provisioned endpoint-hour pricing through service tier and region | Yes | Yes | Yes | `service-mode-provisioned-selection.json` |
| Component-total invariant in conformance tests | Yes | Yes | Partial | Python fixture runner validates Python/JS ledgers; Go fixture test validates expected subsets |
| Componentized cost ledger output | Yes | Yes | Yes | all cost fixtures |
| Multi-call/session ledger aggregation | Yes | Yes | Yes | Aggregates totals, matching components, price sources, discounts, and warnings from existing ledgers |

## Raw Response Extractors

| Surface | Python | JavaScript/TypeScript | Go | Evidence |
|---|---:|---:|---:|---|
| OpenAI Responses | Yes | Yes | Yes | `openai-responses-raw-cached-reasoning.json`, `openai-responses-raw-tool-calls.json`, `openai-responses-stream-completed-event.json` |
| OpenAI Chat Completions | Yes | Yes | Yes | `openai-chat-raw-cached-reasoning.json` |
| Shared OpenAI-compatible chat helper | Yes | Yes | Yes | `extract_openai_compatible_chat_completions_usage`, `extractOpenAICompatibleChatCompletionsUsage`; Go routes through `ExtractUsageLedger` |
| Anthropic Messages | Yes | Yes | Yes | `anthropic-messages-raw-cache.json`, `anthropic-messages-raw-cache-1h.json`, `anthropic-messages-stream-events.json` |
| Google Gemini / AI Studio | Yes | Yes | Yes | `extract_gemini_generate_content_usage`, `extractGeminiGenerateContentUsage`; `gemini-generate-content-raw-reasoning-cache.json`, `gemini-generate-content-stream-chunks.json` |
| Google Vertex AI | Yes | Yes | Yes | Uses Gemini generateContent extractor for `vertex.gemini.generate_content`; `vertex-gemini-generate-content-raw-basic.json` |
| AWS Bedrock Converse | Yes | Yes | Yes | `extract_bedrock_converse_usage`, `extractBedrockConverseUsage`; `bedrock-converse-raw-cache.json` |
| Azure OpenAI | Yes | Yes | Yes | `azure-openai-chat-raw-reasoning.json` |
| Groq | Yes | Yes | Yes | `groq-chat-raw-cache.json` |
| xAI / Grok | Yes | Yes | Yes | `xai-chat-raw-cache-reasoning.json` |
| Cohere | Yes | Yes | Yes | `extract_cohere_chat_usage`, `extractCohereChatUsage`; `cohere-chat-raw-usage-billed-units.json`, `cohere-chat-raw-meta-billed-units.json` |
| Mistral | Yes | Yes | Yes | `mistral-chat-raw-cache.json` |
| Hugging Face Inference Providers | Yes | Yes | Yes | `huggingface-chat-raw-basic.json` |
| OpenRouter chat completions | Yes | Yes | Yes | `extract_openrouter_chat_completions_usage`, `extractOpenRouterChatCompletionsUsage`; `openrouter-chat-raw-basic.json` |
| DeepSeek | Yes | Yes | Yes | `deepseek-chat-raw-cache-reasoning.json` |

## Price Source Adapters

| Source | Python | JavaScript/TypeScript | Go | Evidence |
|---|---:|---:|---:|---|
| User-supplied canonical price cards | Yes | Yes | Yes | most fixtures |
| Simon Willison `llm-prices` | Yes | Yes | Yes | `price_cards_from_llm_prices`, `priceCardsFromLlmPrices`, `PriceCardsFromLlmPrices`; `llm-prices-adapter-basic.json`, `llm-prices-adapter-historical.json` |
| LiteLLM model pricing JSON | Yes | Yes | Yes | `price_cards_from_litellm`, `priceCardsFromLiteLLM`, `PriceCardsFromLiteLLM`; `litellm-adapter-basic.json` |
| Portkey Models pricing shape | Yes | Yes | Yes | `price_cards_from_portkey`, `priceCardsFromPortkey`, `PriceCardsFromPortkey`; `portkey-adapter-basic.json` |
| OpenRouter `/models` API | Yes | Yes | Yes | `price_cards_from_openrouter_models`, `priceCardsFromOpenRouterModels`, `PriceCardsFromOpenRouterModels`; `openrouter-models-adapter-basic.json`, `openrouter-models-adapter-tiered.json` |
| RunCost source-cache envelope | Yes | Yes | Yes | `price_cards_from_source_cache`, `priceCardsFromSourceCache`, `PriceCardsFromSourceCache`; `source-cache-adapter-basic.json` |
| Local JSON price-source file | Yes | Yes | Yes | `price_cards_from_json_file`, `priceCardsFromJSONFile`, `PriceCardsFromJSONFile`; `user-pricing-json-file-loader.json` |
| User compact pricing data | Yes | Yes | Yes | `price_cards_from_user_pricing`, `priceCardsFromUserPricing`, `PriceCardsFromUserPricing`; `user-pricing-adapter-compact.json` |
| Helicone cost package data | Yes | Yes | Yes | `price_cards_from_helicone`, `priceCardsFromHelicone`, `PriceCardsFromHelicone`; `helicone-adapter-basic.json` |
| Provider official pricing snapshots | Planned | Planned | Planned | Milestone 3 |

## Usage Components

| Component | Python | JavaScript/TypeScript | Go | Evidence |
|---|---:|---:|---:|---|
| `input_uncached_tokens` | Yes | Yes | Yes | core fixtures |
| `input_cache_read_tokens` | Yes | Yes | Yes | cache fixtures |
| `input_cache_write_tokens` | Yes | Yes | Yes | Anthropic cache fixture |
| `input_cache_write_1h_tokens` | Yes | Yes | Yes | Anthropic 1-hour cache fixture |
| `input_image_units` | Yes | Yes | Yes | `openrouter-models-adapter-basic.json` |
| `output_text_tokens` | Yes | Yes | Yes | core fixtures |
| `output_reasoning_tokens` | Yes | Yes | Yes | reasoning fixtures |
| `web_search_units` | Yes | Yes | Yes | OpenAI tool-call fixture; Portkey adapter fixture |
| `file_search_units` | Yes | Yes | Yes | OpenAI tool-call fixture |
| `code_interpreter_call_units` | Yes | Yes | Yes | OpenAI tool-call fixture |
| Multimodal image, audio, and video units | Partial | Partial | Partial | `gemini-generate-content-raw-multimodal.json`; Gemini/Vertex modality details supported, broader provider coverage pending |
| Provider-specific tool-call pricing units | Partial | Partial | Partial | generic custom units work; provider breadth remains low |

## Type and Documentation Surfaces

| Surface | Python | JavaScript/TypeScript | Go | Evidence |
|---|---:|---:|---:|---|
| Public typed contract models | Partial | Partial | Partial | `types.py`, `index.d.ts`, Go docs/examples; `DebugTrace` typed for Python and TypeScript |
| Package-level API docs | Partial | Partial | Partial | README, package examples, alpha docs, debug trace docs |
| Public example for basic cost calculation | Yes | Yes | Yes | Python and JS examples; Go example test |
| Schema validation in conformance tests | Yes | Yes | Partial | Python runner validates schemas for Python/JS outputs; Go now validates generated cost-ledger structure and component-total invariants in fixture tests |
| Fixture metadata and coverage report | Yes | Yes | Yes | `schemas/fixture.schema.json`, fixture metadata, `scripts/check_fixture_coverage.py`, `docs/reports/fixture-coverage.md` |
| Generated artifact drift check | Yes | Yes | Yes | `scripts/check_project_hygiene.py` |

## Framework Adapters

| Framework | Python | JavaScript/TypeScript | Go | Evidence |
|---|---:|---:|---:|---|
| LangChain | Yes | Yes | Yes | `from_langchain_message`, `fromLangChainMessage`, `FromLangChainMessage`; lower-level `extract_langchain_chat_usage`, `extractLangChainChatUsage`; `langchain-chat-message-usage-metadata.json` |
| LangChain callback/context manager | Yes | N/A | N/A | `track_langchain_costs`, `RunCostLangChainCallback`; `langchain-callback-context-manager.json` |
| LlamaIndex | Yes | Yes | Yes | `from_llamaindex_token_counter`, `fromLlamaIndexTokenCounter`, `FromLlamaIndexTokenCounter`; lower-level `extract_llamaindex_token_counter_usage`, `extractLlamaIndexTokenCounterUsage`; `llamaindex-token-counter-events.json` |
| Vercel AI SDK | Yes | Yes | Yes | `from_vercel_ai_sdk_result`, `fromVercelAISDKResult`, `FromVercelAISDKResult`; lower-level `extract_vercel_ai_sdk_usage`, `extractVercelAISDKUsage`; `vercel-ai-sdk-generate-text-total-usage.json` |
| Vercel AI SDK middleware | N/A | Yes | N/A | `createRunCostVercelMiddleware`; `vercel-ai-sdk-middleware-wrap-generate.json` |
| Haystack | Yes | Yes | Yes | `from_haystack_generator_result`, `fromHaystackGeneratorResult`, `FromHaystackGeneratorResult`; lower-level `extract_haystack_generator_usage`, `extractHaystackGeneratorUsage`; `haystack-openai-chat-generator-meta.json` |
| LiteLLM proxy response metadata | Yes | Yes | Yes | `from_litellm_response`, `fromLiteLLMResponse`, `FromLiteLLMResponse`; lower-level `extract_litellm_proxy_response_usage`, `extractLiteLLMProxyResponseUsage`; `litellm-proxy-response-cost-metadata.json` |
| AutoGen / AG2 usage summary | Yes | Yes | Yes | `from_ag2_usage_summary`, `fromAG2UsageSummary`, `FromAG2UsageSummary`; lower-level `extract_ag2_usage_summary_usage`, `extractAG2UsageSummaryUsage`; `ag2-usage-summary-actual.json`, `ag2-usage-summary-total.json` |
| OpenAI Agents SDK | Planned | Planned | Planned | Milestone 6 |
| Semantic Kernel | Partial | Partial | Partial | Documented adapter path in `docs/notes/framework-adapter-notes.md`; no fixture-backed extractor yet |
| LangSmith export/compare | Partial | Partial | Partial | Documented adapter path in `docs/notes/framework-adapter-notes.md`; no fixture-backed extractor yet |
| OpenRouter-compatible SDK paths | Partial | Partial | Partial | Documented adapter path in `docs/notes/framework-adapter-notes.md`; OpenRouter chat/model fixtures exist, SDK wrappers do not |

## Release Rule

A feature can be called polyglot-supported only when:

1. The public contract is represented in schemas or package types.
2. At least one shared fixture proves the behavior.
3. Python, JavaScript/TypeScript, and Go pass the fixture.
4. This matrix marks the feature `Yes` for all first-class languages.
5. Any exceptions are explicit and temporary.
