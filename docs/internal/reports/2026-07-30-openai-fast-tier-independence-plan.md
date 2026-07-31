---
title: OpenAI Fast Tier Independence Plan
date: 2026-07-30
type: plan
status: complete
---

# OpenAI Fast Tier Independence Plan

## Objective

Represent OpenAI `fast` and `priority` as independent request and price-card
tiers while their published prices remain equal. Prefer exact Fast pricing and
use Priority only as a one-way compatibility fallback when no applicable Fast
card exists.

## Current Provider Contract

- [OpenAI Fast mode](https://developers.openai.com/api/docs/guides/fast-mode)
  says both request values currently access the same functionality.
- GPT-5.6 and earlier responses may return `priority` even when the request used
  `fast`, so response-only telemetry cannot always recover request intent.
- The pricing page now names the tier Fast. That does not guarantee Fast and
  Priority will remain interchangeable or identically priced indefinitely.

## Selection Contract

1. Preserve `fast` and `priority` independently in request context and price
   cards.
2. For a Fast request, use applicable Fast cards exclusively when any exist.
3. If no applicable Fast card exists, retry selection against Priority cards.
4. Record `requested: fast`, `priced_as: priority`, and the selected card on
   fallback-priced components and in cost-ledger metadata.
5. Never fall from a Priority request to a Fast card.
6. Keep `default` and `auto` normalization to `standard`; provider responses
   that report `default` after a Fast downgrade must use Standard pricing.

## Coverage

- Python, JavaScript/browser, and Go deterministic calculation.
- Raw Responses and Chat Completions, streaming final-usage envelopes, explicit
  request context, OpenAI Agents SDK usage, and OpenTelemetry GenAI context.
- Exact Fast preference even when source-priority ordering favors a Priority
  card.
- One-way fallback and no reverse fallback.
- Separate official Fast and Priority cards at today's equal rates so future
  divergence is a data update rather than a schema or selection change.

## Completion Evidence

- All 181 shared fixtures pass across Python and JavaScript, and the same
  fixture inventory passes through the Go core.
- Focused cases prove exact Fast precedence, auditable Fast-to-Priority
  fallback, no Priority-to-Fast fallback, request-context precedence when an
  older response reports Priority, streaming tier propagation, Agents SDK
  usage, and OpenTelemetry GenAI extraction.
- The official snapshot check passes for 102 explicit cards, including separate
  current Fast and Priority cards for GPT-5.6 Sol, Terra, and Luna.
- The 216-case generated conformance inventory, all Go packages, browser bundle,
  playground production build, installed Python/npm/Go package smokes, project
  hygiene, and release-readiness checks pass.
