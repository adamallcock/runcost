---
title: RunCost Project Plan
date: 2026-05-25
type: plan
status: draft
---

# RunCost Project Plan

Status: Draft
Last updated: 2026-05-25

## 1. Mission

Build a small, boring, highly reliable multi-language library that answers:

> What did this LLM or agent call cost, and why?

The project should give developers a trustworthy cost ledger from raw provider responses, framework metadata, or normalized usage. It should not become a gateway, observability platform, dashboard, tokenizer, or hand-maintained universal pricing table.

The durable product shape is:

```text
raw response / framework metadata / normalized usage
  -> extractor
  -> disjoint usage ledger
  -> alias resolver
  -> price source resolver
  -> modifier engine
  -> discount engine
  -> cost calculator
  -> componentized cost ledger
```

## 2. Current State

The repo currently contains:

- Market validation: `VALIDATION_REPORT.md`
- Product requirements: `PRODUCT_REQUIREMENTS.md`
- Architecture: `ARCHITECTURE.md`
- Evaluation protocol: `LIVE_EVALUATION_PROTOCOL.md`
- Results matrix: `RESULTS_MATRIX.md`
- Polyglot toolchain decision: `docs/decisions/polyglot-toolchain-decision.md`
- Public API parity matrix: `docs/notes/api-parity-matrix.md`
- Progress tracker: `PROGRESS_TRACKER.md`
- Shared JSON schemas: `schemas/`
- Shared conformance fixtures: `fixtures/`
- Prototype cores:
  - JavaScript: `packages/javascript/core/`
  - Python: `packages/python/runcost/`
  - Go: `packages/go/ledger/`

Current prototype capabilities:

- Decimal-safe cost calculation.
- Componentized output ledgers.
- Raw extractors for OpenAI Responses, OpenAI Chat Completions, OpenAI Embeddings, Anthropic Messages, Cohere Chat, Google Gemini/Vertex `generateContent`, AWS Bedrock Converse, and selected OpenAI-compatible chat providers.
- Final streaming usage extraction for selected OpenAI Responses, Anthropic Messages, and Gemini stream shapes.
- Components for input, cached input, cache write, output, reasoning, tool units, and pass-through custom units.
- Exact alias resolution through price-card aliases.
- Component-aware discount policies.
- Simon Willison `llm-prices` adapter.
- LiteLLM, Portkey, OpenRouter models, models.dev, reviewed official snapshots, source-cache, local JSON/YAML files, explicit source refresh, user compact pricing, and Helicone model-registry adapter prototypes.
- Strict mode and compatibility mode.
- Effective-date price-card selection.
- Service-tier and region price-card matching.
- Stale price-source warnings.
- Provider-reported cost comparison warnings.
- Provider-reported cost authoritative use mode with explicit reconciliation adjustment.
- Price-source priority for user overrides.
- Price-source disagreement warnings.
- Required warning metadata payloads with per-code keys enforced by taxonomy and fixtures.
- Long-context threshold price component conditions.
- Batch service-mode pricing through service tier matching.
- Priority service-mode pricing through service tier matching.
- Provisioned endpoint-hour pricing through service tier and region matching.
- Component-total invariant checks in the Python/JavaScript conformance runner.
- Schema validation in the fixture runner.
- TypeScript declarations and Python `TypedDict` contracts.
- Go public API comments and examples.
- CI and project hygiene checks.
- Shared fixture conformance across Python, JavaScript/TypeScript, and Go.
- Framework helpers for LangChain, Vercel AI SDK, LlamaIndex, Haystack, LiteLLM proxy metadata, and AutoGen/AG2 usage summaries.
- MIT license metadata, contribution guide, security policy, changelog, release process, and guarded release workflow.

Current verification command:

```bash
npm test
```

## 3. Product Principles

### 3.1 Trust Before Coverage

It is better to support fewer providers with correct component ledgers than many providers with plausible totals.

### 3.2 One Canonical Contract

Schemas and fixtures are the source of truth. Every language implementation must conform to the same contracts.

### 3.3 Polyglot by Construction

The project is a multi-language product, not a Python package with ports. Every design choice must make Python, JavaScript/TypeScript, Go, and future languages easy to maintain from one canonical contract.

### 3.4 Generated Where Practical, Handwritten Where Valuable

Schemas, types, validators, fixtures, documentation tables, support matrices, and boilerplate should be generated from canonical sources when possible. Business rules should stay readable, tested, and intentionally shared through fixtures rather than copied blindly.

### 3.5 No Hidden Magic

Every alias, fallback, price source, modifier, discount, and warning should be visible in the output or debug trace.

### 3.6 Offline by Default

Normal calculation must not call the network. Price refresh should be explicit.

### 3.7 Source Adapters, Not a Pricing Table Company

The library should normalize data from sources such as LiteLLM, Portkey Models, Helicone, OpenRouter, `llm-prices`, and user-defined price cards.

### 3.8 Component Accounting, Not Just Totals

The core output must explain input, cached input, output, reasoning, tool calls, multimodal units, discounts, and unpriced components separately.

## 4. Scope Boundaries

### In Scope

- Raw response extraction.
- Framework adapters.
- Normalized usage ledger.
- Price-card lookup.
- Model alias resolution.
- Service tier and surface modifiers.
- Custom price overrides.
- Discount policies.
- Point-in-time schema support.
- Source provenance and stale-data warnings.
- Shared conformance fixtures.
- Multi-language packages.

### Out of Scope for V1

- Traffic proxying.
- Dashboard or hosted observability.
- Token estimation before a call.
- Invoice ingestion.
- Automatic scraping and PR creation.
- Provider SDK dependencies in core.
- Replacing LiteLLM, Portkey Models, Helicone, OpenRouter, or models.dev.

## 5. Milestone Roadmap

### Milestone 0: Prototype Foundation

Status: Complete for current scope.

Goal:

Prove the core abstraction works across multiple languages with shared fixtures.

Delivered:

- Schemas for usage ledgers, price cards, discount policies, and cost ledgers.
- Python, JavaScript, and Go cores.
- Fixture conformance runner.
- Basic raw response extractors.
- `llm-prices` source adapter.
- Examples.

Exit criteria:

- `npm test` passes.
- Python and JavaScript examples run.
- Go tests pass.
- Fixture suite includes normalized usage, raw responses, alias, discounts, tool units, and price-source adapter cases.

Hardening delivered:

- Typed interfaces now exist where useful for the v0.x prototype.
- Schema validation runs in the fixture runner.
- CI exists and runs the shared verification battery.

### Milestone 1: Contract Hardening

Status: Complete for current scope.

Goal:

Make the schemas and conformance fixtures strong enough to support real package development.

Features:

