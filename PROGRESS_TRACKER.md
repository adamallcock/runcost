---
title: RunCost Progress Tracker
date: 2026-05-25
type: note
status: draft
---

# RunCost Progress Tracker

Last updated: 2026-05-26

Purpose: keep the implementation state explicit across context compaction and long-running work. This file is the handoff ledger for what is done, what is in progress, what is blocked, and what evidence proves it.

## Active Objective

Keep `PROJECT_PLAN.md` implementation state explicit while closing current-scope roadmap gaps, preserving the polyglot, schema-first, fixture-first architecture across Python, JavaScript/TypeScript, Go, and future languages.

## Status Vocabulary

The tracker separates roadmap state from active work state:

- `Complete for current scope`: the milestone's current prototype or planning-pass exit criteria are satisfied, but later public-beta or V1 hardening may still exist elsewhere.
- `Partial`: meaningful fixture-backed work exists, but the milestone exit gate in `PROJECT_PLAN.md` is not yet satisfied.
- `Not started`: no implementation or validation work has begun for the milestone.
- `Active now`: the only implementation lane currently being advanced. Other partial milestones are backlog, not parallel active work.

## Active Focus

Current active lane: Milestone 8 live smoke and alpha feedback.

Why this lane is active: the current objective is to complete the remaining end-to-end plan after Milestones 0-7. Milestone 8 is the next real gate because it proves RunCost beside live SDK/API calls, starts the findings-to-fixtures loop, and produces the first invoice/dashboard comparison evidence.

Doc rename coordination: another agent may rename Markdown files to match repository naming rules. Until that lands, avoid broad documentation churn and re-inspect paths before changing cross-document links.

## Current Verified Baseline

Evidence collected on 2026-05-26:

- `npm test` passes.
- Python and JavaScript fixture runner checks 86 shared fixtures, with fixture metadata allowing language-scoped framework ergonomics fixtures.
- Fixture metadata and checked-in coverage report pass through `python3 scripts/check_fixture_coverage.py` with 88 fixtures.
- Source refresh command smoke check passes through `python3 scripts/check_source_refresh.py`.
- Alpha smoke harness sample-mode check passes through `python3 scripts/check_alpha_smoke.py`; live API-key-gated runs are implemented for selected direct API paths but have not been executed in this repo evidence yet.
- Alpha smoke product-truth classification checks pass through `python3 scripts/check_alpha_product_truth.py`; the current no-credential live report is tied to machine-readable documented-limitation entries in `fixtures/source-files/alpha-smoke-product-truth-register.json`.
- Invoice/dashboard comparison sample checks pass through `python3 scripts/check_invoice_comparison.py`; comparison outputs include `evidence_type` and `milestone8_real_evidence` so the checked-in sample cannot be mistaken for real provider dashboard/export evidence.
- Go package passes `go test ./packages/go/...`.
- Go typed normalized usage, price-card, discount-policy, and core calculation wrappers are covered by `packages/go/ledger/typed_api_test.go` and `ExampleCalculateCostTyped`.
- Python compile check passes for package, scripts, and Python example.
- JavaScript and Python examples run.
- Clean package install checks pass for Python, JavaScript/TypeScript, and Go through `npm run check:packages`, including the typed Go core wrapper from a clean temporary module.
- Release readiness checks pass through `npm run check:release`.
- No-publish release dry-run checks pass through `npm run check:release-dry-run`.
- Guarded GitHub release workflow passed from `main` with
  `publish=false` in run
  `https://github.com/adamallcock/runcost/actions/runs/26430180080`, then
  passed again after workflow-warning hardening in
  `https://github.com/adamallcock/runcost/actions/runs/26430290844`; artifact
  review and warning follow-up are recorded in
  `docs/reports/2026-05-26-release-workflow-no-publish-rehearsal.md`.
- Real-life live SDK/API smoke tests are implemented as optional API-key-gated harnesses, but credentialed provider evidence has not been captured yet; current completed runs use synthetic responses, fixtures, local package installs, no-network sample smoke, or local/live price-source refresh commands.
- Project hygiene check passes.
- JSON files parse through `jq`.
- ASCII scan reports no non-ASCII text.
- Current cores exist in:
  - `packages/python/runcost/`
  - `packages/javascript/core/`
  - `packages/go/ledger/`
- Shared schemas exist in `schemas/`.
- Locked v0.1 schema taxonomy exists in `schemas/taxonomy.json` and is checked by `python3 scripts/check_schema_taxonomy.py`.
- Shared fixtures exist in `fixtures/`.
- Project plan exists in `PROJECT_PLAN.md`.
- Polyglot decision record exists in `docs/decisions/polyglot-toolchain-decision.md`.
- Public API parity matrix exists in `docs/notes/api-parity-matrix.md`.
- Public quickstart, installation, API reference, aggregation/streaming, debug-trace, fixture-coverage, supported-surface, custom pricing, source adapter, warning, and release process docs exist under `docs/`.
- Registry README policy exists in `docs/process/release-process.md`; PyPI uses the root README and npm carries `packages/javascript/core/README.md`.
- Root `LICENSE`, `CHANGELOG.md`, `CONTRIBUTING.md`, and `SECURITY.md` exist.
- CI workflow exists in `.github/workflows/ci.yml`.
- Guarded release workflow exists in `.github/workflows/release.yml`.

## Completed Sprint Snapshot

Source: `PROJECT_PLAN.md`, section "Immediate Next Sprint".

Goal: move from prototype to private-alpha foundation.

Status: complete for this pass.

| Item | Status | Evidence | Notes |
|---|---|---|---|
| Add schema validation to `scripts/check_fixtures.py` | Done | `npm test` passes; runner validates usage, price-card, discount-policy, and cost-ledger schemas | Uses a no-dependency schema subset validator for the current schemas. |
| Add strict and compatibility modes | Done | `strict-unknown-model.json`; Python/JS fixture runner and Go fixture tests pass | Strict mode fails on warnings; compatibility mode returns warnings. |
| Add warning fixtures for unknown model, unpriced component, and unknown surface | Done | `unknown-model-compatibility.json`, `unpriced-component-compatibility.json`, `unknown-surface-compatibility.json` | Warning codes are shared across languages. |
| Add LiteLLM source adapter prototype | Done | `litellm-adapter-basic.json`; Python/JS/Go tests pass | Maps core token, cache, and reasoning price fields into price cards. |
| Add Portkey source adapter prototype | Done | `portkey-adapter-basic.json`; Python/JS/Go tests pass | Maps token, cache, reasoning, and web-search price fields into price cards. |
| Add OpenRouter models source adapter prototype | Done | `openrouter-models-adapter-basic.json`, `openrouter-models-adapter-tiered.json`; Python/JS/Go tests pass | Maps prompt, completion, cache, reasoning, image-input, request, web-search, and tiered long-context price fields into price cards. |
| Add OpenAI tool-call raw fixture | Done | `openai-responses-raw-tool-calls.json`; Python/JS/Go tests pass | Covers web search, file search, and code-interpreter call units from raw Responses output. |
| Add Anthropic 1-hour cache-write fixture | Done | `anthropic-messages-raw-cache-1h.json`; Python/JS/Go tests pass | Proves `input_cache_write_1h_tokens` extraction. |
| Add polyglot toolchain decision record | Done | `docs/decisions/polyglot-toolchain-decision.md`; hygiene check passes | Decides JSON Schema plus shared fixtures as v0.x source of truth, with typed artifacts now and generation later. |
| Add package-level TypeScript types or generated schema types | Done | `packages/javascript/core/index.d.ts`; JS package `types` and `exports.types` point to it | Manual schema-aligned declarations for v0.x prototype. |
| Add Python type hints and minimal typed dictionaries or generated models | Done | `packages/python/runcost/types.py`; exported from package `__init__.py`; compile check passes | Manual `TypedDict` contracts for v0.x prototype. |
| Add Go public API docs and typed examples | Done | Go doc comments in `ledger.go`; `packages/go/ledger/example_test.go`; Go tests pass | Examples cover `CalculateCost` and `FromResponse`. |
| Add public API parity matrix | Done | `docs/notes/api-parity-matrix.md`; hygiene check validates public API names | Tracks Python, JS/TS, and Go support by capability. |
| Add debug trace fixture shape | Done | `schemas/debug-trace.schema.json`, `debug-trace-explain-decisions.json`; `npm test` passes | Optional `debug_trace` / `debugTrace` explains price-card, component, alias, discount, and warning decisions. |
| Add fixture metadata fields | Done | `schemas/fixture.schema.json`; all 88 fixtures include `metadata` | Metadata covers requirement IDs, provider, surface, scenario, tags, and expected languages. |
| Add fixture coverage report | Done | `docs/reports/fixture-coverage.md`; `scripts/check_fixture_coverage.py`; `npm test` passes | Reports scenarios, provider surfaces, components, warning codes, source adapters, framework adapters, requirements, tags, and expected languages. |
| Add generated-artifact drift checks | Done | `scripts/check_project_hygiene.py`; `npm test` runs it | Starts as required-artifact, package metadata, parity, fixture floor, and CI command checks. |
| Add CI workflow | Done | `.github/workflows/ci.yml`; hygiene check passes | CI runs conformance tests, examples, and Python compile checks. |
| Add cost-ledger aggregation primitive | Done | `cost-ledger-aggregation-basic.json`, `stream-final-usage-missing-warning.json`; Python/JS/Go tests pass | Aggregates already-calculated ledgers and emits `stream_usage_missing` when expected final stream usage is absent. |
| Add provider streaming final-usage extraction | Done | `openai-responses-stream-completed-event.json`, `anthropic-messages-stream-events.json`, `gemini-generate-content-stream-chunks.json`; Python/JS/Go tests pass | Handles selected final-usage stream event envelopes without estimating arbitrary partial deltas. |
| Add documented partial framework adapter paths | Done | `docs/notes/framework-adapter-notes.md`, `docs/reference/supported-surfaces.md`, `docs/notes/api-parity-matrix.md`; hygiene check guards names | Historical documentation slice. The remaining partial paths were later promoted by the Milestone 6 fixture-backed adapter slice. |
| Add Haystack and LiteLLM fixture-backed framework adapters | Done | `haystack-openai-chat-generator-meta.json`, `litellm-proxy-response-cost-metadata.json`; Python/JS fixture runner and Go tests pass | Adds one-call helpers and extractors across Python, JavaScript/TypeScript, and Go. |
| Normalize documentation layout | Done | `docs/guides/`, `docs/reference/`, `docs/notes/`, `docs/decisions/`, `docs/reports/`, `docs/process/`; hygiene and release scripts use new paths | Preserves content while moving dated/uppercase docs into categorized lowercase paths. |
| Add AutoGen/AG2 fixture-backed framework adapter | Done | `ag2-usage-summary-actual.json`, `ag2-usage-summary-total.json`; Python/JS fixture runner, Go tests, package install checks, release checks, examples, JSON parse, ASCII scan, and diff whitespace checks pass | Adds selected usage summary extraction and one-call helpers across Python, JavaScript/TypeScript, and Go. |
| Add fixture generator helpers | Done | `scripts/create_fixture.py`, `scripts/check_fixture_generator.py`, `npm run fixture:new`; generator smoke checks and targeted fixture checks pass | Adds schema-shaped fixture scaffolding and single-fixture validation to reduce future fixture duplication. |
| Add v0.1 schema taxonomy lock | Done | `schemas/taxonomy.json`, `scripts/check_schema_taxonomy.py`; full validation passes | Locks component names, units, warning codes, alias resolution values, fixture scenarios, expected languages, and debug decision types. |
| Add typed warning metadata payloads | Done | `warning_metadata_required_keys` in `schemas/taxonomy.json`; warning fixtures; Python/JS fixture runner and Go fixture tests pass | Every warning now carries metadata, and per-code required metadata keys are enforced across supported languages. |
| Add adversarial decimal arithmetic fixture | Done | `decimal-arithmetic-adversarial.json`; `npm test` passes with 81 fixtures | Proves large token quantities and tiny per-token prices without binary float leakage across Python, JavaScript/TypeScript, and Go. |
| Add Milestone 6 fixture-backed framework adapters | Done | `openai-agents-sdk-usage.json`, `vercel-ai-sdk-stream-text-finish.json`, `langsmith-run-usage-metadata.json`, `langsmith-export-cost-compare.json`, `semantic-kernel-telemetry-basic.json`, `openrouter-openai-sdk-response.json`, `openrouter-agent-sdk-response.json`; `npm test`, Go tests, package install checks, release checks, JSON parse, py_compile, and diff whitespace checks pass | Promotes OpenAI Agents SDK usage, Vercel `streamText` finish objects, LangSmith run/export usage, Semantic Kernel telemetry, and OpenRouter SDK response paths to dependency-free fixture-backed support across Python, JavaScript/TypeScript, and Go. |

## Milestone Roadmap Status

This table tracks roadmap completion, not simultaneous active work. At most one row should be marked `Yes` in `Active now?`.

