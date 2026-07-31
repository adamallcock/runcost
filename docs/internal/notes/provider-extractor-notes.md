---
title: RunCost Provider Extractor Notes
date: 2026-05-25
type: note
status: draft
---

# RunCost Provider Extractor Notes

Status: v0.x prototype
Date: 2026-05-25

This document records raw provider usage fields that the current extractors depend on. It is not a pricing source; it is a mapping note for usage normalization.

## OpenAI Responses

Surface:

- `openai.responses`

Source references:

- OpenAI streaming docs list `response.completed` as a common lifecycle event and the API reference shows completed response events carrying a nested `response` object: https://platform.openai.com/docs/api-reference/streaming
- OpenAI Responses reference documents `usage.input_tokens`, `usage.input_tokens_details.cached_tokens`, `usage.output_tokens`, `usage.output_tokens_details.reasoning_tokens`, and `usage.total_tokens`: https://developers.openai.com/api/reference/resources/responses/methods/create
- OpenAI prompt caching docs document `usage.input_tokens_details.cache_write_tokens` for GPT-5.6 and later models: https://developers.openai.com/api/docs/guides/prompt-caching

Mapping:

- Non-streaming responses read usage from the top-level `usage` object.
- Streaming final events with `type == "response.completed"` read usage from `response.usage`.
- `usage.input_tokens` minus cache-read and cache-write tokens -> `input_uncached_tokens`.
- `usage.input_tokens_details.cached_tokens` -> `input_cache_read_tokens`.
- `usage.input_tokens_details.cache_write_tokens` -> `input_cache_write_tokens`.
- `usage.output_tokens` minus reasoning tokens -> `output_text_tokens`.
- `usage.output_tokens_details.reasoning_tokens` -> `output_reasoning_tokens`.
- OpenAI top-level `service_tier` values `default` and `auto` normalize to
  `standard`; `batch` and `flex` are preserved. OpenAI renamed Priority to Fast
  on July 30, 2026 while keeping both API values valid. RunCost preserves
  `fast` and `priority` independently. Fast requests prefer Fast cards and may
  fall back to Priority cards with explicit resolution metadata; the reverse
  fallback is not allowed.
- GPT-5.6 and earlier responses may report `priority` after a `fast` request.
  Pass the requested tier through extractor options or request telemetry when
  request intent must be retained; response-only data preserves the observed
  `priority` value.
- When callers omit an explicit `priced_at`, OpenAI Responses `created_at` is
  converted from Unix seconds and used for effective-date card selection.
- OpenAI Chat Completions uses the equivalent top-level `created` timestamp;
  OpenAI Agents SDK usage wrappers use `created_at` or `created` when either is
  present on the selected usage root.

## OpenAI Conversations Decision

Surface:

- `openai.conversations`

Source references:

- OpenAI's conversation state guide describes the Conversations API as a way to persist conversation state and pass a conversation into later Responses API calls: https://developers.openai.com/api/docs/guides/conversation-state
- OpenAI's Conversations reference describes conversation objects as state resources for storing and retrieving conversation state across Responses API calls: https://developers.openai.com/api/reference/resources/conversations/methods/create
- OpenAI's Responses reference documents the `conversation` parameter on Responses and the Response object `usage` field for token usage: https://developers.openai.com/api/reference/resources/responses/methods/create

Decision:

- Do not add an `openai.conversations` cost extractor in v0.x.
- Conversations are state containers and item stores, not standalone model inference responses with usage totals.
- Costs for work that uses a Conversation are associated with the Responses API calls that attach to or read from that Conversation.
- `openai.responses` remains the fixture-backed extraction surface for token usage, including Responses that include a `conversation` field.
- OpenAI Responses hosted tool outputs are fixture-backed for web search, file search, code interpreter calls, computer-use action counts, and function-call counts.
- If OpenAI later exposes standalone billable usage on Conversation operations, add a new fixture before promoting `openai.conversations` to fixture-backed support.

## xAI Responses

Surface:

- `xai.responses`

