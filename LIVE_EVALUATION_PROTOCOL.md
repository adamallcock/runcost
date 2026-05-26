---
title: RunCost Live Evaluation Protocol
date: 2026-05-25
type: research
status: draft
---

# RunCost Live Evaluation Protocol

Research date: 2026-05-24

Purpose: prove whether this project should build a new package, contribute to an existing one, or stop.

The protocol uses hard billing fixtures that reflect real provider complexity. A candidate only passes if it returns a correct componentized cost ledger, not just a plausible total.

## Candidate Set

Evaluate at minimum:

- LiteLLM
- Portkey Models plus a tiny local calculator
- Simon Willison `llm-prices`
- Helicone `@helicone-package/cost`
- OpenRouter `/api/v1/models`
- `genai-prices`
- `ai-sdk-cost-calculator`
- TokenLens / models.dev
- `token-costs`
- `ai-cost-meter`
- `tokentally`

Hosted tools such as Langfuse, Helicone, and Portkey Gateway should be evaluated separately only if the product direction shifts toward observability or gateway behavior.

## Pass Criteria

A candidate passes a fixture only when it:

- Extracts or accepts the usage shape without manual token rewriting.
- Resolves the provider, model, alias, surface, and service tier.
- Produces disjoint component costs.
- Avoids double-counting inclusive usage totals.
- Applies the correct long-context, batch, flex, priority, cache TTL, or conditional pricing rule.
- Supports custom prices and discount overlays when the fixture asks for them.
- Emits source/provenance and stale-price metadata.
- Emits warnings for unknown or inferred behavior.
- Produces a total equal to the sum of components.

## Required Output Shape

Every evaluated candidate should be adapted into this common shape:

```json
{
  "provider": "openai",
  "surface": "responses",
  "model_requested": "gpt-5.4",
  "model_billed": "gpt-5.4",
  "currency": "USD",
  "components": [
    {
      "name": "input_uncached",
      "units": 36,
      "unit_type": "token",
      "unit_price_usd": 0.0000025,
      "cost_usd": 0.00009
    }
  ],
  "total_usd": 0.001395,
  "price_source": {
    "name": "portkey-models",
    "url": "https://configs.portkey.ai/pricing/openai.json",
    "retrieved_at": "2026-05-24"
  },
  "warnings": []
}
```

If a candidate cannot natively return this shape, write a minimal adapter around its output and record which fields were inferred.

## Fixture A: OpenAI Responses, Dated Alias, Cached Input, Reasoning, Priority

Input:

- Provider: `openai`
- Surface: `responses`
- Requested model: `gpt-5.4`
- Response model: a dated alias, for example `gpt-5.4-2026-05-24`
- Service tier: `priority`
- Usage:
  - `input_tokens`: 10,000
  - `input_tokens_details.cached_tokens`: 4,000
  - `output_tokens`: 2,000
  - `output_tokens_details.reasoning_tokens`: 500

Expected evaluation:

- Alias resolves to the billable model or returns a source-backed alias warning.
- Cached input is not double charged as full-price input.
- Reasoning tokens are either priced as their own output component or explicitly treated according to provider rules.
- Priority tier pricing is selected if available.
- Component sum equals total.

Common failure modes:

- Pricing all 10,000 input tokens at uncached input price.
- Ignoring priority tier.
- Ignoring reasoning tokens.
- Treating dated model as unknown.

## Fixture B: Anthropic Messages, Cache Write, Cache Read, 1-Hour TTL, Batch

Input:

- Provider: `anthropic`
- Surface: `messages`
- Model: latest Claude Sonnet-class model available at evaluation time.
- Mode: `batch`
- Cache TTL: one prompt segment at 5 minutes, one at 1 hour.
- Usage:
  - `input_tokens`: 3,000
  - `cache_creation_input_tokens`: 20,000
  - `cache_read_input_tokens`: 50,000
  - `output_tokens`: 4,000

