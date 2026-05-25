# RunCost Product Requirements

Status: Draft
Last updated: 2026-05-24

## 1. Purpose

Build a lightweight developer package that answers one question reliably:

> How much did this LLM or agent API call just cost, broken down by billable component?

The package should work with direct provider SDK calls, OpenAI-compatible APIs, third-party agent frameworks, and custom internal model routing. It should be easy enough for a developer to add in one or two lines, while still accurate enough for production spend accounting, customer billing support, and debugging surprising invoices.

This project is a cost-normalization and calculation library. It is not a gateway, observability platform, tokenizer, dashboard, router, or full model catalog.

## 2. Product Thesis

LLM usage accounting is becoming too complex for ad hoc formulas:

- Providers return different usage shapes.
- Model aliases and dated model names drift.
- Cached input, cache writes, cache TTLs, reasoning/thinking, multimodal units, search/tool units, and batch/service tiers are increasingly billable.
- Pricing varies by provider, API surface, region, deployment mode, context length, service tier, and time.
- Many teams have custom contract discounts or private model prices.
- Frameworks such as LangChain, LlamaIndex, Vercel AI SDK, Semantic Kernel, Haystack, and AutoGen often wrap or transform raw provider responses before application code sees them.

The package should provide a single, explicit cost ledger abstraction that can sit underneath direct SDK calls, framework callbacks, and internal billing pipelines.

## 3. Target Users

### 3.1 Application Developers

Developers building LLM features who want a simple cost result next to their API call.

Typical need:

```ts
const cost = await costLedger.fromResponse(response, {
  provider: "openai",
  surface: "responses"
});
```

### 3.2 Agent Framework Developers

Developers using LangChain, LlamaIndex, Vercel AI SDK, Semantic Kernel, Haystack, AutoGen, or similar frameworks who need cost capture through callbacks, middleware, telemetry, or run metadata.

Typical need:

```py
with llm_cost_callback() as costs:
    result = agent.invoke(input)
print(costs.total_usd)
```

### 3.3 Platform and Infra Teams

Teams running multiple model providers behind internal abstractions who need:

- Custom price cards.
- Provider discounts.
- Internal routing model aliases.
- Historical pricing.
- Conformance tests across languages.

### 3.4 Finance, Data, and Billing Teams

Teams reconciling LLM spend with invoices or allocating usage to customers, teams, features, or jobs.

## 4. Non-Goals

The project should not initially:

- Proxy model traffic.
- Store traces.
- Provide dashboards.
- Estimate tokens before a call.
- Replace observability tools such as Langfuse, Helicone, Portkey Gateway, or LangSmith.
- Replace model catalogs such as LiteLLM, Portkey Models, or models.dev.
- Scrape every provider pricing page before the core schema stabilizes.
- Promise invoice-exact reconciliation for every provider without caveats.

## 5. Core Concepts

### 5.1 Provider

The company or routing surface responsible for billing the request.

Examples:

- `openai`
- `azure_openai`
- `anthropic`
- `google_ai_studio`
- `vertex_ai`
- `aws_bedrock`
- `deepseek`
- `xai`
- `groq`
- `mistral`
- `cohere`
- `huggingface_inference_providers`
- `huggingface_inference_endpoints`
- `openrouter`
- `together`
- `fireworks`
- `cerebras`
- `perplexity`
- `ollama`
- `custom`

### 5.2 Surface

The API, SDK, or framework path through which the model was called.

Examples:

- `openai.responses`
- `openai.chat_completions`
- `openai.completions`
- `openai.embeddings`
- `anthropic.messages`
- `google.generate_content`
- `vertex.generate_content`
- `aws_bedrock.converse`
- `aws_bedrock.invoke_model`
- `openai_compatible.chat_completions`
- `vercel_ai_sdk.generate_text`
- `vercel_ai_sdk.stream_text`
- `langchain.chat_model`
- `llamaindex.llm`
- `semantic_kernel.kernel_function`
- `haystack.generator`
- `autogen.openai_wrapper`

Surface is required because the same underlying model can have different pricing, usage fields, or modifiers on different APIs.

### 5.3 Model Identity

The package must distinguish:

- `model_requested`: the model name the user requested.
- `model_returned`: the model name in the response.
- `model_billed`: the model or price-card key used for billing.
- `model_alias_resolution`: the rule or source used to map one to another.

### 5.4 Usage Ledger

Provider-native usage fields must be normalized into disjoint billable buckets before pricing.

The ledger must avoid double counting inclusive totals such as `total_tokens`, `prompt_tokens`, or provider-specific counters that include child buckets.

### 5.5 Price Card

A normalized representation of pricing for one model, provider, surface, region, date, and condition set.

### 5.6 Cost Ledger

The final result returned to the user. It must include component costs, total cost, currency, source provenance, warnings, and confidence/estimate metadata.

## 6. Functional Requirements

### FR-001: Raw Provider Response Input

The package must accept a complete raw provider response object and extract usage when the response shape is known.

Required initial surfaces:

- OpenAI Responses.
- OpenAI Chat Completions.
- Anthropic Messages.
- Google Gemini API `generateContent`.
- Vertex AI Gemini.
- AWS Bedrock Converse.
- DeepSeek OpenAI-compatible chat.
- xAI Chat Completions and Responses.
- Groq OpenAI-compatible chat.
- Mistral chat completions.
- Cohere chat.
- OpenRouter chat completions.
- Hugging Face Inference Providers OpenAI-compatible chat.

### FR-002: Normalized Usage Input

The package must accept already-normalized usage when a caller does not have or does not want to pass a raw response.

Example:

```json
{
  "provider": "openai",
  "surface": "responses",
  "model": "gpt-5.4",
  "usage": {
    "input_uncached_tokens": 36,
    "input_cache_read_tokens": 0,
    "output_text_tokens": 87,
    "output_reasoning_tokens": 0
  }
}
```

