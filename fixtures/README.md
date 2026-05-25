---
title: RunCost Fixture Suite
date: 2026-05-25
type: reference
status: draft
---

# RunCost Fixture Suite

The fixtures are the contract between language implementations.

Each fixture should include:

- `name`
- `description`
- `input.usage_ledger`
- `input.price_cards`
- optional `input.discount_policies`
- optional `input.options`
- `expected.cost_ledger`

Rules:

- Quantities and money values are strings to avoid binary floating-point drift.
- Fixtures should be runnable without network access.
- Provider-specific raw responses can be added beside normalized fixtures once extractors exist.
- Every new provider or billing feature needs at least one fixture.
- Conditional pricing, service tiers, provider-reported cost behavior, and warnings must be represented as shared fixtures before being called supported.
