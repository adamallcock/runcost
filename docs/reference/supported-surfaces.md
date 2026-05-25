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
| Vercel AI SDK | `generateText` result | Fixture-backed |
| Vercel AI SDK | `wrapGenerate` middleware helper | Fixture-backed for JavaScript |
| LlamaIndex | TokenCountingHandler output | Fixture-backed |
| Haystack | OpenAIChatGenerator reply metadata / OpenAIGenerator meta usage | Fixture-backed |
| LiteLLM proxy | OpenAI-compatible usage plus hidden response cost metadata | Fixture-backed |
| AutoGen / AG2 | `get_actual_usage()`, `get_total_usage()`, `gather_usage_summary(...)` summary dictionaries | Fixture-backed for selected usage summary shape |

## Documented Partial Adapter Paths

These paths are researched and documented in [Framework Adapter Notes](../notes/framework-adapter-notes.md), but they are not yet fixture-backed and should not be treated as implemented support.

| Framework / Gateway | Object or Path | Status |
|---|---|---|
| Semantic Kernel | Function invocation filters, auto-function filters, connector token metadata | Documented path; not fixture-backed |
| LangSmith | Trace usage metadata and bulk export cost comparison | Documented path; not fixture-backed |
| OpenRouter-compatible SDK paths | OpenAI SDK base URL, OpenRouter SDK, Agent SDK full responses | Documented path; not fixture-backed |

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
- Documented partial adapter paths are integration targets with source evidence; they still need adapters, fixtures, examples, and parity-matrix promotion before they become supported.
- The next support expansion should prioritize provider-specific tool-call pricing, streaming usage, and clean framework middleware ergonomics.