### FR-003: Disjoint Usage Buckets

The package must normalize usage into disjoint buckets.

Required token buckets:

- `input_uncached_tokens`
- `input_cache_read_tokens`
- `input_cache_write_tokens`
- `input_cache_write_1h_tokens`
- `input_audio_tokens`
- `input_image_tokens`
- `input_video_tokens`
- `output_text_tokens`
- `output_reasoning_tokens`
- `output_audio_tokens`
- `output_image_tokens`
- `output_video_tokens`
- `embedding_tokens`

Required non-token buckets:

- `request_units`
- `web_search_units`
- `file_search_units`
- `code_interpreter_session_units`
- `code_interpreter_call_units`
- `computer_use_action_units`
- `tool_call_units`
- `tool_execution_seconds`
- `rerank_search_units`
- `image_generation_units`
- `video_generation_units`
- `audio_generation_units`
- `transcription_seconds`
- `endpoint_runtime_seconds`
- `endpoint_instance_hours`
- `custom_units`

### FR-004: Inclusive Field Handling

The package must know when provider fields are inclusive and must avoid pricing parent and child fields together.

Examples:

- `total_tokens` is for validation, not a billable component.
- `prompt_tokens` may include `cached_tokens`.
- Cohere `tokens` may differ from `billed_units`; billing should prefer `billed_units` when present.
- OpenRouter can report already-computed `cost` plus detailed token fields; the library must choose between validating provider-reported cost and recalculating from price data.

### FR-005: Componentized Cost Output

The package must return a componentized cost ledger.

Example:

```json
{
  "currency": "USD",
  "components": [
    {
      "name": "input_uncached",
      "quantity": 36,
      "unit": "token",
      "unit_price_usd": 0.0000025,
      "cost_usd": 0.00009,
      "source": "provider_price_card"
    },
    {
      "name": "output_text",
      "quantity": 87,
      "unit": "token",
      "unit_price_usd": 0.000015,
      "cost_usd": 0.001305,
      "source": "provider_price_card"
    }
  ],
  "total_usd": 0.001395
}
```

### FR-006: Model Alias Resolution

The package must support model aliases.

Required alias cases:

- Dated model names returned by providers.
- Provider aliases that point to a current model version.
- Azure deployment names that do not include the exact underlying model version.
- Internal company aliases.
- OpenRouter and aggregator model IDs.
- Framework-level model identifiers.

Alias resolution must be source-backed or user-configured. If a heuristic is used, the result must include a warning.

### FR-007: Exact Alias Map Before Regex

The package may use regex or suffix heuristics only after exact aliases are checked.

Recommended order:

1. User-configured exact alias.
2. Price-source exact alias.
3. Package-maintained exact alias.
4. Provider-specific safe heuristic.
5. Unknown model warning.

### FR-008: Long-Context Pricing

The package must support context-length threshold pricing.

Examples:

- Different prices above a token threshold.
- Provider data that splits models into under-threshold and over-threshold variants.
- Requests where only part of the input crosses a threshold.
- Requests where output pricing changes after a threshold.

### FR-009: Service Tier and Surface Modifiers

The package must support pricing modifiers by service tier and surface.

Required tiers and modes:

- `standard`
- `batch`
- `flex`
- `priority`
- `on_demand`
- `performance`
- `provisioned`
- `global_standard`
- `regional`
- `auto`
- `custom`

Provider-specific examples:

- OpenAI priority, flex, batch, and Responses/Chat differences.
- Azure OpenAI batch, priority, and provisioned/PTU pricing.
- Groq batch and service tiers such as performance, on-demand, flex, and auto.
- Anthropic batch and cache TTL variants.
- Google and Vertex batch and context threshold pricing.
- AWS Bedrock on-demand, batch, and provisioned throughput.
- xAI batch pricing.
- Mistral batch pricing.

### FR-010: Cache Pricing

The package must support:

- Cache read pricing.
- Cache write pricing.
- Cache write TTL pricing.
- Cache-hit/cache-miss pricing.
- Provider-specific cache discounts.
- Response cache cases where billable token counts become zero.

Provider-specific examples:

- Anthropic cache creation, cache read, 5-minute TTL, and 1-hour TTL.
- DeepSeek cache hit and cache miss input pricing.
- xAI cached input and reasoning billing.
- Groq prompt caching and batch non-stacking behavior.
- Mistral cached input at a discount.
- OpenRouter prompt cache and response cache behavior.

### FR-011: Reasoning and Thinking Cost

The package must support reasoning/thinking usage even when providers expose it differently.

Examples:

- OpenAI `output_tokens_details.reasoning_tokens`.
- xAI `completion_tokens_details.reasoning_tokens` and Responses `output_tokens_details.reasoning_tokens`.
- Gemini `thoughtsTokenCount`.
- Mistral `thinking` output chunks even if usage does not expose a distinct reasoning billable bucket.
- Provider cases where reasoning tokens are billed at output-token price rather than a separate reasoning price.

### FR-012: Multimodal Pricing

The package must support multimodal units:

- Audio input tokens.
- Audio output tokens.
- Image input tokens.
- Image output tokens.
- Video input tokens.
- Video output tokens.
- Image generation units.
- Video generation units.
- Text-to-speech output units.
- Speech-to-text duration or token units.

The library must preserve unknown units as warnings rather than silently dropping them.

### FR-013: Non-Token Tool and Feature Pricing

The package must support non-token model-adjacent charges.

Examples:

- Web search.
- File search.
- Code interpreter or tool execution units if exposed.
- Computer use actions.
- Built-in tool calls.
- Hosted tool calls.
- User-defined pass-through tool charges.
- Rerank search units.
- Embedding token units.
- Hugging Face Inference Endpoint runtime.
- Provider request fees.

Tool pricing must be modeled as generic billable components, not one-off provider hacks.

