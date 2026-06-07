---
title: API Surface Cost Accounting Plan
date: 2026-06-06
type: plan
status: active
---

# API Surface Cost Accounting Plan

## Goal

Prevent Gemini-style silent cost omissions across RunCost public APIs. Every
nonzero usage component that an extractor or normalized usage ledger surfaces
must be either priced in the cost ledger or explicitly explained by a warning or
metadata policy.

## Scope

- Core normalized `calculate_cost` / `calculateCost` / Go `CalculateCost`.
- Raw-provider `from_response` / `extract_usage_ledger` fixture surfaces.
- Framework adapter helpers.
- Source adapter fixtures that create price components for cache, reasoning,
  tool, feature, multimodal, and service components.
- Generated fixture coverage report and release gates.

## Acceptance Criteria

- A fixture-backed gate fails if any nonzero usage component disappears from the
  cost ledger without an explicit treatment.
- Gemini raw responses that report `candidatesTokenCount` and
  `thoughtsTokenCount` separately must preserve that split as non-reasoning
  output components and `output_reasoning_tokens`; if the price card lacks a
  separate reasoning price, the output-rate fallback metadata must be present.
- The gate runs across Python, JavaScript, and Go fixture outputs where the
  fixture declares those languages.
- Public API registry entries must have cost-accounting fixture evidence, or an
  explicit non-usage-bearing exception.
- Source adapter coverage must make reasoning/thinking/cache/tool component
  mappings visible.
- Existing fixture, package, hygiene, and release checks remain green.

## Verification

- `python3 scripts/check_fixtures.py`
- `python3 scripts/check_cost_accounting.py`
- `python3 scripts/check_fixture_coverage.py`
- `npm test`