Source references:

- xAI text generation docs state that Responses is the preferred API for xAI models and show the OpenAI-compatible Responses path through `client.responses.create(...)` with `base_url` set to `https://api.x.ai/v1`: https://docs.x.ai/developers/model-capabilities/text/generate-text
- xAI prompt caching docs describe cached-token usage and pricing for Grok models: https://docs.x.ai/developers/advanced-api-usage/prompt-caching/usage-and-pricing

Mapping:

- Uses the same usage fields as OpenAI Responses for fixture-backed extraction.
- `surface: "xai.responses"` defaults the canonical provider to `xai` even when callers omit `provider`.
- Provider-specific tool, multimodal, and future Responses-only fields still need separate fixtures before being treated as supported.

## OpenAI Embeddings

Surface:

- `openai.embeddings`

Source references:

- OpenAI Embeddings API reference documents `CreateEmbeddingResponse` returning `usage.prompt_tokens` and `usage.total_tokens`: https://developers.openai.com/api/reference/resources/embeddings/methods/create

Mapping:

- `usage.prompt_tokens` -> `embedding_tokens`.
- `usage.total_tokens` is preserved in raw usage and used as a fallback only when `prompt_tokens` is absent.
- Embedding vectors are ignored for pricing.

## Anthropic Messages

Surface:

- `anthropic.messages`

Source references:

- Anthropic streaming docs state that `message_delta` usage token counts are cumulative and show `message_start`, `message_delta`, and `message_stop` event sequences: https://platform.claude.com/docs/en/build-with-claude/streaming
- Anthropic streaming docs also describe SDK helpers that accumulate a stream into the final Message object: https://platform.claude.com/docs/en/build-with-claude/streaming
- Anthropic's current refusals and fallback contract says `usage.iterations` is the per-attempt billing record, each billable attempt is priced at its own model's rates, pre-output refusals are not billed, and mid-stream refusals retain billed input plus partial output: https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback
- Anthropic's fallback-credit contract says the retry response's reported usage is authoritative: a redeemed credit appears in cache-creation/cache-read usage, while merely sending a token does not prove redemption. Message Batches neither mint nor redeem fallback credits: https://platform.claude.com/docs/en/build-with-claude/fallback-credit
- Anthropic Message Batches return refusals as `succeeded` result envelopes with `stop_reason: "refusal"`, use the batch price tier, and do not support server-side fallback: https://platform.claude.com/docs/en/build-with-claude/batch-processing

Mapping:

- Non-streaming responses read usage from the top-level `usage` object.
- Streaming event collections read initial model and usage from `message_start.message`, merge cumulative `message_delta.usage`, preserve `content_block_start` fallback blocks, and replace the initial model with the final serving model.
- `usage.input_tokens` -> `input_uncached_tokens`.
- `usage.cache_creation_input_tokens` minus 1-hour creation tokens -> `input_cache_write_tokens`.
- `usage.cache_creation_input_tokens_1h` -> `input_cache_write_1h_tokens`.
- `usage.cache_read_input_tokens` -> `input_cache_read_tokens`.
- `usage.output_tokens` -> `output_text_tokens`.
- When `usage.iterations` is present, RunCost prices every billable iteration instead of the aggregate top-level usage. Each component carries `metadata.billing_model` and the iteration index/type so arbitrary model chains are supported without a Fable/Opus allowlist.
- Any attempt with no output before a later fallback attempt is treated as a pre-output refusal and contributes no billable components. An attempt with partial output retains its reported input, cache, and output components at that attempt's model rates.
- `fallback_message` iterations and `fallback` content blocks populate `metadata.anthropic_fallback`, including requested, attempted, serving, and pricing model identifiers plus explicit hops when present. Sticky-served turns are detected from `usage.iterations` even without a content block.
- Any direct response with `stop_reason: "refusal"` and no output tokens produces zero billable components. Detection deliberately does not depend on `stop_details.category`, which may be new or null.
- The fallback-credit option aliases remain accepted as caller provenance, but never rewrite usage. `metadata.anthropic_fallback_credit.pricing_source` remains `reported_usage`; the response's cache fields decide pricing.
- Python accepts both raw dictionaries and Anthropic SDK/Pydantic response objects exposing `model_dump()` or `dict()`; JavaScript/TypeScript and Go accept the equivalent decoded response object.

