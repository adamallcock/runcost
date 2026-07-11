---
title: OpenAI GPT-5.6 Cache-Write Pricing
date: 2026-07-10
type: decision-record
status: accepted
---

# OpenAI GPT-5.6 Cache-Write Pricing

## Decision

RunCost will ship reviewed OpenAI pricing cards for `gpt-5.6-sol`,
`gpt-5.6-terra`, and `gpt-5.6-luna`, including cached-input reads,
cache writes, the 272,000-token long-context boundary, and published Standard,
Batch, Flex, and Priority service-tier rates.

Raw OpenAI Responses, Chat Completions, and Agents SDK usage will map the
documented `cache_write_tokens` detail field to
`input_cache_write_tokens`. Cache writes are subtracted from the inclusive
input total alongside cache reads so the same token is not also charged as
uncached input.

The 30-minute minimum cache lifetime and explicit-breakpoint support are price
card metadata. They are not separate usage components because OpenAI does not
publish a separate duration-priced cache-write SKU.

## Evidence

Verified on 2026-07-10 from OpenAI primary sources:

- <https://developers.openai.com/api/docs/pricing> lists per-1M-token Standard,
  Batch, Flex, and Priority rates for all three GPT-5.6 models, including cache
  reads and cache writes.
- <https://developers.openai.com/api/docs/guides/prompt-caching> documents
  `cache_write_tokens`, `cached_tokens`, explicit breakpoints, and the `30m`
  minimum cache lifetime for GPT-5.6 and later families.
- <https://developers.openai.com/api/docs/models/gpt-5.6-sol> documents the
  `gpt-5.6` alias and states that prompts above 272,000 input tokens price the
  full request at 2x input and 1.5x output.
- <https://openai.com/index/gpt-5-6/> records GPT-5.6 general availability on
  2026-07-09. The same base pricing was published for the limited preview on
  2026-06-26, which is the effective start date retained in the snapshot.

The original Help Center preview URL now redirects to a ChatGPT availability
article. It is retained only as historical context and is not the catalog's
source URL.

## Pricing Model

- `input_uncached_tokens`: published input rate.
- `input_cache_read_tokens`: published cached-input rate, 10% of uncached input.
- `input_cache_write_tokens`: published cache-write rate, 125% of uncached input.
- `output_text_tokens` and `output_reasoning_tokens`: published output rate.
- Total input up to 272,000 tokens uses short-context prices.
- Total input from 272,001 tokens uses long-context prices for the full request.
- Priority currently has only published short-context prices. Long-context
  Priority usage therefore fails closed with `long_context_rule_missing`.

## Extraction Boundaries

- Responses API: read writes from
  `usage.input_tokens_details.cache_write_tokens`.
- Chat Completions API: read writes from
  `usage.prompt_tokens_details.cache_write_tokens`.
- OpenAI Agents SDK usage: read the Responses-shaped
  `input_tokens_details.cache_write_tokens` field.
- Do not infer writes from cache misses, explicit breakpoint request options, or
  prompt length.
- Normalize OpenAI `default` and `auto` service-tier response values to RunCost
  `standard`; preserve `batch`, `flex`, and `priority`. Unknown tiers remain
  unmatched so RunCost warns instead of guessing contract pricing.

## Release Boundary

This decision and its implementation are not released until the branch is
merged and a versioned GitHub/npm/PyPI/Go release is published and verified.
