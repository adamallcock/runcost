---
title: Local Installation and Reconciliation Recipe
date: 2026-10-04
type: guide
status: active
---

# Local Installation and Reconciliation Recipe

Use an installed package and one response with an independently observed USD charge for exactly the same scope. A dashboard total for several requests cannot validate one response. Keep private responses, invoices, identifiers, and reports outside this public checkout.

Create a clean virtual environment, install the intended PyPI version or candidate wheel, and run from a temporary directory outside the repository:

```bash
python3 -m venv /tmp/runcost-integration
/tmp/runcost-integration/bin/python -m pip install /absolute/path/to/candidate.whl
cd /tmp
/tmp/runcost-integration/bin/python /absolute/path/to/runcost/scripts/run_local_integration.py \
  --response /private/path/response.json \
  --provider openai --surface openai.responses \
  --reported-total 0.001 --tolerance 0.000001 \
  --cache-dir /private/path/runcost-cache \
  --output /private/path/sanitized-comparison.json
```

The first quote retrieves public price data when necessary. The response is processed locally. The second quote runs offline against the same cache and must preserve component costs and total. `--offline` makes both quotes use an existing cache. The report records timings, offline parity, reconciliation residuals, and a sharing copy of the ledger. A nonzero exit means the comparison mismatched, offline parity failed, or pricing warnings need review.

The Python and npm CLIs accept the same price-cache envelope. To check a clean npm candidate too, install a freshly packed tarball in another temporary project and quote the same response with `runcost quote ... --offline --cache-dir /private/path/runcost-cache`. Compare component costs and total, allowing extraction-path metadata to differ.

`export_cost_ledger`, `exportCostLedger`, and Go `ExportCostLedger` make an allowlisted copy. They remove raw usage, arbitrary metadata, debug traces, attribution, source URLs, and warning details. The original ledger retains full local audit evidence. Model names, rate-card identifiers, discount identifiers, quantities, and amounts remain in the copy; review those fields before sharing a report.

Package tests use synthetic evidence to verify this workflow. Independent customer adoption and invoice accuracy require actual scoped evidence; a synthetic success does not close those gates.