Required tool-call fields:

- Tool provider.
- Tool name.
- Tool call count.
- Tool execution duration where billed by time.
- Tool input/output units where exposed.
- Tool result cache hits where applicable.
- Whether the tool charge is provider-billed, gateway-billed, or user-defined.
- Whether the tool unit is eligible for discounts.

Required behavior:

- Preserve unrecognized tool usage as `custom_units` or structured warnings.
- Support provider-specific tool price cards such as web search, file search, code interpreter, computer use, and hosted connector/tool calls.
- Support tool charges that are per request, per call, per session, per search, per file, per GB-day, per execution-second, or pass-through USD cost.
- Support validate-vs-recalculate behavior when a provider or gateway reports a tool cost directly.

### FR-014: Custom Price Overrides

Users must be able to define custom model prices.

Overrides must support:

- Provider.
- Surface.
- Model.
- Alias.
- Region.
- Service tier.
- Unit type.
- Effective start and end dates.
- Currency.
- Source note.

### FR-015: Discount Policies

Users must be able to define discounts and markups.

Required examples:

- 4% off all OpenAI usage.
- 10% off OpenAI batch requests.
- 20% off a specific Azure deployment.
- No discount on web-search pass-through fees.
- Customer-specific markup on internal models.

Discounts must be component-aware. A global multiplier alone is not enough.

### FR-016: Discount Precedence

The package must define deterministic discount precedence.

Recommended order:

1. Base price card.
2. Provider/surface/tier modifier.
3. User price override.
4. Contract discount.
5. User markup.
6. Rounding policy.

The result must disclose all applied adjustments.

### FR-017: Point-in-Time Pricing

The package should support pricing at a requested timestamp.

Required behavior:

- Use the correct price card for `priced_at`.
- Warn when historical data is unavailable.
- Support effective start and end dates.
- Support time-window constraints where providers have time-of-day pricing.

This can be staged after the V0 schema, but the data model must support it from the beginning.

### FR-018: Price Source Provenance

Every cost result must include price-source metadata.

Required fields:

- Source name.
- Source URL or package version.
- Retrieved or generated date.
- Effective date where available.
- Whether the price was user-defined, vendored, live-fetched, inferred, or fallback.

### FR-019: Stale Price Handling

The package must detect stale price data.

Required configuration:

- Max allowed price age.
- Fail open or fail closed.
- Warnings for stale but usable data.
- Source disagreement warnings.

### FR-020: Provider-Reported Cost Validation

When a provider or gateway returns a cost field, the package must be able to:

- Return provider-reported cost.
- Recalculate cost from usage and price data.
- Compare both and report variance.

Examples:

- OpenRouter usage/cost fields.
- Vercel AI Gateway usage/cost fields.
- Hosted gateways or internal routers that report cost.

### FR-021: Framework Integration Layer

The package must support major third-party frameworks through adapters.

Required initial frameworks:

- LangChain.
- LangSmith traces.
- LlamaIndex.
- Vercel AI SDK.
- Microsoft Semantic Kernel.
- Haystack.
- AutoGen / AG2.

Framework adapters may be separate packages to keep the core lightweight.

### FR-022: LangChain Requirements

The LangChain adapter must support:

- `AIMessage.usage_metadata`.
- `response_metadata`.
- callback-collected usage such as `UsageMetadataCallbackHandler`.
- streamed final chunk aggregation.
- `ls_provider` and `ls_model_name` style metadata for LangSmith compatibility.
- provider-specific token detail buckets when available.

### FR-023: LangSmith Requirements

The LangSmith adapter/exporter must support:

- `run_type="llm"`.
- model and provider metadata.
- usage metadata.
- custom cost metadata.
- comparison between LangSmith-computed cost and this library's cost ledger where possible.

### FR-024: LlamaIndex Requirements

The LlamaIndex adapter must support:

- `TokenCountingHandler`.
- `CallbackManager` events.
- LLM response metadata.
- `LLMMetadata.model_name`.
- `additional_kwargs` or raw provider response fields.
- LLM and embedding calls.

### FR-025: Vercel AI SDK Requirements

The Vercel AI SDK adapter must support:

- `generateText`.
- `streamText`.
- `onFinish`.
- `result.usage`.
- `result.totalUsage`.
- provider metadata.
- model/provider telemetry attributes.
- `wrapLanguageModel` middleware.
- multi-step agent/tool calls.

### FR-026: Semantic Kernel Requirements

The Semantic Kernel adapter must support:

- kernel filters.
- function invocation hooks.
- service IDs and model IDs.
- response metadata.
- OpenTelemetry metrics or traces where token usage is exposed there rather than directly on the response.
- Azure model-version ambiguity via explicit override fields.

### FR-027: Haystack Requirements

The Haystack adapter must support:

- generator output `meta`.
- `ChatMessage` metadata.
- pipeline tracing.
- streaming callbacks.
- provider-specific generator metadata.

### FR-028: AutoGen / AG2 Requirements

The AutoGen adapter must support:

- wrapper-level actual and total usage summaries.
- agent-level usage summaries.
- `gather_usage_summary`.
- cached vs actual usage.
- model config lists.
- custom model prices already supplied to AutoGen, when available.
- Azure model-version ambiguity via explicit overrides.

### FR-029: Streaming Support

The package must support streaming responses.

Required behavior:

- Calculate only after final usage metadata is available.
- Aggregate multi-chunk usage where frameworks provide per-chunk usage.
- Avoid charging partial streams twice.
- Support stream abort warnings when final usage is missing.

### FR-030: Multi-Step Agent Calls

The package must support a single logical agent run containing multiple model calls.

Required output:

- Per-call cost ledgers.
- Per-provider totals.
- Per-model totals.
- Whole-run total.
- Ability to attach user metadata such as tenant, customer, feature, trace ID, or request ID.

### FR-031: Aggregation