## OpenAI-Compatible Chat

Surfaces:

- `openai.chat_completions`
- `openrouter.chat_completions`
- `groq.chat_completions`
- `xai.chat_completions`
- `meta.chat_completions`
- `mistral.chat_completions`
- `deepseek.chat_completions`
- `azure.openai.chat_completions`
- `huggingface.chat_completions`

Source references:

- OpenRouter chat completions response shows `usage.prompt_tokens`, `usage.completion_tokens`, and `usage.total_tokens`: https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request
- OpenAI prompt caching docs document `usage.prompt_tokens_details.cache_write_tokens` for GPT-5.6 and later Chat Completions: https://developers.openai.com/api/docs/guides/prompt-caching
- OpenRouter docs state that token counts in completions responses use the model's native tokenizer, and generation stats can be queried later for auditing: https://openrouter.ai/docs/api/reference/overview
- Groq prompt caching docs show OpenAI-compatible `usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens`, and `usage.prompt_tokens_details.cached_tokens`: https://console.groq.com/docs/prompt-caching
- xAI chat completion and prompt caching docs show `usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens`, `usage.prompt_tokens_details.cached_tokens`, and `usage.completion_tokens_details.reasoning_tokens`: https://docs.x.ai/developers/model-capabilities/legacy/chat-completions and https://docs.x.ai/developers/advanced-api-usage/prompt-caching/usage-and-pricing
- Mistral prompt caching docs show `usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens`, and `usage.prompt_tokens_details.cached_tokens`: https://docs.mistral.ai/studio-api/conversations/advanced/prompt-caching
- DeepSeek chat completion docs show `usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens`, `usage.prompt_cache_hit_tokens`, `usage.prompt_cache_miss_tokens`, and `usage.completion_tokens_details.reasoning_tokens`: https://api-docs.deepseek.com/api/create-chat-completion/
- Azure OpenAI REST reference documents `completionUsage` with `prompt_tokens`, `completion_tokens`, `total_tokens`, and optional `completion_tokens_details.reasoning_tokens`: https://learn.microsoft.com/en-us/azure/foundry/openai/reference
- Hugging Face Inference Providers chat completion docs state the API is OpenAI SDK compatible and response usage includes `prompt_tokens`, `completion_tokens`, and `total_tokens`: https://huggingface.co/docs/inference-providers/tasks/chat-completion
- Meta Model API SDK docs are currently login-gated at https://dev.meta.ai/docs/getting-started/sdks in this Codex environment. A credentialed sanitized smoke against `https://api.meta.ai/v1` confirmed `/models`, `/chat/completions`, `/responses`, cached-token usage details, and reasoning-token usage details.

Mapping:

- `usage.prompt_tokens` -> `input_uncached_tokens`, less supported cache-read and cache-write prompt fields.
- `usage.prompt_tokens_details.cached_tokens` -> `input_cache_read_tokens`.
- `usage.prompt_tokens_details.cache_write_tokens` -> `input_cache_write_tokens` when present.
- `usage.prompt_cache_hit_tokens` -> `input_cache_read_tokens` for DeepSeek-compatible responses.
- `usage.prompt_cache_miss_tokens` is preserved in raw usage and can reconstruct prompt tokens when `usage.prompt_tokens` is absent.
- `usage.completion_tokens` -> `output_text_tokens`, less any supported reasoning field.
- `usage.completion_tokens_details.reasoning_tokens` -> `output_reasoning_tokens`.
- `usage.output_tokens_details.reasoning_tokens` is accepted as a compatibility fallback for SDKs that expose chat reasoning under the newer output details name.
- `usage.total_tokens` is preserved in raw usage but is never priced directly.
- For DeepSeek chat completions, top-level `created` is promoted to
  `context.priced_at` so reviewed UTC pricing-period schedules can select peak
  or regular price cards. Caller-supplied context still takes precedence for
  backfills and invoice reconciliation.