- Finalize v0.1 schema naming and component taxonomy.
- Add schema validation in test runners.
- Add fixture metadata fields: requirement IDs, provider, surface, scenario, strictness mode.
- Add explicit `warnings` fixtures for unknown model, unpriced component, stale price, and alias inference.
- Add debug trace fixture shape.
- Add exact total-sum invariant checks.
- Add fixture generator helpers to reduce duplication.

Delivered in current prototype:

- Schema validation in the fixture runner.
- Fixture metadata fields with requirement IDs, provider, surface, scenario, tags, and expected languages.
- Warning fixtures for unknown model, unpriced component, unknown surface, stale price, alias inference, service tiers, long context, streaming usage, provider-reported cost comparison, and source disagreement.
- Debug trace fixture shape.
- Component-total invariant checks for Python and JavaScript fixture outputs.
- Fixture coverage reporting.
- Fixture generator helpers through `scripts/create_fixture.py`, `scripts/check_fixture_generator.py`, and `npm run fixture:new`.
- Go fixture-test validation for generated cost-ledger structure and exact component-total invariants.
- Locked v0.1 taxonomy through `schemas/taxonomy.json`, synchronized with schema enums by `scripts/check_schema_taxonomy.py`.

Progress criteria:

- Every fixture validates against schemas before it runs.
- Every cost ledger validates against `cost-ledger.schema.json`.
- Fixture coverage report lists every component type and provider surface covered.
- Python, JavaScript, and Go all pass the same fixture battery.

Exit gate:

- No implementation-specific behavior may exist without a shared fixture.

### Milestone 1.5: Polyglot Toolchain Foundation

Status: Complete for current scope.

Goal:

Make the multi-language maintenance model explicit before the codebase grows.

Features:

- Choose the canonical schema authoring system for v0.x.
- Generate language types or validators where practical.
- Add a public API parity matrix.
- Add per-language package layout standards.
- Add cross-language differential tests.
- Add a release train policy so Python, JavaScript/TypeScript, and Go versions do not drift.
- Add generated artifact checks in CI.
- Add contribution rules for language-specific changes.

Candidate tooling:

- JSON Schema 2020-12 as the current canonical data-contract format.
- TypeSpec as a candidate higher-level schema/API authoring layer if JSON Schema becomes too repetitive.
- Buf/Protocol Buffers as a candidate only if binary serialization, RPC contracts, or a strongly generated SDK ecosystem becomes important.
- OpenAPI, Stainless, Fern, Speakeasy, Kiota, or OpenAPI Generator only if the project adds a hosted API; they should not drive the local-library design.
- jsii, Rust native bindings, Rust/WASM, UniFFI, or SWIG only as future spikes if handwritten language implementations create unacceptable drift and packaging remains user-friendly.
- quicktype, datamodel-code-generator, json-schema-to-typescript, Pydantic/datamodel tools, and Go JSON Schema generators as type-generation candidates.
- Ajv, Python `jsonschema`, and Go JSON Schema validators as validation candidates.

Progress criteria:

- The repo has a written polyglot toolchain decision record.
- Each language has generated or schema-derived types for core contracts, or an explicit reason not to generate them yet.
- CI fails when generated artifacts are stale.
- A parity matrix lists every public API and whether Python, JavaScript/TypeScript, and Go support it.
- A conformance runner can compare outputs across all supported languages for every fixture.

Exit gate:

- The project can add a new fixture, schema field, warning code, or component type once and get deterministic work items or generated updates for every language.

### Milestone 2: Core Calculator Correctness

Status: Complete for current scope.

Goal:

Turn the prototype calculator into a dependable core.

Features:

- Strict mode and compatibility mode.
- Price source priority and conflict handling.
- Stale price checks.
- Effective-date selection.
- Region, service tier, and surface matching.
- Long-context threshold modifiers.
- Batch/flex/priority/provisioned modifiers.
- Provider-reported cost compare mode.
- Better alias resolver with resolution trace.
- Stable warning codes and typed warning payloads.
- Decimal-safe arithmetic review in all languages.

Delivered in current prototype:

- Strict mode and compatibility mode.
- Effective-date price-card selection.
- Service-tier and region price-card matching.
- Unsupported service-tier warnings.
- Configurable stale price-source warnings.
- Provider-reported cost mismatch warnings in compare mode.
- Provider-reported cost authoritative use mode that preserves a reconciliation component.
- Configurable price-source priority for user overrides.
- Price-source disagreement warnings when matching cards conflict and no priority is configured.
- Long-context threshold component selection through `conditions.min_total_input_tokens` and `conditions.max_total_input_tokens`.
- Long-context missing-rule warnings.
- Typed warning metadata payloads enforced through `warning_metadata_required_keys` in `schemas/taxonomy.json`, cost-ledger schema validation, Python/JavaScript fixture checks, and Go fixture validation.
- Batch, priority, and provisioned service-mode fixture coverage through service tier and region matching.
- Component-total invariant checks for Python, JavaScript, and Go conformance results.
- Canonical cost-ledger output ordering for components, price sources, applied discounts, and warnings, enforced by shared fixtures and Go validation.
- Adversarial decimal arithmetic coverage for large token quantities and tiny per-token prices.
- Typed warning metadata payloads with required keys locked in `schemas/taxonomy.json`, enforced in Python/JavaScript schema validation and Go fixture validation.
- Adversarial decimal arithmetic fixture using large string quantities and tiny per-token prices to catch binary-float leakage.

Progress criteria:

- Unknown and ambiguous cases produce deterministic warnings or strict failures.
- Same inputs produce byte-stable output ordering where practical.
- No binary float behavior leaks into money calculations.
- Component total equals ledger total in every fixture.

Exit gate:

- Core is safe for production-like use with user-supplied price cards and normalized usage.

### Milestone 3: Source Adapter Layer

Status: Complete for current scope.

Goal:

Load real price data without making the project a hand-maintained price database.

Adapters:

- Simon Willison `llm-prices`.
- LiteLLM `model_prices_and_context_window.json`.
- Portkey Models pricing endpoints.
- Helicone cost package or extracted registry-compatible data.
- OpenRouter `/api/v1/models`.
- Reviewed official provider pricing snapshots where license and terms permit.
- User JSON/YAML price cards.
- models.dev catalog enrichment.

Features:

- Source-specific unit conversion.
- Source provenance.
- Source freshness metadata.
- Source capability warnings.
- Source conflict report.
- Offline cache format.
- Explicit refresh command.

Progress criteria:

- Each adapter has at least one fixture that maps source data into canonical price cards.
- Adapter output validates against `price-card.schema.json`.
- Source conflict fixture shows both disagreeing values.
- `llm-prices` historical date windows and historical feed provenance are preserved.
- LiteLLM service tier and cache fields map into canonical components.
- OpenRouter string prices map correctly.
- models.dev per-million token, cache, reasoning, audio token, and context tier fields map into canonical components.
- Reviewed official pricing snapshots preserve provider source URL, retrieval time, version/license metadata, effective dates, aliases, token prices, and tool/search unit prices.
- User compact pricing data maps into canonical price cards.
- Local JSON price-source files map into canonical price cards.
- Local strict YAML price-source files map into canonical price cards.
- Helicone endpoint/deployment pricing maps cache multipliers, reasoning, request, web-search, and modality token fields.
- Source-cache envelopes preserve URL, retrieval time, checksum, generated time, and generated price-card count.
- The explicit refresh command can write source-cache envelopes from live URLs or local reviewed snapshots without changing normal offline calculation behavior.
- Source capability warnings distinguish explicit source limitations from generic unpriced components.

Exit gate:

- Users can calculate costs from vendored or locally refreshed price cards without writing price cards by hand.

### Milestone 4: Provider Extractors V0

Status: Complete for current scope.

Goal:

Support direct SDK/API responses for the first provider set.

Provider surfaces:

- OpenAI Responses.
- OpenAI Chat Completions.
- OpenAI Embeddings.
- Anthropic Messages.
- Google Gemini API `generateContent`.
- Vertex AI Gemini.
- AWS Bedrock Converse.
- DeepSeek OpenAI-compatible chat.
- xAI Chat Completions and Responses.
- Groq OpenAI-compatible chat.
- Mistral chat completions.
- Cohere chat.
- OpenRouter chat completions.
- Azure OpenAI chat completions.
- Hugging Face Inference Providers OpenAI-compatible chat.

Delivered in current prototype:

- OpenAI Responses.
- OpenAI Chat Completions.
- OpenAI Embeddings.
- Anthropic Messages.
- OpenRouter Chat Completions.
- Groq OpenAI-compatible Chat Completions.
- xAI Chat Completions and Responses.
- Mistral Chat Completions.
- DeepSeek Chat Completions.
- Azure OpenAI Chat Completions.
- Hugging Face Inference Providers Chat Completions.
- Cohere Chat.
- Google Gemini API `generateContent`.
- Vertex AI Gemini `generateContent` through the same usage metadata extractor.
- AWS Bedrock Converse.
- AWS Bedrock InvokeModel with Anthropic Messages response bodies.

Current mapping notes:

- `docs/notes/provider-extractor-notes.md` records the official source references and raw usage field mappings for OpenAI Responses, OpenAI Embeddings, xAI Responses, OpenAI-compatible chat providers, Cohere, Gemini, Bedrock Converse, and Bedrock InvokeModel.
- OpenAI Conversations are documented as state resources used with Responses, not standalone usage-bearing model responses. RunCost therefore prices the associated Responses calls and does not add an `openai.conversations` extractor in v0.x.
- xAI Responses is currently mapped through the OpenAI-compatible Responses usage envelope, with provider defaulting to `xai` for `surface: "xai.responses"`.
- Gemini/Vertex `promptTokensDetails`, `cacheTokensDetails`, `toolUsePromptTokensDetails`, and `candidatesTokensDetails` are now mapped into modality-aware image, audio, video, text, cache-read, and thinking components in the shared conformance suite.
- OpenRouter `/api/v1/models` pricing is now mapped into canonical price cards for prompt, completion, cache read/write, internal reasoning, request, image-input, and web-search prices.

Extractor requirements:

- Emit disjoint usage buckets.
- Preserve raw usage.
- Preserve provider/model/surface metadata.
- Warn on ambiguous inclusive fields.
- Never price `total_tokens` directly.
- Preserve unknown billable units.

Progress criteria:

- Each provider surface has at least one raw fixture.
- Cache, reasoning, long-context, and tool fields have explicit fixtures where the provider exposes them.
- Provider extractor behavior is identical across languages or delegated to shared generated metadata.

Exit gate:

- The library can price common direct provider responses from raw objects in Python and JavaScript, with Go at least supporting normalized usage and critical extractors.

### Milestone 5: Tool Call and Feature Pricing

Status: Complete for current scope.

Goal:

Make tool pricing a first-class differentiator.

Feature areas:

- Web search.
- File search.
- Code interpreter.
- Computer use.
- Rerank.
- Embeddings.
- Image generation.
- Audio generation.
- Video generation.
- Transcription.
- Provider request fees.
- Gateway pass-through costs.
- User-defined internal tools.

Pricing forms:

- Per call.
- Per request.
- Per session.
- Per search.
- Per file.
- Per GB-day.
- Per execution-second.
- Per generated item.
- Direct USD pass-through.

Progress criteria:

- Tool components have canonical units.
- Discount policy can include or exclude tool components.
- Provider-reported tool costs can be returned, recalculated, or compared.
- Unrecognized tool usage becomes structured warnings, not dropped data.

Exit gate:

- Tool pricing works for at least OpenAI-style hosted tools, OpenRouter/provider-reported costs, and custom internal tools.

Delivered:

- Canonical tool and feature units cover hosted search, file search, code interpreter, computer-use actions, generic tool calls, request/image/search source pricing, multimodal token details, normalized generated media, rerank, transcription, runtime-second, GB-day storage, custom units, and direct provider-reported cost comparison paths.
- OpenAI Responses raw output fixtures cover hosted tool calls, including web search, file search, code interpreter, computer-use action counts, and function-call counts.
- OpenRouter/source-adapter fixtures cover request, image, and search pricing; provider-reported cost fixtures cover return/recalculate/compare behavior.
- Custom internal tool pricing is fixture-backed through user-defined tool components.
- Unpriced tool/feature usage now emits `tool_component_unpriced` with structured metadata instead of falling through to generic component warnings.
- Broader provider-specific media generation, transcription, rerank, provider-specific storage/session extraction, and live billing validation moves to Milestone 8 feedback and beta/V1 hardening.

### Milestone 6: Framework Adapters

Status: Complete for current scope.

Goal:

Make adoption easy for common agent and LLM frameworks.

Adapters:

- LangChain.
- LangSmith export/compare path.
- LlamaIndex.
- Vercel AI SDK.
- Microsoft Semantic Kernel.
- Haystack.
- AutoGen / AG2.

Adapter patterns:

- Callback handlers.
- Middleware.
- `onFinish` hooks.
- Telemetry/span parsers.
- Wrapper-level summaries.
- Framework metadata extractors.

Delivered in current prototype:

- LangChain AIMessage `usage_metadata` extraction.
- Vercel AI SDK `generateText` `usage` and `totalUsage` extraction.
- LlamaIndex `TokenCountingHandler` event and cumulative counter extraction.
- Haystack OpenAI generator result metadata extraction.
- LiteLLM proxy response metadata extraction with hidden response-cost comparison.
- AutoGen/AG2 usage summary extraction with cached-vs-actual mode selection and framework-reported cost comparison.
- OpenAI Agents SDK usage object extraction with aggregated request usage preservation.
- Vercel AI SDK `streamText` finish/onFinish object extraction.
- LangSmith run/export usage extraction with exported `total_cost` comparison.
- Semantic Kernel telemetry/filter output extraction for basic prompt/completion token metrics and plugin/function metadata preservation.
- OpenRouter-compatible SDK response extraction for OpenAI SDK-routed responses and resolved Agent SDK response objects.
- One-call helper APIs for LangChain, Vercel AI SDK, and LlamaIndex in Python, JavaScript/TypeScript, and Go.
- One-call helper APIs for Haystack, LiteLLM proxy metadata, AutoGen/AG2 usage summaries, OpenAI Agents SDK usage, Vercel stream finish objects, LangSmith runs, Semantic Kernel telemetry, and OpenRouter SDK responses in Python, JavaScript/TypeScript, and Go.
- JavaScript helper APIs for Vercel AI SDK `onFinish` hooks and OpenRouter Agent SDK `getResponse()` objects.
- Framework adapter notes in `docs/notes/framework-adapter-notes.md`.
- Fixture-backed adapter paths for Semantic Kernel, LangSmith export comparison, OpenRouter-compatible SDK paths, OpenAI Agents SDK usage, and Vercel AI SDK streamText final usage.

Progress criteria:

- LangChain Python callback works with one context manager.
- Vercel AI SDK wrapper works with one middleware/helper.
- LlamaIndex callback handler captures model and usage metadata.
- Semantic Kernel, LangSmith, OpenRouter-compatible SDK paths, OpenAI Agents SDK usage, and Vercel AI SDK streamText final usage have fixture-backed adapter paths for current plain-object scope.
- Framework fixtures cover direct result objects, callbacks, streaming finalization, framework-reported cost comparison, and multi-step runs.

Exit gate:

- A developer can integrate with LangChain, OpenAI Agents SDK, Vercel AI SDK, LlamaIndex, Haystack, LiteLLM, AutoGen/AG2, LangSmith, Semantic Kernel, and OpenRouter-compatible SDK responses in one or two lines for the fixture-backed plain-object scope.

### Milestone 7: Packaging and Developer Experience

Status: Complete for current repo-side/private-alpha scope.

Goal:

Turn the repo into usable packages.

Packages:

- Python package: `runcost`
- JavaScript/TypeScript package: `runcost`
- Go module package
- Optional provider and framework packages

DX features:

- README quickstart.
- API reference.
- Provider support matrix.
- Framework support matrix.
- Migration guide from hand-written formulas.
- CLI for fixture checks and price-source conversion.
- Examples for direct provider response, framework callback, custom prices, and discounts.
- License, changelog, contribution guide, and security policy.
- Guarded release workflow for Python, JavaScript/TypeScript, and Go tag-based releases.
- Release readiness checks for versions, docs, metadata, and workflow guardrails.

Delivered in current prototype:

- Package metadata for Python and JavaScript/TypeScript.
- Go module path at `github.com/adamallcock/runcost`.
- Clean local install checks for Python, JavaScript/TypeScript, and Go.
- Public quickstart, installation, API reference, supported-surface, source-adapter, warning, and release-process docs.
- License, changelog, contribution guide, and security policy.
- Guarded release workflow with explicit publish opt-in.
- Release readiness checks through `npm run check:release`.
- Local no-publish release dry run through `npm run check:release-dry-run`, covering Python source distribution and wheel build, npm package packing, and Go clean-module import verification with a local replace directive.
- Registry README policy: PyPI uses the root README, while the npm package carries a short package-local README that links back to the repository docs.
- Installed Python CLI entry point: `runcost price-cards` for local price-source conversion and `runcost fixture-check` for lightweight one-fixture checks.
- Migration guide from hand-written formulas to usage ledgers, price cards, and fixtures.

Progress criteria:

- Local package install works in clean sample projects.
- Public APIs are small and documented.
- Core packages have no provider SDK dependencies.
- Optional packages keep framework dependencies isolated.
- Release readiness checks pass without publishing.
- Manual release workflow can build artifacts and requires explicit publish opt-in.
- Package-user CLI smoke checks pass in a clean installed Python environment.

Exit gate:

- The library is ready for private alpha users from the repository/source-install path. First real registry publication, external trusted-publisher setup, and post-tag Go module verification remain release operations, not repo-side blockers.

### Milestone 8: Alpha Quality and Feedback

Goal:

Use real applications to validate correctness and ergonomics.

Current status:

- Partial. A sanitized, optional alpha smoke harness exists with deterministic
  no-network sample mode and API-key-gated live paths for selected direct API
  calls. Existing checks validate fixtures, local package installs, release
  artifacts, synthetic examples, and the smoke harness shape, but Milestone 8 is
  not complete until at least one live run and one invoice/dashboard comparison
  have been reviewed.

Alpha scenarios:

- OpenAI Responses app.
- Anthropic Messages app with prompt caching.
- Vercel AI SDK streaming app.
- LangChain agent run.
- Multi-provider router with custom discounts.
- OpenRouter usage and provider-reported cost comparison.

Required alpha smoke harness:

- Must be optional and API-key-gated so normal CI never requires secrets.
- Must not print prompts, API keys, full provider responses, account IDs, or
  other sensitive payload data.
- Must emit sanitized evidence: provider, surface, model, usage fields present,
  RunCost ledger total, component names, warning codes, and fixture-candidate
  JSON with private content removed.
- Must treat every mismatch or unsupported field as a decision point: add a
  fixture, add a warning, or document the limitation.
- Must include a no-network mode using checked-in sample responses so the
  smoke harness shape is still testable without credentials.

Delivered so far:

- `scripts/run_alpha_smoke.py` emits sanitized JSON evidence in sample or live
  mode and requires `--allow-sample-prices` so smoke output is not mistaken for
  invoice-exact pricing.
- `scripts/check_alpha_smoke.py` validates deterministic no-network smoke
  output for OpenAI Responses, Anthropic prompt caching, Vercel AI SDK
  streamText final usage, LangChain agent metadata, OpenRouter cost comparison,
  and multi-provider discount scenarios.
- `fixtures/source-files/alpha-smoke-samples.json` stores checked-in sanitized
  sample response shapes.
- `docs/process/alpha-smoke-runbook.md` documents live gates, privacy rules, and
  the product-truth loop.
- `docs/process/invoice-dashboard-comparison.md` defines the invoice/dashboard
  comparison report process.
- `scripts/compare_invoice_dashboard.py`,
  `scripts/check_invoice_comparison.py`,
  `fixtures/source-files/invoice-dashboard-comparison-sample.json`, and
  `docs/reports/2026-05-26-invoice-dashboard-comparison-sample.md` provide a
  sanitized comparison sample with exact, estimated, and unsupported
  classifications.