The package must support aggregation without becoming a database.

In-memory aggregation must support:

- Sum by provider.
- Sum by model.
- Sum by surface.
- Sum by component.
- Sum by user-defined tags.

Persistent aggregation is optional and should live outside the core.

### FR-032: Currency and Precision

The package must use decimal-safe arithmetic.

Required behavior:

- Avoid binary floating point for internal cost calculations.
- Return costs with enough precision for small requests.
- Allow user-configured rounding at display or export boundaries.
- Store canonical prices in unit-safe form.

### FR-033: Error and Warning Model

The package must return structured warnings instead of hiding uncertainty.

Required warning codes:

- `unknown_provider`
- `unknown_surface`
- `unknown_model`
- `alias_inferred`
- `price_not_found`
- `price_stale`
- `price_source_disagreement`
- `usage_field_ignored`
- `inclusive_usage_ambiguous`
- `component_unpriced`
- `service_tier_unsupported`
- `long_context_rule_missing`
- `discount_not_applied`
- `stream_usage_missing`
- `historical_price_missing`

### FR-034: Strict Mode

The package must support strict mode.

In strict mode, the package should fail rather than estimate when:

- Model is unknown.
- Price is stale.
- A billable component is unpriced.
- Alias resolution is inferred.
- Surface or tier is ambiguous.

### FR-035: Compatibility Mode

The package should support compatibility mode for easy adoption.

In compatibility mode, the package may:

- Estimate with warnings.
- Use provider aliases.
- Use newest known price for unknown historical date.
- Ignore unpriced zero-quantity fields.

### FR-036: API Ergonomics

The package must expose multiple API levels.

Required APIs:

1. Easy raw-response API.
2. Normalized usage API.
3. Framework adapter API.
4. Batch aggregation API.
5. Price source and override configuration API.

Example TypeScript:

```ts
const cost = costLedger.fromResponse(response, {
  provider: "openai",
  surface: "responses"
});
```

Example Python:

```py
cost = cost_ledger.from_response(
    response,
    provider="openai",
    surface="responses",
)
```

### FR-037: Framework Packages

Framework adapters should be optional packages where dependency weight matters.

Example package split:

- `runcost-core`
- `runcost-openai`
- `runcost-langchain`
- `runcost-vercel-ai`
- `runcost-llamaindex`
- `runcost-semantic-kernel`

The exact names can change, but the dependency boundary should stay explicit.

### FR-038: Multi-Language Support

The project must be designed to ship in multiple languages.

Initial languages:

- TypeScript/JavaScript.
- Python.

Planned languages:

- Go.

The core behavior must be driven by shared schemas and shared fixtures so language implementations do not drift.

### FR-039: Shared Conformance Fixtures

The repository must include shared JSON fixtures for:

- Raw provider responses.
- Framework metadata objects.
- Normalized usage ledgers.
- Price cards.
- Discount policies.
- Expected cost ledgers.
- Expected warnings.

Each language package must run the same fixture suite.

### FR-040: Public Schema

The package must publish schemas for:

- `UsageLedger`.
- `PriceCard`.
- `PriceSource`.
- `DiscountPolicy`.
- `CostLedger`.
- `CostWarning`.
- `ProviderResponseFixture`.

JSON Schema should be the canonical interchange format.

## 7. Provider Requirements

### 7.1 OpenAI

Required surfaces:

- Responses API.
- Chat Completions.
- Batch.

Required usage fields:

- `input_tokens`.
- `input_tokens_details.cached_tokens`.
- `output_tokens`.
- `output_tokens_details.reasoning_tokens`.
- `prompt_tokens`.
- `prompt_tokens_details.cached_tokens`.
- `completion_tokens`.
- `completion_tokens_details.reasoning_tokens`.

Required pricing dimensions:

- Input.
- Cached input.
- Output.
- Reasoning.
- Batch.
- Flex.
- Priority.
- Long-context variants where applicable.

### 7.2 Azure OpenAI

Required surfaces:

- Azure OpenAI chat and responses-compatible APIs where available.
- Batch.
- Provisioned throughput / PTU.
- Priority processing.

Required usage fields:

- `prompt_tokens`.
- `completion_tokens`.
- `total_tokens`.
- `prompt_tokens_details.cached_tokens`.
- `completion_tokens_details.reasoning_tokens`.

Required pricing dimensions:

- Region.
- Deployment.
- Input.
- Cached input.
- Output.
- Batch discount.
- Provisioned/PTU.
- Priority.

Special requirement:

- Azure deployment names may not include exact underlying model versions. The library must support explicit deployment-to-model mapping.

### 7.3 Anthropic

Required surfaces:

- Messages API.
- Batch.

Required usage fields:

- `input_tokens`.
- `output_tokens`.
- `cache_creation_input_tokens`.
- `cache_read_input_tokens`.

Required pricing dimensions:

- Input.
- Output.
- Cache write.
- Cache read.
- Cache TTL, including 5-minute and 1-hour behavior where supported.
- Batch.
- Long-context variants where applicable.

### 7.4 Google Gemini API

Required surfaces:

- Gemini API `generateContent`.
- Batch where supported.

Required usage fields:

- `promptTokenCount`.
- `cachedContentTokenCount`.
- `thoughtsTokenCount`.
- `candidatesTokenCount`.
- `totalTokenCount`.

Required pricing dimensions:

- Input.
- Output.
- Cached input.
- Thinking.
- Long-context thresholds.
- Batch.
- Multimodal units.

### 7.5 Vertex AI

Required surfaces:

- Vertex AI Gemini.
- Batch prediction where supported.

Required pricing dimensions:

- Region.
- API surface.
- Input.
- Output.
- Cached input.
- Thinking.
- Long-context thresholds.
- Batch.
- Multimodal units.

Special requirement:

- Vertex and Gemini API pricing must not be assumed identical without a source-backed rule.

