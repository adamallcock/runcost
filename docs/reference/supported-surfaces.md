---
title: RunCost Supported Surfaces
date: 2026-05-25
type: reference
status: draft
---

# RunCost Supported Surfaces

This support matrix describes the current fixture-backed prototype. A provider or framework is considered supported only when it has shared conformance fixtures.

For mechanical coverage counts, see [Fixture Coverage](../reports/fixture-coverage.md).

## Provider Extractors

| Provider | Surface | Status |
|---|---|---|
| OpenAI | Responses | Fixture-backed |
| OpenAI | Responses streaming `response.completed` event | Fixture-backed |
| OpenAI | Chat Completions | Fixture-backed |
| OpenAI | Embeddings | Fixture-backed |
| OpenAI | Conversations state resource | Documented non-cost-bearing surface; price associated Responses |
| Anthropic | Messages | Fixture-backed |
| Anthropic | Messages SSE event sequence | Fixture-backed |
| OpenRouter | Chat Completions | Fixture-backed |
| Groq | Chat Completions through OpenAI-compatible usage | Fixture-backed |
| xAI | Chat Completions through OpenAI-compatible usage | Fixture-backed |
| xAI | Responses through OpenAI-compatible usage | Fixture-backed |
| Mistral | Chat Completions through OpenAI-compatible usage | Fixture-backed |
| DeepSeek | Chat Completions through OpenAI-compatible usage plus cache hit and miss fields | Fixture-backed |
| Azure OpenAI | Chat Completions through OpenAI-compatible usage | Fixture-backed |
| Hugging Face Inference Providers | Chat Completions through OpenAI-compatible usage | Fixture-backed |
| Cohere | Chat | Fixture-backed |
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
| Simon Willison `llm-prices` current and historical data | Prototype adapter |
| LiteLLM model price JSON | Prototype adapter |
| OpenRouter models API | Prototype adapter |
| Portkey pricing data | Prototype adapter |
| User compact pricing data | Prototype adapter |
| Helicone model-registry endpoint data | Prototype adapter |

## Notes

- Support means extraction and pricing behavior has at least one shared fixture across Python and JavaScript, with Go coverage through the conformance suite where applicable.
- Support does not mean every model, region, service tier, tool, or historical price is present.
- OpenAI Conversations are documented as state resources, not standalone usage-bearing model responses. Price Responses calls that attach to Conversations through the fixture-backed OpenAI Responses extractor.
- OpenAI Responses hosted tool extraction is fixture-backed for web search, file search, code interpreter calls, computer-use action counts, and function-call counts.
- Tool/feature pricing is complete for the current exit gate: OpenAI-style hosted tools, OpenRouter/provider-reported costs, and custom internal tools. Broader provider-specific generated media, transcription, rerank, storage/session, GB-day, and live validation remain beta hardening.
- Milestone 6 framework paths are fixture-backed for dependency-free plain-object shapes. Live SDK/API-key smoke and real application validation are assigned to Milestone 8.
- The next support expansion should prioritize live smoke, provider-specific feature breadth, broader streaming usage, and framework findings from real app runs.
