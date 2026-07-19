---
title: RunCost Product Expansion Implementation Plan
date: 2026-07-15
type: plan
status: complete
---

# RunCost Product Expansion Implementation Plan

## Objective

Implement every product enhancement proposed by the July 15 product-market and
distribution assessment, then extend the same auditable accounting model to
asynchronous batch outputs and the newer provider routes proven in
ObviousBench.

On July 18 the product boundary was clarified: public price maintenance belongs
to frequently updated upstream databases, not to a broad catalog embedded in
RunCost. The repo-side implementation must therefore replace the earlier
implicit bundled-catalog path with the accepted external resolver in
`docs/internal/decisions/2026-07-18-external-pricing-source-resolution.md`.

The work must preserve RunCost's product boundary: it remains an offline-first,
deterministic cost ledger and conformance library. The expansion may add thin
integration, policy, and proof surfaces, but it must not become a hosted
gateway, datastore, router, or observability backend.

## Source-of-truth rules

- Provider response and batch shapes come from current official documentation
  or sanitized credentialed evidence, not inference from pricing tables.
- Runtime prices come from caller contracts or named, frequently updated
  external databases. Official provider sources remain the validation basis
  for adapter contracts and explicit test snapshots; RunCost does not freeze a
  broad provider catalog into its packages.
- `schemas/`, `fixtures/`, and the public API registry remain the cross-language
  contracts.
- New provider and batch behavior is complete only when Python, JavaScript, and
  Go pass the same fixture unless a language-specific boundary is deliberate
  and documented.
- Live smokes store sanitized proof only. They must not persist prompts,
  response content, headers, account identifiers, credentials, or raw private
  payloads.

## Workstream 1: first-use and CLI activation

### Deliverables

- Keep deterministic response functions explicit and network-free when price
  cards are supplied; never load a RunCost-owned catalog implicitly.
- Add auto-resolving convenience functions and CLIs that default to named
  external price sources with deterministic fallback, cache, refresh, and
  offline controls.
- Add provider/surface inference only for unambiguous raw shapes; return a
  structured warning or require an explicit surface when inference is unsafe.
- Replace registry and root quickstarts with copy-pasteable external-resolver
  examples that print total, line items, sources, and warnings.
- Add `runcost quote` for JSON objects, JSONL streams, stdin, and files.
- Add an npm `runcost`/`npx runcost` CLI with the same quote output contract.

### Acceptance gates

- Clean Python and npm installs can resolve a named upstream source and
  calculate a fixture in under two minutes without RunCost redistributing the
  upstream database.
- Python and npm CLIs produce equivalent canonical JSON for the same fixture.
- Explicit custom price cards and explicit no-catalog mode remain compatible.

## Workstream 2: first-class batch and newer provider surfaces

### Batch surfaces

- OpenAI Batch output lines for Responses, Chat Completions, Embeddings,
  Images, and other nested endpoints supported by existing extractors.
- Anthropic Message Batches result objects.
- Gemini Developer API batch result objects.
- Vertex AI Gemini batch prediction output objects.
- Amazon Bedrock batch/model-invocation job output objects.
- Batch aggregation helpers that preserve per-item IDs, failures, counts,
  service tier, and partial completion rather than relying on output order.

### Provider surfaces from ObviousBench

- Thinking Machines Tinker/Inkling OpenAI-compatible chat responses, preserving
  the vendor-native `minimal` effort label and stable non-promotional prices.
- NVIDIA NIM OpenAI-compatible chat responses with provider/model namespaces
  preserved.
- Explicit Vertex standard, Flex, and asynchronous batch context.
- Confirm existing Meta and native DeepSeek routes remain complete and add any
  missing alias/surface fixtures discovered by comparison.

### Acceptance gates

- Every batch wrapper delegates nested usage extraction to the matching normal
  endpoint extractor and sets `service_tier=batch` without silently applying a
  discount when no batch price evidence exists.
- Failed/expired items remain visible and never become zero-cost successful
  calls.
- Representative Python, JavaScript, and Go fixtures cover each provider batch
  family and each new provider route.
- An authenticated OpenAI smoke validates the current batch object/result
  contract when account permissions and spend limits allow it; otherwise the
  exact live blocker is recorded while official-contract fixtures remain green.

## Workstream 3: catalog compilation, sharding, and performance

### Deliverables

- Memoize parsed external source caches in every language.
- Generate catalog manifests and deterministic provider shards as generic
  caller-owned or site-build artifacts, not package data.
- Add a compiled/indexed catalog representation used by price selection rather
  than scanning the complete catalog for every component.
- Keep a browser/edge-safe JavaScript calculation entrypoint separate from
  Node-only file loaders and the full catalog.
- Provide an explicit browser/edge auto resolver and allow build-time pinned
  external source caches.
- Add reproducible cold/warm latency, memory, and package-size measurements.
- Enforce conservative CI budgets with an update process rather than one-off
  local numbers.

### Acceptance gates

- Browser, Cloudflare Worker-compatible, and Node import smokes pass without
  Node built-in shims on the browser/core entrypoint.
- Repeated resolver calls do not refetch or reparse a fresh source cache.
- Provider-shard and full-catalog results are ledger-equivalent.
- Performance and package-size checks are deterministic enough for CI and
  include documented escape/update rules.

## Workstream 4: source and telemetry adapters

### Deliverables

- Add a Pydantic `genai-prices` JSON adapter, including provider/model match
  clauses, aliases, cache prices, request prices, tiered input thresholds,
  effective dates, and time-of-day schedules where representable.
- Preserve unsupported source capabilities in metadata and warnings rather
  than dropping them silently.