Notes:

- Provider-specific tool, multimodal, and compound-routing fields remain future fixtures even when the base response shape is OpenAI compatible.
- The shared generic helper is exposed as `extract_openai_compatible_chat_completions_usage` in Python and `extractOpenAICompatibleChatCompletionsUsage` in JavaScript/TypeScript.

## Meta Model API

Surfaces:

- `meta.responses`
- `meta.chat_completions`

Source references:

- Meta Model API SDK docs entrypoint: https://dev.meta.ai/docs/getting-started/sdks
- Meta Model API public developer blog: https://developer.meta.com/ai/resources/blog/build-with-muse-spark/
- Sanitized live smoke evidence: `fixtures/source-files/meta-model-api-live-smoke-2026-07-09.json`
- The Verge public-preview coverage: https://www.theverge.com/news/780540/meta-api-ai-vibes-video-code-tools
- Axios public-preview pricing coverage: https://www.axios.com/2026/07/09/meta-superintelligence-labs-ai-api-muse-spark
- Reuters/WTVB public-preview pricing coverage: https://whtc.com/2026/07/09/meta-debuts-muse-spark-1-1-api-after-superintelligence-reorg/

Mapping:

- `meta.responses` reuses the Responses-style usage mapping:
  `usage.input_tokens`, `usage.input_tokens_details.cached_tokens`,
  `usage.output_tokens`, and `usage.output_tokens_details.reasoning_tokens`.
- `meta.chat_completions` reuses the OpenAI-compatible chat mapping for
  `usage.prompt_tokens`, `usage.prompt_tokens_details.cached_tokens`,
  `usage.completion_tokens`, and
  `usage.completion_tokens_details.reasoning_tokens`.
- Function-call items in a Responses-style `output` array are counted as
  `tool_call_units`; without verified Meta tool prices, those units produce a
  structured `tool_component_unpriced` warning.
- `usage.total_tokens` is preserved in raw usage but is never priced directly.

Notes:

- Credentialed live smoke passed for `/models`, `/chat/completions`, and
  `/responses` on `https://api.meta.ai/v1`; the sanitized evidence file omits
  prompts, response content, headers, account identifiers, raw responses, and
  secret values.
- A reviewed public-preview snapshot is retained for explicit opt-in estimates,
  but it is not bundled in the default catalog because the exact rates could not
  be verified from a primary Meta pricing source. Its cache-read and reasoning
  assumptions remain clearly marked as non-authoritative preview behavior.

## Cohere Chat

Surface:

- `cohere.chat`

Source references:

- Cohere v2 Chat API reference shows top-level `usage.billed_units.input_tokens`, `usage.billed_units.output_tokens`, and raw `usage.tokens`: https://docs.cohere.com/reference/chat
- Cohere Chat API guide shows the same billed/raw token split under `meta.billed_units` and `meta.tokens`: https://docs.cohere.com/docs/chat-api
- Cohere pricing docs clarify that billed tokens, not generic token counts, are the tokens actually charged for: https://docs.cohere.com/docs/how-does-cohere-pricing-work

Mapping:

- `usage.billed_units.input_tokens` -> `input_uncached_tokens`.
- `usage.billed_units.output_tokens` -> `output_text_tokens`.
- `meta.billed_units.input_tokens` -> `input_uncached_tokens` for guide-style and SDK responses that put billing metadata under `meta`.
- `meta.billed_units.output_tokens` -> `output_text_tokens` for guide-style and SDK responses that put billing metadata under `meta`.
- `usage.tokens` and `meta.tokens` are preserved in raw usage but are not priced directly.

Notes:

- Cohere can report raw token counts that differ from billed token counts. The extractor intentionally prices billed units.

## Cohere Rerank

Surface:

- `cohere.rerank`

