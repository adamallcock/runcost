---
title: DeepSeek Peak-Valley Pricing Design
date: 2026-07-05
type: decision-record
status: accepted
---

# DeepSeek Peak-Valley Pricing Design

## Decision

RunCost should handle peak, off-peak, and other time-window pricing as a
price-selection dimension, not as new token components and not as a discount.

The recommended model is:

- Keep usage components stable: `input_uncached_tokens`,
  `input_cache_read_tokens`, `output_text_tokens`, and
  `output_reasoning_tokens` remain the correct DeepSeek billing components.
- Add a generic pricing-period dimension to price cards and usage context.
- Derive the pricing period from an explicit billing timestamp when a reviewed
  price source defines a repeating billing schedule.
- Preserve the selected period and window in component metadata and debug
  traces.
- Add a reviewed DeepSeek official snapshot only after the effective timestamp
  and peak windows are confirmed from an official public page, account notice,
  or sanitized billing evidence.

This keeps the calculator deterministic and offline while still letting users
price historical DeepSeek usage accurately.

## Implementation Status

Accepted and implemented for the generic pricing-period mechanism:

- Price cards support `pricing_period` and UTC `billing_schedule`.
- Usage context supports explicit `pricing_period`.
- DeepSeek chat completion extraction promotes response `created` to
  `context.priced_at`.
- Python, JavaScript, and Go share fixture-backed selection behavior for
  regular windows, both peak windows, boundary handling, explicit period
  override, missing-time warnings, synthetic official-snapshot-shaped adapter
  mapping, and raw DeepSeek response extraction.

Bundled DeepSeek default catalog prices are intentionally unchanged until the
effective peak schedule is confirmed from public DeepSeek docs, an account
notice, or sanitized billing evidence.

## Evidence Checked

Public DeepSeek docs checked on 2026-07-05 EDT:

- DeepSeek public model pricing currently lists flat prices for
  `deepseek-v4-flash` and `deepseek-v4-pro`, in USD per 1M tokens:
  <https://api-docs.deepseek.com/quick_start/pricing/>
- The same page says `deepseek-chat` and `deepseek-reasoner` are scheduled for
  deprecation on 2026-07-24 15:59 UTC and currently map to V4 Flash
  compatibility behavior.
- DeepSeek Chat Completions usage reports `prompt_tokens`,
  `prompt_cache_hit_tokens`, `prompt_cache_miss_tokens`, `completion_tokens`,
  `total_tokens`, and optional
  `completion_tokens_details.reasoning_tokens`:
  <https://api-docs.deepseek.com/api/create-chat-completion>
- DeepSeek context caching docs confirm `prompt_cache_hit_tokens` and
  `prompt_cache_miss_tokens` are the cache-hit/cache-miss billing split:
  <https://api-docs.deepseek.com/guides/kv_cache>

User-provided screenshot evidence, not yet verified against the public pricing
page:

- It says the official DeepSeek V4 release is scheduled for mid-July.
- It says pricing will move to a peak-valley mechanism on release.
- It lists peak hours as 01:00-04:00 UTC and 06:00-10:00 UTC.
- It lists regular prices equal to the current public DeepSeek prices:
  - `deepseek-v4-pro`: cache hit `$0.003625`, cache miss `$0.435`, output
    `$0.87`.
  - `deepseek-v4-flash`: cache hit `$0.0028`, cache miss `$0.14`, output
    `$0.28`.
- It lists peak prices as exactly 2x regular:
  - `deepseek-v4-pro`: cache hit `$0.00725`, cache miss `$0.87`, output
    `$1.74`.
  - `deepseek-v4-flash`: cache hit `$0.0056`, cache miss `$0.28`, output
    `$0.56`.
- It says a 24-hour email notice will be sent before the actual pricing update
  date.

Until the effective date is official, these peak rows should be treated as
planning evidence, not as release-ready bundled price data.

## Current RunCost Fit

RunCost already has most of the right primitives:

- DeepSeek cache and reasoning extraction is fixture-backed in
  `fixtures/deepseek-chat-raw-cache-reasoning.json`.
- The canonical component taxonomy already separates uncached input, cache-read
  input, visible output, and reasoning output.
- `PriceCard` supports provider, surface, model, aliases, service tier, region,
  effective date ranges, component-level conditions, source metadata, and exact
  decimal prices.
- `UsageContext.priced_at` already exists and is used for effective-date
  selection and stale-price warnings.
- `price_source_disagreement` already catches conflicting source rows.

The important gaps are:

- `priced_at` is currently reduced to a date for selection, so it cannot choose
  a recurring time-of-day billing window.
- There is no canonical `pricing_period` or `billing_window` field.
- There is no structured warning for period-specific price cards when the
  usage lacks a timestamp or explicit period.
- OpenAI-compatible chat extraction currently does not promote a provider
  response `created` timestamp into `context.priced_at`.
- The bundled default catalog includes DeepSeek V4 rows from generic upstream
  sources. In a local probe, `deepseek-v4-pro` default selection chose an older
  `llm-prices` row at `$3.48` per 1M output tokens and emitted a
  `price_source_disagreement` warning against the lower `models.dev` row. A
  reviewed DeepSeek official source should outrank generic catalogs once
  adopted.

