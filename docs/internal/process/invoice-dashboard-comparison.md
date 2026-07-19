---
title: Invoice Dashboard Comparison
date: 2026-05-26
type: runbook
status: draft
---

# Invoice Dashboard Comparison

RunCost should not claim invoice exactness until at least one real provider
dashboard or invoice sample has been compared against a RunCost ledger.

This process is intentionally separate from alpha smoke tests. Smoke tests prove
that usage extraction works beside live SDK/API calls. Invoice/dashboard
comparison proves whether the resulting ledger aligns with what a provider
actually billed.

## Required Inputs

- Sanitized RunCost smoke report.
- Provider dashboard row, invoice export, or usage export for the same request
  or narrow time window.
- Price source used by RunCost for the comparison.
- Notes about provider-side rounding, minimum billable units, credits, taxes,
  committed-use discounts, batch/flex/priority tiering, and regional modifiers.
- `evidence_type` in the sanitized comparison input. Use
  `real_provider_export` only for a reviewed provider dashboard, invoice, or
  usage export. Use `sanitized_sample` for checked-in mechanical samples.

Do not commit private invoice exports, account IDs, organization IDs, project
IDs, user prompts, message content, or raw provider responses.
The comparison producer fails before writing output unless the input is marked
`safe_to_commit: true`, `contains_private_billing_export: false`, and uses an
allowed `evidence_type`. It also rejects forbidden keys and secret-like values
in the input, so real provider exports must be reviewed and reduced to sanitized
values before running the command.

Sanitized comparison inputs follow
`schemas/invoice-dashboard-comparison-input.schema.json`. The contract requires
provider values, a RunCost cost ledger, and explicit field mappings before the
comparison producer can write output. For `exact` and `estimated` mappings, each
field must name a comparable RunCost value, ledger path, or component set. This
keeps a real provider export reduction from becoming an ad hoc spreadsheet step.

## Comparison Table

Create a dated report under `docs/internal/reports/` with this shape:

| Field | Provider value | RunCost value | Status | Notes |
|---|---:|---:|---|---|
| Request count |  |  | exact / estimated / unsupported |  |
| Input tokens |  |  | exact / estimated / unsupported |  |
| Cached input tokens |  |  | exact / estimated / unsupported |  |
| Output tokens |  |  | exact / estimated / unsupported |  |
| Reasoning tokens |  |  | exact / estimated / unsupported |  |
| Tool/search/media units |  |  | exact / estimated / unsupported |  |
| Provider-reported cost |  |  | exact / estimated / unsupported |  |
| RunCost total |  |  | exact / estimated / unsupported |  |
| Discounts/credits/taxes |  |  | exact / estimated / unsupported |  |

## Classification

- `exact`: same unit and same rounded monetary value after applying known
  provider rules.
- `estimated`: same conceptual usage, but provider rounding, discounts, credits,
  taxes, exchange rates, or hidden billing adjustments prevent exact matching.
- `unsupported`: provider exposes a billed unit RunCost does not yet model.

## Required Outcome

Every comparison discrepancy must become one of:

- a fixture;
- a structured warning;
- a documented limitation;
- an extractor/source-adapter fix;
- a price-source update.

Milestone 8 is not complete until at least one dated comparison report exists
and its discrepancies have been classified.

## Sample Command

The repository includes a sanitized sample to keep the comparison mechanics
tested without committing private billing exports:

```bash
npm run compare:invoice -- \
  --input fixtures/source-files/invoice-dashboard-comparison-sample.json \
  --output /tmp/invoice-comparison.json

python3 scripts/check_invoice_comparison.py
```

### OpenAI dashboard CSV exports

An administrator-scoped API key is not required when an operator can export a
matching cost CSV and completions-activity CSV from the authenticated OpenAI
dashboard. Keep both raw files outside the repository and run:

```bash
npm run compare:invoice:openai-dashboard -- \
  --cost-export /local/private/cost.csv \
  --activity-export /local/private/activity.csv \
  --output /tmp/openai-dashboard-comparison.json \
  --comparison-id openai-dashboard-export-YYYY-MM-DD \
  --confirm-private-inputs-stay-local \
  --refresh

python3 scripts/check_invoice_comparison.py \
  --comparison /tmp/openai-dashboard-comparison.json \
  --require-real
```

Use `--offline` instead of `--refresh` to replay already cached external price
data. The converter refuses unknown export tiers or incomplete pricing. It
applies published batch/flex reductions as explicit policies, uses the public
standard baseline for undocumented internal tier labels, and emits only a
normalized cost relationship. Absolute costs, token volumes, row counts, tier
mix, and provider identifiers are not retained.

The checked-in validator builds private-looking temporary CSVs and asserts that
none of their private values reach the comparison output. The reviewed real
comparison and its interpretation are recorded in
`docs/internal/reports/2026-07-18-openai-dashboard-export-comparison.md`.

For OpenAI Costs API exports, first reduce the reviewed, sanitized Costs API
page into the generic comparison-input contract:

```bash
npm run compare:invoice:openai-costs-input -- \
  --input fixtures/source-files/openai-costs-comparison-source.json \
  --output /tmp/openai-costs-comparison-input.json

npm run compare:invoice -- \
  --input /tmp/openai-costs-comparison-input.json \
  --output /tmp/openai-costs-comparison.json
```

The checked-in OpenAI Costs source fixture is a sanitized mechanical sample. A
real Milestone 8 artifact must be reduced from a reviewed provider export and
use `evidence_type: real_provider_export`.

The helper runner wraps those two steps. Sample mode is safe for CI:

```bash
npm run compare:invoice:openai-costs -- \
  --mode sample \
  --output /tmp/openai-costs-comparison.json \
  --allow-sample-prices
```

Before a live OpenAI Costs comparison, the alpha preflight can check that the
admin credential name and required comparison input names are present without
printing their values:

```bash
npm run smoke:alpha:preflight -- \
  --openai-costs-start-time 1779753600 \
  --openai-costs-runcost-ledger /tmp/runcost-ledger.json
```

Live mode fetches OpenAI Costs API data using `OPENAI_ADMIN_KEY`, strips
provider identifiers from the fetched page, and requires a RunCost ledger for
the same reviewed time window:

```bash
OPENAI_ADMIN_KEY=... npm run compare:invoice:openai-costs -- \
  --mode live \
  --start-time 1779753600 \
  --end-time 1779840000 \
  --runcost-ledger /tmp/runcost-ledger.json \
  --comparison-id openai-costs-live-YYYY-MM-DD \
  --cost-tolerance 0.005 \
  --output /tmp/openai-costs-live-comparison.json
```

Do not commit the unreduced provider export or the admin key. Commit only the
reviewed sanitized comparison artifact if it passes the real-evidence check.

To validate a real sanitized comparison artifact as Milestone 8 evidence:

```bash
python3 scripts/check_invoice_comparison.py \
  --comparison /tmp/invoice-comparison.json \
  --require-real
```

The real-evidence check rejects artifacts that retain private billing exports
or secret-like values. It also requires every row to be classified as `exact`,
`estimated`, or `unsupported`, and every `estimated` or `unsupported` row must
carry a product-truth action instead of `none`.
The producer applies the same input safety policy before writing a comparison
artifact, and `python3 scripts/check_invoice_comparison.py` includes regression
checks that unsafe inputs do not produce output files.

Comparison outputs follow the generated contract documented from
`schemas/invoice-dashboard-comparison.schema.json`. Validate that contract with:

```bash
npm run check:invoice-contract
```

That check validates both the sanitized input contract and the generated
comparison-output contract.

The checked-in sample report is
`docs/internal/reports/2026-05-26-invoice-dashboard-comparison-sample.md`.
It proves the comparison workflow and classification shape, while the real
OpenAI dashboard comparison in
`fixtures/source-files/openai-dashboard-export-comparison-2026-07-18.json`
satisfies the Milestone 8 evidence gate. The sample comparison still sets
`milestone8_real_evidence` to `false` by design and must never be used as
completion evidence.
