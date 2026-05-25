---
title: RunCost Market Gap Validation
date: 2026-05-25
type: report
status: draft
---

# RunCost Market Gap Validation

Research date: 2026-05-24

## Executive Decision

There is a real product gap, but the right project is not a new pricing database from scratch.

The market already has strong ingredients:

- LiteLLM has the broadest model/pricing map and a mature Python cost calculator.
- Portkey Models has an open pricing API with unusually good coverage of hard billing dimensions.
- Simon Willison's `llm-prices` has a clean current/historical JSON schema for simple input/output/cached-input prices.
- Helicone's cost package has a TypeScript model registry and component cost breakdowns shaped by real observability and billing flows.
- OpenRouter's `/api/v1/models` endpoint exposes live OpenRouter model catalog and pricing metadata.
- `genai-prices` has the strongest small Python pricing model, including conditional and point-in-time pricing.
- `ai-sdk-cost-calculator` has the closest Node developer ergonomics and component-level cost return shape.
- TokenLens / models.dev has a large model catalog and useful alias/context metadata.

The unsolved wedge is a lightweight, language-portable "cost ledger" library:

- Accept raw responses or normalized usage from major SDKs.
- Resolve provider, model, alias, API surface, service tier, and pricing date.
- Return a componentized cost breakdown with no double counting.
- Support cached input, cache creation/write, cache TTL variants, reasoning/thinking, long-context tiers, batch/flex/priority tiers, multimodal units, custom prices, and discount overlays.
- Be packaged as a small core that can be reused from Python, Node, Go, and eventually other languages.

Recommended gate: build a thin normalization and calculation layer on top of existing price data sources, with Portkey Models and LiteLLM as first-class upstream references. Do not start with scraping, hosted observability, or a full vendor-priced database unless upstream data gaps force it.

## Thesis

LLM and agent developers increasingly need a simple way to answer: "What did this API call just cost, by component?"

The target user does not want a gateway, dashboard, or full observability stack. They want one or two lines near their SDK call:

```ts
const cost = priceLLM.response(response, { provider: "openai", surface: "responses" });
```

and a reliable ledger:

```json
{
  "provider": "openai",
  "model": "gpt-5.4",
  "components": {
    "input": 0.00009,
    "input_cache_read": 0,
    "output": 0.001305,
    "output_reasoning": 0
  },
  "total": 0.001395,
  "currency": "USD",
  "warnings": []
}
```

## Anti-Thesis

The project should not be built if any existing library already provides all of the following in a small embeddable package:

- Major provider support across OpenAI, Anthropic, Google Gemini, Vertex AI, AWS Bedrock, xAI, DeepSeek, Mistral, Groq, Cohere, OpenRouter, and related aggregators.
- Raw response extraction from current official SDK response shapes.
- Componentized cost by input, cached input read/write, output, reasoning/thinking, and non-token units.
- Model alias and dated model resolution.
- Long-context threshold pricing.
- Service tier and surface modifiers such as batch, flex, priority, provisioned, or provider-specific alternatives.
- Custom model prices and provider/model/surface discount overlays.
- Point-in-time pricing or at least a path to it.
- A portable data model that can be repackaged across Python, Node, Go, and other languages.

No mainstream package met that full bar in this validation.

## Product Gap

Existing tools cluster into four categories:

1. Broad pricing data maps: LiteLLM, Portkey Models, models.dev.
2. Simple current/historical pricing feeds: Simon Willison `llm-prices`.
3. Observability-backed cost registries: Helicone `@helicone-package/cost`.
4. Provider or aggregator live catalogs: OpenRouter `/api/v1/models`.
5. Python calculators: LiteLLM, `genai-prices`, AgentOps `tokencost`, `llm-tokencost`.
6. Node/AI SDK calculators: `ai-sdk-cost-calculator`, TokenLens, `tokentally`, `ai-cost-meter`, `token-costs`.
7. Hosted observability/gateways: Langfuse, Helicone, Portkey Gateway.

The gap sits between categories 1 and 3:

- More accurate and provider-complete than small SDK helpers.
- Smaller and more embeddable than LiteLLM or hosted observability stacks.
- More componentized and billing-aware than model catalogs.
- More portable than Python-only or Vercel AI SDK-only libraries.