### 7.6 AWS Bedrock

Required surfaces:

- Converse.
- InvokeModel.
- Batch inference.
- Provisioned throughput.

Required usage fields:

- `inputTokens`.
- `outputTokens`.
- `totalTokens`.
- cache read/write token fields where returned by the selected model and API.

Required pricing dimensions:

- AWS region.
- Bedrock surface.
- Underlying model provider.
- Input.
- Output.
- Prompt cache.
- Batch.
- Provisioned throughput.

Special requirement:

- The library must price Bedrock as a billing surface, not simply map to public Anthropic, Mistral, Meta, or other provider prices.

### 7.7 DeepSeek

Required surfaces:

- OpenAI-compatible chat.

Required pricing dimensions:

- Cache hit input.
- Cache miss input.
- Output.
- Time-window or off-peak pricing where active.

### 7.8 xAI

Required surfaces:

- Chat Completions.
- Responses API.
- Batch.

Required usage fields:

- `prompt_tokens`.
- `completion_tokens`.
- `total_tokens`.
- `prompt_tokens_details.cached_tokens`.
- `prompt_tokens_details.text_tokens`.
- `prompt_tokens_details.audio_tokens`.
- `prompt_tokens_details.image_tokens`.
- `completion_tokens_details.reasoning_tokens`.
- `input_tokens`.
- `output_tokens`.
- `input_tokens_details.cached_tokens`.
- `output_tokens_details.reasoning_tokens`.

Required pricing dimensions:

- Input.
- Cached input.
- Output.
- Reasoning.
- Batch.
- Multimodal components.

### 7.9 Groq

Required surfaces:

- OpenAI-compatible chat completions.
- Batch.

Required usage fields:

- `prompt_tokens`.
- `completion_tokens`.
- `total_tokens`.
- `prompt_tokens_details.cached_tokens`.
- timing fields should be preserved as metadata, not priced by default.

Required pricing dimensions:

- Input.
- Output.
- Cached input if billable.
- Batch.
- Service tiers such as performance, on-demand, flex, and auto.

Special requirement:

- Groq prompt caching and batch discount interaction must be modeled explicitly, including cases where discounts do not stack.

### 7.10 Mistral

Required surfaces:

- Chat completions.
- Batch.

Required usage fields:

- `prompt_tokens`.
- `completion_tokens`.
- `total_tokens`.
- `prompt_tokens_details.cached_tokens`.

Required pricing dimensions:

- Input.
- Output.
- Cached input.
- Batch.
- Reasoning/thinking output metadata when present.

### 7.11 Cohere

Required surfaces:

- Chat.
- Rerank.
- Embeddings.

Required usage fields:

- `billed_units.input_tokens`.
- `billed_units.output_tokens`.
- `tokens.input_tokens`.
- `tokens.output_tokens`.

Required pricing dimensions:

- Generative input/output tokens.
- Embedding tokens.
- Rerank search units.

Special requirement:

- Prefer `billed_units` over raw `tokens` for cost calculations when both are present.

### 7.12 Hugging Face Inference Providers

Required surfaces:

- OpenAI-compatible chat completions.
- Provider-routed inference.

Required usage fields:

- `prompt_tokens`.
- `completion_tokens`.
- `total_tokens`.
- streaming usage when `include_usage` is enabled.

Required pricing dimensions:

- Provider-routed pass-through pricing.
- Monthly credits where relevant.
- BYO provider key mode where Hugging Face is not the billing source.

Special requirement:

- The library must record whether Hugging Face or the underlying provider is the billing source.

### 7.13 Hugging Face Inference Endpoints

Required pricing model:

- Endpoint runtime.
- Instance type.
- Replica count.
- Initialization/running time.
- Autoscaling windows where available.

Special requirement:

- This is infrastructure-time billing, not token billing. It should use runtime buckets such as `endpoint_instance_hours`.

### 7.14 OpenRouter

Required surfaces:

- Chat completions.
- Generation stats endpoint where needed for post-hoc usage.

Required usage and cost fields:

- `prompt_tokens`.
- `completion_tokens`.
- `total_tokens`.
- `prompt_tokens_details.cached_tokens`.
- `prompt_tokens_details.cache_write_tokens`.
- `prompt_tokens_details.audio_tokens`.
- `prompt_tokens_details.video_tokens`.
- `completion_tokens_details.reasoning_tokens`.
- `completion_tokens_details.audio_tokens`.
- `completion_tokens_details.image_tokens`.
- `cost`.
- `cost_details`.
- `is_byok`.

Required pricing dimensions:

- Native provider token counts.
- Cached input.
- Cache write.
- Reasoning.
- Response caching.
- BYOK vs OpenRouter-billed mode.

Special requirement:

- If OpenRouter returns provider-reported cost, the package should support validate-vs-recalculate mode.

### 7.15 Custom and Internal Providers

The package must support providers unknown to the library when users supply:

- Price cards.
- Usage ledgers.
- Aliases.
- Extractors or field maps.

## 8. Price Data Requirements

### PDR-001: Source Adapters

The package should support source adapters for:

- Portkey Models.
- LiteLLM model pricing data.
- Simon Willison `llm-prices` current and historical JSON.
- Helicone `@helicone-package/cost`.
- OpenRouter `/api/v1/models`.
- models.dev.
- User-defined local JSON/YAML.
- Optional live provider pricing sources.

### PDR-002: Vendored Data

The package may vendor a known-good price snapshot.

Vendored data must include:

- Source URL.
- Source version or retrieval date.
- Generation script version.
- License notes.

### PDR-003: Live Refresh

The package should support refreshing price data where source licenses and stability permit.

Refresh must be explicit by default. The package should not unexpectedly call the network during normal cost calculation unless configured to do so.

### PDR-004: Source Conflict Handling

When multiple sources disagree, the package must:

- Choose a deterministic source according to configured priority.
- Record the disagreement.
- Expose both values in debug output where possible.

