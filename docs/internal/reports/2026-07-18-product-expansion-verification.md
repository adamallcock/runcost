---
title: RunCost Product Expansion Verification
date: 2026-07-18
type: report
status: passed
---

# RunCost Product Expansion Verification

## Verdict

**PASS — the product expansion is implemented, live-provider-smoked, rendered,
and package-verified.**

RunCost remains a deterministic costing and audit library rather than a pricing
database. Published Python, npm, browser, and Go artifacts contain no bundled
provider price catalog. The convenience APIs select one caller-supplied or
external catalog, record the selected source, and preserve warnings instead of
silently combining conflicting databases.

No tag, registry publication, GitHub release, push, or Pages deployment was
performed during this work.

## Implemented Contract

- Existing deterministic APIs remain network-free and require caller-owned
  price cards.
- Opt-in automatic APIs resolve explicit cards first, including an explicitly
  empty list that deliberately disables network lookup. They then try
  `genai-prices`, `models.dev`, and LiteLLM. OpenRouter-billed requests prefer
  OpenRouter's Models API before those general sources.
- A resolver selects one source; it never silently merges price databases.
  Resolution metadata, timestamps, validators, checksums, cache state, and
  fallback warnings remain visible in the resulting ledger.
- Python, Node.js, and Go use atomic persistent caches with a 24-hour default
  freshness window and last-known-good fallback. Browser and edge builds use
  process memory because they do not have a portable filesystem.
- Response, Batch, OpenTelemetry GenAI, and pre-call estimate helpers all have
  automatic-resolution variants.
- Batch normalization covers OpenAI Responses, Chat Completions, Embeddings,
  and Images; Anthropic Messages; Gemini; Vertex AI; Amazon Bedrock; Kimi; and
  DashScope. Failed and pending items remain visible and never inflate totals.
- Direct-provider examples cover Tinker and NVIDIA from ObviousBench plus AI21,
  Arcee, Cohere-compatible, DashScope, Inception, MiniMax, Poolside, Xiaomi, and
  ZAI routes. The current ObviousBench-specific DeepSeek, Kimi, Meta, NVIDIA,
  Tinker, and Vertex pathways are covered.
- Attribution, budgets, pre-call estimates, OpenTelemetry cost attributes,
  catalog-manifest verification, aggregation, and invoice/dashboard
  reconciliation form the accounting and audit layer.

## Automated Verification

The following completed successfully on 2026-07-18:

```text
npm test
npm run check:coverage
npm run check:packages
npm run check:release
npm run check:release-dry-run
npm run check:playground
go test -race ./packages/go/...
go vet ./packages/go/...
git diff --check
```

The verified results include:

- 170 shared core fixtures passing in Python, JavaScript, and Go.
- 32 expansion cases passing with Python/JavaScript parity and corresponding Go
  package coverage.
- 202 conformance cases inventoried: 148 preserved, 47 explicitly warned, and
  7 explicitly unsupported; none are untested.
- 89 explicit official-snapshot price cards passing adapter conformance.
- All warning codes, public API registry entries, schemas, generated docs,
  generated types, and cost-accounting evidence passing coverage checks.
- Fresh external-fixture generation passing independently in Python,
  JavaScript, and Go, followed by removal of the temporary fixture.
- Installed wheel/source, npm tarball/browser/CLI, and external Go-module smokes
  passing without bundled provider pricing.
- Python wheel and source distribution `0.2.0`, npm tarball `runcost-0.2.0.tgz`,
  and a clean external Go import building in the release dry run.
- The npm tarball contains seven files and is approximately 0.10 MB compressed;
  the browser entrypoint is approximately 0.25 MB. Python, JavaScript, and Go
  bundled price-data measurements are all exactly zero.
- A synthetic caller-owned 10,000-card catalog compiles in under 10 ms in both
  Python and JavaScript on this machine; 500 warm quotes and 100 warm automatic
  quotes also remain under 10 ms in both runtimes.
- All four live external sources—`genai-prices`, `models.dev`, LiteLLM, and
  OpenRouter—downloaded, normalized, cached, and resolved successfully in the
  opt-in live checks.

## Live OpenAI Evidence

The authorized Keychain-backed smoke completed without printing or retaining
the credential:

- A live OpenAI Responses request returned usage and produced a priced ledger
  from `genai-prices` with no pricing warnings.
- A live OpenAI Batch request completed with one successful item and produced a
  priced aggregate ledger from the same external source.
- Both temporary OpenAI files were deleted.
- The sanitized evidence contains no credential, request/account identifiers,
  private payloads, response text, or cost amounts and is recorded at
  `fixtures/source-files/openai-expansion-live-smoke-2026-07-18.json`.
- The strict evidence gate passed with
  `python3 scripts/check_openai_expansion_smoke.py --require-passed`.

The organization Costs API probe returned HTTP 403, recorded as
`blocked_admin_scope_or_endpoint_permission`. This is an invoice-reconciliation
permission boundary, not a response or batch costing failure. A real private
billing export remains necessary to validate dashboard reconciliation against
the user's own organization.

## Rendered Playground QA

The production build contains eight pages and a valid 1200 by 630 social image.
Rendered localhost QA covered the response playground and Batch page at desktop
and mobile breakpoints:

- OpenAI loaded with a live-or-cached external `genai-prices` source.
- Switching to Anthropic resolved LiteLLM pricing.
- Editing the sanitized response and submitting it changed the calculated total
  from `$0.0181512` to `$0.0027912`.
- Switching the Batch ledger to Bedrock produced one successful item and the
  expected `$0.00018` total.
- No console warnings or errors were emitted.
- A 962px layout defect that clipped the final cost-table column was found and
  corrected by stacking the workbench before the table becomes constrained.
- At a 390px CSS viewport, there is no page-level horizontal overflow; wide
  ledger tables remain inside their explicit horizontal-scroll containers.

## Remaining Operational Work

Implementation is complete. Publishing the branch, deploying the playground,
and obtaining an organization billing export are separate release and
operations actions. They were not implicitly performed by this verification.
