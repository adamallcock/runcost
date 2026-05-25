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
