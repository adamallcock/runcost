---
title: RunCost Progress Tracker
date: 2026-05-25
type: note
status: draft
---

# RunCost Progress Tracker

Last updated: 2026-05-25

Purpose: keep the implementation state explicit across context compaction and long-running work. This file is the handoff ledger for what is done, what is in progress, what is blocked, and what evidence proves it.

## Active Objective

Complete `PROJECT_PLAN.md` end to end, moving from prototype foundation toward private alpha, public beta, and V1 while keeping the project polyglot, schema-first, fixture-first, and easy to maintain across Python, JavaScript/TypeScript, Go, and future languages.

## Current Verified Baseline

Evidence collected on 2026-05-25:

- `npm test` passes.
- Python and JavaScript fixture runner checks 59 shared fixtures, with fixture metadata allowing language-scoped framework ergonomics fixtures.
- Fixture metadata and checked-in coverage report pass through `python3 scripts/check_fixture_coverage.py`.
- Go package passes `go test ./packages/go/...`.
- Python compile check passes for package, scripts, and Python example.
- JavaScript and Python examples run.
- Clean package install checks pass for Python, JavaScript/TypeScript, and Go through `npm run check:packages`.
- Release readiness checks pass through `npm run check:release`.
- Project hygiene check passes.
- JSON files parse through `jq`.
- ASCII scan reports no non-ASCII text.
- Current cores exist in:
  - `packages/python/runcost/`
  - `packages/javascript/core/`
  - `packages/go/ledger/`
- Shared schemas exist in `schemas/`.
- Shared fixtures exist in `fixtures/`.
- Project plan exists in `PROJECT_PLAN.md`.
- Polyglot decision record exists in `docs/decisions/polyglot-toolchain-decision.md`.
- Public API parity matrix exists in `docs/notes/api-parity-matrix.md`.
- Public quickstart, installation, API reference, aggregation/streaming, debug-trace, fixture-coverage, supported-surface, custom pricing, source adapter, warning, and release process docs exist under `docs/`.
- Root `LICENSE`, `CHANGELOG.md`, `CONTRIBUTING.md`, and `SECURITY.md` exist.
- CI workflow exists in `.github/workflows/ci.yml`.
- Guarded release workflow exists in `.github/workflows/release.yml`.

## Current Sprint

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
| Add fixture metadata fields | Done | `schemas/fixture.schema.json`; all 52 fixtures include `metadata` | Metadata covers requirement IDs, provider, surface, scenario, tags, and expected languages. |
| Add fixture coverage report | Done | `docs/reports/fixture-coverage.md`; `scripts/check_fixture_coverage.py`; `npm test` passes | Reports scenarios, provider surfaces, components, warning codes, source adapters, framework adapters, requirements, tags, and expected languages. |
| Add generated-artifact drift checks | Done | `scripts/check_project_hygiene.py`; `npm test` runs it | Starts as required-artifact, package metadata, parity, fixture floor, and CI command checks. |
| Add CI workflow | Done | `.github/workflows/ci.yml`; hygiene check passes | CI runs conformance tests, examples, and Python compile checks. |
| Add cost-ledger aggregation primitive | Done | `cost-ledger-aggregation-basic.json`, `stream-final-usage-missing-warning.json`; Python/JS/Go tests pass | Aggregates already-calculated ledgers and emits `stream_usage_missing` when expected final stream usage is absent. |
| Add provider streaming final-usage extraction | Done | `openai-responses-stream-completed-event.json`, `anthropic-messages-stream-events.json`, `gemini-generate-content-stream-chunks.json`; Python/JS/Go tests pass | Handles selected final-usage stream event envelopes without estimating arbitrary partial deltas. |
| Add documented partial framework adapter paths | Done | `docs/notes/framework-adapter-notes.md`, `docs/reference/supported-surfaces.md`, `docs/notes/api-parity-matrix.md`; hygiene check guards names | Covers Semantic Kernel, AutoGen/AG2, LangSmith export comparison, and OpenRouter-compatible SDK paths as researched but not fixture-backed targets; Haystack and LiteLLM were later promoted to fixture-backed adapters. |
| Add Haystack and LiteLLM fixture-backed framework adapters | Done | `haystack-openai-chat-generator-meta.json`, `litellm-proxy-response-cost-metadata.json`; Python/JS fixture runner and Go tests pass | Adds one-call helpers and extractors across Python, JavaScript/TypeScript, and Go. |
| Normalize documentation layout | Done | `docs/guides/`, `docs/reference/`, `docs/notes/`, `docs/decisions/`, `docs/reports/`, `docs/process/`; hygiene and release scripts use new paths | Preserves content while moving dated/uppercase docs into categorized lowercase paths. |

