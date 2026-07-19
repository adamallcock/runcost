---
title: OpenAI Dashboard Export Comparison
date: 2026-07-18
type: report
status: evidence
---

# OpenAI Dashboard Export Comparison

## Outcome

A matching one-day OpenAI dashboard cost export and completions-activity export
were compared locally against RunCost `0.2.0`. The strict real-evidence check
passes, so the Milestone 8 invoice/dashboard comparison gate is satisfied.

This result is deliberately not an invoice-exactness claim. Every activity row
was priced, but the public-list-price RunCost estimate was materially above the
provider-reported total. The durable artifact classifies that difference as an
`unsupported` provider-pricing condition with a documented-limitation action.

## Privacy Boundary

The raw dashboard CSV files remained local and are not tracked. The comparison
runner omits absolute costs, token volumes, export row counts, tier mix, and all
account, project, key, user, and organization identifiers. Only the matching
window, full-pricing coverage, normalized cost relationship, classifications,
and product-truth actions are retained.

The sanitized evidence artifact is
`fixtures/source-files/openai-dashboard-export-comparison-2026-07-18.json`.

## Results

| Check | Result |
|---|---:|
| Matching non-empty cost and activity exports | exact |
| Activity rows fully priced | 100% |
| Provider-reported cost, normalized | 1.000000 |
| RunCost public-price estimate, normalized | 2.213151 |
| Difference from provider-reported cost | +121.3151% |
| Classified fields | 4 exact, 1 unsupported |

The normalized result means RunCost's public-price estimate was approximately
2.213151 times the provider-reported dashboard cost for this reviewed window.
No absolute monetary value is retained.

## Interpretation

The comparison exposed a real accounting boundary rather than a calculator
failure:

- The dashboard activity export contained a provider-internal
  `incentivized-tier` label for which the public catalog does not provide an
  account-specific price. The runner uses the public standard rate as the
  auditable baseline rather than inventing an undisclosed discount.
- Published batch and flex reductions are applied as explicit RunCost policies,
  separate from the external public price cards.
- Dashboard activity is aggregated. It does not preserve each request's input
  length, so the runner uses average input per request when selecting any
  long-context price condition.
- Some public model cards do not price cache writes separately. When cache
  writes are the only missing component, the runner folds them into uncached
  input and records that deterministic fallback locally before aggregation.

The provider-reported dashboard cost therefore remains authoritative for
reconciliation. RunCost remains useful as an independently explainable
public-price ledger, and the residual is now visible instead of being hidden or
misrepresented as zero.

## Reproduction

The privacy-preserving runner is
`scripts/run_openai_dashboard_export_comparison.py`. It requires an explicit
acknowledgement that the raw inputs stay local:

```bash
npm run compare:invoice:openai-dashboard -- \
  --cost-export /local/private/cost.csv \
  --activity-export /local/private/activity.csv \
  --output /tmp/openai-dashboard-comparison.json \
  --comparison-id openai-dashboard-export-YYYY-MM-DD \
  --confirm-private-inputs-stay-local \
  --offline

python3 scripts/check_invoice_comparison.py \
  --comparison /tmp/openai-dashboard-comparison.json \
  --require-real
```

The checked-in validator also constructs private-looking temporary CSV inputs,
exercises tier discounting and cache-write fallback with deterministic price
cards, and asserts that none of the private values reach the output.

## Decision

Milestone 8 and public beta may close because a real export was compared, every
row was priced, the discrepancy was classified, and the product limitation is
durable and testable. RunCost must continue to describe provider-reported costs
as reconciliation truth when private discounts, credits, or undocumented tiers
are present.
