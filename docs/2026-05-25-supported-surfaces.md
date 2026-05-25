---
title: RunCost Supported Surfaces
date: 2026-05-25
type: reference
status: draft
---

# RunCost Supported Surfaces

This support matrix describes the current fixture-backed prototype. A provider or framework is considered supported only when it has shared conformance fixtures.

For mechanical coverage counts, see [Fixture Coverage](2026-05-25-fixture-coverage.md).

## Provider Extractors

| Provider | Surface | Status |
|---|---|---|
| OpenAI | Responses | Fixture-backed |
| OpenAI | Chat Completions | Fixture-backed |
| Anthropic | Messages | Fixture-backed |
| OpenRouter | Chat Completions | Fixture-backed |
| Groq | Chat Completions through OpenAI-compatible usage | Fixture-backed |
| xAI | Chat Completions through OpenAI-compatible usage | Fixture-backed |
| Mistral | Chat Completions through OpenAI-compatible usage | Fixture-backed |
| DeepSeek | Chat Completions through OpenAI-compatible usage plus cache hit and miss fields | Fixture-backed |
| Azure OpenAI | Chat Completions through OpenAI-compatible usage | Fixture-backed |
| Hugging Face Inference Providers | Chat Completions through OpenAI-compatible usage | Fixture-backed |
| Cohere | Chat | Fixture-backed |
| Google Gemini | `generateContent` | Fixture-backed |
| Vertex AI Gemini | `generateContent` | Fixture-backed |
| AWS Bedrock | Converse | Fixture-backed |

## Framework Adapters

| Framework | Object | Status |
|---|---|---|
| LangChain | AIMessage usage metadata | Fixture-backed |
| LangChain | Python callback/context-manager helper | Fixture-backed for Python |
| Vercel AI SDK | `generateText` result | Fixture-backed |
| Vercel AI SDK | `wrapGenerate` middleware helper | Fixture-backed for JavaScript |
| LlamaIndex | TokenCountingHandler output | Fixture-backed |

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
- The next support expansion should prioritize provider-specific tool-call pricing, streaming usage, and clean framework middleware ergonomics.