Expected evaluation:

- Cache creation and cache read are separate components.
- 1-hour cache write is priced separately if provider/model supports it.
- Batch pricing is applied to the eligible components.
- No inclusive-token double counting.

Common failure modes:

- Treating cache creation as normal input.
- Treating cache read as normal input.
- Missing the batch modifier.
- Missing cache TTL pricing.

## Fixture C: Gemini API and Vertex AI, Thinking Tokens, Cached Content, Long Context

Input:

- Provider: `google` and separately `vertex`
- Surface: `generate_content` or Vertex equivalent.
- Model: Gemini Pro-class model with threshold pricing.
- Usage metadata:
  - `promptTokenCount`: 150,000
  - `cachedContentTokenCount`: 75,000
  - `thoughtsTokenCount`: 10,000
  - `candidatesTokenCount`: 8,000
  - `totalTokenCount`: 168,000
- Mode: run both normal and batch if supported.

Expected evaluation:

- Cached content is separated from uncached prompt tokens.
- Thinking tokens are separated from visible output tokens where applicable.
- Long-context threshold pricing is applied.
- Gemini API and Vertex AI can differ by surface.

Common failure modes:

- Pricing `totalTokenCount` directly.
- Ignoring thoughts tokens.
- Applying under-threshold pricing to the whole request.
- Treating Gemini API and Vertex as interchangeable.

## Fixture D: AWS Bedrock Converse, Cache Read/Write and Deployment Surface

Input:

- Provider: `aws-bedrock`
- Surface: `converse`
- Underlying model provider: Anthropic or Amazon Nova, depending on current support.
- Usage:
  - `inputTokens`: 25,000
  - `outputTokens`: 3,000
  - cache read/write usage fields if available on the chosen model.
- Pricing mode: on-demand, then batch or provisioned mode if supported.

Expected evaluation:

- Bedrock is treated as its own surface, not only as the underlying provider.
- Cache fields are extracted when present.
- Batch/provisioned/on-demand mode changes pricing or emits an explicit unsupported warning.

Common failure modes:

- Mapping directly to Anthropic public API prices.
- Ignoring Bedrock-specific mode and regional pricing differences.
- Dropping cache usage fields.

## Fixture E: DeepSeek Cache Hit/Miss and Time-Based Pricing

Input:

- Provider: `deepseek`
- Surface: OpenAI-compatible chat.
- Model: current DeepSeek chat or reasoner model.
- Usage:
  - cache hit input tokens: 30,000
  - cache miss input tokens: 5,000
  - output tokens: 2,000
- Evaluation time: one peak and one off-peak timestamp if current pricing has time-window discounts.

Expected evaluation:

- Cache hit and cache miss use different input prices.
- Time-window discount is modeled or rejected with an explicit warning.
- Price date/time is part of the evaluation context.

Common failure modes:

- Collapsing hit/miss into one input bucket.
- Ignoring off-peak pricing.
- Using local machine time without timezone clarity.

## Fixture F: xAI Cached Input Double-Counting

Input:

- Provider: `xai`
- Surface: OpenAI-compatible chat.
- Model: current Grok model with cached input support.
- Usage:
  - prompt tokens including cached tokens.
  - prompt token details containing cached tokens.
  - completion tokens.

Expected evaluation:

- Extractor knows whether cached tokens are included in prompt tokens.
- Cached input is not double counted.
- Any provider ambiguity is surfaced as a warning.

Common failure modes:

- Full prompt billed plus cached input billed again.
- Cached input ignored.

## Fixture G: User Custom Price Override

Input:

- Provider: `openai`
- Surface: `responses`
- Model: `internal-router-model`
- User price override:
  - input: `$1.00 / 1M tokens`
  - cached input read: `$0.10 / 1M tokens`
  - output: `$4.00 / 1M tokens`
  - reasoning output: `$4.00 / 1M tokens`