## Evaluation Criteria

The validation scored candidates on these capabilities:

- Provider coverage and maintenance freshness.
- Raw response extraction for official SDK shapes.
- Model alias resolution, including dated aliases.
- Input/output cost calculation.
- Cached input read/write and cache TTL pricing.
- Reasoning/thinking token pricing.
- Long-context or tiered pricing.
- Service tier, batch, flex, priority, or surface-specific modifiers.
- Custom pricing and discount overlays.
- Point-in-time pricing.
- Multimodal and non-token units.
- Lightweight embeddability.
- Multi-language portability.

See `RESULTS_MATRIX.md` for the full table.

## Deep Candidate Findings

### LiteLLM

Evidence:

- Repository: https://github.com/BerriAI/litellm
- Pricing map: https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json
- Cost calculator source: https://github.com/BerriAI/litellm/blob/main/litellm/litellm_core_utils/llm_cost_calc/utils.py
- PyPI: https://pypi.org/project/litellm/

LiteLLM is the strongest existing pricing and cost-calculation reference.

Observed capabilities:

- Very broad provider/model coverage.
- Rich pricing keys for input, output, cache creation, cache read, reasoning output, long-context thresholds, batch, flex, and priority.
- Explicit support for OpenAI `/v1/responses`, chat completions, batch, and many non-OpenAI endpoints.
- Cost calculation code handles cache read/write, long-context threshold pricing, service tier price key selection, and reasoning token pricing.

Where it falls short for this project:

- It is a large Python gateway/client ecosystem, not a tiny language-neutral cost kernel.
- The public user-facing cost API is not centered on a provider-neutral component ledger.
- It does not try to be a raw-response parser package for every official SDK response object.
- Custom organization discounts and override policies are not the primary abstraction.
- Multi-language packaging would require a new layer around its data model.

Verdict: use as an upstream reference and compatibility oracle. Do not duplicate its pricing map by hand.

### Simon Willison `llm-prices`

Evidence:

- Repository: https://github.com/simonw/llm-prices
- Current prices: https://www.llm-prices.com/current-v1.json
- Historical prices: https://www.llm-prices.com/historical-v1.json

`llm-prices` is a deliberately simple pricing feed.

Observed capabilities:

- Public current and historical JSON files.
- Simple schema with `id`, `vendor`, `name`, `input`, `output`, and `input_cached`.
- Prices are expressed per million tokens in USD, which is convenient for humans and easy to normalize.
- Historical entries use inclusive `from_date` and exclusive `to_date` semantics.
- During validation, `current-v1.json` reported `updated_at: 2026-05-19`, 112 current prices, 10 vendors, and 54 models with cached input pricing.

Where it falls short:

- It only covers input, output, and cached input.
- It does not model cache writes, cache TTLs, reasoning/thinking, service tiers, batch/flex/priority, multimodal units, request fees, provider-specific surfaces, or discounts.
- It is a pricing feed, not a calculator or raw response extractor.
- Repository metadata did not expose a license through the GitHub API during this pass, so license suitability should be checked before vendoring.

Verdict: excellent simple baseline and historical-pricing reference. Add a source adapter, but do not treat it as sufficient for exact component accounting.

### Helicone `@helicone-package/cost`

Evidence:

- Repository path: https://github.com/Helicone/helicone/tree/main/packages/cost
- Package README: https://github.com/Helicone/helicone/blob/main/packages/cost/README.md
- Cost calculation: https://github.com/Helicone/helicone/blob/main/packages/cost/models/calculate-cost.ts
- Usage types: https://github.com/Helicone/helicone/blob/main/packages/cost/usage/types.ts

Helicone's cost package is a strong TypeScript reference for a componentized registry and calculator.

Observed capabilities:

- Model registry with provider model IDs, endpoint configs, deployments, versions, context limits, supported parameters, and PTB/BYOK concepts.
- Component breakdown fields for input, output, cached input, 5-minute cache write, 1-hour cache write, thinking, web search, request, and modality-specific image/audio/video/file input/cached/output.
- Pricing tiers with thresholds and provider-specific threshold logic for Vertex, Google AI Studio, Anthropic, xAI, and defaults.
- Legacy provider mappings cover providers including OpenAI, Anthropic, Azure, AWS, Google, Groq, Mistral, Cohere, OpenRouter, Together, Fireworks, Perplexity, xAI, and others.
- Includes direct-provider-cost passthrough when usage has a `cost` field.