### PDR-005: Simon Willison `llm-prices` Adapter

The package should support `llm-prices` as a simple source adapter.

Required behavior:

- Read `current-v1.json`.
- Read `historical-v1.json`.
- Map `vendor` to provider.
- Map `id` to model alias/source model ID.
- Map `input`, `output`, and `input_cached` from per-million-token USD prices to canonical unit prices.
- Preserve `updated_at`.
- Preserve `from_date` inclusive and `to_date` exclusive historical semantics.
- Warn that unsupported components such as cache write, reasoning, batch, service tier, multimodal, and request fees are not present in this source.

### PDR-006: Helicone Cost Adapter

The package should support Helicone's cost package as a reference source or compatibility target.

Required behavior:

- Read model/provider registry metadata where licensing and packaging permit.
- Preserve provider model IDs.
- Preserve endpoint and deployment overrides.
- Preserve PTB/BYOK billing-source distinctions where available.
- Map Helicone pricing tiers into canonical price cards.
- Map component costs for input, output, cached input, cache write 5m, cache write 1h, thinking, web search, request, and modality-specific components.
- Preserve version and date-range metadata when present.

### PDR-007: OpenRouter Models Adapter

The package should support OpenRouter's model catalog endpoint.

Required behavior:

- Read `/api/v1/models`.
- Preserve model ID and canonical slug.
- Preserve context length and supported parameters where useful.
- Convert pricing fields such as prompt, completion, cache write/read, reasoning, image, and request-like units where present.
- Preserve BYOK or provider-routing metadata where exposed by related OpenRouter usage endpoints.
- Treat OpenRouter as a billing provider/surface, not only as an alias for the routed provider.
- Warn when pricing is current-only and historical semantics are unavailable.

## 9. API Requirements

### 9.1 TypeScript API Sketch

```ts
import { CostLedger } from "runcost";

const ledger = new CostLedger({
  priceSources: ["portkey", "litellm"],
  discounts: [
    { provider: "openai", multiplier: "0.96" }
  ]
});

const cost = ledger.fromResponse(response, {
  provider: "openai",
  surface: "responses",
  serviceTier: "priority",
  pricedAt: new Date()
});
```

### 9.2 Python API Sketch

```py
from runcost import CostLedger

ledger = CostLedger(
    price_sources=["portkey", "litellm"],
    discounts=[{"provider": "openai", "multiplier": "0.96"}],
)

cost = ledger.from_response(
    response,
    provider="openai",
    surface="responses",
    service_tier="priority",
)
```

### 9.3 Normalized API Sketch

```json
{
  "provider": "cohere",
  "surface": "chat",
  "model": "command-a",
  "usage": {
    "input_uncached_tokens": 1000,
    "output_text_tokens": 200
  }
}
```

### 9.4 Framework API Sketch

```py
from runcost.langchain import cost_callback

with cost_callback() as costs:
    result = chain.invoke("Summarize this")

print(costs.total_usd)
```

```ts
import { withCostLedger } from "runcost/vercel-ai";

const model = withCostLedger(openai("gpt-5.4"), {
  provider: "openai",
  surface: "vercel_ai_sdk.generate_text"
});
```

## 10. Output Requirements

### 10.1 Cost Ledger Fields

Required output:

- `provider`.
- `surface`.
- `model_requested`.
- `model_returned`.
- `model_billed`.
- `currency`.
- `components`.
- `total`.
- `price_sources`.
- `applied_modifiers`.
- `applied_discounts`.
- `warnings`.
- `metadata`.

### 10.2 Component Fields

Each component must include:

- `name`.
- `quantity`.
- `unit`.
- `unit_price`.
- `cost`.
- `currency`.
- `source`.
- `modifier`.
- `discount`.
- `notes`.

### 10.3 Debug Mode

Debug mode must expose:

- Raw extracted usage fields.
- Normalization decisions.
- Alias resolution path.
- Price-card lookup path.
- Discount matching path.
- Dropped or ignored fields.

## 11. Configuration Requirements

### 11.1 Provider Defaults

Users must be able to configure defaults:

- Default provider.
- Default surface.
- Default service tier.
- Default region.
- Default strictness.
- Default price source priority.

### 11.2 Aliases

Users must be able to configure:

- Model aliases.
- Deployment aliases.
- Provider aliases.
- Surface aliases.
- Framework model aliases.

### 11.3 Discounts

Users must be able to configure discounts:

- Globally.
- By provider.
- By surface.
- By model.
- By service tier.
- By component.
- By date range.
- By custom tag.

### 11.4 Custom Extractors

Users should be able to register custom extractors for:

- Internal gateways.
- New provider response shapes.
- Framework-specific metadata.

Custom extractors should emit normalized usage ledgers, not prices.

## 12. Non-Functional Requirements

### NFR-001: Lightweight

The core package must have minimal dependencies.

Guidelines:

- No provider SDK dependencies in core.
- No framework dependencies in core.
- Optional integrations in separate packages.
- No database dependency.

### NFR-002: Fast

Cost calculation should be effectively instant for a single response.

Target:

- Less than 1 ms for warm in-memory price lookup in typical cases.
- Less than 10 ms for complex multi-source lookup without network calls.

### NFR-003: Deterministic

Given the same input, price data, and configuration, the package must return the same result.

### NFR-004: No Network by Default

The package must not call the network during normal calculation unless explicitly configured.

### NFR-005: Decimal Safety

The package must avoid floating-point drift in internal money calculations.

### NFR-006: Thread and Async Safety

The package must be safe to use in concurrent request handlers.

### NFR-007: Privacy

The package must not require prompt or completion text for cost calculation unless a provider or framework only exposes usage through a text-counting fallback.

### NFR-008: Testability

Every extractor, alias resolver, price lookup, and discount rule must be unit-testable without network access.

