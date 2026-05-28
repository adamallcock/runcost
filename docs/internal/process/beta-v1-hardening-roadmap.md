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
- At least one invoice/dashboard comparison report exists under `docs/internal/reports/`.
- PyPI and npm trusted publishing are configured externally.
- The guarded release workflow has been run with publishing disabled and
  reviewed.
- A real Go semantic version tag has been verified from a clean external module.
- Known non-invoice-exact cases are documented in the support and warning docs.
- Source-data refresh/update process has an owner, cadence, and review path in
  `docs/internal/process/2026-05-26-source-data-update-process.md`.

The machine-readable gate register lives at
`fixtures/source-files/project-completion-gates.json`. Normal CI validates that
the register is well-formed and that referenced evidence exists:

```bash
npm run check:gates
```

The register follows the generated contract documented from
`schemas/project-completion-gates.schema.json`.

The public caveat view generated from that register lives at
`docs/generated/beta-v1-caveats.md`. Treat it as the current source of truth for
remaining public-beta and V1 limitations.

When the external evidence exists, use the strict checks before calling a gate
complete:

```bash
npm run alpha:bundle -- \
  --mode live \
  --output-dir /tmp/runcost-alpha-evidence-bundle-live \
  --allow-sample-prices \
  --invoice-comparison <sanitized-real-comparison.json> \
  --require-real
python3 scripts/check_alpha_evidence_bundle.py \
  --smoke-report <sanitized-live-report.json> \
  --smoke-report <sanitized-vercel-report.json> \
  --smoke-report <sanitized-langchain-report.json> \
  --invoice-comparison <sanitized-real-comparison.json> \
  --require-real
python3 scripts/check_project_completion_gates.py --require-milestone8
python3 scripts/check_project_completion_gates.py --require-public-beta
python3 scripts/check_project_completion_gates.py --require-v1
```

Those strict checks are expected to fail until the live smoke, real invoice or
dashboard comparison, registry configuration, explicitly approved registry
publication, and post-live caveat review have actually happened.

Current release evidence:

- The guarded release workflow has passed with `publish=false` for intended
  beta version `0.1.0`; artifact review is recorded in
  `docs/internal/reports/2026-05-26-release-workflow-0-1-0-no-publish-rehearsal.md`.
- Remote tag `v0.1.0` has been verified from a clean temporary Go module
  without a local `replace`; evidence is recorded in
  `docs/internal/reports/2026-05-26-go-tag-verification-0-1-0.md`.
- Actual PyPI/npm publication remains intentionally disabled until trusted
  publishing is configured externally and publishing is explicitly approved.
  The workflow also requires `publish_approval=publish-runcost` when
  `publish=true`, so accidental publication fails before publish jobs can run.
- The Python distribution-name decision is recorded in
  `docs/internal/decisions/2026-05-27-python-distribution-name.md`: publish
  `runcost-ai` on PyPI while preserving `import runcost` and the `runcost` CLI.

## Polyglot Hardening Gate

The current polyglot strategy remains:

- JSON schemas define data contracts.
- Shared fixtures define behavior.
- Python, JavaScript/TypeScript, and Go implementations remain handwritten and
  idiomatic.
- Generated artifacts should be types, docs, validators, matrices, and drift
  checks rather than cost-calculation business logic.

Hardening work:

- Keep taxonomy-bearing type artifacts generated for TypeScript, Python, and Go
  with `scripts/generate_language_types.py`; broader full-contract generation
  can be added later if raw JSON Schema editing becomes the maintenance pain.
- Keep exported package-surface parity in
  `fixtures/source-files/public-api-registry.json`; the generated view
  `docs/generated/public-api-registry.md` is drift-checked by
  `scripts/check_public_api_registry.py`.
- Generate docs tables for components, units, warning codes, providers, source
  adapters, framework adapters, and support matrices.
- Keep the fixture-backed support matrix generated from fixture metadata in
  `docs/generated/fixture-support-matrix.md`; `npm run generate:contracts` and
  `scripts/check_generated_contract_docs.py` guard it against drift.
- Keep warning-code fixture coverage generated in
  `docs/generated/warning-coverage.md`; warning codes must stay
  fixture-backed before they are treated as V1-supported behavior.
- Keep `npm run generate:contracts` as the single command that regenerates
  generated docs and language type artifacts; normal tests fail on generated
  language type or generated-doc drift.
- Continue hardening Go's typed struct wrappers for the normalized usage,
  price-card, discount, and core calculation path; raw provider and framework
  adapter paths still use map-backed objects.
- Treat Go public contract types and taxonomy enum-like types as partial until
  they graduate from internal/generated slices and map-backed ledgers to
  stable exported type surfaces.
- Keep every new component, warning, adapter, or discount behavior fixture-first.

## Provider And Framework Breadth Gate

Broader coverage should be driven by alpha findings, not speculative matrix
filling. Priority areas:

- provider-specific aggregate dashboard and Usage API billing beyond
  fixture-backed OpenAI organization usage completions, embeddings, images,
  audio transcription, audio speech, vector-store, and code-interpreter
  buckets;
- provider-specific generated image, audio, and video billing beyond
  fixture-backed OpenAI Images token/image-unit usage, OpenAI organization
  usage image buckets, OpenAI organization usage audio speech character
  buckets, and normalized `image_generation_units`,
  `audio_generation_units`, `audio_generation_characters`, and
  `video_generation_units`;
- provider-specific transcription and speech billing beyond fixture-backed
  OpenAI audio transcription duration/token usage, OpenAI organization usage
  audio transcription buckets, and normalized `transcription_seconds`;
- provider-specific embeddings billing beyond fixture-backed OpenAI Embeddings
  per-response usage, OpenAI organization usage embeddings buckets, and
  normalized `embedding_tokens`;
- provider-specific rerank/search billing beyond fixture-backed Cohere Rerank
  and normalized `rerank_search_units`;
- provider-specific storage/session billing beyond fixture-backed OpenAI Vector
  Stores `usage_bytes` to `storage_gb_days` extraction with an explicit
  storage-day window, OpenAI organization usage code-interpreter session
  extraction, and the normalized `storage_gb_days` and
  `code_interpreter_session_units` components;
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

The V1 release-candidate checklist is machine-checkable:

```bash
npm run check:v1-stabilization
python3 scripts/check_v1_stabilization_checklist.py \
  --checklist /tmp/runcost-v1-stabilization-checklist.json \
  --require-real
```

The checked-in template lives at
`fixtures/source-files/v1-stabilization-checklist-template.json` and follows
`schemas/v1-stabilization-checklist.schema.json`. Normal CI validates the
template; `--require-real` intentionally fails until the checklist is converted
to a release-candidate review with every readiness field true, no known
correctness holes, and reviewer metadata.

Until these gates are met, RunCost should describe itself as pre-1.0 and
fixture-backed for named surfaces only.
