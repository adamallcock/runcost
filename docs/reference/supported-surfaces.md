---
title: RunCost Supported Surfaces
date: 2026-05-25
type: reference
status: active
---

# RunCost Supported Surfaces

This support matrix describes the current fixture-backed alpha. A provider or framework is considered supported only when it has shared conformance fixtures.

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
| OpenAI | Conversations state resource | Documented non-cost-bearing surface; price associated Responses |
| Anthropic | Messages | Fixture-backed |
| Anthropic | Messages SSE event sequence | Fixture-backed |
| OpenRouter | Chat Completions | Fixture-backed |
| OpenRouter | OpenAI-compatible streaming final usage chunk with provider-reported cost | Fixture-backed |
| Groq | Chat Completions through OpenAI-compatible usage | Fixture-backed |
| xAI | Chat Completions through OpenAI-compatible usage | Fixture-backed |
| xAI | Responses through OpenAI-compatible usage | Fixture-backed |
| Mistral | Chat Completions through OpenAI-compatible usage | Fixture-backed |
| DeepSeek | Chat Completions through OpenAI-compatible usage plus cache hit and miss fields | Fixture-backed |
| Azure OpenAI | Chat Completions through OpenAI-compatible usage | Fixture-backed |
| Hugging Face Inference Providers | Chat Completions through OpenAI-compatible usage | Fixture-backed |
| Cohere | Chat | Fixture-backed |
| Cohere | Rerank | Fixture-backed |
| Google Gemini | `generateContent` | Fixture-backed |
| Google Gemini | `generateContent` stream chunks with final `usageMetadata` | Fixture-backed |
| Vertex AI Gemini | `generateContent` | Fixture-backed |
| AWS Bedrock | Converse | Fixture-backed |
| AWS Bedrock | InvokeModel with Anthropic Messages body | Fixture-backed |

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
| Reviewed official pricing snapshots | Fixture-backed representative adapter |
| Portkey pricing data | Fixture-backed representative adapter |
| User compact pricing data | Fixture-backed representative adapter |
| Helicone model-registry endpoint data | Fixture-backed representative adapter |
| RunCost source-cache envelopes | Fixture-backed representative adapter |

## Notes

- Support means extraction and pricing behavior has at least one shared fixture across Python and JavaScript, with Go coverage through the conformance suite where applicable.
- Support does not mean every model, region, service tier, tool, or historical price is present.
- OpenAI Conversations are documented as state resources, not standalone usage-bearing model responses. Price Responses calls that attach to Conversations through the fixture-backed OpenAI Responses extractor.
- OpenAI Responses hosted tool extraction is fixture-backed for web search, file search, code interpreter calls, computer-use action counts, and function-call counts.
- Tool/feature pricing is complete for the current exit gate: OpenAI-style hosted tools, OpenRouter/provider-reported costs, custom internal tools, OpenAI organization usage completions text/cache/audio tokens, OpenAI Embeddings per-response and organization usage bucket tokens, OpenAI Images token/image-unit usage, OpenAI organization usage image buckets, OpenAI organization usage audio speech character buckets, normalized generated media, Cohere Rerank search units, OpenAI audio transcription duration/token usage, OpenAI organization usage audio transcription seconds, OpenAI Vector Stores `usage_bytes` to GB-day conversion with an explicit storage-day window, OpenAI organization usage code-interpreter `num_sessions`, runtime-second, and GB-day storage pricing. Broader provider-specific storage/session extraction and live validation remain beta hardening.
- Framework paths are fixture-backed for dependency-free plain-object shapes. Sanitized sample and live smoke harnesses exist, but real application validation is still expanding.
- Price-source fixtures prove representative adapter mappings. They are not a complete vendored model-price database; see [Price Data Strategy](price-data-strategy.md).
- The next support expansion should prioritize live smoke, provider-specific feature breadth, broader streaming usage, and framework findings from real app runs.