### NFR-009: Maintainability

Provider-specific logic must be isolated from the core calculation engine.

### NFR-010: Clear Failure Modes

The package must fail loudly in strict mode and warn clearly in compatibility mode.

## 13. Architecture Requirements

### 13.1 Layers

Recommended layers:

1. Raw extractors.
2. Framework adapters.
3. Usage ledger normalization.
4. Alias resolver.
5. Price source resolver.
6. Modifier engine.
7. Discount engine.
8. Cost calculator.
9. Aggregator.
10. Exporters.

### 13.2 Core Independence

The core calculator must not depend on:

- OpenAI SDK.
- Anthropic SDK.
- LangChain.
- LlamaIndex.
- Vercel AI SDK.
- HTTP clients.
- Databases.

### 13.3 Provider Modules

Provider modules may include:

- Raw response extractors.
- Provider-specific alias rules.
- Provider-specific warnings.
- Provider-specific surface/tier metadata.

They should not include unrelated business logic.

### 13.4 Framework Modules

Framework modules may include:

- Callbacks.
- Middleware.
- Event handlers.
- Telemetry parsers.
- Convenience wrappers.

They should emit normalized cost inputs to the core.

## 14. Testing Requirements

### TR-001: Golden Fixtures

Every supported provider/surface must have golden raw response fixtures.

### TR-002: Hard Billing Fixtures

The following hard cases must be tested:

- OpenAI Responses with cached input, reasoning, priority tier, and dated alias.
- Anthropic Messages with cache creation, cache read, 1-hour TTL, and batch.
- Gemini/Vertex with cached content, thinking tokens, and long-context threshold.
- Bedrock Converse with Bedrock-specific billing surface.
- DeepSeek cache hit/miss and time-window pricing.
- xAI cached input and reasoning.
- Groq batch and service tier interaction.
- Mistral cached input and batch.
- Cohere `billed_units`.
- Hugging Face Inference Endpoint runtime pricing.
- OpenRouter provider-reported cost validation.
- Custom price override.
- Provider discount overlay.

### TR-003: Framework Fixtures

Framework tests must include:

- LangChain `AIMessage.usage_metadata`.
- LangChain callback totals.
- LlamaIndex `TokenCountingHandler`.
- Vercel AI SDK `result.usage` and `result.totalUsage`.
- Semantic Kernel telemetry-style usage.
- Haystack generator metadata.
- AutoGen wrapper and agent usage summaries.

### TR-004: Cross-Language Conformance

All language implementations must pass the same JSON fixture suite.

### TR-005: Property Tests

The calculator should include property tests:

- Component sum equals total.
- Zero quantities cost zero.
- Discounts do not apply to excluded components.
- Strict mode fails on unknown required prices.
- Compatibility mode warns on unknown optional prices.

## 15. Documentation Requirements

Docs must include:

- Quick start.
- Direct provider examples.
- Framework integration examples.
- Custom pricing examples.
- Discount policy examples.
- Strict vs compatibility mode.
- Price source provenance.
- Known limitations.
- Provider support matrix.
- Framework support matrix.
- Invoice-exactness caveats.

## 16. Release Plan

### V0: Core and Two Providers

Scope:

- Core schemas.
- Cost calculator.
- Alias resolver.
- Price card loader.
- OpenAI Responses and Chat Completions.
- Anthropic Messages.
- Custom price overrides.
- Provider discount policies.
- Shared fixtures.
- TypeScript and Python packages.

### V0.1: Framework Adapters

Scope:

- LangChain.
- Vercel AI SDK.
- LlamaIndex.

### V0.2: More Providers

Scope:

- Google Gemini API.
- Vertex AI.
- AWS Bedrock.
- xAI.
- DeepSeek.
- Groq.
- Mistral.
- Cohere.
- OpenRouter.

### V0.3: Infrastructure and Aggregators

Scope:

- Hugging Face Inference Providers.
- Hugging Face Inference Endpoints.
- Semantic Kernel.
- Haystack.
- AutoGen.
- Provider-reported cost validation.

### V1: Stable Cross-Language Contract

Scope:

- Stable JSON schemas.
- TypeScript package.
- Python package.
- Go package.
- Fixture conformance suite.
- Price-source adapter system.
- Historical pricing support.

## 17. Stretch Requirements

### SR-001: Pricing Scrapers and Monitors

Build automated monitors for provider pricing pages only after the core schema is stable.

Required behavior:

- Detect pricing page changes.
- Compare against current normalized price data.
- Produce a proposed data diff.
- Open or prepare a GitHub PR.
- Include source citations and confidence notes.
- Never auto-publish new prices without review.

### SR-002: Agent-Assisted Price Updates

Use agents to propose updates, but require deterministic validation:

- Schema validation.
- Fixture tests.
- Source URL checks.
- Human review.

### SR-003: Invoice Reconciliation

Add utilities to compare:

- Provider invoice exports.
- Provider-reported cost.
- Library-calculated cost.
- Internal allocation totals.

### SR-004: OpenTelemetry Export

Export cost ledgers as trace/span attributes for frameworks and observability systems.

### SR-005: Browserless Pricing Audit

Support command-line audits:

```bash
runcost audit-prices --provider openai --source portkey --source litellm
```

## 18. Acceptance Criteria

The project is ready for initial public use when:

- A raw OpenAI Responses object can be converted to a componentized cost ledger.
- A raw Anthropic Messages object can be converted to a componentized cost ledger.
- Custom price overrides work for unknown models.
- A 4% OpenAI provider discount works and is visible in output.
- Cached input is not double counted.
- Reasoning tokens are handled explicitly.
- Unknown model behavior differs correctly in strict and compatibility mode.
- Shared fixtures run in both TypeScript and Python.
- Framework integration examples exist for LangChain and Vercel AI SDK.
- Every returned cost includes source provenance and warnings.

## 19. Open Questions

