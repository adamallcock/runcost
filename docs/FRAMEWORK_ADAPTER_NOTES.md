# Framework Adapter Notes

Status: v0.x prototype
Date: 2026-05-24

This document records framework-level usage shapes that the current metadata adapters depend on. These adapters do not replace provider extractors; they normalize framework result objects while preserving the underlying provider, surface, and model supplied by the caller.

## Adapter Dispatch

Framework extraction is selected with `extract.adapter`:

- `langchain.chat_message`
- `vercel_ai_sdk.generate_text`
- `llamaindex.token_counter`

The output usage ledger keeps `provider`, `surface`, and `model` from the caller or framework response, so existing provider price cards remain usable.

For one-call cost calculation, use the public helpers:

- Python: `from_langchain_message`, `from_vercel_ai_sdk_result`, `from_llamaindex_token_counter`.
- JavaScript/TypeScript: `fromLangChainMessage`, `fromVercelAISDKResult`, `fromLlamaIndexTokenCounter`.
- Go: `FromLangChainMessage`, `FromVercelAISDKResult`, `FromLlamaIndexTokenCounter`.

For framework-native ergonomics, use:

- Python LangChain: `track_langchain_costs(...)` or `RunCostLangChainCallback(...)`.
- JavaScript Vercel AI SDK: `createRunCostVercelMiddleware(...)`.

## LangChain AIMessage

Source references:

- LangChain JavaScript message docs show `AIMessage.usage_metadata` with `input_tokens`, `output_tokens`, `total_tokens`, `input_token_details.cache_read`, and `output_token_details.reasoning`: https://docs.langchain.com/oss/javascript/langchain/messages
- LangChain Python `UsageMetadata` reference defines the same cross-provider fields and notes that detail fields such as `cache_read`, `cache_creation`, and `reasoning` are breakdowns that need not sum to the total: https://reference.langchain.com/v0.3/python/core/messages/langchain_core.messages.ai.UsageMetadata.html

Mapping:

- `usage_metadata.input_tokens` minus `input_token_details.cache_read` and `input_token_details.cache_creation` -> `input_uncached_tokens`.
- `usage_metadata.input_token_details.cache_read` -> `input_cache_read_tokens`.
- `usage_metadata.input_token_details.cache_creation` -> `input_cache_write_tokens`.
- `usage_metadata.output_tokens` minus `output_token_details.reasoning` -> `output_text_tokens`.
- `usage_metadata.output_token_details.reasoning` -> `output_reasoning_tokens`.
- `usage_metadata.total_tokens` is preserved in raw usage but is never priced directly.

Callback/context-manager helper:

```python
from runcost import track_langchain_costs

with track_langchain_costs(
    provider="openai",
    surface="openai.chat_completions",
    model="gpt-5-nano",
    price_cards=price_cards,
) as cost_callback:
    chain.invoke(messages, config=cost_callback.as_config())

print(cost_callback.total)
print(cost_callback.latest)
```

The helper is dependency-free and duck-types LangChain callback output. It currently records AIMessage-like generations from `on_llm_end` / `on_chat_model_end`.

## Vercel AI SDK

Source reference:

- AI SDK `generateText` reference documents final-step `usage`, aggregate `totalUsage`, input details including cache read/write and non-cache tokens, output details including text and reasoning tokens, and response `modelId`: https://ai-sdk.dev/docs/reference/ai-sdk-core/generate-text

Mapping:

- Prefer `totalUsage` when present; otherwise use `usage`.
- `inputTokenDetails.noCacheTokens` -> `input_uncached_tokens`.
- If `noCacheTokens` is absent, derive uncached input as `inputTokens - cacheReadTokens - cacheWriteTokens`.
- `inputTokenDetails.cacheReadTokens` or legacy/top-level `cachedInputTokens` -> `input_cache_read_tokens`.
- `inputTokenDetails.cacheWriteTokens` -> `input_cache_write_tokens`.
- `outputTokenDetails.textTokens` -> `output_text_tokens`.
- If `textTokens` is absent, derive output text as `outputTokens - reasoningTokens`.
- `outputTokenDetails.reasoningTokens` or top-level `reasoningTokens` -> `output_reasoning_tokens`.
- `totalTokens` is preserved in raw usage but is never priced directly.

Middleware helper:

```js
import { createRunCostVercelMiddleware } from "runcost";

const runcostMiddleware = createRunCostVercelMiddleware({
  provider: "openai",
  surface: "openai.responses",
  model: "gpt-5-nano",
  priceCards
});
```

The helper implements `wrapGenerate`, records ledgers in `middleware.ledgers`, and attaches the latest ledger to the result as `runCost` by default.

## LlamaIndex TokenCountingHandler

Source references:

- LlamaIndex `TokenCountingHandler` guide documents cumulative prompt, completion, total LLM, embedding token counters, and streaming finalization behavior: https://docs.llamaindex.ai/en/stable/examples/observability/TokenCountingHandler/
- LlamaIndex token counter API docs describe `TokenCountingHandler` as the callback handler for counting LLM and embedding events: https://docs.llamaindex.ai/en/stable/api_reference/callbacks/token_counter/

Mapping:

- Sum `llm_token_counts[*].prompt_token_count` -> `input_uncached_tokens`.
- Sum `llm_token_counts[*].completion_token_count` -> `output_text_tokens`.
- If event lists are absent, use cumulative `prompt_llm_token_count` and `completion_llm_token_count`.
- `total_llm_token_count` and embedding counters are preserved in raw usage but not priced by this LLM adapter.

Notes:

- LlamaIndex token counting may be tokenizer-estimated rather than provider-reported for some providers. The adapter is useful for framework-level visibility but provider raw responses should be preferred when exact billing metadata is available.

## Planned / Partial Adapter Paths

The following paths are documented from current primary docs but are not fixture-backed in the current prototype. Treat them as research-backed adapter targets, not implemented support.

### Microsoft Semantic Kernel

Source references:

- Semantic Kernel filters can intercept function invocation, prompt rendering, and automatic function invocation, with access to the relevant execution context before and after the operation: https://learn.microsoft.com/en-us/semantic-kernel/concepts/enterprise-readiness/filters
- Microsoft's Semantic Kernel metering note describes prompt, completion, and total token metrics captured for Azure OpenAI/OpenAI connector calls: https://devblogs.microsoft.com/agent-framework/track-your-token-usage-and-costs-with-semantic-kernel/

Recommended bridge:

- Use a function-invocation or auto-function-invocation filter to observe the completed call and any framework result object.
- Prefer provider raw response / inner content when the connector exposes it, because Semantic Kernel language SDKs and connectors may represent token metadata differently.
- Map prompt/input tokens to `input_uncached_tokens`, completion/output tokens to `output_text_tokens`, and total tokens only into raw usage.
- Preserve filter/plugin/function metadata as raw framework metadata so later debug traces can explain which Semantic Kernel function produced the cost.

Status:

- Partial documentation only. No `semantic_kernel.*` adapter is implemented yet.

### Haystack

Source references:

- `OpenAIChatGenerator` replies are `ChatMessage` objects with `_meta` containing model, finish reason, and OpenAI-style `usage`; the docs show prompt tokens, completion tokens, total tokens, cached prompt tokens, and reasoning tokens in that metadata. Streaming examples show `usage: None` for the streamed reply metadata: https://docs.haystack.deepset.ai/docs/openaichatgenerator
- `OpenAIGenerator` returns a `meta` list with token-count and finish metadata, including OpenAI-style `usage`: https://docs.haystack.deepset.ai/docs/openaigenerator

Recommended bridge:

- For chat, read `response["replies"][*]._meta.usage` or the public metadata accessor if present.
- For text generation, read `response["meta"][*].usage`.
- Reuse the OpenAI-compatible chat usage mapping for `prompt_tokens`, `completion_tokens`, `total_tokens`, `prompt_tokens_details.cached_tokens`, and `completion_tokens_details.reasoning_tokens`.
- Treat Haystack streaming metadata with `usage: None` as a missing-final-usage case unless a provider raw response or final callback supplies usage separately.

Status:

- Partial documentation only. No `haystack.*` adapter is implemented yet.

### AutoGen / AG2

Source reference:

- AG2 documents `OpenAIWrapper.print_usage_summary()`, `Agent.get_actual_usage()`, `Agent.get_total_usage()`, `autogen.gather_usage_summary(agents)`, cached-vs-actual modes, custom token prices, and an Azure model-version caution: https://docs.ag2.ai/latest/docs/use-cases/notebooks/notebooks/agentchat_cost_token_tracking/