Source reference:

- Cohere Rerank overview documents the response `meta.billed_units.search_units` field for v2 Rerank responses: https://docs.cohere.com/v2/docs/rerank-overview

Mapping:

- `meta.billed_units.search_units` -> `rerank_search_units`.

Notes:

- Rerank result counts, relevance scores, and returned documents are preserved in raw usage but are not priced directly.
- The extractor prices Cohere's billed search units and leaves broader provider-specific rerank/search surfaces for beta hardening.

## Google Gemini Generate Content

Surfaces:

- `google.gemini.generate_content`
- `vertex.gemini.generate_content`

Source reference:

- Firebase AI Logic `GenerateContentResponse.UsageMetadata` documents `thoughtsTokenCount`, `totalTokenCount`, `promptTokensDetails`, cache token details, candidate token details, and tool prompt token details: https://firebase.google.com/docs/reference/swift/firebaseailogic/api/reference/Structs/GenerateContentResponse/UsageMetadata
- Vertex AI REST `GenerateContentResponse` documents `usageMetadata` and `totalTokenCount`, where total is the sum of prompt, candidate, tool-use prompt, and thoughts token counts: https://cloud.google.com/vertex-ai/generative-ai/docs/reference/rest/v1/GenerateContentResponse
- Gemini API text-generation docs state that `generate_content_stream` / `generateContentStream` returns `GenerateContentResponse` chunks incrementally: https://ai.google.dev/gemini-api/docs/text-generation
- Gemini API Priority docs identify `x-gemini-service-tier` as the response header for the actual served tier when Priority requests downgrade to Standard: https://ai.google.dev/gemini-api/docs/priority-inference

Mapping:

- Non-streaming responses read usage from top-level `usageMetadata`.
- Streaming chunk collections read usage from the last chunk with `usageMetadata`.
- Aggregate fallback: `usageMetadata.promptTokenCount` minus `usageMetadata.cachedContentTokenCount`, plus `usageMetadata.toolUsePromptTokenCount` when present, -> `input_uncached_tokens`.
- Aggregate fallback: `usageMetadata.cachedContentTokenCount` -> `input_cache_read_tokens`.
- Aggregate fallback: `usageMetadata.candidatesTokenCount` -> `output_text_tokens`.
- `usageMetadata.thoughtsTokenCount` -> `output_reasoning_tokens`.
- `usageMetadata.promptTokensDetails` -> modality-aware input components:
  - `TEXT`, `DOCUMENT`, and `MODALITY_UNSPECIFIED` -> `input_uncached_tokens`.
  - `IMAGE` -> `input_image_tokens`.
  - `AUDIO` -> `input_audio_tokens`.
  - `VIDEO` -> `input_video_tokens`.
- `usageMetadata.cacheTokensDetails` subtracts matching modality counts from uncached/media input components and `usageMetadata.cachedContentTokenCount` still emits the aggregate `input_cache_read_tokens`.
- `usageMetadata.toolUsePromptTokensDetails` adds tool-use prompt tokens to the matching input modality component. If details are missing but `toolUsePromptTokenCount` exists, the extractor adds the aggregate to `input_uncached_tokens`.
- `usageMetadata.candidatesTokensDetails` -> modality-aware output components:
  - `TEXT`, `DOCUMENT`, and `MODALITY_UNSPECIFIED` -> `output_text_tokens`.
  - `IMAGE` -> `output_image_tokens`.
  - `AUDIO` -> `output_audio_tokens`.
  - `VIDEO` -> `output_video_tokens`.
- `x-gemini-service-tier` is preferred over `usageMetadata.serviceTier` when present because Priority requests can be billed at the downgraded response tier.
- `usageMetadata.totalTokenCount` is preserved in raw usage but is never priced directly.

Notes:

- Modality-aware input splitting only runs when prompt details are present and cache details are available for cached responses. This avoids double-counting cached media tokens when a response has an aggregate cache count but no per-modality cache detail.

## Google Gemini Live API

Surface:

- `google.gemini.live`

