---
title: RunCost Supported Surfaces
date: 2026-05-25
type: reference
status: active
---

# RunCost Supported Surfaces

This support matrix describes the current fixture-backed `0.2.x` public beta. A
provider or framework is considered supported only when it has shared
conformance fixtures.

For the full fixture-derived provider/surface/language matrix, see
[Generated Fixture Support Matrix](../generated/fixture-support-matrix.md).

## Provider Extractors

| Provider | Surface | Status |
|---|---|---|
| OpenAI | Responses | Fixture-backed |
| OpenAI | Responses streaming `response.completed` event | Fixture-backed |
| OpenAI | Chat Completions | Fixture-backed |
| OpenAI | Chat Completions streaming final usage chunk | Fixture-backed |
| OpenAI | Organization usage completions buckets | Fixture-backed |
| OpenAI | Embeddings | Fixture-backed |
| OpenAI | Organization usage embeddings buckets | Fixture-backed |
| OpenAI | Audio Transcriptions duration and token usage | Fixture-backed |
| OpenAI | Organization usage audio transcription buckets | Fixture-backed |
| OpenAI | Images token usage and image-unit responses | Fixture-backed |
| OpenAI | Organization usage image buckets | Fixture-backed |
| OpenAI | Organization usage audio speech character buckets | Fixture-backed |
| OpenAI | Vector Stores storage bytes with explicit storage-day conversion | Fixture-backed |
| OpenAI | Organization usage code-interpreter sessions | Fixture-backed |
| OpenAI | Batch results for Responses, Chat Completions, Embeddings, and Images | Fixture-backed expansion contract |
| OpenAI | Conversations state resource | Documented non-cost-bearing surface; price associated Responses |
| Anthropic | Messages | Fixture-backed |
| Anthropic | Messages SSE event sequence | Fixture-backed |
| Anthropic | Message Batches result rows | Fixture-backed expansion contract |
| OpenRouter | Chat Completions | Fixture-backed |
| OpenRouter | OpenAI-compatible streaming final usage chunk with provider-reported cost | Fixture-backed |
| Meta Model API | Responses-style usage | Fixture-backed; credentialed live smoke passed |
| Meta Model API | Chat Completions through OpenAI-compatible usage | Fixture-backed; credentialed live smoke passed |
| Groq | Chat Completions through OpenAI-compatible usage | Fixture-backed |
| xAI | Chat Completions through OpenAI-compatible usage | Fixture-backed |
| xAI | Responses through OpenAI-compatible usage | Fixture-backed |
| Mistral | Chat Completions through OpenAI-compatible usage | Fixture-backed |
| DeepSeek | Chat Completions through OpenAI-compatible usage plus cache hit and miss fields; response `created` timestamp feeds `context.priced_at` for pricing-period selection | Fixture-backed |
| Azure OpenAI | Chat Completions through OpenAI-compatible usage | Fixture-backed |
| Hugging Face Inference Providers | Chat Completions through OpenAI-compatible usage | Fixture-backed |
| Thinking Machines Tinker | Chat Completions with Inkling effort metadata | Fixture-backed expansion contract |
| NVIDIA NIM | Chat Completions through explicit compatible route | Fixture-backed expansion contract |
| AI21, Arcee, DashScope, Inception, Poolside, Xiaomi, and ZAI | Chat Completions through explicit compatible routes | Fixture-backed expansion contract |
| MiniMax | Anthropic-compatible Messages route | Fixture-backed expansion contract |
| Cohere | Chat | Fixture-backed |
| Cohere | Rerank | Fixture-backed |
| Google Gemini | `generateContent` | Fixture-backed |
| Google Gemini | `generateContent` stream chunks with final `usageMetadata` | Fixture-backed |
| Google Gemini | Live API top-level or final-message `usageMetadata` | Fixture-backed |
| Google Gemini | Interactions stream/event `metadata.total_usage` / `metadata.totalUsage` | Fixture-backed |
| Vertex AI Gemini | `generateContent` | Fixture-backed |
| Google Gemini / Vertex AI | Developer batch and Vertex batch-prediction result rows | Fixture-backed expansion contract |
| AWS Bedrock | Converse | Fixture-backed |
| AWS Bedrock | InvokeModel with Anthropic Messages body | Fixture-backed |
| AWS Bedrock | Model-invocation batch result rows | Fixture-backed expansion contract |
| Kimi and DashScope | Batch result rows | Fixture-backed expansion contract |