Recommended bridge:

- Prefer `Agent.get_actual_usage()` for non-cache completions and `Agent.get_total_usage()` when the caller wants all completions including cache.
- Normalize AG2 summary dictionaries into one ledger per model/provider bucket when the summary is already aggregated.
- Do not trust AG2's estimated cost as authoritative by default; compare it as provider/framework-reported cost because AG2 docs call out custom price and Azure model-version caveats.
- Preserve the AG2 mode (`actual` vs `total`) in raw usage and warnings.

Status:

- Partial documentation only. No `autogen.*` or `ag2.*` adapter is implemented yet.

### LangSmith Export / Compare

Source references:

- LangSmith cost tracking separates input, output, and other costs; it supports token and cost breakdowns with cache, text, image, reasoning, tool, retrieval, and custom-run categories: https://docs.langchain.com/langsmith/cost-tracking
- LangSmith traces can be populated with `usage_metadata` on the current run or returned output, using fields such as input, output, total, cache-read, and cost details: https://docs.langchain.com/langsmith/cost-tracking
- LangSmith bulk exports can limit exported fields, including `total_tokens` and `total_cost`: https://docs.langchain.com/langsmith/data-export

Recommended bridge:

- Export or fetch LangSmith run rows with token and cost fields, then calculate RunCost ledgers from the underlying provider usage if available.
- Compare LangSmith-reported `total_cost` / cost detail fields against RunCost output using the existing provider-reported-cost comparison path.
- Preserve run hierarchy fields so aggregate ledgers can be compared at trace, parent run, or child run level.

Status:

- Partial documentation only. No `langsmith.*` adapter is implemented yet.

### LiteLLM Proxy Metadata

Source references:

- LiteLLM completion docs state that LiteLLM returns token usage by default and exposes response cost in hidden response metadata: https://docs.litellm.ai/docs/completion/token_usage
- LiteLLM proxy model management docs show `model_info` as the place for additional model metadata and model-cost information returned by `/model/info`: https://docs.litellm.ai/docs/proxy/model_management
- LiteLLM custom pricing docs describe proxy spend tracking, custom pricing, cost per token/second, zero-cost models, provider discounts, and provider margins: https://docs.litellm.ai/docs/proxy/custom_pricing

Recommended bridge:

- For direct LiteLLM SDK responses, read provider-compatible `usage` first and compare `_hidden_params.response_cost` as framework/provider-reported cost when present.
- For proxy deployments, ingest `/model/info` pricing metadata as a price source and preserve proxy model aliases separately from upstream provider model IDs.
- Preserve LiteLLM provider discounts/margins as explicit user or gateway adjustment policies rather than silently baking them into provider list price.

Status:

- Partial documentation only. Price-source import from LiteLLM JSON exists, but no `litellm.proxy_response` metadata adapter is implemented yet.

### OpenRouter-Compatible SDK Paths

Source references:

- OpenRouter's API overview says request and response schemas are very similar to the OpenAI Chat API, and its chat completion response includes OpenAI-style `usage`: https://openrouter.ai/docs/api/reference/overview
- OpenRouter usage accounting documents prompt/completion counts, cost credits, reasoning tokens, cached tokens, and final-message streaming usage: https://openrouter.ai/docs/cookbook/administration/usage-accounting
- OpenRouter's OpenAI SDK guide shows using the OpenAI SDK with `baseURL: "https://openrouter.ai/api/v1"`: https://openrouter.ai/docs/guides/community/openai-sdk
- OpenRouter's Agent SDK `callModel` result exposes response accessors such as `getResponse()` and full response streams: https://openrouter.ai/docs/agent-sdk/call-model/api-reference

Recommended bridge:

- For OpenAI SDK compatibility, route responses through the existing `openrouter.chat_completions` / OpenAI-compatible extraction path.
- When OpenRouter usage accounting includes `usage.cost` or `cost_details`, compare it as provider-reported cost.
- For streaming, read the final SSE usage object when present; otherwise use the existing missing-final-usage warning.
- For OpenRouter Agent SDK, unwrap the full response via SDK result accessors and then reuse the OpenRouter/OpenAI-compatible extractor.

Status:

- Partial documentation only. OpenRouter chat completions and OpenRouter models pricing are fixture-backed, but SDK-specific wrappers and Agent SDK result objects are not implemented yet.
