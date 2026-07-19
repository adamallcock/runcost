---
title: RunCost Expansion Launch Copy
date: 2026-07-18
type: report
status: ready
---

# RunCost Expansion Launch Copy

These drafts are intentionally specific. Publish only after the branch is
merged, the Pages deployment is live, and the package release train is complete.

## Positioning sentence

RunCost Ledger turns the LLM response or batch result you already have into an
auditable cost breakdown—with cached, reasoning, tool, tier, price-source, and
warning details intact across Python, JavaScript, and Go.

## GitHub release lead

RunCost now has one-call pricing from named external databases, matching
Python/npm quote CLIs, an edge-safe core, and no provider price database in its
packages. The release also adds batch ledgers for OpenAI, Anthropic, Gemini,
Vertex, Bedrock, Kimi, and DashScope; a Pydantic genai-prices adapter;
OpenTelemetry GenAI enrichment; stateless estimates/budgets; reconciliation;
and a public fixture-backed conformance report.

The release also adds a no-account browser playground. Pasted responses stay in
the browser; every selected rate, dated source, component, and warning remains
visible.

## Short social post

Most “LLM cost calculators” multiply two token counts. That breaks once cache,
reasoning, tools, tiers, batch discounts, and historical prices matter.

RunCost explains the number from the response you already have. New: one-call
pricing from current external sources, batch APIs, browser playground, OTel,
genai-prices, CLI parity, and a 202-case public conformance inventory.

Try it: https://adamallcock.github.io/runcost/playground/
Source: https://github.com/adamallcock/runcost

## Community post

I built RunCost because the difficult part of LLM costing is no longer the
multiplication. It is knowing whether cached input, reasoning output, tools,
media, batch/tier context, and the correct historical price survived the trip
from provider response to total.

The project is deliberately not another proxy or dashboard. It is a local,
cross-language accounting layer that returns components, provenance, warnings,
and a decision trace. The new release makes the simple path genuinely simple
and adds batch normalization, OpenTelemetry and genai-prices adapters, direct
provider routes, catalog integrity checks, and a no-account playground.

I would particularly value sanitized “this bill did not reconcile” fixtures.
The contribution path keeps failures and ambiguity visible instead of asking
for polished success stories.

## Outreach email

Subject: A fixture-backed LLM cost ledger you can embed without a proxy

Hi — I maintain RunCost, an MIT-licensed Python/TypeScript/Go library that
normalizes provider usage into componentized, source-attributed cost ledgers.
It now handles common synchronous and batch result shapes, preserves failed
items and pricing warnings, and can enrich existing OpenTelemetry GenAI spans.

I am looking for a small number of real, sanitized integration or reconciliation
cases—not endorsements. If your project currently has hand-written token math
or a provider/dashboard discrepancy, I can help turn one example into a public
fixture and document the remaining residual honestly.

Playground: https://adamallcock.github.io/runcost/playground/
Conformance: https://github.com/adamallcock/runcost/blob/main/docs/generated/conformance-report.md

## Publication gate

- Live Pages URL returns the expected eight routes and social image.
- PyPI, npm, GitHub Release, and Go tag show the same new version.
- README snippets run from clean installs.
- Any real reconciliation evidence is sanitized and linked.
- Claims use the current generated conformance count and verified source list.