- Usage:
  - input: 1,000
  - cached input: 300
  - output: 500
  - reasoning: 100

Expected evaluation:

- Custom price overrides vendor data.
- Override provenance is visible.
- Component ledger uses override prices.

Common failure modes:

- Unknown model failure despite override.
- Applying override only to input/output and not reasoning/cache.

## Fixture H: Provider Discount Overlay

Input:

- Provider: `openai`
- Surface: `responses`
- Model: known current model.
- Discount policy:
  - 4% off all OpenAI usage.
  - 10% off OpenAI batch usage.
  - No discount on web-search units.
- Usage:
  - input tokens.
  - cached input tokens.
  - output tokens.
  - web search unit if supported.
- Run once as standard, once as batch.

Expected evaluation:

- Discount applies only to eligible components.
- Batch discount composes deterministically with provider discount according to documented precedence.
- Non-discountable components stay undiscounted.

Common failure modes:

- Applying one global multiplier to everything.
- Discounting non-token pass-through fees.
- Ambiguous composition order.

## Fixture I: Unknown Model With Source Fallback

Input:

- Provider: `openrouter`
- Surface: `chat`
- Model: a newly released model present in one upstream source but absent in another.
- Usage:
  - input tokens.
  - output tokens.

Expected evaluation:

- Candidate records which source resolved the model.
- Candidate warns when other configured sources disagree or are stale.
- Candidate can fail closed if configured to require a specific source.

Common failure modes:

- Silent fallback to a similarly named model.
- No source provenance.

## Fixture J: Price Source Adapter Comparison

Input:

- Provider/model set:
  - One OpenAI model with cached input.
  - One Anthropic model with cache write/read.
  - One xAI model with reasoning.
  - One OpenRouter model with live `/api/v1/models` pricing.
- Sources:
  - Portkey Models.
  - LiteLLM pricing map.
  - Simon Willison `llm-prices`.
  - Helicone cost package.
  - OpenRouter models endpoint where applicable.

Expected evaluation:

- Adapter normalizes each source into the same `PriceCard` shape.
- Missing source dimensions become explicit unsupported fields or warnings.
- Source units are converted correctly.
- Source timestamps, package versions, and URLs are preserved.
- Source disagreement is visible in debug output.

Common failure modes:

- Treating a simplified input/output feed as complete.
- Losing historical date semantics from `llm-prices`.
- Losing endpoint/deployment details from Helicone.
- Confusing OpenRouter prompt/completion string prices with per-million prices.

## Evaluation Report Template

For each candidate and fixture, record:

```markdown
### Candidate: <name>

Fixture: <A-I>

- Result: pass / partial / fail
- Total returned:
- Component breakdown returned:
- Missing components:
- Alias behavior:
- Tier/modifier behavior:
- Data source:
- Warnings:
- Notes:
```

## Decision Thresholds

Build the new package if:

- No candidate passes fixtures A, B, C, G, and H.
- No candidate provides a credible multi-language conformance plan.
- Existing candidates require hand-rewriting provider usage into normalized fields for most hard cases.

Contribute instead if:

- One candidate passes at least six fixtures and only needs narrow extractor or alias improvements.
- The package maintainers accept the desired cost-ledger API direction.

Fork if:

- A close candidate has the right license and architecture but cannot accept the needed changes.

Stop if:

- A maintained candidate passes all required fixtures and exposes a small stable API.

## Release Readiness Checklist

Before any public v0 release:

- Each provider/surface has at least one golden raw response fixture.
- Each hard billing component has at least one fixture.
- Component totals are tested with decimal-safe arithmetic.
- Unknown, stale, inferred, and unsupported cases emit deterministic warnings.
- Every price row includes source and retrieval date.
- Python, Node, and Go packages all run the same fixture suite or generated conformance cases.
- Documentation clearly distinguishes estimated costs from invoice-exact costs.