Where it falls short:

- It is TypeScript and tied to Helicone's observability/gateway billing context, including PTB/BYOK routing.
- It is not designed as a standalone multi-language cost-ledger kernel.
- It does not provide the full custom discount policy and source-provenance model required here.
- Historical pricing support appears partial through date ranges and versions, not a complete point-in-time public feed.

Verdict: important implementation reference. Study its registry, endpoint override, PTB/BYOK, and component breakdown design before implementing our own schemas.

### Portkey Models

Evidence:

- Repository: https://github.com/Portkey-AI/models
- Pricing API docs in README: https://github.com/Portkey-AI/models
- OpenAI pricing JSON: https://configs.portkey.ai/pricing/openai.json
- Anthropic pricing JSON: https://configs.portkey.ai/pricing/anthropic.json
- Google pricing JSON: https://configs.portkey.ai/pricing/google.json
- Portkey Gateway: https://github.com/Portkey-AI/gateway

Portkey Models is the best open pricing-data candidate.

Observed capabilities:

- Pricing coverage across many providers and thousands of models.
- Explicit data model for `request_token`, `response_token`, cache read/write, `thinking_token`, web search, file search, and other additional units.
- Batch pricing is modeled separately for OpenAI, Anthropic, and Google/Vertex-style cases.
- Public JSON endpoints are unauthenticated and easy to vendor or cache.

Where it falls short:

- It is a pricing catalog, not a local SDK response cost calculator.
- Prices use provider-specific JSON structure and units that callers must normalize carefully.
- It does not provide a universal raw response extractor.
- It does not provide organization-specific discount overlays.
- Point-in-time pricing was not obvious from the public schema during this pass.

Verdict: strongest candidate for upstream data ingestion. Build the new project as a thin normalizer/calculator around data sources like this.

### `genai-prices`

Evidence:

- Repository: https://github.com/pydantic/genai-prices
- PyPI: https://pypi.org/project/genai-prices/

`genai-prices` is the strongest small Python-library baseline.

Observed capabilities:

- Compact Python API: `calc_price`, `extract_usage`, and price update utilities.
- Provider usage extractors for multiple API flavors.
- Structured `Usage`, `ModelPrice`, `TieredPrices`, and `ConditionalPrice` concepts.
- Avoids double charging inclusive parent/child usage buckets.
- Supports point-in-time and conditional pricing patterns, including start-date and time-of-day constraints.

Smoke-check results from this validation:

- It extracted OpenAI Responses usage from the example-shaped response.
- It computed the expected simple input/output cost for `gpt-5.4`.
- It failed dated OpenAI alias strings such as `gpt-5.4-2026-05-24` and `gpt-5.2-2025-03-20`.
- Its OpenAI Responses extractor did not map `output_tokens_details.reasoning_tokens` into a separate thinking/reasoning component.

Where it falls short:

- Python-only.
- No first-class service tier, flex, priority, or batch modifier layer.
- No returned ledger of every billing component.
- No provider or surface discount overlay abstraction.
- Alias support did not cover common OpenAI dated model suffixes in the smoke check.

Verdict: excellent design reference for pricing constraints and point-in-time support. Consider contributing improvements if the Python ecosystem is the first target.

### `ai-sdk-cost-calculator`

Evidence:

- npm: https://www.npmjs.com/package/ai-sdk-cost-calculator
- Repository link from package metadata when available through npm.

This is the closest Node package to the desired developer ergonomics.

Observed capabilities:

- Designed for Vercel AI SDK flows.
- Provides `withCost`, `getCost`, `calculateCost`, and similar helpers.
- Returns component fields such as input, output, cache read, cache write, reasoning, web search, and total.
- Supports long-context pricing, prompt caching, reasoning tokens, custom pricing, and a global cost multiplier.
- Alias normalization handled dated model suffixes in smoke testing.

Smoke-check results:

- `gpt-5.4-2026-05-24` normalized to `gpt-5.4`.
- The OpenAI Responses-style usage sample produced the expected componentized total.

Where it falls short:

- Strongly Vercel AI SDK-oriented rather than raw official SDK response-oriented.
- No obvious batch, flex, priority, or provider surface tier abstraction.
- Global multiplier is useful but not a full discount policy engine.
- No point-in-time pricing.
- Provider coverage is meaningful but not as broad as LiteLLM or Portkey.
- Node-only.

Verdict: closest ergonomic competitor. The new package must be clearly better on provider/surface coverage, raw response extraction, service tiers, discounts, and portability.

### TokenLens and models.dev

Evidence:

- TokenLens npm: https://www.npmjs.com/package/tokenlens
- models.dev API: https://models.dev/api.json
- models.dev repository: https://github.com/anomalyco/models.dev

TokenLens is a model metadata and usage helper, not a precise billing ledger.

Observed capabilities:

- Large model catalog through models.dev.
- Context window metadata and cost estimates.
- Alias resolution and provider/model normalization.
- Usage normalization for some provider and AI SDK-style shapes.
- Handles cache and reasoning fields in helper code.

Where it falls short:

- Costing is framed as rough estimation.
- No full service tier, batch, long-context, or discount policy engine was found.
- Not designed as a canonical precise billing ledger.

Verdict: useful source for catalog and alias behavior, but not sufficient as the core billing engine.

### `token-costs`

Evidence:

- npm: https://www.npmjs.com/package/token-costs
- Repository: https://github.com/mikkotikkanen/token-costs

`token-costs` has a good data freshness concept but did not validate as reliable enough.

Observed capabilities:

- Daily-pricing-data premise.
- Offline mode, stale-data detection, and custom providers.
- Supports basic OpenAI, Anthropic, Google, and OpenRouter pricing.
- Calculates input, output, and cached input.

Smoke-check result:

- On 2026-05-24, its latest public data snapshot appeared to be 2026-03-12, and the package raised a clock/staleness mismatch during live testing.

Where it falls short:

- Limited providers.
- No reasoning/thinking cost component.
- No service tier, batch, flex, or priority support.
- No raw response extraction.
- Public data freshness did not match the package premise during validation.

Verdict: learn from stale-data detection, but do not rely on it as a baseline.

### `ai-cost-meter`

Evidence:

- npm: https://www.npmjs.com/package/ai-cost-meter

`ai-cost-meter` resembles the desired UX but not the desired correctness.

Observed capabilities:

- Claims raw response parsing, auto detection, custom prices, fetch wrapper, and Vercel AI SDK integration.
- Provider parsers extract useful details such as cached tokens and reasoning tokens for several vendors.

Observed gaps:

- Cost calculation ignored cached and reasoning token arguments in the inspected compiled source.
- Built-in pricing data was shallow.
- No service tier, long-context, discount, or point-in-time support.
- Package naming/README metadata appeared inconsistent.

Verdict: validates user demand for simple response-in cost-out APIs, but is not a strong correctness baseline.

### `tokentally`

Evidence:

- npm: https://www.npmjs.com/package/tokentally

`tokentally` is a small TypeScript helper for normalization and rough cost estimation.

Observed capabilities:

- Static maps plus LiteLLM/OpenRouter-style pricing sources.
- Usage normalization and aggregation.
- Small embeddable design.

Where it falls short:

- Its own README positions perfect accounting as a non-goal.
- No complete cache write/read, service tier, batch, long-context, discount, or point-in-time engine.

Verdict: useful lightweight API inspiration, not a competitor that closes the gap.

### AgentOps `tokencost`

Evidence:

- Repository: https://github.com/AgentOps-AI/tokencost
- PyPI: https://pypi.org/project/tokencost/

`tokencost` is an older Python cost helper focused on prompt/completion tokens.

Observed capabilities:

- Python token counting and cost calculation.
- Static LiteLLM-derived price data with an update path.

Where it falls short:

- Input/output only.
- No cache, reasoning, service tiers, long-context, point-in-time, raw response extraction, or multi-language design.

Verdict: adjacent and historically known, but not the target.

### `llm-tokencost`

Evidence:

- Repository: https://github.com/Paawan13/llm-tokencost
- PyPI: https://pypi.org/project/llm-tokencost/

`llm-tokencost` wraps SDK calls and tracks cost/budgets.

Observed capabilities:

- SDK-specific wrappers for OpenAI, Anthropic, and Gemini.
- Uses LiteLLM for basic cost calculation.
- Has tracking and budget concepts.

Where it falls short:

- Mostly input/output token accounting.
- No detailed component ledger.
- No broad service tier or discount policy.
- Python-only and not a portable core.

Verdict: useful wrapper pattern, not a detailed billing kernel.

### Hosted Observability and Gateways

Evidence:

- Langfuse: https://github.com/langfuse/langfuse
- Helicone: https://github.com/Helicone/helicone
- Portkey Gateway: https://github.com/Portkey-AI/gateway

These products solve different jobs:

- LLM observability.
- Tracing and analytics.
- Gateway routing.
- Spend tracking over time.

They may include cost attribution, but they are not small local packages whose main API is "give me this raw SDK response and get an exact componentized cost ledger."

Verdict: competitors for spend observability, not for a lightweight embeddable developer cost primitive.

## Provider and API Surface Findings

### OpenAI

Evidence:

- Pricing page: https://openai.com/api/pricing/
- API docs: https://platform.openai.com/docs
- LiteLLM OpenAI model pricing reference: https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json
- Portkey OpenAI pricing JSON: https://configs.portkey.ai/pricing/openai.json

Important billing dimensions:

- Input tokens.
- Cached input tokens.
- Output tokens.
- Reasoning tokens on reasoning-capable models.
- Batch pricing.
- Flex and priority/service-tier style pricing on supported surfaces.
- Model aliases and dated model versions.

Validation note: direct shell access to some OpenAI platform pages was blocked by Cloudflare during research, so exact field-level assertions were cross-checked against source-visible LiteLLM and Portkey pricing data plus public OpenAI URLs.

### Anthropic

Evidence:

- Pricing: https://docs.anthropic.com/en/docs/about-claude/pricing
- Prompt caching: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- Messages API usage docs: https://docs.anthropic.com/en/api/messages

Important billing dimensions:

- Input tokens.
- Output tokens.
- Cache creation/write tokens.
- Cache read tokens.
- Cache TTL differences, including 5-minute and 1-hour cache behavior on supported models.
- Batch pricing.
- Long-context pricing on supported models.

Anthropic is a key reason the new project needs separate usage ledger buckets rather than one `cached_input_tokens` field.

### Google Gemini and Vertex AI

Evidence:

- Gemini API pricing: https://ai.google.dev/gemini-api/docs/pricing
- Gemini API usage metadata: https://ai.google.dev/api/generate-content
- Vertex AI generative AI pricing: https://cloud.google.com/vertex-ai/generative-ai/pricing

Important billing dimensions:

- Input tokens.
- Output tokens.
- Cached content tokens.
- Thinking tokens.
- Long-context threshold pricing for some models.
- Batch pricing on some surfaces.
- Vertex AI and AI Studio/Gemini API surface differences.
- Multimodal units and modality-specific pricing.

Google is a key reason the project needs provider/surface-specific extractors and not only model-level pricing.

### AWS Bedrock

Evidence:

- Bedrock pricing: https://aws.amazon.com/bedrock/pricing/
- Converse API: https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html
- Runtime usage block docs: https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_TokenUsage.html

Important billing dimensions:

- Input tokens.
- Output tokens.
- Prompt caching on supported models.
- Batch inference.
- Provisioned throughput and other deployment modes.
- Provider-specific model behavior surfaced through Bedrock abstractions.

Bedrock is a key reason the project needs a `surface` dimension separate from provider and model.

### xAI

Evidence:

- Pricing: https://docs.x.ai/docs/models
- API docs: https://docs.x.ai/docs

Important billing dimensions:

- Input tokens.
- Cached input tokens.
- Output tokens.
- Model-specific context windows.

Validation note: source-visible calculators showed edge cases around cached-token double counting for xAI-style responses. This should be a hard live-evaluation fixture.

### DeepSeek

Evidence:

- Pricing: https://api-docs.deepseek.com/quick_start/pricing
- API docs: https://api-docs.deepseek.com/

Important billing dimensions:

- Cache-hit input pricing.
- Cache-miss input pricing.
- Output pricing.
- Time-of-day or promotional discount behavior.