| Milestone | Roadmap state | Active now? | Evidence | Exit-gate remaining |
|---|---|---:|---|---|
| Milestone 0: Prototype Foundation | Complete for current scope | No | `npm test` passes; cores, examples, schemas, and broad shared fixtures exist. | Later type hardening moved into Milestones 1 and 1.5. |
| Milestone 1: Contract Hardening | Complete for current scope | No | Schemas exist; fixture runner validates schemas including debug traces and fixture metadata; warning fixtures exist; coverage report and hygiene checks exist; fixture generator helpers now create runnable normalized-usage fixture skeletons; Go fixture tests validate generated cost-ledger structure and exact component totals; v0.1 taxonomy lock is checked by `scripts/check_schema_taxonomy.py`. | Future schema-derived type generation is tracked under Milestone 1.5. |
| Milestone 1.5: Polyglot Toolchain Foundation | Complete for current scope | No | Decision record, manual type artifacts, parity matrix, Go examples, generated taxonomy docs, generated schema-field docs, generated-doc drift checks, type-taxonomy parity checks, hygiene checks, and CI workflow exist. | Schema-derived language type workflow remains a later hardening item, not a current active lane. |
| Milestone 2: Core Calculator Correctness | Complete for current scope | No | Decimal-safe calculator, aliases, strict/compatibility modes, effective dates, service tiers, stale prices, provider-reported cost modes, source priority, deterministic price-card tie-breaking, source disagreement, debug traces, long-context thresholds, batch/priority/provisioned fixtures, typed warning metadata payloads, adversarial decimal precision coverage, cross-language component-total invariant checks, and byte-stable component/source/discount/warning ordering checks exist. | Later beta/V1 hardening can add more edge-case fixtures as real smoke tests find them. |
| Milestone 3: Source Adapter Layer | Complete for current scope | No | `llm-prices` current and historical feeds, LiteLLM, Portkey, OpenRouter models, models.dev, reviewed official snapshots, source-cache envelopes, local JSON/YAML file loading, explicit refresh command, source capability warnings, user compact pricing, and Helicone prototype adapters exist. | Later source expansion moves to beta/V1 hardening. |
| Milestone 4: Provider Extractors V0 | Complete for current scope | No | OpenAI Responses, OpenAI Chat Completions, OpenAI Embeddings, Anthropic, OpenRouter, Groq, xAI Chat Completions and xAI Responses, Mistral, DeepSeek, Azure OpenAI, Hugging Face, Cohere, Gemini/Vertex, Bedrock Converse, and Bedrock InvokeModel extractors exist for selected surfaces; selected final streaming usage cases are fixture-backed; OpenAI Conversations are documented as non-cost-bearing state resources whose costs attach to Responses. | Additional stream protocols, provider-specific generated media, rerank, transcription, and deeper provider-specific feature fields move to beta/V1 hardening. |
| Milestone 5: Tool Call and Feature Pricing | Complete for current scope | No | Generic and raw OpenAI tool-call fixtures exist, including web search, file search, code interpreter, computer-use actions, and function calls; OpenRouter request/image/search source pricing, provider-reported cost modes, Gemini/Vertex multimodal token details, normalized generated media, transcription, rerank, runtime-second, GB-day storage pricing, and custom internal tool components exist. | Broader provider-specific generated media, transcription, rerank, provider-specific storage/session extraction, and live provider validation move to Milestone 8/beta hardening. |
| Milestone 6: Framework Adapters | Complete for current scope | No | LangChain AIMessage, OpenAI Agents SDK usage objects, Vercel AI SDK generateText and streamText finish objects, LlamaIndex TokenCountingHandler, Haystack metadata, LiteLLM proxy metadata, AutoGen/AG2 usage summaries, LangSmith run/export usage, Semantic Kernel telemetry, OpenRouter SDK responses, Python LangChain callback/context manager, JavaScript Vercel `wrapGenerate` and `onFinish` helpers, and aggregation exist with fixtures. | Live SDK/API-key smoke, real application validation, deeper framework callback variants, and smoke-derived examples move to Milestone 8/beta hardening. |
| Milestone 7: Packaging and Developer Experience | Complete for current scope | No | Package metadata, types, examples, CI, clean install checks, Python package CLI, migration guide, alpha docs, license metadata, changelog, contributing/security docs, registry README policy, release process, release readiness checks, guarded release workflow, and local no-publish release dry run exist. | First registry publication, external trusted publisher configuration, and real post-tag Go module verification remain release operations outside the repo-side private-alpha gate. |
| Milestone 8: Alpha Quality and Feedback | Partial | Yes | `scripts/run_alpha_smoke.py`, `scripts/run_vercel_alpha_smoke.mjs`, `scripts/run_langchain_alpha_smoke.py`, `scripts/check_alpha_smoke.py`, `scripts/check_alpha_product_truth.py`, `fixtures/source-files/alpha-smoke-samples.json`, `fixtures/source-files/alpha-smoke-product-truth-register.json`, and `docs/process/alpha-smoke-runbook.md` exist; sample mode covers OpenAI Responses, Anthropic prompt caching, Vercel stream finish, LangChain metadata, OpenRouter cost comparison, and multi-provider discounts without credentials. Sanitized invoice/dashboard comparison mechanics exist through `scripts/compare_invoice_dashboard.py`, `scripts/check_invoice_comparison.py`, `fixtures/source-files/invoice-dashboard-comparison-sample.json`, and `docs/reports/2026-05-26-invoice-dashboard-comparison-sample.md`; sample comparison output is explicitly marked as not real Milestone 8 evidence. `fixtures/source-files/project-completion-gates.json` and `scripts/check_project_completion_gates.py` now make each remaining live-smoke and invoice evidence gate explicit. | Execute credentialed live SDK/API runs, classify any new live findings in the product-truth register, and run a real provider dashboard/invoice/usage-export comparison validated with `python3 scripts/check_invoice_comparison.py --comparison <path> --require-real`; then pass `python3 scripts/check_project_completion_gates.py --require-milestone8`. |
| Milestone 9: Public Beta | Partial | No | Guarded release workflow, trusted-publishing docs, no-publish artifact review checklist, local release dry run, successful `publish=false` GitHub release rehearsal from `main`, reviewed rehearsal artifacts, real Go tag verification path, source-data update owner/cadence/review process, historical no-publish dispatch-blocker evidence, and project completion gate register/checker exist. | External PyPI/npm trusted publisher configuration, no-publish workflow rehearsal against the real release version, real tag Go verification, and beta caveat review remain; then pass `python3 scripts/check_project_completion_gates.py --require-public-beta`. |
| Milestone 10: V1 | Not started | No | None. | Stable schemas/warning codes/package APIs, production-ready packages, strong provider/source coverage, historical-pricing path, and top framework integrations. |

## Work Log

### 2026-05-26

- Started Milestone 8 alpha quality gate.
- Added optional sanitized alpha smoke harness:
  - `scripts/run_alpha_smoke.py`
  - `scripts/check_alpha_smoke.py`
  - `fixtures/source-files/alpha-smoke-samples.json`
- Sample mode is no-network and checks OpenAI Responses, Anthropic prompt caching, Vercel AI SDK streamText final usage, LangChain agent metadata, OpenRouter cost comparison, and multi-provider discount scenarios.
- Live mode is explicit, API-key-gated, and currently supports selected direct API paths for OpenAI Responses, Anthropic Messages, and OpenRouter chat completions.
- Added optional framework-specific smoke scripts:
  - `scripts/run_vercel_alpha_smoke.mjs`
  - `scripts/run_langchain_alpha_smoke.py`
- Vercel and LangChain live scripts are API-key-gated and dependency-optional; missing credentials or optional SDK packages produce sanitized skipped reports.
- Ran the aggregate live harness in the current environment. It produced sanitized skipped reports for OpenAI, Anthropic, OpenRouter, Vercel, and LangChain because API-key environment variables were not set, plus a passing local multi-provider discount scenario.
- Added product-truth classification enforcement:
  - `fixtures/source-files/alpha-smoke-product-truth-register.json` records the current no-credential live findings and ties each skipped scenario to `docs/reports/2026-05-26-alpha-smoke-live-no-credentials.md`;
  - `scripts/check_alpha_product_truth.py` validates a live smoke report against that register and fails if non-passing findings lack a product-truth artifact;
  - `npm run check:alpha-truth` and `npm test` now run the product-truth check.
- Captured that finding as `docs/reports/2026-05-26-alpha-smoke-live-no-credentials.md`; this is product-truth documentation for the no-credential state, not completion of the live-provider-run gate.
- Added sanitized invoice/dashboard comparison mechanics:
  - `scripts/compare_invoice_dashboard.py`
  - `scripts/check_invoice_comparison.py`
  - `fixtures/source-files/invoice-dashboard-comparison-sample.json`
  - `docs/reports/2026-05-26-invoice-dashboard-comparison-sample.md`
- Comparison outputs include `evidence_type` and `milestone8_real_evidence`;
  `python3 scripts/check_invoice_comparison.py --comparison <path> --require-real`
  validates future real provider dashboard/export evidence.
- The sample comparison classifies exact, estimated, and unsupported fields and documents product-truth actions. It proves the comparison workflow, but a real provider dashboard/invoice/usage export is still required before Milestone 8 invoice validation is complete.
- Added a project completion gate register and checker:
  - `fixtures/source-files/project-completion-gates.json` records remaining Milestone 8, public beta, polyglot, provider/framework breadth, and V1 gates with required evidence, current evidence, and remaining action.
  - `scripts/check_project_completion_gates.py` validates the register and referenced evidence in normal CI.
  - Strict flags `--require-milestone8`, `--require-public-beta`, and `--require-v1` provide future completion gates and are expected to fail until the external evidence exists.
  - `npm run check:gates` and `npm test` now run the register check.
- Advanced package publication readiness without publishing:
  - release workflow now has a no-publish artifact review checklist in the GitHub step summary;
  - release workflow verifies `github.com/adamallcock/runcost/packages/go/ledger@v<version>` from the real remote tag when that tag exists, without a local `replace`;
  - release process docs distinguish local dry-run `replace` checks from real Go tag verification.
- Advanced polyglot generated-artifact hardening:
  - `scripts/generate_contract_docs.py` generates `docs/generated/contract-taxonomy.md` from `schemas/taxonomy.json`;
  - `scripts/generate_contract_docs.py` also generates `docs/generated/schema-fields.md` from `schemas/*.schema.json`;
  - `scripts/generate_contract_docs.py` also generates `docs/generated/fixture-support-matrix.md` from `fixtures/*.json` metadata;
  - `scripts/generate_contract_docs.py` also generates `docs/generated/warning-coverage.md` from `schemas/taxonomy.json` and fixture warning metadata, currently showing 14 of 19 warning codes fixture-backed;
  - `scripts/check_generated_contract_docs.py` fails on generated contract-doc, schema-field-doc, fixture-support-matrix, and warning-coverage drift;
  - `scripts/check_type_taxonomy_parity.py` fails when Python, TypeScript, or Go public taxonomy-bearing type surfaces drift from `schemas/taxonomy.json`;
  - `npm run generate:contracts` refreshes the checked-in generated docs.
- Advanced Go API hardening:
  - added typed structs for normalized usage, model identity, usage components, price cards, price components, prices, sources, effective ranges, discount policies, discount matches, discount adjustments, and calculator options;
  - added `CalculateCostTyped`, `CalculateCostTypedWithMode`, and `CalculateCostTypedWithOptions` as typed wrappers over the existing conformance-tested calculator;
  - added `packages/go/ledger/typed_api_test.go` and `ExampleCalculateCostTyped` so the typed API is exercised in Go tests.
- Advanced provider/feature breadth:
  - added `storage_gb_days` as a canonical component with `gb_day` units across schemas, taxonomy, Python types, TypeScript declarations, Go ordering, and tool/feature warning classification;
  - added `fixtures/storage-gb-day-pricing.json` to prove normalized GB-day storage pricing across Python, JavaScript/TypeScript, and Go;
  - added `fixtures/feature-pricing-generated-media-rerank-transcription.json` to prove normalized generated image, video, audio, rerank, transcription, tool-execution-second, and endpoint-runtime-second pricing across Python, JavaScript/TypeScript, and Go;
  - added `fixtures/feature-component-unpriced-warning.json` to prove unpriced runtime-second feature usage emits `tool_component_unpriced`;
  - regenerated contract taxonomy docs and fixture coverage; fixture count is now 88.
  - added warning fixtures for `price_not_found` and `historical_price_missing`, reducing uncovered warning codes from 7 to 5.
- Advanced public-beta source-data process hardening:
  - added `docs/process/2026-05-26-source-data-update-process.md` with owner, cadence, review checklist, and product-truth loop for source refreshes;
  - linked the process from README, source-adapter docs, release process, beta/V1 roadmap, and contributing guide;
  - added project hygiene and release readiness checks so the source-data process remains part of beta/release validation.
- Attempted guarded no-publish release workflow dispatch:
  - `gh workflow run release.yml --ref package-doc-readiness -f version=0.0.0 -f publish=false`;
  - GitHub returned `workflow release.yml not found on the default branch`;
  - captured the finding as `docs/reports/2026-05-26-release-workflow-no-publish-blocked.md`;
  - updated release docs to clarify that GitHub workflow dispatch requires the release workflow to exist on the default branch before branch-targeted no-publish rehearsal can run.
- Opened PR for review and default-branch workflow landing:
  - `https://github.com/adamallcock/runcost/pull/1`;
  - fixed the first GitHub CI failure by making the YAML file-source fixture portable across checkout paths;
  - latest PR CI `test` check passed at `https://github.com/adamallcock/runcost/actions/runs/26430029924/job/77801179229`;
  - PR was merged to `main` as merge commit
    `13ccb8e953056d2e4c9bd718bd5eef2277776c83`.
- Retried guarded no-publish release workflow dispatch from `main`:
  - `gh workflow run release.yml --ref main -f version=0.0.0 -f publish=false`;
  - workflow run `https://github.com/adamallcock/runcost/actions/runs/26430180080` passed;
  - artifact `runcost-release-artifacts` contained a Python wheel, Python
    source distribution, and npm tarball;
  - artifact review was captured as
    `docs/reports/2026-05-26-release-workflow-no-publish-rehearsal.md`;
  - real Go tag verification was skipped as expected because tag `v0.0.0` does
    not exist.
- Hardened release workflow warnings:
  - CI and release workflows now opt Actions into Node 24 early with
    `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true`;
  - Go module caching is disabled because the dependency-free Go module has no
    `go.sum`;
  - `main` CI passed at
    `https://github.com/adamallcock/runcost/actions/runs/26430288699`;
  - hardened no-publish release rehearsal passed at
    `https://github.com/adamallcock/runcost/actions/runs/26430290844`.
- Added docs:
  - `docs/process/alpha-smoke-runbook.md`
  - `docs/process/invoice-dashboard-comparison.md`
  - `docs/process/2026-05-26-source-data-update-process.md`
  - `docs/process/beta-v1-hardening-roadmap.md`
  - `docs/reports/2026-05-26-release-workflow-no-publish-blocked.md`
  - `docs/reports/2026-05-26-release-workflow-no-publish-rehearsal.md`

