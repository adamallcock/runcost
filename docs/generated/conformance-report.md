---
title: RunCost Conformance Report
date: 2026-07-18
type: report
status: generated
---

# RunCost Conformance Report

This report describes RunCost's own fixture-backed behavior. It does not score or infer the behavior of competitors.

## Outcome definitions

- **Preserved:** The expected billing semantics are asserted without warning.
- **Warned:** The implementation preserves a visible caveat or expected error.
- **Unsupported:** The implementation explicitly reports that a billing semantic is not priced or supported.
- **Not Tested:** The case does not request that language implementation.

## Summary

217 cases are inventoried.

| Outcome | Cases |
| --- | ---: |
| Preserved | 162 |
| Warned | 48 |
| Unsupported | 7 |
| Not Tested | 0 |

## Cases

| Case | Provider | Surface or operation | Outcome | Languages |
| --- | --- | --- | --- | --- |
| `ag2-usage-summary-actual` | openai | `openai.chat_completions` | warned | python: warned, javascript: warned, go: warned |
| `ag2-usage-summary-total` | openai | `openai.chat_completions` | warned | python: warned, javascript: warned, go: warned |
| `anthropic-messages-client-fallback-credit-non-opus-ignored` | anthropic | `anthropic.messages` | preserved | python: preserved, javascript: preserved, go: preserved |
| `anthropic-messages-fable-client-fallback-credit-token` | anthropic | `anthropic.messages` | preserved | python: preserved, javascript: preserved, go: preserved |
| `anthropic-messages-fable-client-fallback-credit` | anthropic | `anthropic.messages` | preserved | python: preserved, javascript: preserved, go: preserved |
| `anthropic-messages-fable-direct-classifier-block` | anthropic | `anthropic.messages` | preserved | python: preserved, javascript: preserved, go: preserved |
| `anthropic-messages-fable-server-fallback-midstream` | anthropic | `anthropic.messages` | preserved | python: preserved, javascript: preserved, go: preserved |
| `anthropic-messages-fable-server-fallback-unavailable` | anthropic | `anthropic.messages` | preserved | python: preserved, javascript: preserved, go: preserved |
| `anthropic-messages-fable-server-fallback` | anthropic | `anthropic.messages` | preserved | python: preserved, javascript: preserved, go: preserved |
| `anthropic-messages-fable-sticky-fallback-inferred` | anthropic | `anthropic.messages` | preserved | python: preserved, javascript: preserved, go: preserved |
| `anthropic-messages-fable-sticky-fallback-served` | anthropic | `anthropic.messages` | preserved | python: preserved, javascript: preserved, go: preserved |
| `anthropic-messages-generic-fallback-chain` | anthropic | `anthropic.messages` | preserved | python: preserved, javascript: preserved, go: preserved |
| `anthropic-messages-missing-usage-warning` | anthropic | `anthropic.messages` | warned | python: warned, javascript: warned, go: warned |
| `anthropic-messages-raw-cache-1h` | anthropic | `anthropic.messages` | preserved | python: preserved, javascript: preserved, go: preserved |
| `anthropic-messages-raw-cache` | anthropic | `anthropic.messages` | preserved | python: preserved, javascript: preserved, go: preserved |
| `anthropic-messages-stream-events` | anthropic | `anthropic.messages` | preserved | python: preserved, javascript: preserved, go: preserved |
| `anthropic-messages-stream-fallback-events` | anthropic | `anthropic.messages` | preserved | python: preserved, javascript: preserved, go: preserved |
| `azure-openai-chat-raw-reasoning` | azure | `azure.openai.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `bedrock-converse-raw-cache` | bedrock | `aws.bedrock.converse` | preserved | python: preserved, javascript: preserved, go: preserved |
| `bedrock-invoke-model-anthropic-messages` | bedrock | `aws.bedrock.invoke_model` | preserved | python: preserved, javascript: preserved, go: preserved |
| `byte-stable-component-ordering` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `byte-stable-price-card-tie-break` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `cohere-chat-raw-meta-billed-units` | cohere | `cohere.chat` | preserved | python: preserved, javascript: preserved, go: preserved |
| `cohere-chat-raw-usage-billed-units` | cohere | `cohere.chat` | preserved | python: preserved, javascript: preserved, go: preserved |
| `cohere-rerank-raw-billed-units` | cohere | `cohere.rerank` | preserved | python: preserved, javascript: preserved, go: preserved |
| `component-metadata-billing-model-passive` | anthropic | `anthropic.messages` | preserved | python: preserved, javascript: preserved, go: preserved |
| `cost-ledger-aggregation-basic` | aggregate | `aggregate.cost_ledgers` | preserved | python: preserved, javascript: preserved, go: preserved |
| `date-only-priced-at-effective-date-selection` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `debug-trace-explain-decisions` | openai | `openai.responses` | warned | python: warned, javascript: warned, go: warned |
| `decimal-arithmetic-adversarial` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `deepseek-chat-created-out-of-range-ignored` | deepseek | `deepseek.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `deepseek-chat-created-priced-at` | deepseek | `deepseek.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `deepseek-chat-raw-cache-reasoning` | deepseek | `deepseek.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `deepseek-official-snapshot-period-adapter` | deepseek | `deepseek.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `deepseek-peak-pricing-boundary-before-second-window` | deepseek | `deepseek.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `deepseek-peak-pricing-boundary-first-start` | deepseek | `deepseek.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `deepseek-peak-pricing-boundary-regular` | deepseek | `deepseek.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `deepseek-peak-pricing-boundary-second-end` | deepseek | `deepseek.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `deepseek-peak-pricing-boundary-second-start` | deepseek | `deepseek.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `deepseek-peak-pricing-debug-trace-period` | deepseek | `deepseek.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `deepseek-peak-pricing-explicit-period` | deepseek | `deepseek.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `deepseek-peak-pricing-first-window` | deepseek | `deepseek.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `deepseek-peak-pricing-missing-time-warning` | deepseek | `deepseek.chat_completions` | warned | python: warned, javascript: warned, go: warned |
| `deepseek-peak-pricing-regular-window` | deepseek | `deepseek.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `deepseek-peak-pricing-second-window` | deepseek | `deepseek.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `deepseek-peak-pricing-unsupported-period-warning` | deepseek | `deepseek.chat_completions` | warned | python: warned, javascript: warned, go: warned |
| `deepseek-peak-pricing-unsupported-timezone-warning` | deepseek | `deepseek.chat_completions` | warned | python: warned, javascript: warned, go: warned |
| `deepseek-user-pricing-camelcase-period-adapter` | deepseek | `deepseek.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `discount-not-applied-warning` | openai | `openai.responses` | warned | python: warned, javascript: warned, go: warned |
| `discount-policy-openai-basic` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `effective-date-selection` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `feature-component-unpriced-warning` | multi | `normalized.feature_pricing` | unsupported | python: unsupported, javascript: unsupported, go: unsupported |
| `feature-pricing-generated-media-rerank-transcription` | multi | `normalized.feature_pricing` | preserved | python: preserved, javascript: preserved, go: preserved |
| `gemini-3-1-flash-lite-raw-separate-thinking-output-pricing` | google | `google.gemini.generate_content` | preserved | python: preserved, javascript: preserved, go: preserved |
| `gemini-3-1-flash-lite-reasoning-output-pricing` | google | `google.gemini.generate_content` | warned | python: warned, javascript: warned, go: warned |
| `gemini-3-5-flash-raw-separate-thinking-output-pricing` | google | `google.gemini.generate_content` | preserved | python: preserved, javascript: preserved, go: preserved |
| `gemini-3-5-flash-reasoning-output-pricing` | google | `google.gemini.generate_content` | warned | python: warned, javascript: warned, go: warned |
| `gemini-generate-content-raw-multimodal` | google | `google.gemini.generate_content` | preserved | python: preserved, javascript: preserved, go: preserved |
| `gemini-generate-content-raw-reasoning-cache` | google | `google.gemini.generate_content` | preserved | python: preserved, javascript: preserved, go: preserved |
| `gemini-generate-content-service-tier-enum-name` | google | `google.gemini.generate_content` | preserved | python: preserved, javascript: preserved, go: preserved |
| `gemini-generate-content-service-tier-header-downgrade` | google | `google.gemini.generate_content` | preserved | python: preserved, javascript: preserved, go: preserved |
| `gemini-generate-content-service-tier-usage-metadata` | google | `google.gemini.generate_content` | preserved | python: preserved, javascript: preserved, go: preserved |
| `gemini-generate-content-stream-chunks` | google | `google.gemini.generate_content` | preserved | python: preserved, javascript: preserved, go: preserved |
| `gemini-live-translate-aggregate-audio-thinking` | google | `google.gemini.live` | preserved | python: preserved, javascript: preserved, go: preserved |
| `gemini-live-translate-audio-plus-text-output` | google | `google.gemini.live` | unsupported | python: unsupported, javascript: unsupported, go: unsupported |
| `gemini-live-translate-audio-thinking-preferred` | google | `google.gemini.live` | preserved | python: preserved, javascript: preserved, go: preserved |
| `gemini-live-translate-raw-audio-usage` | google | `google.gemini.live` | preserved | python: preserved, javascript: preserved, go: preserved |
| `gemini-live-translate-stream-final-usage` | google | `google.gemini.live` | preserved | python: preserved, javascript: preserved, go: preserved |
| `google-interactions-legacy-usage-metadata` | google | `google.gemini.interactions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `google-interactions-service-tier-header-downgrade` | google | `google.gemini.interactions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `google-interactions-total-usage-camelcase-event` | google | `google.gemini.interactions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `google-interactions-total-usage-metadata` | google | `google.gemini.interactions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `google-official-pricing-live-translate` | google | `google.gemini.live` | preserved | python: preserved, javascript: preserved, go: preserved |
| `groq-chat-raw-cache` | groq | `groq.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `haystack-openai-chat-generator-meta` | openai | `openai.chat_completions` | warned | python: warned, javascript: warned, go: warned |
| `helicone-adapter-basic` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `historical-price-missing-warning` | openai | `openai.responses` | warned | python: warned, javascript: warned, go: warned |
| `huggingface-chat-raw-basic` | huggingface | `huggingface.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `inclusive-usage-ambiguous-warning` | openai | `openai.responses` | warned | python: warned, javascript: warned, go: warned |
| `langchain-callback-context-manager` | openai | `openai.chat_completions` | warned | python: warned, javascript: not_tested, go: not_tested |
| `langchain-chat-message-usage-metadata` | openai | `openai.chat_completions` | warned | python: warned, javascript: warned, go: warned |
| `langsmith-export-cost-compare` | openai | `openai.chat_completions` | warned | python: warned, javascript: warned, go: warned |
| `langsmith-run-usage-metadata` | openai | `openai.chat_completions` | warned | python: warned, javascript: warned, go: warned |
| `litellm-adapter-basic` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `litellm-proxy-response-cost-metadata` | openai | `openai.chat_completions` | warned | python: warned, javascript: warned, go: warned |
| `llamaindex-token-counter-events` | openai | `openai.chat_completions` | warned | python: warned, javascript: warned, go: warned |
| `llm-prices-adapter-basic` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `llm-prices-adapter-historical` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `long-context-rule-missing` | openai | `openai.responses` | warned | python: warned, javascript: warned, go: warned |
| `long-context-threshold-selection` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `meta-chat-null-usage` | meta | `meta.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `meta-chat-raw-cached-reasoning` | meta | `meta.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `meta-responses-null-usage` | meta | `meta.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `meta-responses-raw-tools-warning` | meta | `meta.responses` | unsupported | python: unsupported, javascript: unsupported, go: unsupported |
| `meta-reviewed-preview-snapshot-adapter` | meta | `meta.responses` | warned | python: warned, javascript: warned, go: warned |
| `mistral-chat-raw-cache` | mistral | `mistral.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `models-dev-adapter-basic` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `official-snapshot-adapter-basic` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-agents-sdk-usage` | openai | `openai.responses` | warned | python: warned, javascript: warned, go: warned |
| `openai-audio-transcription-duration-usage` | openai | `openai.audio_transcriptions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-audio-transcription-token-usage` | openai | `openai.audio_transcriptions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-chat-fast-exact-card` | openai | `openai.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-chat-gpt-56-terra-created-historical-price` | openai | `openai.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-chat-raw-cached-reasoning` | openai | `openai.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-chat-stream-final-usage-chunk` | openai | `openai.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-embeddings-raw-basic` | openai | `openai.embeddings` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-fast-prefers-exact-card` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-gpt-56-luna-price-before-july-30` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-gpt-56-luna-price-from-july-30` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-gpt-56-terra-price-before-july-30` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-gpt-56-terra-price-from-july-30` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-images-token-usage` | openai | `openai.images` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-images-unit-usage` | openai | `openai.images` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-priority-does-not-fallback-to-fast` | openai | `openai.responses` | warned | python: warned, javascript: warned, go: warned |
| `openai-responses-basic` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-responses-gpt-56-luna-fast-tier` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-responses-raw-cached-reasoning` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-responses-raw-computer-and-function-tools` | openai | `openai.responses` | warned | python: warned, javascript: warned, go: warned |
| `openai-responses-raw-dated-alias` | openai | `openai.responses` | warned | python: warned, javascript: warned, go: warned |
| `openai-responses-raw-orchestration-usage` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-responses-raw-tool-calls` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-responses-stream-completed-event` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-usage-audio-speeches-buckets` | openai | `openai.usage.audio_speeches` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-usage-audio-transcriptions-buckets` | openai | `openai.usage.audio_transcriptions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-usage-code-interpreter-sessions` | openai | `openai.usage.code_interpreter_sessions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-usage-completions-buckets` | openai | `openai.usage.completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-usage-embeddings-buckets` | openai | `openai.usage.embeddings` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-usage-images-buckets` | openai | `openai.usage.images` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-vector-store-storage-gb-days` | openai | `openai.vector_stores` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openrouter-agent-sdk-response` | openrouter | `openrouter.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openrouter-chat-raw-basic` | openrouter | `openrouter.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openrouter-models-adapter-basic` | openrouter | `openrouter.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openrouter-models-adapter-tiered` | openrouter | `openrouter.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openrouter-openai-sdk-response` | openrouter | `openrouter.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openrouter-sdk-stream-provider-cost` | openrouter | `openrouter.chat_completions` | warned | python: warned, javascript: warned, go: warned |
| `portkey-adapter-basic` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `price-not-found-context-mismatch` | openai | `openai.responses` | warned | python: warned, javascript: warned, go: warned |
| `price-source-deepseek-period-preferred-over-generic-priority` | deepseek | `deepseek.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `price-source-disagreement-warning` | openai | `openai.responses` | warned | python: warned, javascript: warned, go: warned |
| `price-source-priority-non-official-conditional-fallback` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `price-source-priority-official-conditional-gap` | openai | `openai.responses` | warned | python: warned, javascript: warned, go: warned |
| `price-source-priority-user-override` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `provider-reported-cost-mismatch` | openrouter | `openrouter.chat_completions` | warned | python: warned, javascript: warned, go: warned |
| `provider-reported-cost-used` | openrouter | `openrouter.chat_completions` | warned | python: warned, javascript: warned, go: warned |
| `reasoning-output-default-pricing` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `semantic-kernel-telemetry-basic` | openai | `openai.chat_completions` | warned | python: warned, javascript: warned, go: warned |
| `service-mode-batch-selection` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `service-mode-priority-selection` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `service-mode-provisioned-selection` | bedrock | `aws.bedrock.converse` | preserved | python: preserved, javascript: preserved, go: preserved |
| `service-tier-deepseek-peak-pricing-warning-precedence` | deepseek | `deepseek.chat_completions` | warned | python: warned, javascript: warned, go: warned |
| `service-tier-default-standard-selection` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `service-tier-region-selection` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `service-tier-unsupported-compatibility` | openai | `openai.responses` | warned | python: warned, javascript: warned, go: warned |
| `source-cache-adapter-basic` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `source-capability-warning` | openai | `openai.responses` | unsupported | python: unsupported, javascript: unsupported, go: unsupported |
| `stale-price-warning` | openai | `openai.responses` | warned | python: warned, javascript: warned, go: warned |
| `storage-gb-day-pricing` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `stream-final-usage-missing-warning` | aggregate | `aggregate.cost_ledgers` | warned | python: warned, javascript: warned, go: warned |
| `strict-unknown-model` | openai | `openai.responses` | warned | python: warned, javascript: warned, go: warned |
| `tool-call-units-basic` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `tool-component-unpriced-warning` | openai | `openai.responses` | unsupported | python: unsupported, javascript: unsupported, go: unsupported |
| `unknown-model-compatibility` | openai | `openai.responses` | warned | python: warned, javascript: warned, go: warned |
| `unknown-provider-compatibility` | custom-provider | `openai.responses` | warned | python: warned, javascript: warned, go: warned |
| `unknown-surface-compatibility` | custom | `custom.unknown` | unsupported | python: unsupported, javascript: unsupported, go: unsupported |
| `unpriced-component-compatibility` | openai | `openai.responses` | unsupported | python: unsupported, javascript: unsupported, go: unsupported |
| `usage-field-ignored-warning` | openai | `openai.embeddings` | warned | python: warned, javascript: warned, go: warned |
| `user-pricing-adapter-compact` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `user-pricing-json-file-loader` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `user-pricing-yaml-file-loader` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `vercel-ai-sdk-generate-text-total-usage` | openai | `openai.responses` | warned | python: warned, javascript: warned, go: warned |
| `vercel-ai-sdk-middleware-wrap-generate` | openai | `openai.responses` | warned | python: not_tested, javascript: warned, go: not_tested |
| `vercel-ai-sdk-openai-responses-orchestration-usage` | openai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `vercel-ai-sdk-stream-text-finish` | openai | `openai.responses` | warned | python: warned, javascript: warned, go: warned |
| `vercel-ai-sdk-stream-transcribe-finish` | openai | `openai.audio_transcriptions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `vertex-gemini-generate-content-raw-basic` | vertex | `vertex.gemini.generate_content` | preserved | python: preserved, javascript: preserved, go: preserved |
| `xai-chat-raw-cache-reasoning` | xai | `xai.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `xai-grok-4-3-reasoning-output-pricing` | xai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `xai-responses-output-x-search-call` | xai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `xai-responses-provider-reported-cost-ticks` | xai | `openai.responses` | warned | python: warned, javascript: warned, go: warned |
| `xai-responses-raw-cache-reasoning` | xai | `xai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `xai-responses-server-side-tool-count` | xai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `xai-responses-server-side-tool-usage-map` | xai | `openai.responses` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-chat-batch-partial` | openai | `from_batch_results` | warned | python: warned, javascript: warned, go: warned |
| `openai-chat-batch-pending` | openai | `from_batch_results` | warned | python: warned, javascript: warned, go: warned |
| `openai-responses-batch` | openai | `from_batch_results` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-embeddings-batch` | openai | `from_batch_results` | preserved | python: preserved, javascript: preserved, go: preserved |
| `openai-images-batch` | openai | `openai.images` | preserved | python: preserved, javascript: preserved, go: preserved |
| `anthropic-message-batch-partial` | anthropic | `from_batch_results` | preserved | python: preserved, javascript: preserved, go: preserved |
| `anthropic-message-batch-refusal-retry` | anthropic | `from_batch_results` | preserved | python: preserved, javascript: preserved, go: preserved |
| `gemini-developer-batch-partial` | google | `from_batch_results` | preserved | python: preserved, javascript: preserved, go: preserved |
| `vertex-gemini-batch` | vertex | `from_batch_results` | preserved | python: preserved, javascript: preserved, go: preserved |
| `bedrock-model-invocation-batch` | bedrock | `aws.bedrock.invoke_model` | preserved | python: preserved, javascript: preserved, go: preserved |
| `kimi-batch` | kimi | `from_batch_results` | preserved | python: preserved, javascript: preserved, go: preserved |
| `dashscope-batch` | dashscope | `from_batch_results` | preserved | python: preserved, javascript: preserved, go: preserved |
| `tinker-inkling-route` | tinker | `from_response` | preserved | python: preserved, javascript: preserved, go: preserved |
| `nvidia-nim-route` | nvidia | `from_response` | preserved | python: preserved, javascript: preserved, go: preserved |
| `zai-compatible-route` | zai | `from_response` | preserved | python: preserved, javascript: preserved, go: preserved |
| `ai21-compatible-route` | ai21 | `from_response` | preserved | python: preserved, javascript: preserved, go: preserved |
| `arcee-compatible-route` | arcee | `from_response` | preserved | python: preserved, javascript: preserved, go: preserved |
| `cohere-compatible-route` | cohere | `from_response` | preserved | python: preserved, javascript: preserved, go: preserved |
| `dashscope-compatible-route` | dashscope | `from_response` | preserved | python: preserved, javascript: preserved, go: preserved |
| `inception-compatible-route` | inception | `from_response` | preserved | python: preserved, javascript: preserved, go: preserved |
| `poolside-compatible-route` | poolside | `from_response` | preserved | python: preserved, javascript: preserved, go: preserved |
| `xiaomi-compatible-route` | xiaomi | `from_response` | preserved | python: preserved, javascript: preserved, go: preserved |
| `minimax-anthropic-compatible-route` | minimax | `from_response` | preserved | python: preserved, javascript: preserved, go: preserved |
| `otel-genai-usage-netting` | cross-provider | `usage_ledger_from_otel` | preserved | python: preserved, javascript: preserved, go: preserved |
| `otel-genai-cost` | cross-provider | `from_otel` | preserved | python: preserved, javascript: preserved, go: preserved |
| `otel-genai-fast-tier` | cross-provider | `from_otel` | preserved | python: preserved, javascript: preserved, go: preserved |
| `otel-genai-fast-request-context` | cross-provider | `usage_ledger_from_otel` | preserved | python: preserved, javascript: preserved, go: preserved |
| `precall-estimate-attribution` | openai | `openai.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `precall-estimate-attribution-tag-miss` | openai | `openai.chat_completions` | preserved | python: preserved, javascript: preserved, go: preserved |
| `budget-warning` | cross-provider | `evaluate_budget` | preserved | python: preserved, javascript: preserved, go: preserved |
| `budget-zero-unspent` | cross-provider | `evaluate_budget` | preserved | python: preserved, javascript: preserved, go: preserved |
| `reconciliation-within-tolerance` | cross-provider | `reconcile_cost` | preserved | python: preserved, javascript: preserved, go: preserved |
| `genai-prices-tiered-dated-scheduled` | cross-provider | `price_cards_from_genai_prices` | preserved | python: preserved, javascript: preserved, go: preserved |
| `price-resolution-unavailable-warning` | cross-provider | `attach_price_resolution` | warned | python: warned, javascript: warned, go: warned |
| `price-resolution-refresh-failed-warning` | cross-provider | `attach_price_resolution` | warned | python: warned, javascript: warned, go: warned |

The canonical machine-readable form is [`conformance-report.json`](./conformance-report.json).
