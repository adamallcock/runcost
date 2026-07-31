---
title: GPT-5.6 Terra and Luna Price Transition Plan
date: 2026-07-30
type: plan
status: complete
---

# GPT-5.6 Terra and Luna Price Transition Plan

## Objective

Preserve GPT-5.6 Terra and Luna pricing before July 30, 2026 while applying
OpenAI's permanent lower prices from July 30 onward across Standard, Batch,
Flex, and Fast/Priority processing.

## Verified current contract

- [OpenAI API pricing](https://developers.openai.com/api/docs/pricing) lists
  Terra at $2 input, $0.20 cached input, $2.50 cache writes, and $12 output per
  million short-context tokens; Luna is $0.20, $0.02, $0.25, and $1.20.
- The same page publishes the long-context, Batch, Flex, and Fast rates and says
  Priority processing was renamed Fast mode on July 30, 2026; both
  `service_tier: "priority"` and `service_tier: "fast"` remain accepted.
- [Terra's model page](https://developers.openai.com/api/docs/models/gpt-5.6-terra)
  and [the model comparison](https://developers.openai.com/api/docs/models/compare)
  independently show the new Standard rates.

## Implementation

1. Close the existing Terra/Luna cards on July 29, 2026 without changing their
   historical rates.
2. Add permanent cards effective July 30, 2026 for all four service tiers and
   both context bands.
3. Preserve OpenAI `fast` and `priority` independently in Python,
   JavaScript/browser, and Go, with exact Fast precedence and a one-way,
   auditable Fast-to-Priority compatibility fallback.
4. Add explicit July 29 / July 30 boundary checks and current Fast-tier checks.
5. Derive the pricing timestamp from OpenAI Responses `created_at` and Chat
   Completions `created` when callers do not provide an explicit override.
6. Refresh generated conformance artifacts and validate installed packages.

## Completion Evidence

- The reviewed source snapshot expands to separate current Fast and Priority
  cards, while the historical snapshot retains the eight superseded Terra/Luna
  cards through July 29.
- Six focused transition fixtures pass across Python and JavaScript, with the
  shared Go fixture suite passing the same cases.
- The full 181-fixture suite, 102-card official snapshot check, 216-case
  generated conformance inventory, all Go packages, browser bundle, playground
  build, installed Python/npm/Go package smokes, project hygiene, and release
  readiness checks pass.