## Framework Adapters

| Framework | Object | Status |
|---|---|---|
| LangChain | AIMessage usage metadata | Fixture-backed |
| LangChain | Python callback/context-manager helper | Fixture-backed for Python |
| OpenAI Agents SDK | Usage objects and aggregated request usage entries | Fixture-backed |
| Vercel AI SDK | `generateText` result | Fixture-backed |
| Vercel AI SDK | `streamText` finish/onFinish result | Fixture-backed |
| Vercel AI SDK | `wrapGenerate` middleware helper | Fixture-backed for JavaScript |
| Vercel AI SDK | `onFinish` helper | Fixture-backed for JavaScript |
| LlamaIndex | TokenCountingHandler output | Fixture-backed |
| Haystack | OpenAIChatGenerator reply metadata / OpenAIGenerator meta usage | Fixture-backed |
| LiteLLM proxy | OpenAI-compatible usage plus hidden response cost metadata | Fixture-backed |
| AutoGen / AG2 | `get_actual_usage()`, `get_total_usage()`, `gather_usage_summary(...)` summary dictionaries | Fixture-backed for selected usage summary shape |
| Semantic Kernel | Basic telemetry/filter token metadata | Fixture-backed |
| LangSmith | Trace/run usage metadata and export `total_cost` comparison | Fixture-backed |
| OpenRouter-compatible SDK paths | OpenAI SDK base URL responses and resolved Agent SDK full responses | Fixture-backed |

## Aggregation

| Surface | Object | Status |
|---|---|---|
| Aggregate | Already-calculated `CostLedger` objects | Fixture-backed |
| Aggregate | Missing final streaming usage warning | Fixture-backed |

## Price Sources

| Source | Status |
|---|---|
| Simon Willison `llm-prices` current and historical data | Fixture-backed representative adapter |
| LiteLLM model price JSON | Fixture-backed representative adapter |
| OpenRouter models API | Fixture-backed representative adapter |
| models.dev API catalog | Fixture-backed representative adapter |
| Reviewed official/public-preview pricing snapshots | Fixture-backed representative adapter |
| Portkey pricing data | Fixture-backed representative adapter |
| User compact pricing data | Fixture-backed representative adapter |
| Helicone model-registry endpoint data | Fixture-backed representative adapter |
| RunCost source-cache envelopes | Fixture-backed representative adapter |
| External resolver and managed cache | Fixture-backed selection, conditional refresh, offline, last-known-good, and audit metadata across Python, JavaScript/browser, and Go; no provider prices are packaged |
| Pydantic `genai-prices` | Fixture-backed representative adapter |

## Telemetry, Estimation, and Reconciliation

| Surface | Status |
|---|---|
| OpenTelemetry GenAI span to usage/cost ledger | Fixture-backed across Python, JavaScript, and Go |
| RunCost cost attributes for an existing OTel pipeline | Fixture-backed across Python, JavaScript, and Go |
| Stateless pre-call component estimate | Fixture-backed across Python, JavaScript, and Go |
| Stateless warning/exceeded budget evaluation | Fixture-backed across Python, JavaScript, and Go |
| Provider-reported total reconciliation and residuals | Fixture-backed across Python, JavaScript, and Go |

## Notes