## Milestone Status

| Milestone | Status | Evidence |
|---|---|---|
| Milestone 0: Prototype Foundation | Complete for current prototype scope | `npm test` passes; cores, examples, schemas, and 16 fixtures exist. |
| Milestone 1: Contract Hardening | In progress | Schemas exist; fixture runner validates schemas including debug traces and fixture metadata; warning fixtures exist; debug trace fixture exists; coverage report and hygiene checks exist. |
| Milestone 1.5: Polyglot Toolchain Foundation | Complete for current prototype scope | Decision record, type artifacts, parity matrix, Go examples, hygiene checks, and CI workflow exist. |
| Milestone 2: Core Calculator Correctness | In progress | Decimal-safe calculator, aliases, strict mode, compatibility warnings, effective dates, service tier/region matching, stale price warnings, provider-reported mismatch/use modes, source priority, source disagreement warnings, debug traces, long-context thresholds, batch/priority/provisioned service-mode fixture coverage, and component-total invariant checks exist. |
| Milestone 3: Source Adapter Layer | In progress | `llm-prices`, LiteLLM, Portkey, OpenRouter models, user compact pricing, and Helicone prototype adapters exist. |
| Milestone 4: Provider Extractors V0 | In progress | OpenAI, Anthropic, OpenRouter, Groq, xAI, Mistral, DeepSeek, Azure OpenAI, Hugging Face, Cohere, Google Gemini/Vertex, and AWS Bedrock extractors exist; cache, reasoning, billed-unit, basic raw response, and selected final streaming usage cases covered for supported surfaces. |
| Milestone 5: Tool Call and Feature Pricing | In progress | Generic and raw OpenAI tool-call fixtures exist; Gemini/Vertex multimodal token detail fixture exists; provider-specific tool pricing coverage still sparse. |
| Milestone 6: Framework Adapters | In progress | LangChain AIMessage, Vercel AI SDK generateText, LlamaIndex TokenCountingHandler, Haystack generator metadata, LiteLLM proxy response metadata, Python LangChain callback/context manager, JavaScript Vercel `wrapGenerate` middleware, and cross-language cost-ledger aggregation exist with fixtures; Semantic Kernel, AutoGen/AG2, LangSmith export comparison, and OpenRouter-compatible SDK paths have documented partial adapter paths; remaining frameworks still need fixtures, implementations, examples, and streaming parsers. |
| Milestone 7: Packaging and Developer Experience | In progress | Package metadata, type surfaces, examples, CI, clean install smoke checks, public alpha docs, license metadata, changelog, contributing/security docs, release process, release readiness checks, and guarded release workflow exist; first registry publishing remains incomplete. |
| Milestone 8: Alpha Quality and Feedback | Not started | None. |
| Milestone 9: Public Beta | Not started | None. |
| Milestone 10: V1 | Not started | None. |

## Work Log

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

## Gap Audit 2026-05-25

Purpose: step back from feature slices and record what is actually done, what is partial, what is a stub, and what still needs completion before private alpha, public beta, and V1.

Naming update:

- Project/package name selected: `runcost`.
- Public docs now use `RunCost`.
- Python import path is now `runcost`.
- JavaScript package name is now `runcost`.
- Go module path is now `github.com/adamallcock/runcost`.

Audit evidence:

- `python3 scripts/check_fixtures.py` passed with 59 fixtures across declared Python and JavaScript fixture coverage.
- `python3 scripts/check_fixture_coverage.py` passed with metadata on all 59 fixtures and a current checked-in coverage report.
- `npm test` passed: fixture checks, Go tests, and project hygiene checks green.
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
- Go: first-class conformance participant with public functions, docs, example tests, public GitHub module path, and clean module import checks, but still map-backed prototype APIs rather than stable schema-derived structs.
- Future languages: no implementation yet. The policy says future languages must consume schemas and fixtures first.

What is implemented and well covered:

- Canonical schemas for usage ledgers, price cards, discount policies, and cost ledgers.
- Shared fixture-first conformance across Python, JavaScript/TypeScript, and Go.
- Fixture metadata and generated coverage reporting for requirements, provider surfaces, components, warnings, source adapters, framework adapters, tags, and expected languages.
- Decimal-safe component cost calculation.
- Strict and compatibility modes.
- Alias resolution through price-card aliases.
- Discounts with component include/exclude policy.
- Effective-date selection, service tier, region, batch, priority, provisioned, long-context conditions, stale-source warnings, provider-reported cost compare/use modes, price-source priority, and price-source disagreement warnings.
- Optional debug traces for price-card candidates, component matches, model alias resolution, discount applications, and warnings.
- Source adapters for `llm-prices`, LiteLLM, Portkey, OpenRouter models, user compact pricing, and Helicone model-registry data.
- Provider extractors for OpenAI Responses, OpenAI Chat Completions, Anthropic Messages, OpenRouter chat completions, Groq, xAI chat, Mistral, DeepSeek, Azure OpenAI chat, Hugging Face Inference Providers chat, Cohere Chat, Gemini/Vertex generateContent, and Bedrock Converse, including selected final streaming usage envelopes for OpenAI Responses, Anthropic Messages, and Gemini generateContent.
- Framework metadata helpers for LangChain AIMessage, Vercel AI SDK generateText result objects, LlamaIndex TokenCountingHandler data, Python LangChain callback/context-manager usage, and JavaScript Vercel `wrapGenerate` middleware.
- Cost-ledger aggregation for multi-call/session rollups, with fixture-backed `stream_usage_missing` warnings when final stream usage is expected but absent.
- Docs for project plan, product requirements, architecture, market validation, live evaluation protocol, parity matrix, provider extractor notes, framework adapter notes, polyglot tooling decision, contribution, security, changelog, and release process.

Partially implemented:

- Contract hardening: schema validation, fixture metadata, debug trace fixtures, and fixture coverage reporting exist. Remaining gaps are fixture generator helpers and stronger Go-side schema validation/component-total invariant checks.
- Polyglot maintainability: parity matrix and hygiene checks exist, but generated type/docs workflows are not real yet. TypeScript and Python types are manual. Go uses object maps.
- Go conformance: Go runs every fixture and checks expected subsets, but schema validation for generated Go outputs and component-total invariant checks are weaker than Python/JavaScript.
- Source adapters: core adapters exist for six sources, including user compact pricing and Helicone model-registry data. Provider official pricing snapshots, models.dev enrichment, full file-reading YAML loaders, offline cache format, explicit refresh command, and source capability warnings are still missing.
- Historical pricing: effective dates and `llm-prices` date fields exist, but `llm-prices` historical feed semantics are not fixture-proven end to end.
- Provider extractors: broad base coverage exists, but many surfaces are thin. OpenAI Responses, Anthropic Messages, and Gemini final stream usage shapes now have fixtures, but xAI Responses, OpenAI Conversations, Bedrock non-Converse paths, provider-specific tool fields, other streaming variants, embeddings, rerank, image/audio/video generation, and transcription paths are not covered.
- Tool pricing: generic tool components, OpenAI raw tool calls, OpenRouter image/request/search source pricing, and custom units exist. Provider-specific tool pricing remains sparse.
- Multimodal: Gemini/Vertex modality token details are covered. Other providers and generated-media billing are not.
- Framework adapters: direct metadata/result objects are covered for LangChain, Vercel AI SDK, LlamaIndex, Haystack, and LiteLLM proxy responses. Initial Python LangChain callback/context-manager plus JavaScript Vercel middleware helpers exist, and generic multi-step cost-ledger aggregation now exists. Semantic Kernel, AutoGen/AG2, LangSmith export comparison, and OpenRouter-compatible SDK paths have documented partial adapter paths, but they are not implemented or fixture-backed. Framework-specific stream integrations, OpenAI Agents SDK, and concrete examples for the remaining partial paths are still missing.
- Documentation: public quickstart, installation, API reference, aggregation/streaming, debug trace, custom pricing, discount, warning/strict-mode, source adapter, support-matrix docs, contribution guide, security/privacy note, changelog, and release process now exist. Deeper framework integration guides and automated release notes are still missing.
- Packaging: clean local install checks now pass for Python, JavaScript/TypeScript, and Go. License metadata, PyPI/npm guarded release workflow, Go tag policy, changelog, provenance guidance, and release readiness checks exist. First real registry publication and trusted publisher configuration remain incomplete.

