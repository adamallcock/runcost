---
title: RunCost Aggregation And Streaming
date: 2026-05-25
type: guide
status: draft
---

# RunCost Aggregation And Streaming

RunCost can aggregate already-calculated cost ledgers into a single session, batch, or agent-run ledger. This is the boring primitive needed by streaming wrappers and framework callbacks: price each call with the normal core API, then merge the resulting ledgers.

## Current API

| Language | Function |
|---|---|
| Python | `aggregate_cost_ledgers(cost_ledgers, ...)` |
| JavaScript/TypeScript | `aggregateCostLedgers({ costLedgers, ... })` |
| Go | `AggregateCostLedgers(costLedgers, options)` |

The aggregate ledger:

- Sums `total`.
- Groups components by component name, unit, unit price, price card, and discount eligibility.
- Sums grouped component quantities and costs.
- De-duplicates price sources by name, URL, retrieval timestamp, and version.
- Copies applied discounts and warnings from source ledgers.
- Adds metadata with the observed ledger count.

## Streaming Warning

Some providers and frameworks only expose reliable usage at the end of a stream. If a wrapper expected final usage but did not observe it, call aggregation with the streaming flags.

Python:

```python
from runcost import aggregate_cost_ledgers

ledger = aggregate_cost_ledgers(
    [],
    model="streaming-run",
    expected_ledger_count=1,
    stream_final_usage_expected=True,
    stream_final_usage_present=False,
)
```

JavaScript:

```js
import { aggregateCostLedgers } from "runcost";

const ledger = aggregateCostLedgers({
  costLedgers: [],
  model: "streaming-run",
  expectedLedgerCount: 1,
  streamFinalUsageExpected: true,
  streamFinalUsagePresent: false
});
```

Go:

```go
result := ledger.AggregateCostLedgers([]any{}, ledger.Object{
    "model": "streaming-run",
    "expected_ledger_count": 1,
    "stream_final_usage_expected": true,
    "stream_final_usage_present": false,
})
```

The returned ledger includes `stream_usage_missing`, which means the aggregate total may be incomplete.

## Boundary

This is not yet a provider-specific streaming parser. RunCost does not currently read OpenAI, Anthropic, Gemini, Bedrock, or framework stream chunks directly. The supported contract is:

1. Convert each completed call or final stream usage object into a `CostLedger`.
2. Aggregate the ledgers.
3. Emit an explicit warning when the caller knows an expected final usage ledger is missing.
