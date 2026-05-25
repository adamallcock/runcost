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

Generator:

- `npm run fixture:new -- --example normalized_usage` prints a complete normalized-usage fixture.
- `npm run fixture:new -- --name my-fixture --description "..." --provider openai --surface openai.responses --scenario normalized_usage --requirement-id RC-FIXTURE-CONFORMANCE --usage-ledger-json @usage.json --price-cards-json @price-cards.json --expected-cost-ledger-json @expected.json` builds a fixture from JSON fragments.
- `python3 scripts/check_fixtures.py --fixture fixtures/my-fixture.json` validates one new fixture before running the full suite.
- Generated fixtures are starting points; expected ledgers still need review before commit.