- Completed Milestone 5 for the current tool-call and feature-pricing scope.
- Added `openai-responses-raw-computer-and-function-tools.json` to fixture OpenAI Responses `computer_call` action counts and `function_call` counts as first-class tool/feature components across Python, JavaScript/TypeScript, and Go.
- Added `tool-component-unpriced-warning.json` to prove non-token tool/feature units emit `tool_component_unpriced` with structured metadata when no matching price exists.
- Updated Python, JavaScript/TypeScript, and Go extractors to map OpenAI Responses computer-use actions to `computer_use_action_units` and function calls to `tool_call_units`.
- Updated Python, JavaScript/TypeScript, and Go warning classification so known tool/feature components no longer depend on a substring match.
- Regenerated `docs/reports/fixture-coverage.md`; fixture count is now 83 and `tool_pricing` tag coverage is now 4.
- Verification after the Milestone 5 slice:
  - `python3 scripts/check_fixtures.py --fixture fixtures/openai-responses-raw-computer-and-function-tools.json --fixture fixtures/tool-component-unpriced-warning.json` passed.
  - `npm test` passed: 83 fixtures checked across Python and JavaScript, fixture generator/source refresh/coverage/schema taxonomy/hygiene checks passed, Go tests green.
  - `go test ./packages/go/...` passed.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/cli.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_package_installs.py scripts/check_project_hygiene.py scripts/check_release_readiness.py` passed.
  - `npm run check:packages` passed with installed Python CLI smoke, npm tarball import smoke, and Go clean-module import smoke.
  - `npm run check:release` passed.
  - `jq empty package.json packages/javascript/core/package.json schemas/*.json fixtures/*.json fixtures/source-files/*.json` passed.
  - `git diff --check` passed.

### 2026-05-25

- Completed Milestone 7 for the current repo-side/private-alpha scope.
- Added installed Python CLI coverage:
  - `runcost price-cards --source-type ... --input ...`
  - `runcost fixture-check ...`
- Added `docs/guides/2026-05-26-migration-from-hand-written-formulas.md`.
- Updated package installation, quickstart, API reference, release process, README, project plan, and hygiene/release checks for the CLI and migration guide.
- `npm run check:packages` now verifies the Python CLI in a clean installed virtual environment.
- External registry publication, trusted-publisher setup, and post-tag Go module verification remain release operations rather than repo-side Milestone 7 blockers.
- Verification after Milestone 7 packaging/DX slice:
  - `npm run check:packages` passed with CLI smoke, Python import smoke, npm tarball import smoke, and Go clean-module import smoke.
  - `python3 scripts/check_project_hygiene.py` passed.
  - `npm run check:release` passed.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/cli.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_package_installs.py scripts/check_project_hygiene.py scripts/check_release_readiness.py` passed.

- Completed Milestone 6 for the current no-live-smoke scope.
- Added fixture-backed framework adapter paths:
  - OpenAI Agents SDK usage objects.
  - Vercel AI SDK `streamText` finish/onFinish objects.
  - LangSmith run/export usage metadata and `total_cost` comparison.
  - Semantic Kernel telemetry/filter token metadata.
  - OpenRouter-compatible SDK and resolved Agent SDK response objects.
- Added dependency-free helper APIs across Python, JavaScript/TypeScript, and Go:
  - `from_openai_agents_usage`, `from_vercel_ai_sdk_stream_finish`, `from_langsmith_run`, `from_semantic_kernel_telemetry`, `from_openrouter_sdk_response`.
  - `fromOpenAIAgentsUsage`, `fromVercelAISDKStreamFinish`, `createRunCostVercelOnFinish`, `fromLangSmithRun`, `fromSemanticKernelTelemetry`, `fromOpenRouterSDKResponse`, `fromOpenRouterAgentResult`.
  - `FromOpenAIAgentsUsage`, `FromVercelAISDKStreamFinish`, `FromLangSmithRun`, `FromSemanticKernelTelemetry`, `FromOpenRouterSDKResponse`.
- Added shared fixtures:
  - `openai-agents-sdk-usage.json`
  - `vercel-ai-sdk-stream-text-finish.json`
  - `langsmith-run-usage-metadata.json`
  - `langsmith-export-cost-compare.json`
  - `semantic-kernel-telemetry-basic.json`
  - `openrouter-openai-sdk-response.json`
  - `openrouter-agent-sdk-response.json`
- Regenerated `docs/reports/fixture-coverage.md`; fixture count is now 81 and framework-adapter scenario count is now 16.
- Kept live SDK/API-key smoke and real application validation explicitly assigned to Milestone 8.
- Verification after Milestone 6 adapter slice:
  - `python3 scripts/check_fixtures.py --fixture ...` passed for the seven new fixtures.
  - `npm test` passed: 81 fixtures checked across Python and JavaScript, fixture generator/source refresh/coverage/schema taxonomy/hygiene checks passed, Go tests green.
  - `go test ./packages/go/...` passed.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_package_installs.py scripts/check_project_hygiene.py` passed.
  - `npm run check:packages` passed with fresh Python, npm, and Go install checks.
  - `npm run check:release` passed.
  - `jq empty package.json packages/javascript/core/package.json schemas/*.json fixtures/*.json fixtures/source-files/*.json` passed.
  - `git diff --check` passed.

### 2026-05-24

- Created progress tracker from current repo evidence.
- Baseline verification before new work: `npm test` passed with 8 fixtures and Go tests green.
- Added schema validation in the fixture runner, strict/compatibility modes, warning fixtures, LiteLLM and Portkey adapter fixtures, OpenAI raw tool-call fixture, and Anthropic 1-hour cache-write fixture.
- Verification after expanded fixtures: `npm test` passes with 16 shared fixtures and Go tests green.
- Added `docs/decisions/polyglot-toolchain-decision.md` and `docs/notes/api-parity-matrix.md`.
- Added TypeScript declarations in `packages/javascript/core/index.d.ts` and package metadata pointing at them.
- Added Python `TypedDict` contracts in `packages/python/runcost/types.py` and exported them.
- Added Go public API comments and examples in `packages/go/ledger/example_test.go`.
- Added `scripts/check_project_hygiene.py` and `.github/workflows/ci.yml`.
- Updated `README.md` and `PROJECT_PLAN.md` to reference the polyglot maintenance artifacts.
- Verification after polyglot foundation work:
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_project_hygiene.py examples/python_basic.py` passed.
  - `python3 scripts/check_project_hygiene.py` passed.
  - `npm test` passed: 16 fixtures checked across Python and JavaScript, Go tests green, hygiene checks green.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq` parsed schemas, fixtures, and package JSON files.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
- Added Milestone 2 correctness fixtures:
  - `effective-date-selection.json`
  - `service-tier-region-selection.json`
  - `service-tier-unsupported-compatibility.json`
  - `stale-price-warning.json`
  - `provider-reported-cost-mismatch.json`
- Implemented effective-date selection, service-tier and region matching, unsupported service-tier warnings, stale price-source warnings, provider-reported cost mismatch warnings, and component-total invariant checks across the conformance runner.
- Updated `docs/notes/api-parity-matrix.md`, `PROJECT_PLAN.md`, and `scripts/check_project_hygiene.py` for the new correctness coverage.
- Verification after Milestone 2 slice:
  - `python3 scripts/check_fixtures.py` passed with 21 fixtures across Python and JavaScript.
  - `gofmt -w packages/go/ledger/ledger.go packages/go/ledger/ledger_test.go packages/go/ledger/example_test.go && go test ./packages/go/...` passed.
  - `npm test` passed: 21 fixtures checked across Python and JavaScript, Go tests green, hygiene checks green.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_project_hygiene.py examples/python_basic.py` passed.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq` parsed schemas, fixtures, and package JSON files.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
- Added price-source priority and disagreement fixtures:
  - `price-source-priority-user-override.json`
  - `price-source-disagreement-warning.json`
- Implemented configured price source priority and price source disagreement warnings across Python, JavaScript, and Go.
- Verification after source-priority slice:
  - `python3 scripts/check_fixtures.py` passed with 23 fixtures across Python and JavaScript.
  - `gofmt -w packages/go/ledger/ledger.go packages/go/ledger/ledger_test.go packages/go/ledger/example_test.go && go test ./packages/go/...` passed.
  - `npm test` passed: 23 fixtures checked across Python and JavaScript, Go tests green, hygiene checks green.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_project_hygiene.py examples/python_basic.py` passed.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq` parsed schemas, fixtures, and package JSON files.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
- Added long-context, batch service-mode, and provider-reported-cost-used fixtures:
  - `long-context-threshold-selection.json`
  - `long-context-rule-missing.json`
  - `service-mode-batch-selection.json`
  - `provider-reported-cost-used.json`
- Added price-component `conditions` schema support for `min_total_input_tokens` and `max_total_input_tokens`.
- Implemented conditional price components, missing long-context rule warnings, and provider-reported authoritative cost mode with explicit USD reconciliation components across Python, JavaScript, and Go.
- Verification after long-context/service-mode slice:
  - `python3 scripts/check_fixtures.py` passed with 27 fixtures across Python and JavaScript.
  - `gofmt -w packages/go/ledger/ledger.go packages/go/ledger/ledger_test.go packages/go/ledger/example_test.go && go test ./packages/go/...` passed.
  - `npm test` passed: 27 fixtures checked across Python and JavaScript, Go tests green, hygiene checks green.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_project_hygiene.py examples/python_basic.py` passed.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq` parsed schemas, fixtures, and package JSON files.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
- Added additional service-mode fixtures:
  - `service-mode-priority-selection.json`
  - `service-mode-provisioned-selection.json`
- Verification after priority/provisioned fixture pass:
  - `npm test` passed: 29 fixtures checked across Python and JavaScript, Go tests green, hygiene checks green.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_project_hygiene.py examples/python_basic.py` passed.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq` parsed schemas, fixtures, and package JSON files.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
- Verified official usage shapes for this provider extractor pass:
  - OpenRouter chat completion usage exposes OpenAI-compatible `usage.prompt_tokens`, `usage.completion_tokens`, and `usage.total_tokens`.
  - Gemini generateContent usage metadata exposes prompt, candidate, total, and thinking token fields.
  - AWS Bedrock Converse usage exposes input, output, total, cache read, cache write, and cache details fields.
- Added provider extractor mapping notes in `docs/notes/provider-extractor-notes.md`.
- Added raw provider fixtures:
  - `gemini-generate-content-raw-reasoning-cache.json`
  - `bedrock-converse-raw-cache.json`
  - `openrouter-chat-raw-basic.json`
- Implemented raw extractors across Python, JavaScript, and Go for:
  - `google.gemini.generate_content`
  - `vertex.gemini.generate_content`
  - `aws.bedrock.converse`
  - `openrouter.chat_completions`
- Updated `docs/notes/api-parity-matrix.md`, `PROJECT_PLAN.md`, `README.md`, TypeScript declarations, Python exports, and hygiene checks for the new provider coverage.
- Verification after provider extractor slice:
  - `python3 scripts/check_fixtures.py` passed with 32 fixtures across Python and JavaScript.
  - `gofmt -w packages/go/ledger/ledger.go packages/go/ledger/ledger_test.go packages/go/ledger/example_test.go && go test ./packages/go/...` passed.
  - `npm test` passed: 32 fixtures checked across Python and JavaScript, Go tests green, hygiene checks green.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_project_hygiene.py examples/python_basic.py` passed.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq` parsed schemas, fixtures, and package JSON files.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
- Verified official usage shapes for this OpenAI-compatible provider alias pass:
  - Groq prompt caching reports OpenAI-compatible `usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens`, and `usage.prompt_tokens_details.cached_tokens`.
  - xAI chat completions and prompt caching report OpenAI-compatible token usage, cached prompt tokens, and completion reasoning token details.
  - Mistral prompt caching reports cached prompt tokens in `usage.prompt_tokens_details.cached_tokens`.
  - DeepSeek chat completions report `prompt_cache_hit_tokens`, `prompt_cache_miss_tokens`, and completion reasoning details alongside OpenAI-compatible totals.
  - Azure OpenAI chat completion usage reports prompt, completion, total, and optional reasoning-token details.
  - Hugging Face Inference Providers chat completions are OpenAI SDK compatible and report prompt, completion, and total token usage.
- Added shared OpenAI-compatible chat extraction helper in Python and JavaScript/TypeScript, with Go routing through the same supported-surface table.
- Added raw provider fixtures:
  - `groq-chat-raw-cache.json`
  - `xai-chat-raw-cache-reasoning.json`
  - `mistral-chat-raw-cache.json`
  - `deepseek-chat-raw-cache-reasoning.json`
  - `azure-openai-chat-raw-reasoning.json`
  - `huggingface-chat-raw-basic.json`
- Updated `docs/notes/provider-extractor-notes.md`, `docs/notes/api-parity-matrix.md`, `PROJECT_PLAN.md`, `README.md`, TypeScript declarations, Python exports, and hygiene checks for the new OpenAI-compatible provider coverage.
- Verification after OpenAI-compatible provider alias slice:
  - `python3 scripts/check_fixtures.py` passed with 38 fixtures across Python and JavaScript.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_project_hygiene.py examples/python_basic.py` passed.
  - `gofmt -w packages/go/ledger/ledger.go packages/go/ledger/ledger_test.go packages/go/ledger/example_test.go` completed.
  - `go test ./packages/go/...` passed.
  - `npm test` passed: 38 fixtures checked across Python and JavaScript, Go tests green, hygiene checks green.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq` parsed schemas, fixtures, and package JSON files.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `git status --short` could not run because this directory is not a Git repository.
- Verified official usage shapes for this Cohere provider extractor pass:
  - Cohere v2 Chat API reference reports top-level `usage.billed_units.input_tokens`, `usage.billed_units.output_tokens`, and raw `usage.tokens`.
  - Cohere Chat API guide reports the same billed/raw token split under `meta.billed_units` and `meta.tokens`.
  - Cohere pricing docs state that billed tokens, not generic token totals, are what users are actually charged for.
- Added raw Cohere fixtures:
  - `cohere-chat-raw-usage-billed-units.json`
  - `cohere-chat-raw-meta-billed-units.json`
- Implemented Cohere Chat extractors across Python, JavaScript, and Go, using billed units for pricing and preserving raw token counts in raw usage.
- Updated `docs/notes/provider-extractor-notes.md`, `docs/notes/api-parity-matrix.md`, `PROJECT_PLAN.md`, `README.md`, TypeScript declarations, Python exports, Go comments, and hygiene checks for Cohere coverage.
- Verification after Cohere provider extractor slice:
  - `python3 scripts/check_fixtures.py` passed with 40 fixtures across Python and JavaScript.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_project_hygiene.py examples/python_basic.py` passed.
  - `gofmt -w packages/go/ledger/ledger.go packages/go/ledger/ledger_test.go packages/go/ledger/example_test.go` completed.
  - `go test ./packages/go/...` passed.
  - `npm test` passed: 40 fixtures checked across Python and JavaScript, Go tests green, hygiene checks green.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq` parsed schemas, fixtures, and package JSON files.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `git status --short` could not run because this directory is not a Git repository.
- Verified Vertex AI Gemini `generateContent` usage metadata against the official Vertex AI REST `GenerateContentResponse` reference.
- Added `vertex-gemini-generate-content-raw-basic.json` to prove the `vertex.gemini.generate_content` dispatch path with cache and reasoning fields through the shared Gemini extractor.
- Updated `docs/notes/provider-extractor-notes.md`, `docs/notes/api-parity-matrix.md`, `scripts/check_project_hygiene.py`, and this tracker for the Vertex fixture evidence.
- Verification after Vertex fixture slice:
  - `python3 scripts/check_fixtures.py` passed with 41 fixtures across Python and JavaScript.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_project_hygiene.py examples/python_basic.py` passed.
  - `gofmt -w packages/go/ledger/ledger.go packages/go/ledger/ledger_test.go packages/go/ledger/example_test.go && go test ./packages/go/...` passed.
  - `npm test` passed: 41 fixtures checked across Python and JavaScript, Go tests green, hygiene checks green.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq` parsed schemas, fixtures, and package JSON files.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `python3 scripts/check_project_hygiene.py` passed.
  - `git status --short` could not run because this directory is not a Git repository.
- Verified official framework usage shapes for this framework adapter slice:
  - LangChain AIMessage exposes provider-normalized `usage_metadata` with `input_tokens`, `output_tokens`, `total_tokens`, `input_token_details.cache_read`, `input_token_details.cache_creation`, and `output_token_details.reasoning`.
  - Vercel AI SDK `generateText` exposes final-step `usage`, aggregate `totalUsage`, cache read/write input details, text/reasoning output details, and response `modelId`.
  - LlamaIndex `TokenCountingHandler` exposes prompt/completion/total LLM counters, embedding counters, streaming-finalized counts, and per-event token count objects.
- Added `docs/notes/framework-adapter-notes.md` for framework metadata mapping and limitations.
- Added framework adapter extractors across Python, JavaScript, and Go for:
  - `langchain.chat_message`
  - `vercel_ai_sdk.generate_text`
  - `llamaindex.token_counter`
- Added framework fixtures:
  - `langchain-chat-message-usage-metadata.json`
  - `vercel-ai-sdk-generate-text-total-usage.json`
  - `llamaindex-token-counter-events.json`
- Updated `docs/notes/api-parity-matrix.md`, `PROJECT_PLAN.md`, `README.md`, TypeScript declarations, Python exports, and hygiene checks for framework adapter coverage.
- Fixed Python `from_response` option pass-through so framework adapters can be selected with `adapter` while still pricing against the caller-supplied provider and surface.
- Verification after framework adapter slice:
  - `python3 scripts/check_fixtures.py` passed with 44 fixtures across Python and JavaScript.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_project_hygiene.py examples/python_basic.py` passed.
  - `gofmt -w packages/go/ledger/ledger.go packages/go/ledger/ledger_test.go packages/go/ledger/example_test.go && go test ./packages/go/...` passed.
  - `npm test` passed: 44 fixtures checked across Python and JavaScript, Go tests green, hygiene checks green.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq` parsed schemas, fixtures, and package JSON files.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `python3 scripts/check_project_hygiene.py` passed.
  - `git status --short` could not run because this directory is not a Git repository.
- Added one-call framework helper APIs across Python, JavaScript/TypeScript, and Go:
  - `from_langchain_message`, `fromLangChainMessage`, `FromLangChainMessage`
  - `from_vercel_ai_sdk_result`, `fromVercelAISDKResult`, `FromVercelAISDKResult`
  - `from_llamaindex_token_counter`, `fromLlamaIndexTokenCounter`, `FromLlamaIndexTokenCounter`
- Routed the existing LangChain, Vercel AI SDK, and LlamaIndex shared fixtures through those helpers in Python, JavaScript, and Go fixture runners.
- Updated `docs/notes/framework-adapter-notes.md`, `docs/notes/api-parity-matrix.md`, `PROJECT_PLAN.md`, `README.md`, TypeScript declarations, Python exports, Go API comments, and hygiene checks for helper coverage.
- Verification after framework helper API slice:
  - `python3 scripts/check_fixtures.py` passed with 44 fixtures across Python and JavaScript.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_project_hygiene.py examples/python_basic.py` passed.
  - `gofmt -w packages/go/ledger/ledger.go packages/go/ledger/ledger_test.go packages/go/ledger/example_test.go && go test ./packages/go/...` passed.
  - `npm test` passed: 44 fixtures checked across Python and JavaScript, Go tests green, hygiene checks green.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq` parsed schemas, fixtures, and package JSON files.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `python3 scripts/check_project_hygiene.py` passed.
  - `git status --short` could not run because this directory is not a Git repository.
- Verified Vertex AI Gemini `GenerateContentResponse` usage metadata fields for modality details in the official Vertex AI REST reference.
- Added `gemini-generate-content-raw-multimodal.json` covering Gemini/Vertex-style `promptTokensDetails`, `cacheTokensDetails`, `toolUsePromptTokensDetails`, `candidatesTokensDetails`, and `thoughtsTokenCount`.
- Implemented Gemini/Vertex modality-aware extraction across Python, JavaScript/TypeScript, and Go:
  - text/document/unspecified prompt details -> `input_uncached_tokens`
  - image/audio/video prompt details -> `input_image_tokens`, `input_audio_tokens`, `input_video_tokens`
  - cache details -> subtract from uncached/media input and emit `input_cache_read_tokens`
  - candidate modality details -> `output_text_tokens`, `output_image_tokens`, `output_audio_tokens`, `output_video_tokens`
  - `thoughtsTokenCount` -> `output_reasoning_tokens`
- Updated `docs/notes/provider-extractor-notes.md`, `docs/notes/api-parity-matrix.md`, `PROJECT_PLAN.md`, `README.md`, `scripts/check_project_hygiene.py`, and this tracker for multimodal coverage.
- Verification after Gemini/Vertex multimodal slice:
  - `python3 scripts/check_fixtures.py` passed with 45 fixtures across Python and JavaScript.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_project_hygiene.py examples/python_basic.py` passed.
  - `gofmt -w packages/go/ledger/ledger.go packages/go/ledger/ledger_test.go packages/go/ledger/example_test.go` completed.
  - `go test ./packages/go/...` passed.
  - `npm test` passed: 45 fixtures checked across Python and JavaScript, Go tests green, hygiene checks green.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq` parsed schemas, fixtures, and package JSON files.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `python3 scripts/check_project_hygiene.py` passed.
  - `git status --short` could not run because this directory is not a Git repository.
- Verified OpenRouter `/api/v1/models` against the official OpenRouter API reference and pricing documentation:
  - API reference returns `data[]` model objects with `id`, `canonical_slug`, `name`, and `pricing.prompt`, `pricing.completion`, `pricing.image`, and `pricing.request`.
  - OpenRouter model docs describe pricing values as USD per token/request/unit and include `web_search`, `internal_reasoning`, `input_cache_read`, and `input_cache_write`.
- Added OpenRouter source adapter fixtures:
  - `openrouter-models-adapter-basic.json` covering prompt, completion, cache read/write, internal reasoning, image-input, request, and web-search price fields.
  - `openrouter-models-adapter-tiered.json` covering tiered long-context price arrays with `min_context`.
- Added `input_image_units` to the canonical usage component contract for per-image input pricing.
- Implemented OpenRouter models source adapters across Python, JavaScript/TypeScript, and Go:
  - `price_cards_from_openrouter_models`
  - `priceCardsFromOpenRouterModels`
  - `PriceCardsFromOpenRouterModels`
- Updated `docs/notes/api-parity-matrix.md`, `PROJECT_PLAN.md`, `README.md`, TypeScript declarations, Python exports, Go API comments, fixture runners, hygiene checks, and this tracker for OpenRouter source coverage.
- Verification after OpenRouter source adapter slice:
  - `python3 scripts/check_fixtures.py` passed with 47 fixtures across Python and JavaScript.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_project_hygiene.py examples/python_basic.py` passed.
  - `gofmt -w packages/go/ledger/ledger.go packages/go/ledger/ledger_test.go packages/go/ledger/example_test.go` completed.
  - `go test ./packages/go/...` passed.
  - `npm test` passed: 47 fixtures checked across Python and JavaScript, Go tests green, hygiene checks green.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq` parsed schemas, fixtures, and package JSON files.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `python3 scripts/check_project_hygiene.py` passed.
  - `git status --short` could not run because this directory is not a Git repository.
- Added package and documentation readiness slice:
  - Switched Go module path to `github.com/adamallcock/runcost`.
  - Made the JavaScript package publishable by removing package-level `private` and adding package files, keywords, and repository metadata.
  - Added Python project URLs and keywords.
  - Added `scripts/check_package_installs.py` to verify clean Python, JavaScript/TypeScript, and Go installs from temporary projects.
  - Added `npm run check:packages` and CI coverage for clean install checks.
  - Added public docs for quickstart, installation, API reference, supported surfaces, custom pricing and discounts, source adapters, and warnings/limitations.
  - Updated `README.md` from draft-only project inventory toward alpha package onboarding.
  - Updated hygiene checks to require the new docs, package check script, package check CI command, and JavaScript package publish allowlist.
- Verification after package/docs readiness slice:
  - `npm test` passed: 47 fixtures checked across Python and JavaScript, Go tests green, hygiene checks green.
  - `npm run check:packages` passed: fresh Python venv import, npm tarball import, and fresh Go module import all green.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_project_hygiene.py scripts/check_package_installs.py examples/python_basic.py` passed.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq` parsed schemas, fixtures, and package JSON files.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
- Added debug trace slice:
  - Added `schemas/debug-trace.schema.json` and optional `debug_trace` support in `schemas/cost-ledger.schema.json`.
  - Added `debug-trace-explain-decisions.json` to prove source priority, price-card selection, alias resolution, component pricing, and discount trace decisions.
  - Implemented opt-in debug trace output across Python, JavaScript/TypeScript, and Go with `debug_trace` / `debugTrace` options.
  - Added Python and TypeScript `DebugTrace` type surfaces.
  - Added debug trace docs in `docs/reference/debug-trace.md` and updated README, API reference, warnings/limitations, API parity matrix, fixture runner schema validation, and hygiene checks.
  - Tightened Go fixture comparison so JSON numeric expectations compare by numeric value rather than representation.
- Verification after debug trace slice:
  - `npm test` passed: 48 fixtures checked across Python and JavaScript, Go tests green, hygiene checks green.
  - `npm run check:packages` passed: fresh Python venv import, npm tarball import, and fresh Go module import all green.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_project_hygiene.py scripts/check_package_installs.py examples/python_basic.py` passed.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq` parsed schemas, fixtures, and package JSON files.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
- Added fixture metadata and coverage slice:
  - Added `schemas/fixture.schema.json` for the shared `ProviderResponseFixture` contract.
  - Backfilled metadata into all 48 fixtures: requirement IDs, provider, surface, scenario, tags, and expected languages.
  - Added `scripts/check_fixture_coverage.py` with metadata validation, generated coverage reporting, and stale-report detection.
  - Added generated coverage report `docs/reports/fixture-coverage.md`.
  - Wired fixture coverage checks into `npm test`, added `npm run check:coverage`, and updated CI compile coverage.
  - Updated README, supported-surfaces doc, API parity matrix, project hygiene checks, and this tracker.
- Verification after fixture metadata and coverage slice:
  - `python3 scripts/check_fixture_coverage.py --write-metadata --write-report` passed for 48 fixtures.
  - `python3 scripts/check_fixture_coverage.py` passed for 48 fixtures.
  - `npm test` passed: 48 fixtures checked across Python and JavaScript, fixture coverage checks passed, Go tests green, hygiene checks green.
  - `npm run check:coverage` passed.
  - `npm run check:packages` passed: fresh Python venv import, npm tarball import, and fresh Go module import all green.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_fixture_coverage.py scripts/check_project_hygiene.py scripts/check_package_installs.py examples/python_basic.py` passed.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq` parsed schemas, fixtures, and package JSON files.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
- Added framework ergonomics slice:
  - Added Python `RunCostLangChainCallback` and `track_langchain_costs(...)` context-manager helper.
  - Added JavaScript `createRunCostVercelMiddleware(...)` with `wrapGenerate`, ledger collection, callback hook, and default `runCost` attachment.
  - Added language-scoped fixtures:
    - `langchain-callback-context-manager.json` for Python.
    - `vercel-ai-sdk-middleware-wrap-generate.json` for JavaScript.
  - Updated fixture runner and Go tests to honor fixture `metadata.expected_languages`, so framework-specific helpers can be explicit without pretending every language has the same runtime integration surface.
  - Updated TypeScript declarations, package import smoke checks, framework docs, API reference, supported surfaces, warnings/limitations, API parity matrix, and this tracker.
- Verification after framework ergonomics slice:
  - `python3 scripts/check_fixtures.py` passed with 50 fixtures across declared Python and JavaScript fixture coverage.
  - `python3 scripts/check_fixture_coverage.py --write-report` passed and regenerated coverage for 50 fixtures.
  - `python3 scripts/check_fixture_coverage.py` passed.
  - `python3 scripts/check_project_hygiene.py` passed.
  - `gofmt -w packages/go/ledger/ledger_test.go && go test ./packages/go/...` passed.
  - `npm test` passed: 50 fixtures checked across declared Python and JavaScript fixture coverage, fixture coverage checks passed, Go tests green, hygiene checks green.
  - `npm run check:coverage` passed.
  - `npm run check:packages` passed: fresh Python venv import including `track_langchain_costs`, npm tarball import including `createRunCostVercelMiddleware`, and fresh Go module import all green.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_fixture_coverage.py scripts/check_project_hygiene.py scripts/check_package_installs.py examples/python_basic.py` passed.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq` parsed schemas, fixtures, and package JSON files.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
- Verified Helicone cost package source shape against live primary sources:
  - `packages/cost/README.md` describes the model registry, endpoint configs, PTB/BYOK split, and legacy cost table fields.
  - `packages/cost/models/types.ts` defines `ModelPricing` with threshold, input, output, cache multipliers, thinking, request, modality, and web-search fields.
  - `packages/cost/models/calculate-cost.ts` applies cache multipliers, thinking cost fallback, modality costs, web-search cost, request cost, and provider-specific threshold selection.
- Added source adapter fixtures:
  - `user-pricing-adapter-compact.json`
  - `helicone-adapter-basic.json`
- Implemented source adapters across Python, JavaScript/TypeScript, and Go:
  - `price_cards_from_user_pricing`, `priceCardsFromUserPricing`, `PriceCardsFromUserPricing`
  - `price_cards_from_helicone`, `priceCardsFromHelicone`, `PriceCardsFromHelicone`
- Updated fixture runners, TypeScript declarations, Python exports, Go API comments, package hygiene checks, API reference, source-adapter docs, supported-surface docs, README, project plan, and this tracker for the new adapters.
- Verification after source adapter slice:
  - `python3 scripts/check_fixtures.py` passed with 52 fixtures across declared Python and JavaScript fixture coverage.
  - `python3 scripts/check_fixture_coverage.py --write-report` passed and regenerated coverage for 52 fixtures.
  - `go test ./packages/go/...` passed.
- Added package publish-readiness slice:
  - Added MIT `LICENSE`, package license metadata, `CHANGELOG.md`, `CONTRIBUTING.md`, and `SECURITY.md`.
  - Added `docs/process/release-process.md` covering version policy, PyPI trusted publishing, npm trusted publishing/provenance, Go semantic version tags, pre-release checks, and rollback guidance.
  - Added guarded manual `.github/workflows/release.yml` that verifies, builds Python and npm artifacts, uploads release artifacts, and publishes only when the workflow input explicitly enables publishing.
  - Added `scripts/check_release_readiness.py`, `npm run check:release`, and CI coverage for release-readiness checks.
  - Updated package install docs, README, project plan, CI workflow, project hygiene checks, and this tracker.
- Verification after package publish-readiness slice:
  - `npm test` passed: 52 fixtures, fixture coverage, Go tests, and hygiene checks green.
  - `npm run check:coverage` passed.
  - `npm run check:packages` passed with clean Python, npm, and Go install smoke checks.
  - `npm run check:release` passed.
  - `python3 scripts/check_project_hygiene.py` passed.
  - `python3 -m py_compile` passed for package modules, scripts, and examples.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - Python package build passed in an isolated virtual environment and produced sdist/wheel artifacts.
  - npm package tarball build passed.
  - `jq empty` parsed schemas, fixtures, and package JSON files.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `git diff --check` passed.

### 2026-05-25 models.dev Source Adapter Slice

- Selected the planned models.dev catalog enrichment gap within Milestone 3.
- Added `price_cards_from_models_dev`, `priceCardsFromModelsDev`, and `PriceCardsFromModelsDev` across Python, JavaScript/TypeScript, and Go.
- Added `fixtures/models-dev-adapter-basic.json` to prove models.dev provider/model data maps per-million token prices, cache read/write, reasoning, audio token fields, context tiers, capabilities, limits, source license, and provenance into canonical price cards.
- Added `models-dev` support to fixture runners, local JSON price file loading, and the explicit refresh command preset list.
- Updated cost-ledger source schema and Go ledger validation to allow source license metadata that was already present in public type surfaces.
- Updated source-adapter docs, API reference, API parity docs, README, project plan, package install checks, fixture floor, fixture coverage report, and this tracker.
- Verification after the models.dev source adapter slice:
  - `python3 scripts/check_fixtures.py --fixture fixtures/models-dev-adapter-basic.json` passed.
  - `python3 scripts/check_fixture_coverage.py --write-report` passed and regenerated coverage for 65 fixtures.
  - `gofmt -w packages/go/ledger/ledger.go packages/go/ledger/ledger_test.go && go test ./packages/go/...` passed.
  - `python3 scripts/check_project_hygiene.py` passed.
  - `npm test` passed: 65 fixtures, fixture generator checks, source refresh command checks, fixture coverage, taxonomy checks, Go tests, and hygiene checks green.
  - `npm run check:packages` passed with clean Python, npm, and Go install smoke checks including models.dev adapter exports.
  - `npm run check:release` passed.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_fixture_coverage.py scripts/check_fixture_generator.py scripts/check_project_hygiene.py scripts/check_package_installs.py scripts/check_release_readiness.py scripts/check_schema_taxonomy.py scripts/check_source_refresh.py scripts/refresh_price_sources.py scripts/create_fixture.py examples/python_basic.py` passed.
  - `jq empty package.json packages/javascript/core/package.json schemas/*.json fixtures/*.json fixtures/source-files/*.json` passed.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `git diff --check` passed.

### 2026-05-25 Reviewed Official Snapshot Adapter Slice

- Selected the planned official pricing snapshots gap within Milestone 3.
- Added `price_cards_from_official_snapshot`, `priceCardsFromOfficialSnapshot`, and `PriceCardsFromOfficialSnapshot` across Python, JavaScript/TypeScript, and Go.
- Added `fixtures/official-snapshot-adapter-basic.json` to prove reviewed provider pricing page rows map source URL, retrieval time, version/license metadata, effective dates, aliases, token prices, reasoning, cache, and web-search unit prices into canonical price cards.
- Added `official-snapshot` support to fixture runners, local JSON price file loading, and the explicit refresh command.
- Updated source-adapter docs, API reference, API parity docs, README, project plan, package install checks, fixture floor, fixture coverage report, and this tracker.
- Verification after the reviewed official snapshot adapter slice:
  - `python3 scripts/check_fixtures.py --fixture fixtures/official-snapshot-adapter-basic.json` passed.
  - `python3 scripts/check_fixture_coverage.py --write-report` passed and regenerated coverage for 66 fixtures.
  - `gofmt -w packages/go/ledger/ledger.go packages/go/ledger/ledger_test.go && go test ./packages/go/...` passed.
  - `npm test` passed: 66 fixtures, fixture generator checks, source refresh command checks, fixture coverage, taxonomy checks, Go tests, and hygiene checks green.
  - `npm run check:packages` passed with clean Python, npm, and Go install smoke checks including official snapshot adapter exports.
  - `npm run check:release` passed.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_fixture_coverage.py scripts/check_fixture_generator.py scripts/check_project_hygiene.py scripts/check_package_installs.py scripts/check_release_readiness.py scripts/check_schema_taxonomy.py scripts/check_source_refresh.py scripts/refresh_price_sources.py scripts/create_fixture.py examples/python_basic.py` passed.
  - `jq empty package.json packages/javascript/core/package.json schemas/*.json fixtures/*.json fixtures/source-files/*.json` passed.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `git diff --check` passed.

### 2026-05-25 Source Capability Warning Slice

- Selected the planned source capability warnings gap within Milestone 3.
- Added shared warning code `source_capability_unsupported` to the taxonomy, schemas, Python types, and TypeScript declarations.
- Added generic calculator behavior across Python, JavaScript/TypeScript, and Go: when a matching price card carries `metadata.source_capabilities.unsupported_components`, unsupported usage components emit a source capability warning instead of a generic unpriced-component warning.
- Wired reviewed official snapshot rows to copy `capabilities` into generic `metadata.source_capabilities`.
- Added `fixtures/source-capability-warning.json` to prove a source can explicitly mark `web_search_units` unsupported while still pricing token components.
- Updated warning docs, README, project plan, fixture floor, fixture coverage report, and this tracker.
- Verification after the source capability warning slice:
  - `python3 scripts/check_fixtures.py --fixture fixtures/source-capability-warning.json` passed.
  - `gofmt -w packages/go/ledger/ledger.go packages/go/ledger/ledger_test.go && go test ./packages/go/...` passed.
  - `python3 scripts/check_schema_taxonomy.py` passed.
  - `python3 scripts/check_fixture_coverage.py --write-report` passed and regenerated coverage for 67 fixtures.
  - `npm test` passed: 67 fixtures, fixture generator checks, source refresh command checks, fixture coverage, taxonomy checks, Go tests, and hygiene checks green.
  - `npm run check:packages` passed with clean Python, npm, and Go install smoke checks.
  - `npm run check:release` passed.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_fixture_coverage.py scripts/check_fixture_generator.py scripts/check_project_hygiene.py scripts/check_package_installs.py scripts/check_release_readiness.py scripts/check_schema_taxonomy.py scripts/check_source_refresh.py scripts/refresh_price_sources.py scripts/create_fixture.py examples/python_basic.py` passed.
  - `jq empty package.json packages/javascript/core/package.json schemas/*.json fixtures/*.json fixtures/source-files/*.json` passed.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `git diff --check` passed.

### 2026-05-25 YAML Price File Loader Slice

- Selected the final remaining Milestone 3 source adapter gap: YAML file loading.
- Added dependency-free strict YAML price-source file loaders across Python, JavaScript/TypeScript, and Go:
  - `price_cards_from_yaml_file`
  - `priceCardsFromYAMLFile`
  - `PriceCardsFromYAMLFile`
- Added `fixtures/source-files/user-pricing-file-basic.yaml` and `fixtures/user-pricing-yaml-file-loader.json`.
- Wired YAML file sources into Python, JavaScript/TypeScript, and Go fixture runners.
- Updated package install checks, source-adapter docs, API reference, API parity docs, README, project plan, fixture floor, fixture coverage report, and this tracker.
- Marked Milestone 3 complete for current scope and moved the active lane to Milestone 7 release hardening.
- Verification after the YAML price file loader slice:
  - `python3 scripts/check_fixtures.py --fixture fixtures/user-pricing-yaml-file-loader.json` passed.
  - `gofmt -w packages/go/ledger/ledger.go packages/go/ledger/ledger_test.go && go test ./packages/go/...` passed.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_package_installs.py scripts/check_project_hygiene.py` passed.
  - `python3 scripts/check_fixture_coverage.py --write-report` passed and regenerated coverage for 68 fixtures.
  - `npm test` passed: 68 fixtures, fixture generator checks, source refresh command checks, fixture coverage, taxonomy checks, Go tests, and hygiene checks green.
  - `npm run check:packages` passed with clean Python, npm, and Go install smoke checks including YAML file loader exports.
  - `npm run check:release` passed.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_fixture_coverage.py scripts/check_fixture_generator.py scripts/check_project_hygiene.py scripts/check_package_installs.py scripts/check_release_readiness.py scripts/check_schema_taxonomy.py scripts/check_source_refresh.py scripts/refresh_price_sources.py scripts/create_fixture.py examples/python_basic.py` passed.
  - `jq empty package.json packages/javascript/core/package.json schemas/*.json fixtures/*.json fixtures/source-files/*.json` passed.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `git diff --check` passed.

### 2026-05-25 Cost-Ledger Aggregation Slice

- Added `aggregate_cost_ledgers`, `aggregateCostLedgers`, and `AggregateCostLedgers` across Python, JavaScript/TypeScript, and Go.
- Added aggregation behavior for already-calculated cost ledgers:
  - Sums aggregate totals.
  - Groups compatible cost components and sums quantity/cost.
  - De-duplicates price sources.
  - Carries through discounts and warnings.
  - Adds aggregate metadata with observed and expected ledger counts.
- Added `stream_usage_missing` emission when final streaming usage was expected but not observed, or when fewer ledgers than expected are present.
- Added shared aggregation fixtures:
  - `cost-ledger-aggregation-basic.json`
  - `stream-final-usage-missing-warning.json`
- Updated fixture schema and coverage tooling for the `aggregation` scenario and `RC-AGGREGATION` requirement.
- Added `docs/reference/aggregation-and-streaming.md` and updated README, API reference, supported surfaces, warnings/limitations, API parity matrix, project plan, package install checks, and hygiene checks.
- Regenerated `docs/reports/fixture-coverage.md`.
- Verification after aggregation slice:
  - `python3 scripts/check_fixture_coverage.py --write-report` passed and regenerated coverage for 54 fixtures.
  - `python3 scripts/check_project_hygiene.py` passed.
  - `python3 scripts/check_fixtures.py` passed with 54 fixtures across Python and JavaScript.
  - `go test ./packages/go/...` passed.
  - `npm test` passed: 54 fixtures, fixture coverage, Go tests, and hygiene checks green.
  - `npm run check:packages` passed with clean Python, npm, and Go install smoke checks including the new aggregation APIs.
  - `npm run check:release` passed.
  - `python3 -m py_compile` passed for package modules, scripts, and examples.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq empty` parsed schemas, fixtures, and package JSON files.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `git diff --check` passed.

### 2026-05-25 Provider Streaming Final-Usage Slice

- Verified current primary docs for supported stream final-usage shapes:
  - OpenAI Responses streaming emits lifecycle events including `response.completed`, with completed response objects carrying `usage`.
  - Anthropic Messages streaming emits `message_start`, cumulative `message_delta.usage`, and `message_stop` events.
  - Gemini `generateContentStream` returns `GenerateContentResponse` chunks; RunCost reads the final chunk carrying `usageMetadata`.
- Added provider streaming fixtures:
  - `openai-responses-stream-completed-event.json`
  - `anthropic-messages-stream-events.json`
  - `gemini-generate-content-stream-chunks.json`
- Implemented stream final-usage normalization across Python, JavaScript/TypeScript, and Go:
  - OpenAI Responses unwraps the nested `response` object from `response.completed`.
  - Anthropic Messages accumulates a supplied `events` array into a final Message-like payload.
  - Gemini generateContent selects the last chunk with `usageMetadata` from `chunks` or `stream`.
- Updated provider extractor notes, API reference, supported surfaces, warnings/limitations, aggregation/streaming guide, README, API parity matrix, fixture coverage report, and hygiene fixture floor.
- Verification after provider streaming slice:
  - `python3 scripts/check_fixtures.py` passed with 57 fixtures across Python and JavaScript.
  - `go test ./packages/go/...` passed.
  - `python3 scripts/check_fixture_coverage.py --write-report` passed and regenerated coverage for 57 fixtures.
  - `python3 scripts/check_project_hygiene.py` passed.
  - `npm test` passed: 57 fixtures, fixture coverage, Go tests, and hygiene checks green.
  - `npm run check:coverage` passed.
  - `npm run check:packages` passed with clean Python, npm, and Go install smoke checks.
  - `npm run check:release` passed.
  - `python3 -m py_compile` passed for package modules, scripts, and examples.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq empty` parsed schemas, fixtures, and package JSON files.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `git diff --check` passed.

### 2026-05-25 Framework Adapter Path Documentation Slice

- Verified current primary docs for additional framework and gateway adapter paths:
  - Semantic Kernel filters provide interception points around function invocation, prompt rendering, and automatic function invocation; Microsoft also documents prompt, completion, and total token metering for Azure OpenAI/OpenAI connector requests.
  - Haystack `OpenAIChatGenerator` and `OpenAIGenerator` expose OpenAI-style `usage` in reply metadata for non-streaming calls, while current streaming examples can return `usage: None`.
  - AG2 documents `OpenAIWrapper`, `Agent.get_actual_usage()`, `Agent.get_total_usage()`, and `autogen.gather_usage_summary(agents)` usage summaries, plus custom-price and Azure model-version caveats.
  - LangSmith cost tracking exposes input, output, and other categories with token/cost subtypes; trace usage metadata and bulk exports can carry total token and cost fields for comparison.
  - LiteLLM documents token usage, response cost metadata, proxy model metadata, custom pricing, provider discounts, and margins.
  - OpenRouter documents OpenAI-compatible schemas, OpenAI SDK base-URL usage, usage accounting with cost/reasoning/cache fields, and Agent SDK full-response accessors.
- Added documented partial adapter paths in `docs/notes/framework-adapter-notes.md` for:
  - Semantic Kernel.
  - Haystack.
  - AutoGen / AG2.
  - LangSmith export / compare.
  - LiteLLM proxy metadata.
  - OpenRouter-compatible SDK paths.
- Updated `docs/reference/supported-surfaces.md` to distinguish fixture-backed framework adapters from documented partial paths.
- Updated `docs/notes/api-parity-matrix.md`, `PROJECT_PLAN.md`, `README.md`, and `docs/reference/warnings-and-limitations.md` so these paths are visible without overstating support.
- Added hygiene checks to keep the documented partial framework paths present in the adapter notes, supported-surface matrix, and API parity matrix.
- Verification after framework adapter path documentation slice:
  - `python3 scripts/check_project_hygiene.py` passed.
  - `npm test` passed: 57 fixtures, fixture coverage, Go tests, and hygiene checks green.
  - `npm run check:coverage` passed.
  - `npm run check:packages` passed with clean Python, npm, and Go install smoke checks.
  - `npm run check:release` passed.
  - `python3 -m py_compile` passed for package modules, scripts, and examples.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq empty` parsed schemas, fixtures, and package JSON files.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `git diff --check` passed.

### 2026-05-25 Haystack And LiteLLM Adapter Slice

- Verified current primary docs for the two closest documented partial paths:
  - Haystack `OpenAIChatGenerator` reply metadata carries OpenAI-style `usage` under reply `_meta`, including cached prompt and reasoning token details; `OpenAIGenerator` returns equivalent metadata in a `meta` list.
  - LiteLLM returns OpenAI-compatible `usage` across providers and exposes `_hidden_params.response_cost` / logging `response_cost` for computed cost comparison.
- Added framework adapter extractors and one-call helpers across Python, JavaScript/TypeScript, and Go:
  - `extract_haystack_generator_usage`, `extractHaystackGeneratorUsage`, Go internal extraction, plus `from_haystack_generator_result`, `fromHaystackGeneratorResult`, `FromHaystackGeneratorResult`.
  - `extract_litellm_proxy_response_usage`, `extractLiteLLMProxyResponseUsage`, Go internal extraction, plus `from_litellm_response`, `fromLiteLLMResponse`, `FromLiteLLMResponse`.
- Added shared fixtures:
  - `haystack-openai-chat-generator-meta.json`
  - `litellm-proxy-response-cost-metadata.json`
- Updated fixture runners, TypeScript declarations, Python exports, Go API comments, package install smoke checks, API reference, supported surfaces, API parity matrix, framework notes, README, project plan, warning docs, fixture coverage report, and hygiene checks.
- Verification after Haystack and LiteLLM adapter slice:
  - `python3 scripts/check_fixtures.py` passed with 59 fixtures across Python and JavaScript.
  - `gofmt -w packages/go/ledger/ledger.go packages/go/ledger/ledger_test.go && go test ./packages/go/...` passed.
  - `python3 scripts/check_fixture_coverage.py --write-report` passed and regenerated coverage for 59 fixtures.
  - `python3 scripts/check_project_hygiene.py` passed.
  - `npm test` passed: 59 fixtures, fixture coverage, Go tests, and hygiene checks green.
  - `npm run check:coverage` passed.
  - `npm run check:packages` passed with clean Python, npm, and Go install smoke checks including the new Haystack and LiteLLM helper APIs.
  - `npm run check:release` passed.
  - `python3 -m py_compile` passed for package modules, scripts, and examples.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq empty` parsed schemas, fixtures, and package JSON files.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `git diff --check` passed.

### 2026-05-25 Documentation Layout Stabilization Slice

- Completed the in-progress docs reorganization against the current worktree instead of reverting it.
- Moved existing docs into stable category paths:
  - `docs/guides/` for quickstart and package installation.
  - `docs/reference/` for API, streaming, debug trace, pricing, source adapter, supported surface, and warning references.
  - `docs/notes/` for API parity, framework adapter notes, and provider extractor notes.
  - `docs/decisions/` for the polyglot toolchain decision record.
  - `docs/reports/` for fixture coverage.
  - `docs/process/` for release process docs.
- Updated README, project plan, contribution guidance, progress tracker, moved docs, fixture coverage generation, release readiness checks, and project hygiene checks to the new paths.
- Added/kept YAML frontmatter on root and docs markdown files, with `README.md` remaining the only root onboarding doc without frontmatter.
- Verification after documentation layout stabilization slice:
  - `python3 scripts/check_project_hygiene.py` passed.
  - `python3 scripts/check_fixture_coverage.py --write-report` passed and regenerated coverage at `docs/reports/fixture-coverage.md`.
  - `python3 scripts/check_fixture_coverage.py` passed.
  - `npm run check:release` passed.
  - `npm test` passed: 59 fixtures, fixture coverage, Go tests, and hygiene checks green.
  - `git diff --check` passed.
  - Markdown frontmatter inventory passed with `README.md` intentionally exempted.

### 2026-05-25 AutoGen/AG2 Adapter Slice

- Verified the current AG2 usage tracking docs:
  - `OpenAIWrapper.print_usage_summary()` exposes actual and total modes.
  - `Agent.get_actual_usage()`, `Agent.get_total_usage()`, and `autogen.gather_usage_summary(agents)` return usage summary dictionaries.
  - AG2 documents custom token prices and Azure model-version caveats, so RunCost treats AG2 cost as framework-reported comparison data rather than authoritative price data by default.
- Added framework adapter extractors and one-call helpers across Python, JavaScript/TypeScript, and Go:
  - `extract_ag2_usage_summary_usage`, `extractAG2UsageSummaryUsage`, Go internal extraction, plus `from_ag2_usage_summary`, `fromAG2UsageSummary`, `FromAG2UsageSummary`.
- Added shared fixtures:
  - `ag2-usage-summary-actual.json`
  - `ag2-usage-summary-total.json`
- Updated fixture runners, TypeScript declarations, Python exports, Go API comments, package install smoke checks, API reference, supported surfaces, API parity matrix, framework notes, README, project plan, warning docs, fixture coverage report, and hygiene checks.
- Verification after AutoGen/AG2 adapter slice:
  - `python3 scripts/check_fixtures.py` passed with 61 fixtures across Python and JavaScript.
  - `gofmt -w packages/go/ledger/ledger.go packages/go/ledger/ledger_test.go && go test ./packages/go/...` passed.
  - `python3 scripts/check_fixture_coverage.py --write-report` passed and regenerated coverage for 61 fixtures.
  - `python3 scripts/check_project_hygiene.py` passed.
  - `npm test` passed: 61 fixtures, fixture coverage, Go tests, and hygiene checks green.
  - `npm run check:coverage` passed.
  - `npm run check:packages` passed with clean Python, npm, and Go install smoke checks including the new AutoGen/AG2 helper APIs.
  - `npm run check:release` passed.
  - `python3 -m py_compile` passed for package modules, scripts, and examples.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq empty` parsed schemas, fixtures, and package JSON files.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `git diff --check` passed.

### 2026-05-25 Tracker Status Taxonomy Cleanup

- Paused feature expansion after user review feedback that the milestone table made too many roadmap lanes look actively in progress.
- Added explicit status vocabulary separating roadmap state from active work state.
- Added `Active Focus` with the current single active lane and a note to avoid broad docs churn while another agent may rename Markdown files.
- Replaced the milestone table with `Roadmap state`, `Active now?`, evidence, and `Exit-gate remaining` columns.
- Clarified that `Recommended Next Sprint Candidates` and `Backlog: Next Best Actions` are not concurrent active work.
- Verification after tracker cleanup:
  - `python3 scripts/check_project_hygiene.py` passed.
  - `python3 scripts/check_fixture_coverage.py` passed with 61 fixtures.
  - `git diff --check` passed.
  - Tracker text scan showed no remaining milestone-table `In progress` status and no pending verification line after this update.

### 2026-05-25 Fixture Generator Helper Slice

- Selected a low-conflict Milestone 1 slice while another agent may rename Markdown files.
- Added `scripts/create_fixture.py`:
  - Emits a complete normalized-usage example fixture.
  - Builds fixture JSON from metadata and optional JSON fragments for usage ledgers, raw responses, price cards, source data, discounts, options, extraction hints, helper names, expected ledgers, and expected errors.
  - Enforces lowercase kebab-case fixture names and stable metadata fields.
- Added `scripts/check_fixture_generator.py`:
  - Generates a temporary normalized-usage fixture.
  - Runs that generated fixture through `scripts/check_fixtures.py --fixture`.
- Updated `scripts/check_fixtures.py` with `--fixture` so a single new fixture can be validated before running the full suite.
- Added `npm run fixture:new` and wired the generator smoke check into `npm test`, project hygiene, and CI Python compilation.
- Updated `fixtures/README.md` with generator usage.
- Verification after fixture generator helper slice:
  - `python3 scripts/check_fixture_generator.py` passed.
  - `python3 scripts/check_fixtures.py --fixture fixtures/openai-responses-basic.json` passed.
  - `npm --silent run fixture:new -- --example normalized_usage | python3 -m json.tool >/dev/null` passed.
  - `npm test` passed: 61 fixtures, fixture generator smoke checks, fixture coverage, Go tests, and hygiene checks green.
  - `python3 scripts/check_project_hygiene.py` passed.
  - `python3 -m py_compile` passed for package modules, scripts including the new generator/checker, and examples.
  - `python3 scripts/check_fixture_coverage.py` passed with 61 fixtures.
  - `npm run check:coverage` passed.
  - `npm run check:packages` passed with clean Python, npm, and Go install smoke checks.
  - `npm run check:release` passed.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq empty package.json fixtures/*.json schemas/*.json` passed.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `git diff --check` passed.

### 2026-05-25 Go-Side Cost-Ledger Validation Slice

- Selected a second Milestone 1 hardening slice focused on Go conformance, avoiding broad Markdown rename churn.
- Added Go fixture-test validation for generated `CostLedger` objects:
  - Top-level allowed keys and required fields.
  - Model object shape.
  - Cost component required fields and decimal fields.
  - Exact component cost sum equals ledger total with `big.Rat`.
  - Price source, applied discount, warning, debug trace, and metadata object shapes.
- Kept existing expected-subset comparison after structural validation, so Go still verifies fixture-specific expected output.
- Updated API parity notes to reflect stronger Go conformance evidence.
- Verification after Go-side validation slice:
  - `go test ./packages/go/...` passed.
  - `npm test` passed: 61 fixtures, fixture generator checks, fixture coverage, Go tests, and hygiene checks green.
  - `python3 -m py_compile` passed for package modules, scripts, and examples.
  - `python3 scripts/check_project_hygiene.py` passed.
  - `npm run check:coverage` passed.
  - `npm run check:release` passed.
  - `npm --silent run fixture:new -- --example normalized_usage | python3 -m json.tool >/dev/null` passed.
  - `jq empty package.json packages/javascript/core/package.json schemas/*.json fixtures/*.json` passed.
  - `npm run check:packages` passed with clean Python, npm, and Go install smoke checks.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `git diff --check` passed.

### 2026-05-25 Schema Taxonomy Lock Slice

- Selected the remaining Milestone 1 taxonomy-lock gap as a low-conflict data/test slice while Markdown renames may happen separately.
- Added `schemas/taxonomy.json` as the locked v0.1 taxonomy for:
  - Usage and price component names.
  - Units.
  - Warning codes.
  - Alias resolution values.
  - Fixture scenarios.
  - Expected languages.
  - Debug decision types.
- Tightened `schemas/price-card.schema.json` so `components[*].usage_component` uses the same component-name enum as `usage-ledger.schema.json`.
- Added `scripts/check_schema_taxonomy.py` to fail when taxonomy and schema enums drift.
- Wired taxonomy checks into `npm test`, `npm run check:taxonomy`, CI Python compilation, and project hygiene.
- Verification after schema taxonomy lock slice:
  - `python3 scripts/check_schema_taxonomy.py` passed.
  - `python3 scripts/check_fixtures.py` passed with 61 fixtures across Python and JavaScript.
  - `python3 scripts/check_project_hygiene.py` passed.
  - `jq empty schemas/*.json package.json` passed.
  - `npm test` passed: 61 fixtures, fixture generator checks, fixture coverage, taxonomy checks, Go tests, and hygiene checks green.
  - `python3 -m py_compile` passed for package modules, scripts including the taxonomy checker, and examples.
  - `npm run check:taxonomy` passed.
  - `npm run check:coverage` passed.
  - `npm run check:release` passed.
  - `npm --silent run fixture:new -- --example normalized_usage | python3 -m json.tool >/dev/null` passed.
  - `jq empty package.json packages/javascript/core/package.json schemas/*.json fixtures/*.json` passed.
  - `go test ./packages/go/...` passed.
  - `npm run check:packages` passed with clean Python, npm, and Go install smoke checks.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `git diff --check` passed.

### 2026-05-25 Source-Cache Adapter Slice

- Selected Milestone 3 source adapter hardening as the active lane after the taxonomy lock.
- Added `price_cards_from_source_cache`, `priceCardsFromSourceCache`, and `PriceCardsFromSourceCache` across Python, JavaScript/TypeScript, and Go.
- Added `fixtures/source-cache-adapter-basic.json` to prove an offline source-cache envelope can carry URL, retrieval time, checksum, generated time, generated card count, and canonical price cards.
- Updated source-adapter docs, API parity docs, README, project plan, fixture runner routing, Go fixture routing, and project hygiene checks.
- Verification after source-cache adapter slice:
  - `python3 scripts/check_fixtures.py --fixture fixtures/source-cache-adapter-basic.json` passed.
  - `python3 scripts/check_fixture_coverage.py --write-report` passed and regenerated coverage for 62 fixtures.
  - `go test ./packages/go/...` passed.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_fixture_coverage.py scripts/check_project_hygiene.py scripts/check_schema_taxonomy.py scripts/check_package_installs.py examples/python_basic.py` passed.
  - `python3 scripts/check_project_hygiene.py` passed.
  - `npm test` passed: 62 fixtures, fixture generator checks, fixture coverage, taxonomy checks, Go tests, and hygiene checks green.
  - `npm run check:packages` passed with clean Python, npm, and Go install smoke checks including source-cache exports.
  - `npm run check:release` passed.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq empty package.json packages/javascript/core/package.json schemas/*.json fixtures/*.json` passed.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `git diff --check` passed.

### 2026-05-25 llm-prices Historical Semantics Slice

- Verified the live `llm-prices` feed shapes before changing behavior:
  - `current-v1.json` includes top-level `updated_at` and simple price records.
  - `historical-v1.json` uses the same `prices` array shape with `from_date` and `to_date` windows.
- Updated `price_cards_from_llm_prices`, `priceCardsFromLlmPrices`, and `PriceCardsFromLlmPrices` to detect historical records and preserve `https://www.llm-prices.com/historical-v1.json` as the source URL by default.
- Added `fixtures/llm-prices-adapter-historical.json` to prove historical date windows select the effective price card through `context.priced_at`.
- Updated source-adapter docs, API parity docs, project plan, fixture floor, and this tracker.
- Verification after the historical slice:
  - `python3 scripts/check_fixtures.py --fixture fixtures/llm-prices-adapter-historical.json` passed.
  - `python3 scripts/check_fixture_coverage.py --write-report` passed and regenerated coverage for 63 fixtures.
  - `gofmt -w packages/go/ledger/ledger.go packages/go/ledger/ledger_test.go && go test ./packages/go/...` passed.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_fixture_coverage.py scripts/check_project_hygiene.py scripts/check_schema_taxonomy.py scripts/check_package_installs.py examples/python_basic.py` passed.
  - `python3 scripts/check_project_hygiene.py` passed.
  - `npm test` passed: 63 fixtures, fixture generator checks, fixture coverage, taxonomy checks, Go tests, and hygiene checks green.
  - `npm run check:packages` passed with clean Python, npm, and Go install smoke checks.
  - `npm run check:release` passed.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq empty package.json packages/javascript/core/package.json schemas/*.json fixtures/*.json` passed.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `git diff --check` passed.

### 2026-05-25 Local JSON Price File Loader Slice

- Selected the planned user local custom price-file gap within Milestone 3.
- Added `price_cards_from_json_file`, `priceCardsFromJSONFile`, and `PriceCardsFromJSONFile` across Python, JavaScript/TypeScript, and Go.
- Added `fixtures/source-files/user-pricing-file-basic.json` as a local source file and `fixtures/user-pricing-json-file-loader.json` as the conformance fixture.
- Wired the local JSON file source into Python, JavaScript/TypeScript, and Go fixture runners.
- Updated source-adapter docs, API reference, API parity docs, README, project plan, package install checks, fixture floor, and this tracker.
- Verification after the local JSON file-loader slice:
  - `python3 scripts/check_fixtures.py --fixture fixtures/user-pricing-json-file-loader.json` passed.
  - `python3 scripts/check_fixture_coverage.py --write-report` passed and regenerated coverage for 64 fixtures.
  - `gofmt -w packages/go/ledger/ledger.go packages/go/ledger/ledger_test.go && go test ./packages/go/...` passed.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_fixture_coverage.py scripts/check_project_hygiene.py scripts/check_schema_taxonomy.py scripts/check_package_installs.py examples/python_basic.py` passed.
  - `python3 scripts/check_project_hygiene.py` passed.
  - `npm test` passed: 64 fixtures, fixture generator checks, fixture coverage, taxonomy checks, Go tests, and hygiene checks green.
- `npm run check:packages` passed with clean Python, npm, and Go install smoke checks including local JSON file loader exports.
- `npm run check:release` passed.
- `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `jq empty package.json packages/javascript/core/package.json schemas/*.json fixtures/*.json fixtures/source-files/*.json` passed.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `git diff --check` passed.

### 2026-05-25 Explicit Source Refresh Command Slice

- Selected the planned explicit refresh command gap within Milestone 3.
- Added `scripts/refresh_price_sources.py`:
  - Fetches a live JSON source through an explicit command path, or converts a local reviewed JSON snapshot through `--input`.
  - Supports presets for `llm-prices-current`, `llm-prices-historical`, and `openrouter-models`.
  - Converts through existing source adapters and writes a RunCost source-cache envelope with source URL, retrieval time, generated time, SHA-256 checksum, and canonical price cards.
  - Rewrites generated card source metadata to the refreshed source URL and retrieval timestamp so downstream ledgers preserve provenance.
- Added `scripts/check_source_refresh.py` as a no-network smoke check using the local user-pricing source fixture.
- Added `npm run prices:refresh -- ...`, wired the smoke check into `npm test`, and added CI compile/hygiene coverage.
- Updated source-adapter docs, README, project plan, and this tracker.
- Verification after the explicit source refresh command slice:
  - `python3 scripts/check_source_refresh.py` passed.
  - `python3 -m py_compile scripts/refresh_price_sources.py scripts/check_source_refresh.py scripts/check_project_hygiene.py` passed.
  - `python3 scripts/check_project_hygiene.py` passed.
  - `npm test` passed: 64 fixtures, fixture generator checks, source refresh command checks, fixture coverage, taxonomy checks, Go tests, and hygiene checks green.
  - `npm run check:packages` passed with clean Python, npm, and Go install smoke checks.
  - `npm run check:release` passed.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/types.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_fixture_coverage.py scripts/check_fixture_generator.py scripts/check_project_hygiene.py scripts/check_package_installs.py scripts/check_release_readiness.py scripts/check_schema_taxonomy.py scripts/check_source_refresh.py scripts/refresh_price_sources.py scripts/create_fixture.py examples/python_basic.py` passed.
  - `jq empty package.json packages/javascript/core/package.json schemas/*.json fixtures/*.json fixtures/source-files/*.json` passed.
  - `LC_ALL=C rg -n "[^[:ascii:]]" .` found no non-ASCII text.
  - `git diff --check` passed.

### 2026-05-25 Release Dry Run Slice

- Selected the active Milestone 7 release-hardening gap for a no-publish release dry run.
- Added `scripts/check_release_dry_run.py` and `npm run check:release-dry-run`.
- The dry run:
  - Builds the Python wheel and source distribution in a temporary directory.
  - Packs the JavaScript/TypeScript package with `npm pack`.
  - Verifies the Go module path is `github.com/adamallcock/runcost`.
  - Creates a clean temporary Go module, uses a local replace directive, imports `github.com/adamallcock/runcost/packages/go/ledger`, and runs a small cost calculation.
- Wired the dry-run command into the guarded release workflow verification stage.
- Updated release readiness checks and release-process docs so the command is required and documented.
- Verification after the release dry-run slice:
  - `npm run check:release-dry-run` passed, building `runcost-0.0.0.tar.gz`, `runcost-0.0.0-py3-none-any.whl`, and `runcost-0.0.0.tgz`, then passing the clean Go import smoke test.
  - `python3 -m py_compile scripts/check_release_dry_run.py scripts/check_release_readiness.py` passed.
  - `npm run check:release` passed.
  - `npm test` passed: 68 fixtures, fixture generator checks, source refresh command checks, fixture coverage, taxonomy checks, Go tests, and hygiene checks green.
  - `git diff --check` passed.

### 2026-05-25 Registry README And Trusted Publisher Notes Slice

- Selected the active Milestone 7 registry README and trusted-publisher documentation gap.
- Added `packages/javascript/core/README.md` as the npm package-page README and included it in the npm package allowlist.
- Kept the root `README.md` as the canonical GitHub/PyPI README through `pyproject.toml`.
- Added a registry README policy and exact npm trusted-publisher setup notes to `docs/process/release-process.md`.
- Strengthened release readiness checks so they fail if:
  - PyPI no longer points at the root README.
  - The npm package allowlist drops `README.md`.
  - The npm README stops linking back to the full repository docs.
  - The root README omits the release dry-run command.
  - Release docs drop the registry README policy or npm trusted-publisher fields.
- Strengthened the release dry run so it opens the packed npm tarball and verifies `package/README.md` is present.
- Updated package install checks to install, pack, and import from a temporary source copy so validation does not leave Python build metadata in the working tree.
- Verification after the registry README and trusted-publisher notes slice:
  - `python3 -m py_compile scripts/check_package_installs.py scripts/check_release_dry_run.py scripts/check_release_readiness.py` passed.
  - `npm run check:release` passed.
  - `npm run check:release-dry-run` passed and showed the npm tarball includes `README.md`.
  - `npm run check:packages` passed with the npm tarball containing `README.md`.
  - `npm test` passed: 68 fixtures, fixture generator checks, source refresh command checks, fixture coverage, taxonomy checks, Go tests, and hygiene checks green.
  - `find . -maxdepth 4 \( -name 'build' -o -name '*.egg-info' -o -name 'dist' \) -print` produced no output after package and release dry-run checks.
  - `git diff --check` passed.

### 2026-05-25 xAI Responses Extractor Slice

- Selected a concrete Milestone 4 provider-surface gap during the Milestones 0-4 completion pass.
- Added `fixtures/xai-responses-raw-cache-reasoning.json` to prove xAI Responses usage extraction with cached input and reasoning output tokens.
- Reused the OpenAI-compatible Responses extractor path across Python, JavaScript/TypeScript, and Go, while defaulting `surface: "xai.responses"` to provider `xai` when callers omit the provider.
- Updated provider extractor notes, supported surfaces, API reference, API parity matrix, project plan, fixture coverage report, and this tracker.
- Verification after the xAI Responses slice:
  - `python3 scripts/check_fixtures.py --fixture fixtures/xai-responses-raw-cache-reasoning.json` passed.
  - `go test ./packages/go/...` passed.
  - `python3 scripts/check_fixture_coverage.py --write-report` passed and regenerated coverage for 69 fixtures.
  - `npm test` passed: 69 fixtures, fixture generator checks, source refresh command checks, fixture coverage, taxonomy checks, Go tests, and hygiene checks green.
  - `python3 -m py_compile packages/python/runcost/core.py scripts/check_fixtures.py scripts/check_fixture_coverage.py` passed.
  - `jq empty package.json packages/javascript/core/package.json schemas/*.json fixtures/*.json fixtures/source-files/*.json` passed.
  - `npm run check:packages` passed.
  - `npm run check:release` passed.
  - `npm run check:release-dry-run` passed.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `find . -maxdepth 4 \( -name 'build' -o -name '*.egg-info' -o -name 'dist' \) -print` produced no output after package and release dry-run checks.
  - `git diff --check` passed.

### 2026-05-25 OpenAI Embeddings And Tie-Break Slice

- Selected a combined Milestone 4/Milestone 2 closure slice after the next visible gaps were OpenAI embeddings and deterministic calculator tie-breaking.
- Added `fixtures/openai-embeddings-raw-basic.json` to prove OpenAI Embeddings usage extraction from `usage.prompt_tokens` into `embedding_tokens`.
- Added `fixtures/byte-stable-price-card-tie-break.json` to prove matching price-card ties are resolved deterministically by source name and card id rather than caller array order.
- Added `extract_openai_embeddings_usage` / `extractOpenAIEmbeddingsUsage` and Go dispatch support for `openai.embeddings`.
- Updated provider extractor notes, supported surfaces, API reference, API parity matrix, project plan, fixture coverage report, package install checks, hygiene checks, and this tracker.
- Verification after the OpenAI embeddings and tie-break slice:
  - `python3 scripts/check_fixtures.py --fixture fixtures/byte-stable-price-card-tie-break.json --fixture fixtures/openai-embeddings-raw-basic.json` passed.
  - `python3 scripts/check_fixtures.py` passed with 71 fixtures.
  - `python3 scripts/check_fixture_coverage.py --write-report` passed and regenerated coverage for 71 fixtures.
  - `npm test` passed: 71 fixtures, fixture generator checks, source refresh command checks, fixture coverage, taxonomy checks, Go tests, and hygiene checks green.
  - `go test -count=1 ./packages/go/...` passed.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_package_installs.py scripts/check_project_hygiene.py` passed.
  - `jq empty package.json packages/javascript/core/package.json schemas/*.json fixtures/*.json fixtures/source-files/*.json` passed.
  - `npm run check:packages` passed with the new Python and JavaScript embeddings exports included in clean package install checks.
  - `npm run check:release` passed.
  - `npm run check:release-dry-run` passed.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `find . -maxdepth 4 \( -name 'build' -o -name '*.egg-info' -o -name 'dist' \) -print` produced no output after package and release dry-run checks.
  - `git diff --check` passed.

### 2026-05-25 Bedrock InvokeModel And Byte-Stable Ordering Slice

- Selected a Milestone 4 provider-surface gap from the active completion pass: AWS Bedrock non-Converse `InvokeModel` with Anthropic Messages response bodies.
- Added `fixtures/bedrock-invoke-model-anthropic-messages.json` to prove `body.usage.input_tokens` and `body.usage.output_tokens` extraction into canonical input/output token components.
- Added `fixtures/byte-stable-component-ordering.json` to prove output components are canonicalized even when usage-ledger and price-card components arrive in a different order.
- Added `extract_bedrock_invoke_model_usage` / `extractBedrockInvokeModelUsage` and Go dispatch support for `aws.bedrock.invoke_model`.
- Tightened Milestone 2 byte-stable output ordering by checking expected and actual components, price sources, applied discounts, and warnings in the Python/JavaScript fixture runner and Go fixture validation.
- Normalized older fixture expected component arrays to the canonical taxonomy order without changing usage inputs or pricing amounts.
- Updated provider extractor notes, supported surfaces, API reference, API parity matrix, project plan, fixture coverage report, package install checks, hygiene checks, and this tracker.
- Verification after the Bedrock InvokeModel and byte-stable ordering slice:
  - `python3 scripts/check_fixtures.py --fixture fixtures/byte-stable-component-ordering.json --fixture fixtures/anthropic-messages-raw-cache-1h.json --fixture fixtures/bedrock-converse-raw-cache.json --fixture fixtures/gemini-generate-content-raw-multimodal.json` passed.
  - `python3 scripts/check_fixtures.py` passed with 73 fixtures.
  - `python3 scripts/check_fixture_coverage.py --write-report` passed and regenerated coverage for 73 fixtures.
  - `npm test` passed: 73 fixtures, fixture generator checks, source refresh command checks, fixture coverage, taxonomy checks, Go tests, and hygiene checks green.
  - `go test ./packages/go/...` passed.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/__init__.py scripts/check_fixtures.py scripts/check_fixture_coverage.py scripts/check_package_installs.py scripts/check_project_hygiene.py` passed.
  - `jq empty package.json packages/javascript/core/package.json schemas/*.json fixtures/*.json fixtures/source-files/*.json` passed.
  - `npm run check:packages` passed with the new Python and JavaScript Bedrock InvokeModel exports included in clean package install checks.
  - `npm run check:release` passed.
  - `npm run check:release-dry-run` passed.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `find . -maxdepth 4 \( -name 'build' -o -name '*.egg-info' -o -name 'dist' \) -print` produced no output after package and release dry-run checks.
  - `git diff --check` passed.

### 2026-05-25 OpenAI Conversations Cost-Surface Decision

- Verified current official OpenAI docs for Conversations and Responses.
- Recorded the decision that OpenAI Conversations are state resources used with Responses, not standalone usage-bearing model responses.
- Chose not to add an `openai.conversations` extractor in v0.x because pricing belongs to the associated Responses calls.
- Updated provider extractor notes, supported surfaces, API parity matrix, project plan, and this tracker.
- Reclassified Milestone 4 as complete for current scope. Remaining generated-media, rerank, transcription, provider-specific tool fields, and deeper stream variants move to Milestone 5+ or beta/V1 hardening.
- Follow-up focus then moved to the remaining Milestone 2 warning metadata and adversarial-calculator hardening, which is closed in the next work-log entry.
- Verification after the OpenAI Conversations decision:
  - `python3 scripts/check_project_hygiene.py` passed.
  - `git diff --check` passed.
  - `npm test` passed: 73 fixtures, fixture generator checks, source refresh command checks, fixture coverage, taxonomy checks, Go tests, and hygiene checks green.

### 2026-05-25 Warning Metadata And Decimal Hardening Slice

- Selected the final Milestone 2 hardening gap from the active Milestones 0-4 completion pass.
- Made warning metadata required in `schemas/cost-ledger.schema.json`.
- Added `warning_metadata_required_keys` to `schemas/taxonomy.json` and strengthened `scripts/check_schema_taxonomy.py` so every warning code has explicit required metadata keys.
- Strengthened `scripts/check_fixtures.py` so expected ledgers and Python/JavaScript actual ledgers must include required warning metadata.
- Strengthened Go fixture validation so Go actual ledgers must include required warning metadata from the shared taxonomy.
- Added typed warning metadata surfaces in Python and TypeScript.
- Added required metadata to all warning fixtures.
- Added `fixtures/decimal-arithmetic-adversarial.json` to prove large string quantities and tiny prices do not leak binary-float behavior.
- Updated fixture coverage, API parity notes, warning docs, project plan, and this tracker.
- Reclassified Milestone 2 as complete for current scope. Milestones 0, 1, 1.5, 2, 3, and 4 are now all complete for current scope.
- Verification after the warning metadata and decimal hardening slice:
  - `python3 scripts/check_fixtures.py --fixture fixtures/decimal-arithmetic-adversarial.json` passed.
  - `python3 scripts/check_fixtures.py --fixture fixtures/provider-reported-cost-mismatch.json --fixture fixtures/long-context-rule-missing.json --fixture fixtures/unknown-model-compatibility.json --fixture fixtures/unknown-surface-compatibility.json --fixture fixtures/unpriced-component-compatibility.json` passed.
  - `go test ./packages/go/...` passed.
  - `python3 -m py_compile packages/python/runcost/core.py packages/python/runcost/__init__.py packages/python/runcost/types.py scripts/check_fixtures.py scripts/check_schema_taxonomy.py scripts/check_fixture_coverage.py scripts/check_package_installs.py scripts/check_project_hygiene.py` passed.
  - `jq empty package.json packages/javascript/core/package.json schemas/*.json fixtures/*.json fixtures/source-files/*.json` passed.
  - `python3 scripts/check_fixture_coverage.py --write-report` passed and regenerated coverage for the then-current fixture set.
  - `npm test` passed: fixture checks, fixture generator checks, source refresh command checks, fixture coverage, taxonomy checks, Go tests, and hygiene checks green.
  - `npm run check:packages` passed.
  - `npm run check:release` passed.
  - `npm run check:release-dry-run` passed.
  - `npm run example:js` and `npm run example:py` both ran and returned total `0.000228`.
  - `find . -maxdepth 4 \( -name 'build' -o -name '*.egg-info' -o -name 'dist' \) -print` produced no output after package and release dry-run checks.
  - `git diff --check` passed.

## Gap Audit 2026-05-25

Purpose: step back from feature slices and record what is actually done, what is partial, what is a stub, and what still needs completion before private alpha, public beta, and V1.

### Finalization Re-Evaluation 2026-05-25

Question: do we have real-life smoke tests?

Answer: not yet. The repo has strong local validation, but not a real SDK/API/application smoke harness.

What exists today:

- Fixture conformance: `npm test` runs 81 shared fixtures through Python and JavaScript, runs Go tests, checks fixture metadata coverage, source-refresh smoke behavior, schema taxonomy, fixture generator behavior, and project hygiene.
- Package smoke tests: `npm run check:packages` installs Python from a temporary source copy, packs and installs the npm tarball into a clean npm project, and imports the Go package from a clean temporary module with a local replace directive.
- Release artifact smoke tests: `npm run check:release-dry-run` builds Python wheel/source distribution, packs npm, confirms the npm tarball includes `README.md`, and verifies Go importability from a clean temporary module.
- Examples: `examples/python_basic.py`, `examples/javascript_basic.mjs`, and Go example tests exercise synthetic provider responses and price cards.
- Price-source refresh smoke tests: `python3 scripts/check_source_refresh.py` proves the refresh command shape without depending on network access.

What does not exist yet:

- No live OpenAI Responses, Anthropic Messages, OpenRouter, Gemini/Vertex, Bedrock, or framework SDK smoke script.
- No optional API-key-gated alpha smoke harness that records provider response shape, RunCost ledger output, and regression fixture candidates.
- No sample invoice/dashboard reconciliation run.
- No real application integration evidence for Vercel streaming, LangChain agent runs, OpenAI Agents SDK runs, Semantic Kernel filters, LangSmith exports, or multi-provider router usage.
- No recurring live-source drift monitor that proposes fixture/source updates.

Language support today:

- Python: first-class prototype package. Public functions, manual `TypedDict` contracts, source install, package smoke checks, examples, and fixture conformance exist.
- JavaScript/TypeScript: first-class prototype package. ESM runtime, manual TypeScript declarations, npm package README, tarball install checks, examples, and fixture conformance exist.
- Go: first-class conformance participant for core/package behavior. Go now has typed wrappers for normalized usage, price cards, discount policies, calculator options, and core calculation, while raw provider/framework/source paths remain map-backed prototype APIs.
- Future languages: not started. New language support should not begin until schema-derived artifacts and alpha smoke results stabilize Python, JavaScript/TypeScript, and Go.

Finalization path after the Milestones 0-4 completion pass:

1. Build the Milestone 8 alpha smoke harness. It should be optional and API-key-gated, never require secrets for normal CI, and emit sanitized outputs that can become fixtures. Minimum scenarios: OpenAI Responses with cached/reasoning/tool usage, Anthropic Messages with cache write/read, OpenRouter provider-reported cost comparison, Vercel AI SDK streaming final usage, LangChain callback/context manager, OpenAI Agents SDK usage, LangSmith export comparison, Semantic Kernel telemetry/filter output, and one multi-call aggregation run.
2. Convert every smoke discrepancy into a fixture, warning, or documented limitation. This is the quality loop that prevents live findings from staying as notes.
3. Run one invoice/dashboard comparison sample. The goal is not universal invoice exactness; it is to document where RunCost is exact, estimated, or intentionally limited.
4. Cut the first registry release after smoke harness confidence: configure PyPI/npm trusted publishers externally, tag `v0.1.0`, run the release workflow with publishing disabled, inspect artifacts, then publish.
5. After private alpha feedback, choose the beta hardening lane: schema-derived types and generated drift checks, or provider/framework breadth, depending on actual alpha failures.

Naming update:

- Project/package name selected: `runcost`.
- Public docs now use `RunCost`.
- Python import path is now `runcost`.
- JavaScript package name is now `runcost`.
- Go module path is now `github.com/adamallcock/runcost`.

Audit evidence:

- `python3 scripts/check_fixtures.py` passed with 81 fixtures across declared Python and JavaScript fixture coverage after the Milestone 6 framework adapter slice.
- `python3 scripts/check_fixture_coverage.py` passed with metadata on all 81 fixtures and a current checked-in coverage report after the Milestone 6 framework adapter slice.
- `python3 scripts/check_source_refresh.py` passed against a no-network local snapshot.
- `npm test` passed: fixture checks, source refresh command checks, fixture coverage checks, schema taxonomy checks, Go tests, and project hygiene checks green after the warning metadata and decimal hardening slice.
- `npm run check:packages` passed: clean Python, npm, and Go install smoke checks green.
- `npm run check:release` passed: release docs, license metadata, version sync, changelog, and release workflow guardrails are checked.
- Current package surfaces inspected:
  - `packages/python/runcost/`
  - `packages/javascript/core/`
  - `packages/go/ledger/`
  - `schemas/`
  - `fixtures/`
  - `docs/`
  - `PROJECT_PLAN.md`
  - `PRODUCT_REQUIREMENTS.md`
  - `README.md`
  - `ARCHITECTURE.md`

Supported languages today:

- Python: first-class prototype core, typed with manual `TypedDict` contracts, package metadata exists in `pyproject.toml`, examples run, and clean local install checks pass.
- JavaScript/TypeScript: first-class prototype ESM core, manual `index.d.ts` declarations, package metadata exists, package tarball install checks pass, publish allowlist exists, and guarded npm publish workflow exists, but no registry release has been cut yet.
- Go: first-class conformance participant with public functions, docs, example tests, public GitHub module path, clean module import checks, and typed wrappers for the normalized usage/price-card/discount core path. Raw provider/framework/source APIs are still map-backed rather than schema-derived structs.
- Future languages: no implementation yet. The policy says future languages must consume schemas and fixtures first.

What is implemented and well covered:

- Canonical schemas for usage ledgers, price cards, discount policies, and cost ledgers.
- Locked v0.1 taxonomy for component names, units, warning codes, warning metadata required keys, alias resolution values, fixture scenarios, expected languages, and debug decision types.
- Shared fixture-first conformance across Python, JavaScript/TypeScript, and Go.
- Fixture metadata and generated coverage reporting for requirements, provider surfaces, components, warnings, source adapters, framework adapters, tags, and expected languages.
- Decimal-safe component cost calculation.
- Adversarial decimal arithmetic coverage for large token quantities and tiny per-token prices.
- Strict and compatibility modes.
- Alias resolution through price-card aliases.
- Discounts with component include/exclude policy.
- Effective-date selection, service tier, region, batch, priority, provisioned, long-context conditions, stale-source warnings, provider-reported cost compare/use modes, price-source priority, and price-source disagreement warnings.
- Deterministic price-card tie-breaking by source name and card id when matching cards have the same score.
- Byte-stable cost-ledger output ordering for components, price sources, applied discounts, and warnings.
- Typed warning metadata payloads enforced by the cost-ledger schema, taxonomy, Python/JavaScript fixture runner, and Go fixture validation.
- Optional debug traces for price-card candidates, component matches, model alias resolution, discount applications, and warnings.
- Source adapters for `llm-prices` current and historical feeds, LiteLLM, Portkey, OpenRouter models, models.dev, reviewed official snapshots, source-cache envelopes, local JSON/YAML files, source capability warnings, user compact pricing, and Helicone model-registry data.
- Provider extractors for OpenAI Responses, OpenAI Chat Completions, OpenAI Embeddings, Anthropic Messages, OpenRouter chat completions, Groq, xAI Chat Completions and xAI Responses, Mistral, DeepSeek, Azure OpenAI chat, Hugging Face Inference Providers chat, Cohere Chat, Gemini/Vertex generateContent, Bedrock Converse, and Bedrock InvokeModel with Anthropic Messages bodies, including selected final streaming usage envelopes for OpenAI Responses, Anthropic Messages, and Gemini generateContent.
- Framework metadata helpers for LangChain AIMessage, OpenAI Agents SDK usage objects, Vercel AI SDK generateText and streamText finish objects, LlamaIndex TokenCountingHandler data, Haystack generator metadata, LiteLLM proxy response metadata, AutoGen/AG2 usage summaries, LangSmith run/export usage, Semantic Kernel telemetry, OpenRouter SDK response objects, Python LangChain callback/context-manager usage, and JavaScript Vercel `wrapGenerate` / `onFinish` helpers.
- Cost-ledger aggregation for multi-call/session rollups, with fixture-backed `stream_usage_missing` warnings when final stream usage is expected but absent.
- Docs for project plan, product requirements, architecture, market validation, live evaluation protocol, parity matrix, provider extractor notes, framework adapter notes, polyglot tooling decision, contribution, security, changelog, and release process.

Partially implemented:

- Contract hardening is complete for the current prototype scope: schema validation, fixture metadata, debug trace fixtures, fixture coverage reporting, single-fixture validation, fixture generator helpers, Go-side cost-ledger structure/component-total/output-order validation, and a machine-checked v0.1 taxonomy lock exist. Broader schema-derived type generation is tracked under Milestone 1.5.
- Polyglot maintainability: parity matrix and hygiene checks exist, generated taxonomy plus schema-field docs now have drift checks, and Python/TypeScript/Go taxonomy-bearing type surfaces are checked against `schemas/taxonomy.json`. TypeScript and Python types are manual. Go has typed wrappers for the core normalized usage/price-card/discount path, but provider/framework/source APIs still use object maps.
- Go conformance: Go runs every fixture, validates generated cost-ledger structure, enforces exact component-total invariants, checks byte-stable output ordering and warning metadata keys, and checks expected subsets. Full JSON Schema validation and schema-derived structs remain future hardening work.
- Source adapters: complete for the current prototype scope. Core adapters exist for nine source families plus local JSON/YAML file loading and an explicit source refresh command, including source-cache envelopes, models.dev enrichment, reviewed official pricing snapshots, source capability warnings, user compact pricing, and Helicone model-registry data. Later source expansion moves to beta/V1 hardening.
- Historical pricing: effective dates and `llm-prices` historical feed date windows are fixture-proven, but broader provider historical catalogs and migration semantics remain future hardening.
- Provider extractors: complete for the current V0 provider-surface scope. OpenAI Responses, OpenAI Embeddings, xAI Responses, Anthropic Messages, Bedrock InvokeModel with Anthropic Messages bodies, and Gemini final stream usage shapes now have fixtures. OpenAI Conversations are documented as non-cost-bearing state resources whose costs attach to Responses. Provider-specific tool fields, other streaming variants, rerank, image/audio/video generation, and transcription paths move to Milestone 5+ or beta/V1 hardening.
- Tool pricing: generic tool components, OpenAI raw tool calls, OpenRouter image/request/search source pricing, and custom units exist. Provider-specific tool pricing remains sparse.
- Multimodal: Gemini/Vertex modality token details are covered. Other providers and generated-media billing are not.
- Framework adapters: complete for the current no-live-smoke scope. Direct metadata/result objects are fixture-backed for LangChain, OpenAI Agents SDK usage, Vercel AI SDK generateText and streamText finish results, LlamaIndex, Haystack, LiteLLM proxy responses, AutoGen/AG2 usage summaries, LangSmith run/export usage, Semantic Kernel telemetry, and OpenRouter-compatible SDK responses. Initial Python LangChain callback/context-manager plus JavaScript Vercel middleware/onFinish helpers exist, and generic multi-step cost-ledger aggregation exists. Live SDK/API-key smoke, real app validation, product-truth register updates for new findings, and deeper callback/stream variants move to Milestone 8/beta hardening.
- Documentation: public quickstart, installation, API reference, aggregation/streaming, debug trace, custom pricing, discount, warning/strict-mode, source adapter, support-matrix docs, contribution guide, security/privacy note, changelog, registry README policy, and release process now exist. Deeper framework integration guides and automated release notes are still missing.
- Packaging: clean local install checks now pass for Python, JavaScript/TypeScript, and Go. License metadata, PyPI/npm guarded release workflow, Go tag policy, changelog, provenance guidance, release readiness checks, registry README checks, local no-publish release dry run, and a successful `publish=false` GitHub release rehearsal from `main` exist. First real registry publication, external trusted publisher configuration, real-version no-publish rehearsal, and real post-tag Go module verification remain incomplete.

Stubs or placeholders:

- `DebugTrace` now has a schema, fixture, docs, and opt-in output across Python, JavaScript/TypeScript, and Go, but traces are still focused on calculator decisions rather than full extractor/framework middleware internals.
- Streaming parser coverage is intentionally narrow: selected final usage envelopes are supported, but arbitrary text-delta estimation and most provider/framework stream protocols remain out of scope.
- Public API type surfaces are manually maintained placeholders for generated/schema-derived models.
- `scripts/check_project_hygiene.py` and `scripts/check_release_readiness.py` are useful guards but still mostly check presence, API-name strings, fixture floor, fixture metadata presence, package metadata, CI commands, release docs, version sync, and release workflow snippets. They are not yet full drift detectors.
- README now provides alpha package onboarding and links to public docs, but does not yet represent a production-ready package.
- Go APIs still include prototype map-backed `Object` functions for raw provider, framework, and source-adapter paths; the normalized usage/price-card/discount calculation path now has typed wrappers.

Highest-risk gaps before private alpha:

1. First real registry release readiness: configure PyPI/npm trusted publishing and verify Go tags after a real tag is pushed.
2. Broader provider/framework streaming support beyond the initial OpenAI, Anthropic, and Gemini final-usage fixtures.
3. Schema-derived typed models and generated artifact workflow, especially for Go structs and generated language types.
4. Broader framework integration ergonomics from live smoke findings, especially real SDK examples, deeper callback variants, and sanitized fixture conversion.
5. Deeper debug traces for extractor and framework adapter internals.
6. Broader schema-derived type generation and drift detection.

Recommended next sprint candidates:

Only one candidate should become the active lane at a time. The Milestones 0-4 completion pass is closing; future broad documentation work should still re-inspect the Markdown rename pass before changing cross-document links.

1. Alpha smoke harness slice: add an optional API-key-gated smoke runner with a no-network sample mode and sanitized output for fixture conversion.
2. Invoice/dashboard comparison slice: add one reviewed sample comparison and document exact, estimated, and unsupported fields.
3. Generated artifact slice: add schema-derived language types.
4. Provider/framework streaming slice: broaden final-usage stream fixtures and wrapper examples based on smoke-test findings.

## Backlog: Next Best Actions

These are ranked backlog items, not simultaneous active work.

1. Add the alpha smoke harness with no-network samples plus optional live OpenAI, Anthropic, OpenRouter, Vercel AI SDK, and LangChain scenarios.
2. Convert smoke findings into fixtures, warnings, or documented limitations.
3. Add one invoice/dashboard comparison sample and document exact versus estimated behavior.
4. Harden release automation with first registry publication and first-tag verification.
5. Add schema-derived language types once alpha smoke findings stop changing core contract shapes.
