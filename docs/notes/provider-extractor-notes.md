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

Mapping:

- Non-streaming responses read usage from the top-level `usage` object.
- Streaming final events with `type == "response.completed"` read usage from `response.usage`.
- `usage.input_tokens` minus cached tokens -> `input_uncached_tokens`.
- `usage.input_tokens_details.cached_tokens` -> `input_cache_read_tokens`.
- `usage.output_tokens` minus reasoning tokens -> `output_text_tokens`.
- `usage.output_tokens_details.reasoning_tokens` -> `output_reasoning_tokens`.

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

Mapping:

- Non-streaming responses read usage from the top-level `usage` object.
- Streaming event collections read initial model and usage from `message_start.message`, then merge cumulative `message_delta.usage`.
- `usage.input_tokens` -> `input_uncached_tokens`.
- `usage.cache_creation_input_tokens` minus 1-hour creation tokens -> `input_cache_write_tokens`.
- `usage.cache_creation_input_tokens_1h` -> `input_cache_write_1h_tokens`.
- `usage.cache_read_input_tokens` -> `input_cache_read_tokens`.
- `usage.output_tokens` -> `output_text_tokens`.

## OpenAI-Compatible Chat

Surfaces:

- `openai.chat_completions`
- `openrouter.chat_completions`
- `groq.chat_completions`
- `xai.chat_completions`
- `mistral.chat_completions`
- `deepseek.chat_completions`
- `azure.openai.chat_completions`
- `huggingface.chat_completions`

Source references:

- OpenRouter chat completions response shows `usage.prompt_tokens`, `usage.completion_tokens`, and `usage.total_tokens`: https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request
- OpenRouter docs state that token counts in completions responses use the model's native tokenizer, and generation stats can be queried later for auditing: https://openrouter.ai/docs/api/reference/overview
- Groq prompt caching docs show OpenAI-compatible `usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens`, and `usage.prompt_tokens_details.cached_tokens`: https://console.groq.com/docs/prompt-caching
- xAI chat completion and prompt caching docs show `usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens`, `usage.prompt_tokens_details.cached_tokens`, and `usage.completion_tokens_details.reasoning_tokens`: https://docs.x.ai/developers/model-capabilities/legacy/chat-completions and https://docs.x.ai/developers/advanced-api-usage/prompt-caching/usage-and-pricing
- Mistral prompt caching docs show `usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens`, and `usage.prompt_tokens_details.cached_tokens`: https://docs.mistral.ai/studio-api/conversations/advanced/prompt-caching
- DeepSeek chat completion docs show `usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens`, `usage.prompt_cache_hit_tokens`, `usage.prompt_cache_miss_tokens`, and `usage.completion_tokens_details.reasoning_tokens`: https://api-docs.deepseek.com/api/create-chat-completion/
- Azure OpenAI REST reference documents `completionUsage` with `prompt_tokens`, `completion_tokens`, `total_tokens`, and optional `completion_tokens_details.reasoning_tokens`: https://learn.microsoft.com/en-us/azure/foundry/openai/reference
- Hugging Face Inference Providers chat completion docs state the API is OpenAI SDK compatible and response usage includes `prompt_tokens`, `completion_tokens`, and `total_tokens`: https://huggingface.co/docs/inference-providers/tasks/chat-completion

Mapping:

- `usage.prompt_tokens` -> `input_uncached_tokens`, less any supported cached prompt field.
- `usage.prompt_tokens_details.cached_tokens` -> `input_cache_read_tokens`.
- `usage.prompt_cache_hit_tokens` -> `input_cache_read_tokens` for DeepSeek-compatible responses.
- `usage.prompt_cache_miss_tokens` is preserved in raw usage and can reconstruct prompt tokens when `usage.prompt_tokens` is absent.
- `usage.completion_tokens` -> `output_text_tokens`, less any supported reasoning field.
- `usage.completion_tokens_details.reasoning_tokens` -> `output_reasoning_tokens`.
- `usage.output_tokens_details.reasoning_tokens` is accepted as a compatibility fallback for SDKs that expose chat reasoning under the newer output details name.
- `usage.total_tokens` is preserved in raw usage but is never priced directly.

Notes:

- Provider-specific tool, multimodal, and compound-routing fields remain future fixtures even when the base response shape is OpenAI compatible.
- The shared generic helper is exposed as `extract_openai_compatible_chat_completions_usage` in Python and `extractOpenAICompatibleChatCompletionsUsage` in JavaScript/TypeScript.

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

## Google Gemini Generate Content

Surfaces:

- `google.gemini.generate_content`
- `vertex.gemini.generate_content`

Source reference:

- Firebase AI Logic `GenerateContentResponse.UsageMetadata` documents `thoughtsTokenCount`, `totalTokenCount`, `promptTokensDetails`, cache token details, candidate token details, and tool prompt token details: https://firebase.google.com/docs/reference/swift/firebaseailogic/api/reference/Structs/GenerateContentResponse/UsageMetadata
- Vertex AI REST `GenerateContentResponse` documents `usageMetadata` and `totalTokenCount`, where total is the sum of prompt, candidate, tool-use prompt, and thoughts token counts: https://cloud.google.com/vertex-ai/generative-ai/docs/reference/rest/v1/GenerateContentResponse
- Gemini API text-generation docs state that `generate_content_stream` / `generateContentStream` returns `GenerateContentResponse` chunks incrementally: https://ai.google.dev/gemini-api/docs/text-generation

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
- `usageMetadata.totalTokenCount` is preserved in raw usage but is never priced directly.

Notes:

- Modality-aware input splitting only runs when prompt details are present and cache details are available for cached responses. This avoids double-counting cached media tokens when a response has an aggregate cache count but no per-modality cache detail.

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
