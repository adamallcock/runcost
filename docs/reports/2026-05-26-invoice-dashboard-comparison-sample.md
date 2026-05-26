---
title: Invoice Dashboard Comparison Sample
date: 2026-05-26
type: report
status: draft
---

# Invoice Dashboard Comparison Sample

Comparison ID: `openai-alpha-smoke-sample-2026-05-26`

Source data:

- Provider: `openai`
- Surface: `openai.responses`
- Model: `gpt-alpha-smoke`
- Provider source: sanitized dashboard-style sample
- RunCost source: sample alpha smoke ledger
- Input artifact: `fixtures/source-files/invoice-dashboard-comparison-sample.json`
- Comparison command:

```bash
python3 scripts/compare_invoice_dashboard.py \
  --input fixtures/source-files/invoice-dashboard-comparison-sample.json \
  --output /tmp/invoice-comparison.json
```

This is a sanitized comparison sample. It contains no private billing export,
account identifier, prompt, message content, raw provider response, or API key.
It proves the comparison mechanics and classification loop, but it does not
replace a credentialed provider dashboard or invoice review.

## Comparison

| Field | Provider value | RunCost value | Status | Notes |
|---|---:|---:|---|---|
| Request count | 1 | 1 | `exact` | One sanitized smoke request maps to one dashboard request row. |
| Input tokens | 120 | 120 | `exact` | Provider dashboard reports total prompt/input tokens including cached reads. |
| Cached input tokens | 20 | 20 | `exact` | Provider and RunCost both expose cached read tokens. |
| Output tokens | 40 | 40 | `exact` | Provider output total includes visible text plus reasoning tokens. |
| Reasoning tokens | 8 | 8 | `exact` | Reasoning tokens are first-class in the cost ledger. |
| Tool/search/media units | 1 | 1 | `exact` | Hosted search is represented as one search unit. |
| Provider-reported cost | 0.011188 | 0.011182 | `estimated` | Dashboard total includes provider-side rounding and a small adjustment not represented by the sample price card. |
| RunCost total | 0.011182 | 0.011182 | `exact` | Dashboard sample stores the reviewed RunCost total for traceability. |
| Discounts/credits/taxes | -0.000004 |  | `unsupported` | Provider-side credits, taxes, and rounded adjustments are not modeled by RunCost cost ledgers. |

Summary:

- Exact: 7
- Estimated: 1
- Unsupported: 1

## Product-truth actions

| Finding | Action |
|---|---|
| Provider-reported cost differs from RunCost total by 0.000006 | Documented limitation for provider-side rounding or adjustments until a real dashboard export proves a reusable rule. |
| Provider credits/taxes/adjustments are present | Documented limitation; RunCost cost ledgers intentionally represent API-call usage cost, not taxes, credits, or invoice-level adjustments. |

Next required evidence:

- Run the same comparison process against at least one real provider dashboard,
  invoice export, or usage export.
- If a real discrepancy is reusable, add a fixture, structured warning,
  extractor/source-adapter fix, or price-source update.
