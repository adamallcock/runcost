---
title: Beta And V1 Hardening Roadmap
date: 2026-05-26
type: plan
status: draft
---

# Beta And V1 Hardening Roadmap

This document keeps the post-private-alpha work explicit. Milestones 0-7 are
complete for current scope, but public beta and V1 require live evidence,
publishing proof, generated-artifact discipline, and stronger provider breadth.

## Public Beta Gate

Public beta requires:

- Milestone 8 alpha smoke harness exists and has at least one real live run.
- Every live smoke finding is converted into a fixture, warning, documented
  limitation, extractor/source fix, or price-source update.
- At least one invoice/dashboard comparison report exists under `docs/reports/`.
- PyPI and npm trusted publishing are configured externally.
- The guarded release workflow has been run with publishing disabled and
  reviewed.
- A real Go semantic version tag has been verified from a clean external module.
- Known non-invoice-exact cases are documented in the support and warning docs.
- Source-data refresh/update process has an owner, cadence, and review path in
  `docs/process/2026-05-26-source-data-update-process.md`.

The machine-readable gate register lives at
`fixtures/source-files/project-completion-gates.json`. Normal CI validates that
the register is well-formed and that referenced evidence exists:

```bash
npm run check:gates
```

When the external evidence exists, use the strict checks before calling a gate
complete:

```bash
python3 scripts/check_project_completion_gates.py --require-milestone8
python3 scripts/check_project_completion_gates.py --require-public-beta
python3 scripts/check_project_completion_gates.py --require-v1
```

Those strict checks are expected to fail until the live smoke, real invoice or
dashboard comparison, registry configuration, real-version no-publish
rehearsal, and real Go tag verification have actually happened.

## Polyglot Hardening Gate

The current polyglot strategy remains:

- JSON schemas define data contracts.
- Shared fixtures define behavior.
- Python, JavaScript/TypeScript, and Go implementations remain handwritten and
  idiomatic.
- Generated artifacts should be types, docs, validators, matrices, and drift
  checks rather than cost-calculation business logic.

Hardening work:

- Choose schema-derived type generation tools for TypeScript, Python, and Go.
- Generate docs tables for components, units, warning codes, providers, source
  adapters, framework adapters, and support matrices.
- Keep the fixture-backed support matrix generated from fixture metadata in
  `docs/generated/fixture-support-matrix.md`; `npm run generate:contracts` and
  `scripts/check_generated_contract_docs.py` guard it against drift.
- Keep warning-code fixture coverage generated in
  `docs/generated/warning-coverage.md`; uncovered warning codes are valid
  contract values but must not be treated as V1-supported behavior until they
  have shared fixtures.
- Add a single command that regenerates artifacts and fails on diff.
- Continue hardening Go's typed struct wrappers for the normalized usage,
  price-card, discount, and core calculation path; raw provider and framework
  adapter paths still use map-backed objects.
- Keep every new component, warning, adapter, or discount behavior fixture-first.

## Provider And Framework Breadth Gate

Broader coverage should be driven by alpha findings, not speculative matrix
filling. Priority areas:

- provider-specific generated image, audio, and video billing beyond normalized
  `image_generation_units`, `audio_generation_units`, and
  `video_generation_units`;
- provider-specific transcription and speech billing beyond normalized
  `transcription_seconds`;
- provider-specific rerank/search billing beyond normalized
  `rerank_search_units`;
- provider-specific storage/session billing beyond the normalized
  `storage_gb_days` component;
- additional final stream usage protocols;
- deeper framework callbacks and real app examples for Vercel AI SDK,
  LangChain, LangSmith, Semantic Kernel, OpenAI Agents SDK, OpenRouter, and
  LlamaIndex.

## V1 Gate

V1 requires:

- stable schemas;
- stable warning codes;
- stable public package APIs;
- production-ready Python and JavaScript packages;
- Go APIs stable for normalized usage and core cost calculation;
- strong source/provider coverage for supported surfaces;
- historical-pricing path with documented effective-date behavior;
- top framework integrations backed by live smoke evidence;
- no known correctness holes in surfaces marked supported.

Until these gates are met, RunCost should describe itself as pre-1.0 and
fixture-backed for named surfaces only.
