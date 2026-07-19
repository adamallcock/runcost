---
title: Catalog Performance and Package Budgets
date: 2026-07-18
type: reference
status: complete
---

# Catalog Performance and Package Budgets

Run `python3 scripts/check_catalog_performance.py` to measure imports, compilation
of a synthetic 10,000-card caller-owned catalog, warm deterministic and auto
quotes, resident memory, browser output, package data, and npm tarball size. The
thresholds in `fixtures/source-files/performance-budgets.json` are deliberately
conservative CI regression guards; they are not claims that different machines
have comparable timing.

External price responses are cached persistently with freshness metadata and
memoized in-process. Their canonical cards are compiled into provider/model/alias
indexes once per process. The deterministic APIs can also accept a precompiled
caller-owned catalog for high-throughput loops and batches.

Published Python, npm, and Go artifacts must contain zero bundled provider price
data. The benchmark uses synthetic data generated in memory, and the npm browser
entrypoint uses the same external resolver with an in-memory cache.

To raise a threshold, attach a dated `--write-report` before/after result,
explain the regression, and review whether the same behavior can be represented
without expanding the published package or weakening the no-bundled-prices
boundary.
