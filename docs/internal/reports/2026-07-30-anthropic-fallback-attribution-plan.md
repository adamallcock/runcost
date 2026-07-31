---
title: Anthropic Fallback Attribution and Pricing Plan
date: 2026-07-30
type: plan
status: complete
---

# Anthropic Fallback Attribution and Pricing Plan

## Objective

Make RunCost price the model attempt that actually ran, expose when Anthropic
fallback was attempted or served, and preserve correct behavior for direct
Messages responses, Anthropic SDK middleware/final streaming responses, and
Message Batch results.

## Verified provider contract

- [Refusals and fallback](https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback): a pre-output refusal is not billed; a mid-stream refusal bills its input and partial output. `usage.iterations` is the per-attempt billing record, and the top-level `model` identifies the model that returned the message.
- [Fallback credit](https://platform.claude.com/docs/en/build-with-claude/fallback-credit): manual retries must be priced from the retry response's reported cache-write/cache-read fields. Supplying a credit token does not by itself prove a credit was redeemed.
- [Message Batches](https://platform.claude.com/docs/en/build-with-claude/batch-processing): batch refusals are successful result envelopes with `stop_reason: "refusal"`; server-side `fallbacks` is unsupported; retry work must be submitted separately. Batch usage receives the Batch API price tier.
- [Pricing](https://platform.claude.com/docs/en/about-claude/pricing): Batch API input and output pricing is 50% of standard pricing. Claude Opus 5 standard pricing is $5/MTok input and $25/MTok output, with normal prompt-cache multipliers.

## Implementation decisions

1. Treat `usage.iterations` as authoritative per-attempt usage. Price each
   component against that iteration's `model`.
2. Suppress all token components for an attempt that refused before output;
   retain both input/cache and output components for a mid-stream refusal.
3. Detect fallback generically from `fallback_message` iterations or fallback
   content blocks. Do not hard-code Fable 5, Opus 4.8, or a category list.
4. Record structured ledger metadata for requested, attempted, and serving
   models so applications can render “fallback utilized; X was used for
   pricing.” This is provenance, not a warning.
5. Derive the serving model for raw streaming event collections from the final
   `fallback_message` iteration when `message_start` still names the primary.
6. Keep legacy fallback-credit option names accepted for compatibility, but do
   not rewrite reported usage merely because the caller says a token was sent.
7. For Message Batch results, keep provider status `succeeded` while marking
   refusals as retry-required metadata and pricing them at zero when no output
   was produced. Successful retry batches price the returned retry model at the
   batch tier.
8. Add Claude Opus 5 to the reviewed Anthropic pricing snapshot and verify both
   standard and batch cache/token components.

## Validation

- Shared Python/JavaScript/Go fixtures for generic fallback, Opus 5 fallback,
  pre-output and mid-stream refusal, streaming events, manual credit usage, and
  Message Batch refusal/retry results.
- Focused conformance, expansion/batch, official-pricing, schema, and type checks.
- Full repository test and release-readiness checks after focused checks pass.

## Completion evidence

- `npm test`: passed, including 181 shared Python/JavaScript fixtures, the Go
  conformance suite, 35 expansion cases, the 216-case generated conformance
  report, browser bundle checks, examples, and the playground production build.
- `go test ./...`: passed.
- `python3 scripts/check_package_installs.py`: passed for installed Python, npm,
  and Go packages.
- `python3 scripts/check_release_readiness.py`: passed.