- `docs/process/beta-v1-hardening-roadmap.md` keeps public beta, polyglot
  hardening, provider breadth, and V1 stabilization gates explicit.
- `scripts/run_vercel_alpha_smoke.mjs` and
  `scripts/run_langchain_alpha_smoke.py` provide optional framework-specific
  sample/live smoke entrypoints without adding Vercel AI SDK or LangChain as
  core dependencies.
- `docs/reports/2026-05-26-alpha-smoke-live-no-credentials.md` records the
  first live-harness execution in this environment: safe sanitized skips because
  API-key environment variables were absent. It is documentation of the finding,
  not completion of the live-provider-run gate.

Progress criteria:

- Alpha users can integrate without modifying core code.
- Every alpha issue becomes a fixture, warning, or documented limitation.
- At least one invoice or dashboard sample is compared against ledger output.
- Unknown price and missing component cases are understandable.

Exit gate:

- API shape survives real usage without major conceptual rewrites.

### Finalization Strategy

RunCost should not be called "finalized" just because the fixture suite passes.
The finalization path is:

1. Finish the Milestone 8 alpha smoke harness and run it against at least one
   real provider or framework workflow.
2. Convert all smoke findings into fixtures, warnings, or documented
   limitations.
3. Run one invoice/dashboard comparison sample and document exact versus
   estimated cases.
4. Configure PyPI and npm trusted publishers outside the repo.
5. Cut the first registry release with the guarded workflow, first with
   publishing disabled and then with publishing enabled after artifact review.
6. Use private-alpha feedback to choose the beta hardening lane: schema-derived
   type generation and drift checks if language maintenance is the largest
   risk, or provider/framework breadth if real integrations fail on coverage.

Release rehearsal progress:

- The guarded release workflow can run with publishing disabled.
- No-publish runs write an artifact review checklist to the workflow summary.
- A `publish=false` GitHub release rehearsal was run from `main` for version
  `0.0.0`, passed, and produced reviewed Python wheel, Python source
  distribution, and npm tarball artifacts. Evidence is recorded in
  `docs/reports/2026-05-26-release-workflow-no-publish-rehearsal.md`.
- When a remote `v<version>` tag exists, the workflow verifies the Go package
  from `github.com/adamallcock/runcost/packages/go/ledger@v<version>` without a
  local `replace`.
- Actual trusted-publisher configuration, a real-version no-publish workflow
  execution, real Go tag verification, and publishing remain release
  operations.

Polyglot hardening progress:

- `scripts/generate_contract_docs.py` generates
  `docs/generated/contract-taxonomy.md` from `schemas/taxonomy.json`.
- `scripts/check_generated_contract_docs.py` fails when the checked-in
  generated contract docs drift from the locked taxonomy.
- This is the first generated documentation artifact beyond fixture coverage;
  schema-derived language types remain future hardening.
- Go now has typed struct wrappers for the normalized usage, price-card,
  discount-policy, and core calculation path through `UsageLedger`,
  `PriceCard`, `DiscountPolicy`, `CostOptions`, and `CalculateCostTyped`.
  These wrappers still delegate to the shared map-backed calculator so the
  conformance-tested business logic remains single-path.

For evaluation, the next concrete project checkpoint is not more source-adapter
breadth. It is proving that an installed package can sit next to real SDK calls
and produce a useful ledger without leaking private data or requiring app code
rewrites.

### Milestone 9: Public Beta

Goal:

Release a credible public package with clear limitations.

Beta requirements:

- Stable v0.x schemas.
- CI across languages.
- Package publishing pipeline.
- Changelog.
- License decision.
- Security/privacy note.
- Source-data update process.
- Contribution guide for new providers and fixtures.

Delivered so far:

- Guarded release workflow and local release dry-run checks exist.
- PyPI/npm trusted-publishing setup instructions exist, but external registry
  configuration is not verified yet.
- A guarded `publish=false` GitHub release rehearsal from `main` has passed for
  version `0.0.0`; this proves workflow dispatch, build, package artifact, and
  upload mechanics, but it is not a real release-version rehearsal.
- Real Go tag verification exists in the guarded release workflow when a remote
  `v<version>` tag is present; no real tag verification evidence has been
  captured yet.
- Source-data update ownership, cadence, review checklist, and product-truth
  loop are documented in
  `docs/process/2026-05-26-source-data-update-process.md` and checked by
  release readiness and project hygiene scripts.

Progress criteria:

- Green CI on every PR.
- Docs include known non-invoice-exact cases.
- Provider/source freshness is visible.
- New provider contribution path is fixture-first.

Exit gate:

- Public users can depend on the package for supported surfaces with documented caveats.

### Milestone 10: V1

Goal:

Declare the core contract stable.

V1 requirements:

- Stable schemas.
- Stable warning codes.
- Stable package APIs for core functions.
- Production-ready Python and JavaScript packages.
- Go package at minimum stable for normalized usage and core calculation.
- Strong provider/source coverage for the most common APIs.
- Historical-pricing path.
- Framework integrations for the top adoption paths.

Exit gate:

- No known correctness holes in supported surfaces.
- Every supported provider and feature has fixtures.
- Contract is stable enough for external package maintainers and internal billing pipelines.

## 6. Feature Workstreams

### 6.1 Core Schema Workstream

Deliverables:

- `UsageLedger`
- `PriceCard`
- `DiscountPolicy`
- `CostLedger`
- `CostWarning`
- `DebugTrace`
- `ProviderResponseFixture`

Key decisions:

- Component taxonomy.
- Unit taxonomy.
- Money precision representation.
- Date/effective-period semantics.
- Source provenance shape.

### 6.2 Calculator Workstream

Deliverables:

- Component matching.
- Price card selection.
- Alias resolution.
- Discount application.
- Modifier application.
- Warning generation.
- Total and subtotal aggregation.

Hard parts:

- Inclusive usage fields.
- Context threshold pricing.
- Service-tier modifiers.
- Discount precedence.
- Provider-reported costs.

### 6.3 Price Source Workstream

Deliverables:

- `llm-prices` adapter.
- LiteLLM adapter.
- Portkey adapter.
- OpenRouter models adapter.
- Helicone adapter/reference importer.
- User JSON/YAML loader.

Hard parts:

- Unit conversion.
- Missing component representation.
- Source disagreements.
- License and vendoring constraints.
- Historical data.

### 6.4 Provider Extractor Workstream

Deliverables:

- Provider response fixtures.
- Raw response extractors.
- Provider-specific warnings.
- Surface-specific model metadata.

Initial priority:

1. OpenAI.
2. Anthropic.
3. Google Gemini / Vertex.
4. AWS Bedrock.
5. xAI.
6. DeepSeek.
7. Groq.
8. Mistral.
9. Cohere.
10. OpenRouter.
11. Hugging Face.

### 6.5 Framework Adapter Workstream

Deliverables:

- LangChain callback/context manager.
- Vercel AI SDK wrapper/middleware.
- LlamaIndex callback handler.
- LangSmith export/compare helpers.
- Semantic Kernel filter/telemetry parser.
- Haystack generator metadata parser.
- AutoGen usage summary parser.

### 6.6 Multi-Language Workstream

Deliverables:

- Python package.
- JavaScript/TypeScript package.
- Go package.
- Shared fixture runner.
- Generated or shared schema types.
- Cross-language release checklist.

Rule:

No language implementation is complete until it passes the shared fixture suite.

### 6.7 Polyglot Maintainability Workstream

Goal:

Make every language package easy to maintain without relying on heroic manual synchronization.

Deliverables:

- Canonical schema source directory.
- Generated type models for Python, TypeScript, and Go where practical.
- Generated documentation tables for schemas, warning codes, components, providers, and source adapters.
- Language API parity matrix.
- Cross-language fixture runner.
- Cross-language differential test report.
- Generated artifact drift check.
- Per-language style, lint, format, and package standards.
- Release checklist covering package versions, changelogs, and schema versions.

Engineering standards:

- Schemas define data contracts.
- Fixtures define behavior.
- Source adapters and extractors must be fixture-first.
- Public APIs must be intentionally idiomatic in each language while preserving the same concepts.
- Language-specific convenience APIs may differ, but core outputs must stay equivalent.
- No language may introduce a component, warning code, source-adapter behavior, or discount rule without a shared fixture.
- Generated files must be clearly marked and reproducible.
- Handwritten files must be small, reviewed, and covered by fixtures or unit tests.
- Package dependencies must be minimal and justified per language.

Tooling strategy:

- Keep JSON Schema 2020-12 as the v0.x contract format unless a stronger candidate proves better.
- Evaluate TypeSpec for authoring schemas once the first schema churn pain appears; it can emit JSON Schema and OpenAPI and may become the source authoring layer if useful.
- Evaluate Buf/Protocol Buffers only for a future v1+ contract if the project needs binary compatibility, RPC service contracts, or generated SDKs across many more languages.
- Evaluate jsii or Rust/WASM/native bindings only if shared fixtures show language drift is becoming more expensive than package-install complexity.
- Use language-specific validators in tests rather than forcing runtime validation in core hot paths.
- Prefer code generation for types and docs, not for the cost-calculation business rules until the rule model is mature.

Language standards:

- TypeScript/JavaScript: idiomatic ESM package, typed public API, generated types from schema or TypeSpec, no provider SDK dependency in core.
- Python: typed package, generated or schema-derived models where practical, optional Pydantic layer outside the hot-path core if useful, Python 3.9+ until package policy changes.
- Go: stable structs and functions, generated schema-derived types where practical, no reflection-heavy behavior in hot paths once APIs stabilize.
- Future languages: must start by consuming the shared schemas and fixture suite before adding provider-specific functionality.

Progress criteria:

- `npm test` or an equivalent single command runs all conformance tests.
- Every public core API has a parity row for Python, JavaScript/TypeScript, and Go.
- Every fixture records which languages are expected to pass.
- Generated types and docs are reproducible from checked-in commands.
- CI reports schema validation, conformance, lint/format, and generated-artifact drift.

Exit gate:

- Maintainers can safely change a core contract and immediately see every required language update, test change, fixture update, and doc update.

### 6.8 Documentation Workstream

Deliverables:

- Quickstart.
- Concept docs.
- Provider support matrix.
- Framework support matrix.
- Source adapter docs.
- Custom pricing guide.
- Discount guide.
- Warning and strict-mode guide.
- Contribution guide.

## 7. Test Batteries

### 7.1 Schema Battery

Purpose:

Prove all input and output artifacts conform to public contracts.

Tests:

- Validate every fixture input against its schema.
- Validate every fixture expected output.
- Validate generated output from each language.
- Validate source-adapter output price cards.
- Validate warning payloads.

Pass criteria:

- No fixture can run unless it validates.
- Every schema change is explicit and reviewed.

### 7.2 Cross-Language Conformance Battery

Purpose:

Prevent language drift.

Tests:

- Run every fixture through Python.
- Run every fixture through JavaScript.
- Run every fixture through Go.
- Compare output against shared expected ledger.

Pass criteria:

- All languages produce fixture-equivalent output.
- Any intentional language limitation is documented and represented in the fixture metadata.

### 7.2.1 Polyglot Drift Battery

Purpose:

Prevent maintenance drift across languages, generated artifacts, docs, and package releases.

Tests:

- Generated type drift check.
- Generated docs/support-matrix drift check.
- Public API parity check.
- Fixture expected-language coverage check.
- Warning-code parity check.
- Component taxonomy parity check.
- Package version alignment check.
- Changelog/release-note completeness check.

Pass criteria:

- A schema or fixture change cannot merge until every language either supports it or has an explicit tracked limitation.
- Generated files are reproducible.
- Public API parity changes are intentional and documented.

### 7.3 Provider Extraction Battery

Purpose:

Prove raw responses normalize correctly.

Scenarios:

- OpenAI Responses with cached input and reasoning.
- OpenAI Chat Completions with cached prompt and reasoning completion.
- Anthropic Messages with cache creation and cache read.
- Gemini with cached content and thoughts tokens.
- Vertex with threshold-specific pricing.
- Bedrock Converse with Bedrock usage fields.
- DeepSeek cache hit/miss.
- xAI cached input and reasoning.
- Groq service tier and cached input.
- Mistral cached input.
- Cohere `billed_units`.
- OpenRouter provider-reported cost.
- Hugging Face OpenAI-compatible usage.

Pass criteria:

- Extractors emit disjoint usage buckets.
- Inclusive totals are not priced.
- Ambiguous fields produce warnings.

### 7.4 Price Source Battery

Purpose:

Prove price-source adapters preserve source semantics.

Scenarios:

- `llm-prices` current data.
- `llm-prices` historical data with date windows.
- LiteLLM cache/reasoning/tier fields.
- Portkey additional units and batch config.
- Helicone endpoint/deployment pricing.
- OpenRouter model pricing strings.
- User local custom price file.

Pass criteria:

- Price cards validate.
- Source URLs and dates are preserved.
- Unsupported source dimensions produce warnings.
- Unit conversion is tested.

### 7.5 Billing Edge Battery

Purpose:

Catch expensive mistakes.

Scenarios:

- Cached tokens included in parent input count.
- Reasoning tokens included in parent output count.
- Cache write plus cache read in same request.
- Cache write 5-minute vs 1-hour TTL.
- DeepSeek cache hit/miss.
- xAI cached token double-counting.
- Long-context threshold split.
- Batch discount plus provider discount.
- Non-discountable pass-through tool cost.
- Unknown model in strict mode.
- Unknown model in compatibility mode.
- Provider-reported cost mismatch.

Pass criteria:

- No double counting.
- Component sum equals total.
- Strict mode fails when it should.
- Compatibility mode warns when it estimates.

### 7.6 Tool Pricing Battery

Purpose:

Validate the product's main differentiator beyond tokens.

Scenarios:

- Web search per search.
- Web search by context size.
- File search per call.
- File storage per GB-day.
- Code interpreter per session.
- Computer use per action.
- Tool execution by duration.
- Provider-reported direct USD tool cost.
- Custom internal tool pass-through cost.
- Tool discount excluded.
- Tool discount included.

Pass criteria:

- Every tool charge appears as a component.
- Unknown tool units are preserved or warned.
- Discounts apply only where eligible.

### 7.7 Framework Battery

Purpose:

Prove one- or two-line integrations.

Scenarios:

- LangChain `AIMessage.usage_metadata`.
- LangChain callback totals.
- LangSmith trace metadata.
- LlamaIndex `TokenCountingHandler`.
- Vercel AI SDK `generateText`.
- Vercel AI SDK `streamText`.
- Semantic Kernel telemetry.
- Haystack generator metadata.
- AutoGen wrapper usage summary.
- Multi-step agent run.

Pass criteria:

- Integration examples run.
- Streaming finalization is handled.
- Multi-step runs produce per-call and aggregate ledgers.

### 7.8 Performance Battery

Purpose:

Keep the library lightweight.

Tests:

- Single cost calculation latency.
- Large price-card lookup.
- Batch aggregation of many calls.
- Source-adapter conversion time.
- Memory allocation profiles where tooling is available.

Targets:

- Warm single-call calculation under 1 ms in common cases.
- Complex no-network lookup under 10 ms.
- No provider SDK dependencies in core.

### 7.9 API Stability Battery

Purpose:

Protect downstream users.

Tests:

- Public API snapshot.
- Schema compatibility checks.
- Fixture version migration tests.
- Warning code stability tests.

Pass criteria:

- Breaking changes require explicit version bump and migration note.

## 8. Core Scenarios

### Scenario A: Direct OpenAI Responses

User passes a raw OpenAI Responses object and receives:

- Input cost.
- Cached input cost.
- Output cost.
- Reasoning cost.
- Tool cost if present.
- Alias resolution.
- Total.

### Scenario B: Direct Anthropic Messages With Prompt Cache

User passes raw Anthropic Messages response and receives:

- Input cost.
- Cache creation cost.
- Cache read cost.
- Output cost.
- Cache TTL support where present.

### Scenario C: Vercel AI SDK Streaming

User wraps a model or uses `onFinish` and receives:

- Final-step cost.
- Total multi-step cost.
- Provider metadata.
- Stream-abort warning if final usage is missing.

### Scenario D: LangChain Agent Run

User wraps a chain/agent with a callback and receives:

- Per-call ledgers.
- Run total.
- Provider/model breakdown.
- Warnings for missing metadata.

### Scenario E: Custom Internal Model

User supplies:

- Custom model alias.
- Custom price card.
- 4% provider discount.
- Non-discountable internal tool pass-through.

Expected output:

- Correct componentized cost with applied discounts and exclusions.

### Scenario F: OpenRouter Provider-Reported Cost

User passes OpenRouter usage/cost metadata.

Expected output:

- Provider-reported cost.
- Recalculated cost where price data is available.
- Variance warning if the two differ.

### Scenario G: Historical Audit

User supplies `priced_at`.

Expected output:

- Price card selected by effective date.
- Warning if historical pricing is unavailable.

### Scenario H: Polyglot Contract Change

A maintainer adds a new billable component to the canonical schema.

Expected output:

- Generated or schema-derived types update for every supported language.
- Fixture coverage identifies expected behavior.
- Python, JavaScript/TypeScript, and Go tests either pass or show explicit missing implementation work.
- Documentation/support matrices update from the same canonical source.
- CI blocks release if any language silently drifts.

## 9. Progress Metrics

### Coverage Metrics

- Number of supported provider surfaces.
- Number of supported framework adapters.
- Number of billable component types covered.
- Number of source adapters.
- Number of fixtures.
- Percentage of requirements with fixtures.

### Correctness Metrics

- Fixture pass rate by language.
- Number of known unsupported billable fields.
- Number of source disagreement cases covered.
- Number of strict-mode failure fixtures.

### DX Metrics

- Lines of code needed for direct provider integration.
- Lines of code needed for framework integration.
- Time to first cost ledger in a new project.
- Number of optional dependencies in core.

### Maintenance Metrics

- Days since last price-source refresh.
- Number of stale source warnings.
- PR fixture coverage for new provider changes.
- Schema churn per release.
- Number of generated-artifact drift failures.
- Public API parity coverage by language.
- Time from schema change to all-language support.

## 10. Release Gates

### Polyglot Release Gate

Required for every release:

- All supported language packages pass the shared fixture suite.
- Generated artifacts are current.
- Public API parity matrix is updated.
- Schema version and package versions are compatible.
- Changelog names every language package affected.
- Language-specific docs and examples run.
- Any unsupported language/package gap is documented in the support matrix.

### Private Alpha Gate

Required:

- Python and JavaScript packages install locally.
- Core APIs documented.
- OpenAI and Anthropic support usable from raw responses.
- Custom price cards and discounts documented.
- Fixture CI green.

### Public Beta Gate

Required:

- Published packages.
- CI across Python, JavaScript, and Go.
- Provider/source support matrix.
- Framework examples for LangChain and Vercel AI SDK.
- Strict/compatibility mode docs.
- Contribution guide.
- License selected.

### V1 Gate

Required:

- Stable schemas.
- Stable warning codes.
- Stable core APIs.
- Strong provider coverage for common production usage.
- Historical pricing path.
- Tool pricing coverage.
- Framework adapter coverage.
- Known limitations documented.

## 11. Risk Register

### Risk: Pricing Data Freshness

Mitigation:

- Source provenance.
- Explicit refresh commands.
- Stale warnings.
- Multiple source adapters.

### Risk: Double Counting

Mitigation:

- Disjoint usage ledger.
- Inclusive-field fixtures.
- Component-sum invariant.

### Risk: Provider Surface Drift

Mitigation:

- Raw response fixtures from official SDKs.
- Versioned extractors.
- Unknown-field warnings.

### Risk: Multi-Language Drift

Mitigation:

- Shared fixtures.
- Shared schemas.
- CI across all languages.

### Risk: Overbuilding