- Add an OpenTelemetry GenAI span/attribute adapter for standard token, cache,
  reasoning, provider, model, request, trace, and service-tier attributes.
- Add an enricher that returns cost attributes/events without requiring a
  telemetry backend.

### Acceptance gates

- Source-adapter fixtures are polyglot and trace every produced card to the
  upstream source/version.
- OpenTelemetry fixtures cover current stable semantic-convention names and
  safely retain unknown experimental attributes.

## Workstream 5: attribution, estimation, budgets, and reconciliation

### Deliverables

- Add schema-backed attribution metadata for run, session, workflow, tenant,
  feature, and user-defined tags, propagated from usage to cost and aggregate
  ledgers.
- Add stateless pre-call estimation from expected component quantities.
- Add stateless budget evaluation that reports `within_budget`, `warning`, or
  `exceeded` without storing spend or routing requests.
- Add provider-reported-cost reconciliation helpers that expose calculated
  total, reported total, signed/absolute residual, tolerance, and status.
- Add signed SHA-256 catalog manifests and a verification command.

### Acceptance gates

- Attribution survives extraction, calculation, aggregation, batch processing,
  and CLI output without affecting price selection unless an explicit discount
  tag policy uses it.
- Budget policy is deterministic and side-effect free.
- Catalog verification detects one-byte mutation.

## Workstream 6: conformance as a public product

### Deliverables

- Publish a machine-readable and rendered RunCost conformance report generated
  from the fixture corpus.
- Separate “preserved”, “warned”, “unsupported”, and “not tested” outcomes.
- Add a redaction-safe external fixture template, creation command, review
  checklist, and contribution guide.
- Add a one-command conformance runner suitable for external calculators or
  adapters without asserting unsupported competitors' behavior.

### Acceptance gates

- Generated reports are reproducible and checked for drift.
- A freshly generated external fixture passes schema and all requested language
  checks without manual edits.

## Workstream 7: proof and distribution surfaces

### Deliverables

- Build a static, no-account “Explain this response” playground using bundled
  sanitized fixtures and the browser-safe core.
- Add indexable exact-problem pages for general LLM cost calculation, Anthropic
  cache/batch cost, Gemini thinking/batch cost, and OpenAI batch/cache cost.
- Add runnable examples for direct providers, Pydantic AI/`genai-prices`, Vercel
  AI SDK, LangChain, and OpenTelemetry.
- Add a fair methodology page and generated support/conformance matrix.
- Prepare launch copy, case-study template, and a distribution measurement
  runbook centered on successful integrations and external fixtures rather than
  package-download totals.
- Update package descriptions and keywords to include the category language
  users actually search for while retaining the “RunCost Ledger” distinction
  and the `runcost-ai` PyPI installation spelling.

### Acceptance gates

- The playground works over loopback HTTP without uploading response data or
  secrets. Public catalog downloads are visible, and a dated, explicitly
  labelled site-only fallback keeps the demo usable when those downloads fail.
- Social metadata uses a real 1200x630 image and passes repository checks.
- All documented examples execute in CI or a dedicated smoke command.

## Workstream 8: external truth and release readiness

### Deliverables

- Attempt a sanitized real OpenAI Costs API comparison with the authorized
  Keychain-backed credential.
- Attempt the smallest safe OpenAI Batch smoke only if it can be cancelled or
  completed with negligible spend and no private payload retention in repo
  artifacts.
- Update the project completion gates only for evidence actually obtained.
- Produce a dated final implementation and verification report.
- Prepare, but do not publish, the next version. Registry publication, GitHub
  release creation, pushing, and public launch posts remain separate external
  actions unless explicitly authorized.

## Verification ladder

1. Focused Python/JavaScript/Go fixture slices after each contract change.
2. Generated-schema, type, API-registry, docs, catalog, and performance checks.
3. Browser/edge import and static-playground QA.
4. Clean package install and CLI smokes.
5. Full `npm test`, package checks, hygiene, and release-readiness checks.
6. Focused code-quality, test/documentation, and completion review.

## Progress

- [x] Product-market assessment and live competitor refresh.
- [x] Current trunk isolated from the dirty main checkout.
- [x] OpenAI Batch result and discount contract fetched from official docs.
- [x] Workstream 1 external-price correction complete.
- [x] Workstream 2 complete.
- [x] Workstream 3 external-cache/package correction complete.
- [x] Workstream 4 complete.
- [x] Workstream 5 complete.
- [x] Workstream 6 complete.
- [x] Workstream 7 complete.
- [x] Workstream 8 repo-side implementation, attempt, evidence, and release preparation complete.

## Implementation status — July 18, 2026

All eight implementation workstreams and their repository-side acceptance
harnesses are complete. Published artifacts contain zero bundled provider price
data. Automatic resolution selects one of the caller's cards, `genai-prices`,
`models.dev`, LiteLLM, or OpenRouter with explicit cache and warning metadata.
The shared conformance inventory contains 202 cases: 170 established fixtures
and 32 product-expansion cases. Batch failure and pending states are stable
warning-taxonomy values, and all warning codes have fixture coverage.

The authorized Keychain-backed OpenAI smoke completed both a Responses request
and a one-item Batch request. Both produced externally priced ledgers, the Batch
job completed, temporary remote files were deleted, and the strict sanitized
evidence gate passed. The organization Costs API returned HTTP 403, so matching
against a private invoice/dashboard remains an operational evidence task that
requires an administrator-scoped credential or user-supplied billing export.

No package publication, GitHub release, push, Pages deployment, or public post
is part of this implementation branch. Those remain explicit release actions.