DeepSeek is a key reason the project should model conditional pricing, not only static price rows.

### OpenRouter and Aggregators

Evidence:

- Models and pricing: https://openrouter.ai/models
- Models API: https://openrouter.ai/docs/api/api-reference/models/get-models
- Live endpoint: https://openrouter.ai/api/v1/models
- API docs: https://openrouter.ai/docs

Important billing dimensions:

- Aggregated provider routing.
- Provider/model-specific prices.
- Model catalog pricing fields such as prompt, completion, cache write/read, and modality-dependent prices where available.
- Potential usage and cost reporting at the routing layer.

Validation note: on 2026-05-24, the public `/api/v1/models` endpoint returned 358 models in a live check. A sample model exposed pricing keys including `prompt`, `completion`, and `input_cache_write`.

Aggregators should be modeled as providers/surfaces, not only as aliases for underlying vendors.

## What Exists Today

Solved well by existing tools:

- Large provider/model price catalogs: LiteLLM, Portkey Models, models.dev.
- Basic input/output cost calculation: many packages.
- Prompt caching in at least some form: LiteLLM, Portkey, `genai-prices`, `ai-sdk-cost-calculator`, TokenLens.
- Reasoning/thinking as a known pricing dimension: LiteLLM, Portkey, `ai-sdk-cost-calculator`, TokenLens.
- Point-in-time and conditional pricing pattern: `genai-prices`.
- Vercel AI SDK ergonomics: `ai-sdk-cost-calculator`.

Partially solved:

- Raw response extraction: `genai-prices`, `ai-cost-meter`, TokenLens, SDK wrappers.
- Alias normalization: TokenLens, `ai-sdk-cost-calculator`, LiteLLM-style maps.
- Long-context pricing: LiteLLM, Portkey data, `genai-prices`, `ai-sdk-cost-calculator`.
- Batch pricing: LiteLLM and Portkey data, but not a universal user-facing modifier API.
- Custom prices: many packages offer some override mechanism.

Still meaningfully unsolved in one package:

- A universal componentized cost ledger.
- Complete current SDK response extraction across major official SDKs.
- Service tier/surface modifier engine across batch, flex, priority, Bedrock, Vertex, OpenRouter, and similar cases.
- Discount overlays by provider, model, surface, service tier, or date range.
- Portable canonical schema and multi-language SDK generation.
- Strict no-double-counting behavior with explainable warnings.
- Pricing-source provenance and stale-data reporting as first-class output.

## Recommended Product Shape

Build a small, boring core with explicit data contracts:

```text
Raw SDK response
  -> provider/surface extractor
  -> normalized usage ledger
  -> model alias resolver
  -> price source resolver
  -> modifier and discount engine
  -> componentized cost ledger
```

Core concepts:

- `Provider`: `openai`, `anthropic`, `google`, `vertex`, `bedrock`, `xai`, `deepseek`, `openrouter`, etc.
- `Surface`: `responses`, `chat_completions`, `messages`, `converse`, `generate_content`, `batch`, `vertex_predict`, `ai_sdk`, etc.
- `UsageLedger`: disjoint counted units, never provider-native inclusive totals.
- `PriceCard`: normalized price rows with units, effective dates, conditions, and source provenance.
- `Modifiers`: service tier, batch, long-context threshold, cache TTL, provisioned mode, and similar.
- `DiscountPolicy`: user-controlled price multipliers or fixed overrides by provider/model/surface/tier/date.
- `CostLedger`: component prices, total, source, confidence, and warnings.

The most important engineering rule: normalize provider usage into disjoint ledger buckets before pricing. Do not price inclusive totals directly.

Suggested ledger buckets:

- `input_uncached_tokens`
- `input_cache_read_tokens`
- `input_cache_write_tokens`
- `input_cache_write_1h_tokens`
- `output_text_tokens`
- `output_reasoning_tokens`
- `input_audio_tokens`
- `output_audio_tokens`
- `image_units`
- `video_units`
- `web_search_units`
- `file_search_units`
- `request_units`
- `unknown_billable_units`

## Source Strategy

Start with source adapters, not scrapers:

1. Portkey Models adapter for provider/model price rows and additional units.
2. LiteLLM adapter or compatibility tests for model aliases, service tier keys, and edge cases.
3. Helicone cost-package adapter or compatibility tests for registry, endpoint, PTB/BYOK, and cost-breakdown behavior.
4. Simon Willison `llm-prices` adapter for simple current/historical input/output/cached-input prices.
5. OpenRouter `/api/v1/models` adapter for live OpenRouter catalog/pricing data.
6. Optional models.dev adapter for catalog/context/alias enrichment.
7. Optional `genai-prices` comparison fixture for point-in-time and conditional pricing behavior.

Only build scrapers after this library has a stable schema and tests prove that upstream sources cannot cover required freshness or detail.

## Multi-Language Strategy

Do not start with Stainless unless the project exposes a hosted API. Stainless is strongest for API-client generation, while this project is primarily a local deterministic library.

Prefer:

- A canonical JSON Schema for `UsageLedger`, `PriceCard`, `DiscountPolicy`, and `CostLedger`.
- Shared fixture files for every provider/surface hard case.
- A reference implementation in TypeScript or Python.
- Generated or hand-thin wrappers in Python, Node, and Go that all run the same fixture suite.

If a hosted pricing-resolution API is added later, Stainless or OpenAPI-based client generation can become useful.

## Build / Contribute / Fork / Stop Gates

Build if:

- Live fixture tests show no package can correctly price the hard cases in `LIVE_EVALUATION_PROTOCOL.md`.
- Existing packages remain language- or SDK-specific.
- Service tiers, discounts, and raw response extraction remain fragmented.

Contribute if:

- `genai-prices` can accept raw response extractor, alias, reasoning, service-tier, and discount improvements without changing its philosophy.
- `ai-sdk-cost-calculator` can add generic raw official SDK response parsing and tier policy without becoming too broad.
- Portkey Models can add missing source provenance or point-in-time fields useful to this project.

Fork only if:

- A close package has the right license, architecture, and maintenance posture but maintainers reject a narrow correctness PR.

Stop if:

- One existing package passes the full hard-case matrix with a small, documented API and multi-language plan.
- The project cannot maintain price data freshness without becoming a large observability or scraping company.

## Minimum Viable Scope

V0 should support:

- OpenAI Responses and Chat Completions.
- Anthropic Messages.
- Google Gemini API `generateContent`.
- Vertex AI Gemini usage metadata.
- AWS Bedrock Converse usage.
- DeepSeek OpenAI-compatible responses.
- xAI OpenAI-compatible responses.
- OpenRouter where usage/pricing metadata is available.
- Vercel AI SDK `usage` objects as an adapter.

V0 should return:

- Normalized provider/model/surface.
- Matched price source and last-updated metadata.
- Component cost breakdown.
- Total.
- Warnings for unknown model, unknown component, stale price, inferred alias, and inclusive-token ambiguity.

V0 should not include:

- Hosted observability.
- Budget alerts.
- Tracing.
- Prompt token counting.
- Automatic pricing page scrapers.
- UI dashboards.

## Key Risks

Data freshness:

- Pricing changes frequently, and upstream sources disagree.
- Mitigation: source provenance, stale-data warnings, fixture comparisons against multiple upstreams.

Double counting:

- Providers often report inclusive parent totals plus child detail buckets.
- Mitigation: require all extractors to emit disjoint ledger buckets and test component sums.

Surface ambiguity:

- The same model can have different prices by API surface, tier, region, batch mode, or deployment mode.
- Mitigation: make `surface` and `tier` explicit parameters, infer only when safe, and warn otherwise.

Alias drift:

- Dated models and aliases change over time.
- Mitigation: exact alias map first, optional suffix normalization only behind warnings or source-backed rules.

Multi-language drift:

- Independent implementations can diverge.
- Mitigation: shared JSON fixtures and conformance tests.

## Final Recommendation

Proceed, but build the smallest possible library:

1. Define the canonical usage and cost ledger schemas.
2. Implement OpenAI Responses and Anthropic Messages extractors first.
3. Use Portkey Models and LiteLLM as data/reference sources.
4. Add discount and custom-price overlays before broadening providers.
5. Run every candidate package against the hard-case matrix before deciding the exact public API.

The market gap is real enough to justify a focused build, provided the project is framed as a normalization/calculation kernel rather than another model-pricing catalog.