1. Should the reference implementation start in TypeScript, Python, or both at once?
2. Should Portkey Models or LiteLLM be the first default upstream price source?
3. Should the package ever fetch live prices at runtime, or only through explicit update commands?
4. Should invoice-reconciliation support be in core or a separate package?
5. What should the default strictness be for production environments?
6. Should OpenRouter provider-reported cost be treated as authoritative by default?
7. How should region-specific pricing be represented for Azure, Vertex, Bedrock, and infrastructure providers?
8. What is the minimum acceptable historical-pricing support for V1?

## 20. Source Index

Market baselines:

- LiteLLM: https://github.com/BerriAI/litellm
- LiteLLM pricing map: https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json
- Portkey Models: https://github.com/Portkey-AI/models
- Portkey pricing data: https://configs.portkey.ai/pricing/openai.json
- Simon Willison llm-prices: https://github.com/simonw/llm-prices
- llm-prices current JSON: https://www.llm-prices.com/current-v1.json
- llm-prices historical JSON: https://www.llm-prices.com/historical-v1.json
- Helicone cost package: https://github.com/Helicone/helicone/tree/main/packages/cost
- genai-prices: https://github.com/pydantic/genai-prices
- ai-sdk-cost-calculator: https://www.npmjs.com/package/ai-sdk-cost-calculator
- TokenLens: https://www.npmjs.com/package/tokenlens
- models.dev: https://models.dev/api.json

Provider docs:

- OpenAI pricing: https://openai.com/api/pricing/
- OpenAI docs: https://platform.openai.com/docs
- Azure OpenAI pricing: https://azure.microsoft.com/en-us/pricing/details/azure-openai/
- Azure OpenAI prompt caching: https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/prompt-caching
- Anthropic pricing: https://docs.anthropic.com/en/docs/about-claude/pricing
- Anthropic prompt caching: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- Google Gemini pricing: https://ai.google.dev/gemini-api/docs/pricing
- Google Gemini generate content API: https://ai.google.dev/api/generate-content
- Vertex AI pricing: https://cloud.google.com/vertex-ai/generative-ai/pricing
- AWS Bedrock pricing: https://aws.amazon.com/bedrock/pricing/
- AWS Bedrock Converse API: https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html
- AWS Bedrock token usage: https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_TokenUsage.html
- DeepSeek pricing: https://api-docs.deepseek.com/quick_start/pricing
- xAI pricing: https://docs.x.ai/developers/pricing
- xAI prompt caching usage and pricing: https://docs.x.ai/developers/advanced-api-usage/prompt-caching/usage-and-pricing
- Groq docs: https://console.groq.com/docs
- Groq prompt caching: https://console.groq.com/docs/prompt-caching
- Groq batch: https://console.groq.com/docs/batch
- Groq service tiers: https://console.groq.com/docs/service-tiers
- Mistral chat completions: https://docs.mistral.ai/studio-api/conversations/chat-completion
- Mistral prompt caching: https://docs.mistral.ai/studio-api/conversations/advanced/prompt-caching
- Mistral batch processing: https://docs.mistral.ai/studio-api/batch-processing
- Cohere pricing behavior: https://docs.cohere.com/docs/how-does-cohere-pricing-work
- Cohere pricing: https://cohere.com/pricing
- Hugging Face Inference Providers pricing: https://huggingface.co/docs/inference-providers/en/pricing
- Hugging Face chat completion: https://huggingface.co/docs/inference-providers/tasks/chat-completion
- Hugging Face Inference Endpoints pricing: https://huggingface.co/docs/inference-endpoints/pricing
- OpenRouter API reference: https://openrouter.ai/docs/api-reference/overview
- OpenRouter models API: https://openrouter.ai/docs/api/api-reference/models/get-models
- OpenRouter live models endpoint: https://openrouter.ai/api/v1/models
- OpenRouter usage accounting: https://openrouter.ai/docs/cookbook/administration/usage-accounting
- OpenRouter prompt caching: https://openrouter.ai/docs/guides/best-practices/prompt-caching
- OpenRouter response caching: https://openrouter.ai/docs/guides/features/response-caching

Framework docs:

- LangChain messages: https://docs.langchain.com/oss/javascript/langchain/messages
- LangChain Python models and callbacks: https://docs.langchain.com/oss/python/langchain/models
- LangSmith cost tracking: https://docs.langchain.com/langsmith/cost-tracking
- LangSmith metadata parameters: https://docs.langchain.com/langsmith/ls-metadata-parameters
- LlamaIndex callbacks: https://docs.llamaindex.ai/en/stable/api_reference/callbacks/
- LlamaIndex token counting handler: https://docs.llamaindex.ai/en/v0.10.33/examples/callbacks/TokenCountingHandler/
- LlamaIndex LLM API reference: https://docs.llamaindex.ai/en/stable/api_reference/llms/
- Vercel AI SDK generating text: https://ai-sdk.dev/docs/ai-sdk-core/generating-text
- Vercel AI SDK telemetry: https://ai-sdk.dev/docs/ai-sdk-core/telemetry
- Vercel AI SDK middleware: https://ai-sdk.dev/docs/ai-sdk-core/middleware
- Semantic Kernel filters: https://learn.microsoft.com/en-us/semantic-kernel/concepts/enterprise-readiness/filters
- Semantic Kernel observability: https://learn.microsoft.com/en-us/semantic-kernel/concepts/enterprise-readiness/observability/
- Haystack tracing: https://docs.haystack.deepset.ai/v2.9/docs/tracing
- Haystack ChatMessage: https://docs.haystack.deepset.ai/v2.9/docs/chatmessage
- AutoGen usage tracking: https://autogenhub.github.io/autogen/docs/notebooks/agentchat_cost_token_tracking/
- AutoGen usage utilities: https://autogenhub.github.io/autogen/docs/reference/agentchat/utils/