- Support means extraction and pricing behavior has at least one shared fixture across Python and JavaScript, with Go coverage through the conformance suite where applicable.
- Support does not mean every model, region, service tier, tool, or historical price is present.
- OpenAI Conversations are documented as state resources, not standalone usage-bearing model responses. Price Responses calls that attach to Conversations through the fixture-backed OpenAI Responses extractor.
- Anthropic Messages extraction is fixture-backed for standard prompt caching, streaming final usage, and Fable 5 fallback billing variants: direct zero-bill classifier blocks, server-side fallback, mid-stream fallback with per-model output attribution, sticky-served fallback turns, and client-side fallback-credit retries.
- OpenAI Responses hosted tool extraction is fixture-backed for web search, file search, code interpreter calls, computer-use action counts, and function-call counts. Responses usage detail fields for cache writes, orchestration input, cached orchestration input, and orchestration output are mapped onto the existing cache-write, input, cache-read, and output token components when present. Chat Completions and OpenAI Agents SDK usage also map the documented `cache_write_tokens` detail field.
- Targeted OpenAI GPT-5.6 fixtures cover Standard, Batch, Flex, and Priority pricing. Standard, Batch, and Flex include the published 272,000-token long-context split; Priority remains short-context only because OpenAI does not currently publish Priority long-context rates. These snapshots are conformance evidence, not package defaults.
- Pricing-period selection is fixture-backed for DeepSeek-style UTC peak and
  regular windows. When a provider response does not contain a usable timestamp,
  callers can set `context.priced_at` on normalized usage or pass an explicit
  `pricing_period` through their own usage ledger.
- Tool/feature pricing is complete for the current exit gate: OpenAI-style hosted tools, OpenRouter/provider-reported costs, custom internal tools, OpenAI organization usage completions text/cache/audio tokens, OpenAI Embeddings per-response and organization usage bucket tokens, OpenAI Images token/image-unit usage, OpenAI organization usage image buckets, OpenAI organization usage audio speech character buckets, normalized generated media, Cohere Rerank search units, OpenAI audio transcription duration/token usage, OpenAI organization usage audio transcription seconds, OpenAI Vector Stores `usage_bytes` to GB-day conversion with an explicit storage-day window, OpenAI organization usage code-interpreter `num_sessions`, runtime-second, and GB-day storage pricing. Broader provider-specific storage/session extraction and live validation remain beta hardening.
- Gemini Live API extraction uses `google.gemini.live`, reads `usageMetadata.promptTokensDetails` and `usageMetadata.responseTokensDetails`, maps `AUDIO` entries to `input_audio_tokens` and `output_audio_tokens`, and preserves `usageMetadata.totalTokenCount` as raw usage rather than pricing it directly. A reviewed `google-official` test snapshot covers `gemini-3.5-live-translate-preview`.
- Google Gemini Interactions extraction uses `google.gemini.interactions`, reads v2.9.0 `metadata.total_usage`, camelCase `metadata.totalUsage`, or legacy `metadata.usage`, maps lower-case modality token arrays into the canonical token components, and treats `google_search` grounding counts as `web_search_units`; broader grounding/tool pricing still depends on caller-supplied price cards.
- Meta Model API extraction uses `meta.responses` for Responses-style usage and
  `meta.chat_completions` for OpenAI-compatible chat usage. RunCost packages no
  Meta prices. An opt-in reviewed-preview
  fixture remains available for compatibility testing. A sanitized credentialed
  smoke against `https://api.meta.ai/v1` confirmed `/models`,
  `/chat/completions`, `/responses`, cached-token fields, and reasoning-token
  fields. Meta-specific tool/media pricing still depends on primary pricing
  documentation.
- Framework paths are fixture-backed for dependency-free plain-object shapes. Sanitized sample and live smoke harnesses exist, but real application validation is still expanding.
- Price-source fixtures prove representative adapter mappings. Current public
  price data comes from the external resolver or caller-owned cards; see
  [Price Data Strategy](price-data-strategy.md).
- The next support expansion should prioritize live smoke, provider-specific feature breadth, broader streaming usage, and framework findings from real app runs.
