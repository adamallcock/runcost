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

## Comparison Table

Create a dated report under `docs/reports/` with this shape:

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

The checked-in sample report is
`docs/reports/2026-05-26-invoice-dashboard-comparison-sample.md`.
It proves the comparison workflow and classification shape, but Milestone 8
still needs at least one real provider dashboard, invoice export, or usage export
review before invoice/dashboard validation is complete. The sample comparison
sets `milestone8_real_evidence` to `false` by design.
