---
title: DeepSeek Weekly Timezone Pricing Contract
date: 2026-08-22
type: decision-record
status: accepted
---

# DeepSeek Weekly Timezone Pricing Contract

## Decision

RunCost price cards may describe recurring billing windows in an IANA
timezone. `UTC` remains a valid timezone value and remains compatible with
existing cards.

Each billing window may include an optional `days_of_week` array containing
lowercase local weekday names from `monday` through `sunday`. When omitted,
the window applies on every local calendar day. The weekday filter is applied
to the local calendar day on which the window starts. A window that crosses
midnight retains that start day; it does not move its weekday membership to
the following day.

The schedule keeps the existing `start_inclusive_end_exclusive` boundary
policy. `default_period` applies to every local time and local day that does
not match a valid window. An unrecognized or malformed weekday list is not a
request to ignore the filter: the runtime must fail closed with
`billing_schedule_unsupported` and leave the usage unpriced.

## Effective bounds

`effective.from` and `effective.to` may each be either an ISO full date or an
RFC3339 date-time.

- A date-only bound retains the existing inclusive whole-day behavior in UTC.
- A date-time is an instant. `from` is inclusive and `to` is exclusive.
- A card with a precise date-time effective bound must not be selected when
  the usage context has no timestamp precise enough to compare to that bound.

This keeps historical date-only cards compatible while preventing a date-only
comparison from selecting a card whose applicability begins or ends at a
precise instant.

## Synthetic fixture boundary

The weekly DeepSeek cards in this change use deliberately synthetic prices
and a synthetic source name. They are contract/conformance data only; they do
not represent DeepSeek's published rates, a private account notice, an email
address, or verified provider time-window evidence.

That boundary is now complemented, rather than replaced, by
`fixtures/source-files/deepseek-official-pricing-snapshot.json`. It records the
reviewed public DeepSeek pricing page as retrieved on 2026-08-23, including its
weekday-only UTC peak windows and published rates. It remains explicit
conformance/source-adapter data: RunCost deliberately does not ship a bundled
default provider catalog, so callers must choose and provide a reviewed source
cache or price cards for production calculations.

The fixture schedules cover:

| Fixture | Contract behavior |
|---|---|
| `deepseek-weekly-pricing-asia-shanghai-weekday-peak` | A weekday peak window evaluated in `Asia/Shanghai` local time. |
| `deepseek-weekly-pricing-weekend-offpeak` | Weekend times fall through to the whole-weekend `default_period`. |
| `deepseek-weekly-pricing-sunday-monday-boundary` | A Sunday 23:00–Monday 01:00 window remains active at Monday 00:30 because its start day is Sunday. |
| `deepseek-weekly-pricing-effective-start` | A precise card is selected at `2026-08-22T16:00:00Z`, which is 00:00 on Sunday in Beijing. |
| `deepseek-weekly-pricing-effective-before-start` | The preceding second selects the older precise-effective card. |
| `deepseek-effective-timestamp-required` | A precise-effective card cannot outrank an unbounded card when usage has no timestamp. |
| `deepseek-effective-date-offset-boundary` | Date-only effective bounds use UTC even when usage supplies an RFC3339 offset. |
| `deepseek-weekly-pricing-malformed-weekday-list` | An unrecognized weekday entry fails closed with no priced components. |

Product-expansion conformance verifies that the `genai-prices` adapter
preserves a representable weekday/timezone schedule (including its common
camel-case aliases) and omits a row with an unrepresentable semantic
constraint. It does not turn that constraint into an unconstrained price card.

## Integration dependency

The Python, JavaScript, and Go calculators must independently implement IANA
timezone conversion, local-day window matching, midnight-crossing start-day
semantics, malformed-weekday fail-closed handling, and instant-aware effective
range selection before the shared fixtures can pass cross-language conformance.