Stubs or placeholders:

- `DebugTrace` now has a schema, fixture, docs, and opt-in output across Python, JavaScript/TypeScript, and Go, but traces are still focused on calculator decisions rather than full extractor/framework middleware internals.
- Streaming parser coverage is intentionally narrow: selected final usage envelopes are supported, but arbitrary text-delta estimation and most provider/framework stream protocols remain out of scope.
- Public API type surfaces are manually maintained placeholders for generated/schema-derived models.
- `scripts/check_project_hygiene.py` and `scripts/check_release_readiness.py` are useful guards but still mostly check presence, API-name strings, fixture floor, fixture metadata presence, package metadata, CI commands, release docs, version sync, and release workflow snippets. They are not yet full drift detectors.
- README now provides alpha package onboarding and links to public docs, but does not yet represent a production-ready package.
- Go APIs are explicitly prototype map-backed `Object` functions.

Highest-risk gaps before private alpha:

1. First real registry release readiness: configure PyPI/npm trusted publishing, decide package README shape, cut a dry-run release, and verify Go tags.
2. Broader provider/framework streaming support beyond the initial OpenAI, Anthropic, and Gemini final-usage fixtures.
3. Source adapter completeness: official snapshots, full file-reading YAML loaders, refresh/cache workflow, and historical feed semantics.
4. Hardened typed models and generated artifact workflow, especially for Go structs and generated docs.
5. Broader framework integration ergonomics beyond the initial LangChain/Vercel helpers, especially turning documented partial paths into fixture-backed adapters and examples.
6. Deeper debug traces for extractor and framework adapter internals.
7. Fixture generator helpers and stronger generated artifact drift detection.

Recommended next sprint:

1. Broader framework implementation slice: add fixtures and minimal adapters/examples for the next documented partial path, likely AutoGen/AG2 usage summaries or LangSmith export comparison.
2. Provider streaming expansion slice: add additional stream finalization fixtures for Vertex-specific SDK wrappers, Bedrock ConverseStream, Vercel AI SDK `streamText` finish parts, and any provider-specific tool streaming fields.
3. Release hardening slice: configure trusted publishing outside the repo, decide registry README shape, and run a no-publish release workflow dry run.
4. Source adapter hardening slice: add official snapshots, full file-reading YAML loaders, refresh/cache workflow, and historical feed semantics.
5. Generated artifact slice: add fixture generator helpers and schema-derived type/doc checks.

## Next Best Actions

1. Add fixture-backed adapter coverage for AutoGen/AG2 usage summaries or LangSmith export comparison.
2. Add provider-specific fixtures for OpenAI-compatible tool, remaining multimodal providers, compound-routing, and service-tier fields beyond base token usage.
3. Extend debug traces into source conflict reports, extractor internals, and framework middleware decisions.
4. Add framework examples showing one- or two-line integration in Python and JavaScript for fixture-backed framework paths.
5. Harden release automation with registry README decisions, trusted-publisher setup notes, and a no-publish release workflow dry run.
