---
title: Meta Model API Compatibility Plan
date: 2026-07-09
type: plan
status: active
---

# Meta Model API Compatibility Plan

## Objective

Add fixture-backed and credentialed-smoke-backed RunCost compatibility for Meta
Model API pricing.

## Evidence

- Requested docs URL: https://dev.meta.ai/docs/getting-started/sdks
- Current docs access result: the docs page returns "Not Logged In" in this
  Codex environment.
- Credentialed API smoke result: `fixtures/source-files/meta-model-api-live-smoke-2026-07-09.json`
  confirms `https://api.meta.ai/v1/models`, `/chat/completions`, and
  `/responses` with sanitized usage evidence and no retained raw response.
- The Verge reports that Muse Spark 1.1 is available to US developers through a
  public Meta Model API preview with $20 of free credits.
- Axios and Reuters/WTVB report Muse Spark 1.1 pricing at $1.25 per million
  input tokens and $4.25 per million output tokens.
- Meta for Developers search-result text for the public preview reports base
  Muse Spark pricing at $0.40 per million input tokens and $2.00 per million
  output tokens.

## Decisions

- Add provider `meta`.
- Add surfaces `meta.chat_completions` and `meta.responses`.
- Route `meta.chat_completions` through the OpenAI-compatible chat extractor
  because the SDK docs are not yet accessible and Meta is positioning the API
  for coding-agent tooling where OpenAI-compatible shapes are common.
- Route `meta.responses` through the Responses-style extractor so package users
  can price SDKs that expose `input_tokens`, `output_tokens`, reasoning-token
  detail, final streaming envelopes, and hosted tool call items.
- Retain a reviewed public-preview price-source snapshot for explicit opt-in
  compatibility estimates, with aliases for likely SDK/model strings. Do not
  include it in the default catalog until exact rates are primary-source verified.
- Price cache-read and reasoning components at the published input/output token
  rates until Meta documents separate rates. Record this assumption in price
  card metadata.
- Do not model Meta-specific tool, image, video, storage, endpoint, or
  computer-use pricing until a primary source exposes those prices. If a raw
  response contains supported tool counters without a matching price component,
  return structured unpriced-tool warnings.

## Implementation Checklist

- Add shared fixtures for Meta OpenAI-compatible chat extraction and
  Responses-style extraction.
- Add a Meta reviewed-preview source-adapter fixture.
- Add Python, JavaScript/TypeScript, and Go dispatch support.
- Export Python and JavaScript Meta convenience extractors.
- Keep Meta preview rates outside the default source-cache catalog and priority
  list until primary pricing evidence is available.
- Update API/reference docs and generated fixture/API docs.
- Add a sanitized optional live smoke runner for `/models`, `/chat/completions`,
  and `/responses`.
- Run targeted fixture checks first, then broaden to fixture, catalog, hygiene,
  docs, and Go checks.

## Remaining Follow-Up

- Re-open the credentialed SDK docs in a logged-in browser and replace any
  remaining inferred SDK wording with exact request and response examples.
- Verify whether cached input, reasoning output, tool use, multimodal input, and
  generated media have separate billable rates.
- Promote the reviewed-preview snapshot into a primary-source-backed default
  snapshot only if Meta publishes exact stable rates.
