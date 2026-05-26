---
title: Source Data Update Process
date: 2026-05-26
type: runbook
status: draft
---

# Source Data Update Process

RunCost treats public pricing catalogs as source inputs, not as hidden code.
Normal cost calculation stays offline. Source updates are explicit, reviewed,
fixture-backed, and released with provenance.

## Ownership

Until a maintainer rotation is formalized, source-data updates are owned by the
release maintainer for the active release branch.

The owner is responsible for:

- choosing which pricing sources to refresh;
- preserving source URLs, retrieval timestamps, checksums, and license or terms
  notes where available;
- reviewing changed price cards before release;
- converting ambiguous or unsupported fields into fixtures, warnings, a
  documented limitation, or source-adapter fixes;
- recording user-impacting price changes in `CHANGELOG.md` when they affect
  package behavior or bundled fixtures.

## Cadence

Private alpha:

- refresh reviewed source snapshots before every alpha release candidate;
- refresh live presets only when validating a source-adapter change or preparing
  a price-source update PR;
- do not run network refreshes in normal CI.

Public beta:

- run a scheduled monthly source review;
- run an ad hoc review when a provider announces pricing changes;
- require a maintainer review before merging refreshed source-cache envelopes or
  changed adapter mappings.

V1:

- keep the monthly cadence unless user demand requires a faster release train;
- consider automation that opens draft PRs, but keep human review mandatory for
  source-data changes.

## Refresh Procedure

Use the explicit refresh command. Live preset example:

```bash
npm run prices:refresh -- \
  --preset llm-prices-current \
  --output vendor/prices/llm-prices-current.source-cache.json
```

Reviewed snapshot example:

```bash
npm run prices:refresh -- \
  --source-type official-snapshot \
  --input vendor/reviewed/openai-pricing-snapshot.json \
  --output vendor/prices/openai-pricing.source-cache.json
```

Every refresh PR should include:

- the source URL or reviewed snapshot path;
- retrieval time and checksum from the generated source-cache envelope;
- adapter type and command used;
- summary of added, removed, and materially changed price cards;
- classification for every unsupported or ambiguous source field;
- fixture additions or updates when behavior changes.

## Review Checklist

Before merging a source-data update:

- verify source provenance is present and non-secret;
- confirm generated price cards validate against `schemas/price-card.schema.json`;
- compare changed cards against provider documentation or the upstream catalog;
- check units carefully, especially per-token, per-million-token, per-request,
  per-second, per-hour, and `gb_day`;
- ensure user overrides still win through source-priority behavior;
- add a fixture for every new component, service tier, context condition,
  warning, or adapter mapping;
- run the validation battery below.

```bash
npm test
npm run check:coverage
npm run check:packages
npm run check:release
git diff --check
```

## Product Truth Loop

A source refresh can reveal four kinds of findings:

| Finding | Required outcome |
|---|---|
| Supported field missing from fixtures | Add or update a fixture. |
| Known but unsafe-to-price field | Add a structured warning or source capability limitation. |
| Intentionally unsupported source shape | Document the limitation. |
| Adapter bug or stale mapping | Fix the source adapter and add regression coverage. |

Do not merge source changes that leave unsupported billable fields only in a
terminal log or PR comment.

## Boundaries

- Do not commit API keys, account IDs, customer prompts, invoices, or private
  provider exports.
- Do not scrape provider pages in normal package tests.
- Do not make normal calculation fetch network pricing data.
- Do not claim invoice exactness from source refresh alone; invoice/dashboard
  comparisons remain a separate Milestone 8 gate.
- Do not publish refreshed source data automatically.