## Rejected Designs

### New usage components

Do not add components such as `peak_input_tokens` or
`off_peak_output_tokens`.

Peak status describes how the same usage is priced, not what was consumed. New
components would fragment fixtures, downstream dashboards, and cross-provider
comparisons.

### Service tier overload

Do not model DeepSeek peak hours as `service_tier: peak`.

Service tier means a requested or served quality/capacity mode such as
standard, priority, batch, or provisioned. DeepSeek peak status is determined
by billing time. Reusing service tier would make actual service-tier providers
harder to reason about.

### Discount or markup policy

Do not model peak price as a 100 percent markup discount policy.

The peak price is a provider-published base price, not a customer-specific
post-price adjustment. Using discounts would make source provenance and
invoice reconciliation weaker, and it would interact badly with real customer
discounts.

### Date-only effective ranges

Do not try to express recurring daily peak windows with date ranges.

That would require unbounded generated rows and still would not encode the
timezone or boundary policy.

### Runtime network lookup

Do not fetch the current DeepSeek pricing page during cost calculation.

RunCost's calculator must remain offline, deterministic, and auditable. Network
refresh belongs in explicit source-cache generation.

## Proposed Data Contract

### Usage context

Add optional fields to `UsageContext`:

```json
{
  "priced_at": "2026-07-15T01:30:00Z",
  "pricing_period": "peak"
}
```

Rules:

- `priced_at` should accept a full ISO 8601 timestamp with timezone for
  time-window pricing.
- Date-only `priced_at` remains valid for existing effective-date behavior, but
  cannot derive a pricing period.
- `pricing_period` is an explicit override for invoice imports or callers that
  already know the provider's billing period.
- If both are present, `pricing_period` wins, and debug trace should record
  that period selection was explicit.
- If neither is present and only period-specific cards match the model, return
  a structured warning rather than silently selecting regular prices.

For raw DeepSeek responses, extraction should set `context.priced_at` from the
provider response `created` Unix timestamp when present. A caller-provided
context timestamp should override the extracted timestamp for backfills and
invoice reconciliation.

### Price cards

Add optional fields to `PriceCard`:

```json
{
  "pricing_period": "peak",
  "billing_schedule": {
    "timezone": "UTC",
    "default_period": "regular",
    "boundary_policy": "start_inclusive_end_exclusive",
    "windows": [
      {"period": "peak", "start": "01:00", "end": "04:00"},
      {"period": "peak", "start": "06:00", "end": "10:00"}
    ]
  }
}
```

Rules:

- `pricing_period` is a selector like provider, model, surface, region, and
  service tier.
- A card without `pricing_period` remains a generic card and keeps current
  behavior.
- If usage context has `pricing_period`, matching should prefer cards with the
  same period over generic cards.
- If usage context has `priced_at` and a candidate card has a
  `billing_schedule`, derive the period before selecting cards.
- The first implementation should support UTC schedules. Provider-local
  schedules should be normalized into UTC in the reviewed source snapshot until
  IANA timezone support is fixture-backed across Python, JavaScript, and Go.
- Windows are half-open: start inclusive, end exclusive. For the screenshot
  schedule, `01:00:00Z` is peak and `04:00:00Z` is regular.
- Overnight windows should be allowed eventually, but the DeepSeek case does
  not require them.

### Cost ledger metadata

For period-selected components, include metadata such as:

```json
{
  "pricing_period": "peak",
  "pricing_window": "01:00-04:00",
  "pricing_timezone": "UTC",
  "period_selection": "derived_from_priced_at"
}
```

This makes aggregation by peak/off-peak possible without reparsing price-card
IDs.

### Warning taxonomy

Add warning codes only if implementation needs behavior that existing warnings
cannot express cleanly:

- `pricing_period_required`: period-specific price cards exist, but usage has
  no full timestamp and no explicit `pricing_period`.
- `pricing_period_unsupported`: usage requests a period for which no matching
  card exists.
- `billing_schedule_unsupported`: a source declares a schedule shape or
  timezone the runtime cannot safely evaluate.

Each warning should have required metadata in `schemas/taxonomy.json` and
generated language types.

## DeepSeek Snapshot Shape

Once the effective date is confirmed from official evidence, add a reviewed
official snapshot such as
`fixtures/source-files/deepseek-official-pricing-snapshot.json`. Until then,
keep examples and fixtures labeled as synthetic:

```json
{
  "type": "official-snapshot",
  "provider": "deepseek",
  "surface": "deepseek.chat_completions",
  "source": {
    "name": "deepseek-official",
    "url": "https://api-docs.deepseek.com/quick_start/pricing/",
    "retrieved_at": "2026-07-15T00:00:00Z",
    "license": "reviewed"
  },
  "per": "1000000",
  "billing_schedule": {
    "timezone": "UTC",
    "default_period": "regular",
    "boundary_policy": "start_inclusive_end_exclusive",
    "windows": [
      {"period": "peak", "start": "01:00", "end": "04:00"},
      {"period": "peak", "start": "06:00", "end": "10:00"}
    ]
  },
  "rows": [
    {
      "model": "deepseek-v4-pro",
      "pricing_period": "regular",
      "effective": {"from": "2026-07-15"},
      "input_cache_read": "0.003625",
      "input": "0.435",
      "output": "0.87"
    },
    {
      "model": "deepseek-v4-pro",
      "pricing_period": "peak",
      "effective": {"from": "2026-07-15"},
      "input_cache_read": "0.00725",
      "input": "0.87",
      "output": "1.74"
    }
  ]
}
```

The real `effective.from` must come from official evidence. If DeepSeek gives
an exact effective timestamp rather than a date, the schema should preserve it
in metadata even if date-level effective matching remains separate from
time-window matching.

## Matching Algorithm

Recommended order:

1. Build usage context.
2. If caller provided `context.pricing_period`, use it.
3. Else if `context.priced_at` is a full timestamp and matching price cards
   expose a billing schedule, derive `pricing_period`.
4. Filter candidate price cards by provider, surface, model, service tier,
   region, effective date, and pricing period.
5. Score exact period matches above generic cards.
6. Select component prices using existing component-name and condition logic.
7. Attach period metadata to cost components and debug trace.
8. Emit period warnings when selection cannot be determined.

Timestamp precedence for extractors:

1. Caller-provided `context.priced_at`.
2. Provider response timestamp, such as DeepSeek `created`.
3. No timestamp. Do not substitute current wall-clock time for historical
   pricing.

## Fixture Matrix

Add one focused fixture family before changing public package data:

- `deepseek-peak-pricing-regular-window.json`: prices a call outside both peak
  windows with regular rates.
- `deepseek-peak-pricing-first-window.json`: prices `01:00:00Z` through before
  `04:00:00Z` with peak rates.
- `deepseek-peak-pricing-second-window.json`: prices `06:00:00Z` through before
  `10:00:00Z` with peak rates.
- `deepseek-peak-pricing-boundary-*.json`: proves `00:59:59Z` regular,
  `01:00:00Z` peak, `04:00:00Z` regular, `05:59:59Z` regular,
  `06:00:00Z` peak, and `10:00:00Z` regular across focused boundary fixtures.
- `deepseek-peak-pricing-explicit-period.json`: proves
  `context.pricing_period` overrides derived timestamp selection.
- `deepseek-peak-pricing-missing-time-warning.json`: proves period-specific
  cards do not silently underprice usage when no timestamp or period exists.
- `deepseek-official-snapshot-period-adapter.json`: uses synthetic
  official-snapshot-shaped data to prove the adapter preserves
  `pricing_period` and `billing_schedule`.
- `deepseek-chat-created-priced-at.json`: proves DeepSeek/OpenAI-compatible
  extraction promotes `created` to `context.priced_at`.

All fixtures should run through Python, JavaScript, and Go, and generated docs
should be refreshed with:

```bash
python3 scripts/check_fixture_coverage.py --write-report
python3 scripts/check_cost_accounting.py --write-report
python3 scripts/generate_contract_docs.py --write
```

## Release And Catalog Plan

Do not update bundled DeepSeek peak prices until the effective timestamp is
confirmed.

When confirmed:

1. Capture sanitized evidence under `docs/internal/reports/`.
2. Add or update `fixtures/source-files/deepseek-official-pricing-snapshot.json`.
3. Add `deepseek-official` to `scripts/build_default_price_catalog.py` before
   generic sources.
4. Regenerate all package default source caches.
5. Check whether default source-cache priority is carried into normal cost
   calculation. If not, add a small public helper or internal option so the
   bundled reviewed priority is not lost.
6. Run the source-refresh, fixture, coverage, hygiene, package, and release
   readiness checks.
7. If credentials or billing export evidence is available, run a sanitized live
   DeepSeek smoke across one regular timestamp and one peak timestamp, or
   compare against a provider invoice/export.

## Open Questions

- Does DeepSeek bill peak status by request acceptance time, response `created`
  time, completion time, or another server-side ledger timestamp?
- Are the exact boundary instants half-open as assumed here?
- Will all DeepSeek V4 surfaces use the same schedule, including OpenAI-format,
  Anthropic-format, FIM, and future endpoints?
- Will `deepseek-chat` and `deepseek-reasoner` compatibility aliases receive
  the same V4 Flash period pricing until their 2026-07-24 deprecation?
- Will DeepSeek publish peak status in API responses, account usage exports, or
  invoices?

## Done Criteria

This work is complete only when:

- Public or sanitized account evidence confirms the effective date and schedule.
- Period selection is schema-backed and fixture-backed across Python,
  JavaScript, and Go.
- Missing timestamps produce structured warnings instead of silent regular-rate
  estimates.
- DeepSeek official snapshot rows outrank stale generic catalog rows.
- DeepSeek cache hit, cache miss, output, and reasoning-output behavior remain
  covered by fixtures.
- Generated docs, taxonomy types, default source cache, package installs,
  release readiness, and project hygiene all pass.