Mitigation:

- Keep core normalized and dependency-free.
- Put provider/framework dependencies in optional packages.
- Prefer source adapters over hand-maintained prices.

### Risk: Invoice-Exactness Expectations

Mitigation:

- Clear docs.
- Confidence/warning output.
- Provider-reported cost comparison mode.
- Explicit caveats for unsupported pricing dimensions.

## 12. Immediate Next Sprint

Goal:

Move from prototype to private-alpha foundation.

Status:

Completed for this planning pass. The tracker in `PROGRESS_TRACKER.md` carries the latest evidence and next actions.

Tasks:

1. Done: add schema validation to `scripts/check_fixtures.py`.
2. Done: add strict and compatibility modes.
3. Done: add warning fixtures for unknown model, unpriced component, and unknown surface.
4. Done: add LiteLLM source adapter prototype.
5. Done: add Portkey source adapter prototype.
6. Done: add OpenAI tool-call raw fixture.
7. Done: add Anthropic 1-hour cache-write fixture.
8. Done: add a polyglot toolchain decision record.
9. Done: add package-level TypeScript types or generated schema types.
10. Done: add Python type hints and minimal typed dictionaries or generated models.
11. Done: add Go public API docs and typed examples.
12. Done: add public API parity matrix.
13. Done: add generated-artifact drift checks.
14. Done: add CI workflow.
15. Done: add OpenRouter `/api/v1/models` source adapter prototype with tiered pricing fixtures.
16. Done: add user compact pricing source adapter prototype.
17. Done: add Helicone model-registry source adapter prototype.
18. Done: add cost-ledger aggregation and missing final streaming usage warning fixtures.
19. Done: add selected provider streaming final-usage extraction fixtures.
20. Done: add fixture generator helpers and single-fixture validation.
21. Done: add Go-side cost-ledger structure and component-total invariant validation.
22. Done: add v0.1 schema naming and component taxonomy lock.
23. Done: add byte-stable cost-ledger output ordering checks across Python, JavaScript/TypeScript, and Go.
24. Done: add typed warning metadata payload enforcement across schemas, fixtures, Python, JavaScript/TypeScript, and Go.
25. Done: add adversarial decimal arithmetic fixture coverage across Python, JavaScript/TypeScript, and Go.

Sprint exit criteria:

- `npm test` validates schemas and runs all language conformance tests.
- At least 16 fixtures pass across Python, JavaScript, and Go.
- Strict mode and compatibility mode behavior is documented and tested.
- Five real upstream price-source adapters beyond `llm-prices` exist in prototype form, plus reviewed official snapshots and a user compact pricing adapter.
- Multi-call cost-ledger aggregation is fixture-backed across Python, JavaScript/TypeScript, and Go.
- OpenAI Responses, Anthropic Messages, and Gemini generateContent final streaming usage shapes are fixture-backed across Python, JavaScript/TypeScript, and Go.
- The plan for code generation, schema validation, and package release synchronization is documented and actionable.

## 13. Definition of Done

A feature is done only when:

- It has a requirement or scenario reference.
- It has at least one fixture.
- It passes in every supported language or the language limitation is explicit.
- It validates against schemas.
- It has warning behavior for unsupported/ambiguous cases.
- It is documented at the right level.

For provider support, "done" means:

- Raw fixture exists.
- Extractor exists.
- Price-card mapping exists or unsupported pricing is warned.
- Inclusive-token behavior is tested.
- Component ledger output is verified.

For source adapters, "done" means:

- Source fixture exists.
- Unit conversion is tested.
- Provenance is preserved.
- Missing dimensions are warned.
- License/vendoring status is documented.

For framework adapters, "done" means:

- Minimal integration example exists.
- Fixture or integration test captures expected metadata.
- Streaming or aggregation behavior is covered where applicable.

For alpha smoke readiness, "done" means:

- The scenario can run from an installed package, not only from repo source.
- Live runs are optional and gated by explicit environment variables.
- Sanitized smoke output can be safely attached to an issue or converted into a fixture.
- A no-network sample path proves the harness itself in CI.
- Any provider/framework mismatch becomes a fixture, warning, or documented limitation before the scenario is marked supported.

For polyglot readiness, "done" means:

- Schema and fixture changes are reflected across all supported languages.
- Generated artifacts are up to date.
- Public API parity matrix is updated.
- Package docs and examples run for every supported language.
- Release notes mention every affected language package.

## 14. Decision Log

### Decision: Schemas and Fixtures First

Reason:

This prevents the three language implementations from drifting and makes provider/source additions reviewable.

### Decision: Core Is Normalized and Dependency-Free

Reason:

Provider SDKs and frameworks change quickly. The core should stay stable and small.

### Decision: Price Sources Are Adapters

Reason:

Existing sources already contain valuable price data. The project's gap is normalization, calculation, provenance, and developer ergonomics.

### Decision: Tool Pricing Is a First-Class Component Family

Reason:

Modern LLM costs increasingly include search, file, code, computer use, multimodal, and gateway pass-through charges. A token-only design would fail quickly.

### Decision: Polyglot Maintenance Is a Core Feature

Reason:

The product promise depends on developers trusting the same behavior in Python, JavaScript/TypeScript, Go, and future languages. Schema-first contracts, generated artifacts, conformance fixtures, and parity gates are product requirements, not internal niceties.

## 15. Open Questions

1. Which generated type tools should be standardized once the schemas settle beyond v0.1?
2. Should generated types be committed, generated in CI, or both after generation is adopted?
3. Which source adapter should be prioritized after `llm-prices`, LiteLLM, and Portkey?
4. How much provider-specific price data should be vendored in package releases?
5. Should strict mode be the default in server environments?
6. Should OpenRouter provider-reported cost be authoritative by default?
7. How should regional pricing be represented for Azure, Vertex, and Bedrock?
8. What is the earliest acceptable historical-pricing guarantee?
9. Should framework adapters live in separate packages from the start?

## 16. Polyglot Tooling References

These are candidate tools and standards to evaluate during Milestone 1.5. They are not commitments until the toolchain decision record is written.

- JSON Schema 2020-12: current canonical contract format in this repo.
- TypeSpec: candidate higher-level authoring layer that can emit JSON Schema and OpenAPI.
- Buf/Protocol Buffers: candidate for generated SDKs or binary/RPC contracts if the library eventually needs that shape.
- quicktype: candidate for generating language types from JSON Schema and fixture samples.
- datamodel-code-generator: candidate for generating Python/Pydantic models from JSON Schema.
- json-schema-to-typescript or TypeSpec emitters: candidates for TypeScript type generation.
- Go JSON Schema generators or handwritten stable structs: candidates for Go type generation.
- Ajv, Python `jsonschema`, and Go validators: candidates for schema validation in tests and CI.