Source references:

- Gemini Live API server messages include top-level `usageMetadata` on `BidiGenerateContentServerMessage`: https://ai.google.dev/api/live
- Gemini Live API `UsageMetadata` documents `promptTokenCount`, `responseTokenCount`, `totalTokenCount`, `promptTokensDetails`, `cacheTokensDetails`, `responseTokensDetails`, and related tool/thought token fields: https://ai.google.dev/api/live
- Gemini 3.5 Live Translate model docs list `gemini-3.5-live-translate-preview` with audio input and audio/text output through the Live API: https://ai.google.dev/gemini-api/docs/models/gemini-3.5-live-translate-preview

Mapping:

- Non-streaming/final server-message responses read usage from top-level `usageMetadata`.
- Streaming or collected server-message responses read usage from the last `chunks` or `stream` item with `usageMetadata`.
- Aggregate fallback: `usageMetadata.promptTokenCount` minus `usageMetadata.cachedContentTokenCount`, plus `usageMetadata.toolUsePromptTokenCount` when present, -> `input_uncached_tokens`.
- Aggregate fallback: `usageMetadata.cachedContentTokenCount` -> `input_cache_read_tokens`.
- `usageMetadata.promptTokensDetails` -> modality-aware input components using the same Gemini modality map as generateContent. `AUDIO` maps to `input_audio_tokens`.
- `usageMetadata.cacheTokensDetails` subtracts matching modality counts from uncached/media input components when cache details are available.
- `usageMetadata.toolUsePromptTokensDetails` adds tool-use prompt tokens to the matching input modality component. If details are missing but `toolUsePromptTokenCount` exists, the extractor adds the aggregate to `input_uncached_tokens`.
- `usageMetadata.responseTokensDetails` -> modality-aware output components. `AUDIO` maps to `output_audio_tokens`; `TEXT`, `DOCUMENT`, and `MODALITY_UNSPECIFIED` map to `output_text_tokens`.
- Aggregate fallback: for `gemini-3.5-live-translate-preview`, `usageMetadata.promptTokenCount` -> `input_audio_tokens` and `usageMetadata.responseTokenCount` -> `output_audio_tokens` when modality details are absent. Other Live models fall back to text until they have fixture-backed modality rules.
- `usageMetadata.thoughtsTokenCount` -> `output_reasoning_tokens`; when the price card has no direct reasoning price, Gemini thinking tokens price at the applicable output-token rate. For Live Translate, that means `output_audio_tokens`.
- `usageMetadata.totalTokenCount` is preserved in raw usage but is never priced directly.

Pricing notes:

- `gemini-3.5-live-translate-preview` is bundled through the reviewed `google-official` default source with `input_audio_tokens` and `output_audio_tokens` prices from the Gemini pricing page.
- The model can return transcript text alongside translated audio. The reviewed `google-official` card marks `output_text_tokens` unsupported because the pricing page publishes audio-token rates for this model, not a separate transcript text-token rate.
- The Google pricing page states Live Translate billing is based on audio token consumption at 25 tokens per second. RunCost prices the provider-reported token counts; it does not infer token counts from minutes.

## Google Gemini Interactions

Surface:

- `google.gemini.interactions`

Source references:

- js-genai v2.9.0 adds `UsageMetadata.serviceTier`: https://github.com/googleapis/js-genai/releases/tag/v2.9.0
- js-genai v2.9.0 renames Interactions stream metadata usage from `usage` to `total_usage`: https://github.com/googleapis/js-genai/releases/tag/v2.9.0
- The v2.9.0 `ServiceTier` enum uses lower-case string values: `unspecified`, `flex`, `standard`, and `priority`: https://github.com/googleapis/js-genai/commit/1f44b04
- Gemini API Priority docs identify `x-gemini-service-tier` as the response header for the actual served tier when Priority requests downgrade to Standard: https://ai.google.dev/gemini-api/docs/priority-inference

Mapping:

- Non-streaming or event-shaped responses read usage from `metadata.total_usage`, `metadata.totalUsage`, or legacy `metadata.usage`.
- Streaming or collected event responses read usage from the last `chunks`, `stream`, or `events` item carrying usage metadata.
- Aggregate fallback: `total_input_tokens` minus `total_cached_tokens`, plus `total_tool_use_tokens` when present, -> `input_uncached_tokens`.
- Aggregate fallback: `total_cached_tokens` -> `input_cache_read_tokens`.
- `input_tokens_by_modality` -> modality-aware input components using lower-case Interactions modality values mapped through the shared Gemini modality table.
- `cached_tokens_by_modality` subtracts matching modality counts from uncached/media input components when cache details are available.
- `tool_use_tokens_by_modality` adds tool-use tokens to the matching input modality component. If details are missing but `total_tool_use_tokens` exists, the extractor adds the aggregate to `input_uncached_tokens`.
- `output_tokens_by_modality` -> modality-aware output components. `text` and `document` map to `output_text_tokens`; `image`, `audio`, and `video` map to their matching media output components.
- `total_thought_tokens` -> `output_reasoning_tokens`.
- `grounding_tool_count` maps `google_search` to `web_search_units`; `google_maps` and `retrieval` map conservatively to `tool_call_units` until those provider-specific price surfaces have stronger public price-card coverage.
- `x-gemini-service-tier` is preferred over `service_tier` / `serviceTier`; body values are normalized like other Gemini service tiers, including SDK string forms such as `ServiceTier.PRIORITY`.
- `total_tokens` is preserved in raw usage but is never priced directly.

## AWS Bedrock Converse

Surface:

- `aws.bedrock.converse`

Source references:

- AWS Bedrock user guide notes that the Converse API returns token information in the response `usage` field: https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
- Boto3 Converse response shape documents `usage.inputTokens`, `usage.outputTokens`, `usage.totalTokens`, `usage.cacheReadInputTokens`, `usage.cacheWriteInputTokens`, and `usage.cacheDetails`: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime/client/converse.html

Mapping:

- `usage.inputTokens` minus cache read and cache write tokens -> `input_uncached_tokens`.
- `usage.cacheReadInputTokens` -> `input_cache_read_tokens`.
- `usage.cacheWriteInputTokens` minus 1-hour cache details -> `input_cache_write_tokens`.
- `usage.cacheDetails[]` entries with `ttl == "1h"` -> `input_cache_write_1h_tokens`.
- `usage.outputTokens` -> `output_text_tokens`.
- `usage.totalTokens` is preserved in raw usage but is never priced directly.

Notes:

- Bedrock model-specific reasoning, guardrail, tool, and multimodal fields should get separate fixtures before being treated as supported.

## AWS Bedrock InvokeModel

Surface:

- `aws.bedrock.invoke_model`

Source references:

- Boto3 `invoke_model` documents that the operation invokes a Bedrock model for inference, requires a `modelId`, and returns an inference `body`: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime/client/invoke_model.html
- AWS Bedrock Anthropic Claude Messages request/response docs show the `InvokeModel` body shape and response `usage.input_tokens` / `usage.output_tokens` fields: https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages-request-response.html

Mapping:

- `response.modelId` -> returned and billed model when present.
- `body.usage.input_tokens` -> `input_uncached_tokens`.
- `body.usage.cache_creation_input_tokens` minus `cache_creation_input_tokens_1h` -> `input_cache_write_tokens` when present.
- `body.usage.cache_creation_input_tokens_1h` -> `input_cache_write_1h_tokens` when present.
- `body.usage.cache_read_input_tokens` -> `input_cache_read_tokens` when present.
- `body.usage.output_tokens` -> `output_text_tokens`.
- Any aggregate or provider-specific total field is preserved in raw usage but is never priced directly.

Notes:

- Current fixture coverage targets Anthropic Messages-compatible bodies inside `InvokeModel`. Other Bedrock native body formats, image generation, embeddings, streaming chunks, and guardrail/tool fields need separate fixtures before being treated as supported.
