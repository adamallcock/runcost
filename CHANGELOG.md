---
title: RunCost Changelog
date: 2026-05-25
type: changelog
status: draft
---

# RunCost Changelog

RunCost follows semantic versioning while the public API is pre-1.0. During
`0.x`, minor versions may still introduce breaking changes when the schemas or
core ledgers change. Every release must include fixture evidence and note known
limitations.

## Unreleased

## 0.2.2 (2026-08-23)

- Add Vercel AI SDK `experimental_streamTranscribe` final-result handling for
  duration-priced OpenAI transcription, including `gpt-realtime-whisper`
  fixture coverage across Python, JavaScript/TypeScript, and Go.
- Support timezone-aware weekly billing schedules across Python,
  JavaScript/browser, and Go: IANA timezone names, local weekday windows,
  weekend defaults, overnight start-day matching, and precise RFC3339
  effective-time boundaries.
- Preserve DeepSeek's response billing timestamp through the pricing path and
  add official-source, adapter, DST, malformed-schedule, and Windows timezone
  regression coverage for weekday peak and weekend off-peak pricing.
- Harden release publication around the exact reviewed artifacts, including
  checksum verification, registry and GitHub Release asset parity, and
  fail-closed Go tag verification.

## 0.2.1 (2026-07-30)

- Preserve original GPT-5.6 Terra and Luna pricing through July 29, 2026 and
  apply OpenAI's permanent 20% and 80% reductions respectively from July 30
  across Standard, Batch, Flex, and Fast processing.
- Preserve OpenAI `service_tier: "fast"` and `"priority"` as independent request
  and price-card tiers. Prefer exact Fast cards and use an auditable, one-way
  Fast-to-Priority compatibility fallback only when no applicable Fast card
  exists; Priority never falls forward to Fast.
- Derive historical pricing time from raw Responses `created_at` and Chat
  Completions `created` timestamps when a caller does not supply an override.
- Price Anthropic `usage.iterations` per attempt and per actual model across
  Python, JavaScript/TypeScript, and Go, including arbitrary multi-hop fallback
  chains, pre-output zero billing, and billed mid-stream refusal usage.
- Expose requested, attempted, serving, and pricing model attribution for direct
  Messages and streaming events; accept Anthropic Python SDK/Pydantic response
  objects without caller serialization.
- Mark Message Batch refusal results as retry-required while preserving their
  provider `succeeded` status, price separately submitted retry results at the
  batch tier, and add Claude Opus 5 to the reviewed official pricing snapshot.
- Keep fallback-credit option aliases as provenance only and price the retry
  from Anthropic's reported cache usage instead of assuming token redemption.

## 0.2.0 (2026-07-18)

- Add one-call external pricing resolution in Python, JavaScript/browser, and
  Go using `genai-prices`, models.dev, LiteLLM, and OpenRouter where appropriate;
  include 24-hour conditional caches, last-known-good fallback, offline mode,
  source provenance, and matching Python/npm quote and cache-management CLIs.
- Remove all provider price databases and provider shards from published
  package artifacts. Keep deterministic calculation network-free and preserve
  explicit empty-card opt-out behavior.
- Add itemized batch ledgers for OpenAI Responses, Chat Completions,
  Embeddings, and Images; Anthropic Message Batches; Gemini Developer and
  Vertex AI; Bedrock model-invocation jobs; Kimi; and DashScope.
- Add explicit compatible routes for Tinker/Inkling, NVIDIA, AI21, Arcee,
  Cohere, DashScope, Inception, Poolside, Xiaomi, ZAI, and MiniMax.
- Add Pydantic `genai-prices` and OpenTelemetry GenAI adapters, cost attribute
  enrichment, attribution, pre-call estimates, stateless budgets, and explicit
  provider-total reconciliation.
- Compile and memoize caller-owned and externally cached catalogs across Python,
  JavaScript, and Go; add generic SHA-256 manifests, mutation detection, and
  enforced latency/memory/package-size budgets.
- Add a browser/edge-safe npm entrypoint, an
  eight-page no-account playground, GitHub Pages deployment workflow, canonical/social
  metadata, and a 1200x630 social card.
- Publish a generated 202-case RunCost conformance inventory, redaction-safe
  external fixture workflow, new schemas/types/API registry entries, and
  runnable provider, batch, framework, and telemetry examples.

## 0.1.13

- Add primary-source-backed GPT-5.6 Sol, Terra, and Luna pricing for Standard,
  Batch, Flex, and Priority service tiers, including cache reads, 1.25x cache
  writes, and the 272,000-token long-context boundary.
- Extract OpenAI cache-write usage from Responses, Chat Completions, and Agents
  SDK payloads across Python, JavaScript/TypeScript, and Go without double
  charging writes as uncached input.
- Fail closed when a reviewed official conditional pricing rule has no matching
  long-context rate while preserving ordinary fallback between third-party
  price sources.
- Add Meta Model API Responses and Chat Completions compatibility, public
  Python/JavaScript helpers, sanitized credentialed smoke evidence, and null
  usage handling across all three languages.
- Retain media-corroborated Meta preview rates as an explicit opt-in fixture,
  excluding them from the default catalog until exact rates are verified from
  a primary Meta pricing source.
- Expand shared conformance coverage to 170 fixtures and exercise both GPT-5.6
  and Meta behavior from installed Python, npm, and Go artifacts.

## 0.1.12

- Add generic pricing-period selection for peak, regular, and other
  time-window price cards across Python, JavaScript/TypeScript, and Go.
- Extract DeepSeek chat completion `created` timestamps into `context.priced_at`
  so UTC peak-window pricing can be derived from raw provider responses.
- Add fixture-backed warnings for missing, unsupported, and unsupported-timezone
  pricing periods, plus debug trace metadata for selected period windows.
- Normalize billing schedules from official-snapshot, user-pricing, source-cache,
  and canonical price-card adapters, including camelCase user-owned source data.
- Keep bundled DeepSeek default catalog prices unchanged until peak-valley
  prices are verified from official evidence.

## 0.1.11

- Add Anthropic Claude Fable 5 fallback billing extraction and pricing behavior
  across Python, JavaScript/TypeScript, and Go.
- Cover server-side fallback, sticky fallback, client-side fallback credit,
  direct classifier blocks, unavailable fallback metadata, and missing usage
  warnings with shared fixtures.
- Keep component metadata passive for billing decisions and require explicit
  billing model fields for pricing overrides.

## 0.1.10

- Fix JavaScript decimal normalization for tiny bundled default-catalog prices
  that arrive from JSON numbers as exponent-form strings such as `4e-7`.
- Strengthen package install checks with OpenAI default-catalog cost smokes
  across Python, JavaScript, and Go so exponent-form pricing regressions are
  caught before release.
- Correct Go `FromResponse` documentation examples to pass price cards and
  discount policies through the exported Go signature.

## 0.1.9

- Refresh the bundled default price catalog from live public sources and expand
  the reviewed Anthropic official snapshot to active current Claude API rows
  verified against Anthropic pricing and model lifecycle docs.
- Update the Vercel AI SDK development smoke dependencies to `ai@6.0.208` and
  `@ai-sdk/openai@3.0.73`, sharing `@ai-sdk/provider-utils@4.0.30`.
- Update CI and release workflows from `actions/checkout@v6` to
  `actions/checkout@v7`.

## 0.1.8

- Add Gemini `usageMetadata.serviceTier` extraction across Python,
  JavaScript, and Go so Flex, Standard, and Priority usage selects matching
  price cards.
- Refresh reviewed Google official Gemini service-tier pricing for Gemini 3.5
  Flash, Gemini 3.1 Pro Preview, and Gemini 2.5 Pro.
- Preserve explicit official snapshot component conditions and assert that
  absent Gemini service tier defaults to Standard pricing.

## 0.1.7

- Default reported reasoning tokens to the matching output-token price when a
  provider publishes output pricing but no separate reasoning price.
- Preserve direct reasoning-token prices and explicit unsupported-component
  warnings ahead of the default fallback.
- Prefer the active output modality for fallback pricing, including Gemini Live
  Translate audio thinking tokens when both text and audio output prices exist.
- Add shared Python, JavaScript, and Go fixtures plus a decision record for the
  cross-provider fallback policy.

## 0.1.6

- Add reviewed Claude Fable/Mythos and Gemini Live Translate pricing snapshots
  to the bundled default catalog.
- Add Gemini Live Translate extraction for audio input/output usage, streaming
  final usage chunks, aggregate audio-only usage, and transcript text output.
- Price Gemini Live Translate thinking tokens against the applicable output
  modality when the provider reports thinking without a dedicated reasoning
  price.
- Strengthen package install smokes so Python, JavaScript, and Go execute the
  Gemini Live Translate fixture against the packaged default catalog.

## 0.1.5

- Price reported xAI/Grok reasoning tokens at the matching output-token rate
  when xAI price cards do not publish a dedicated reasoning component.
- Extract xAI provider-reported `cost_in_usd_ticks` for exact billed-cost
  reconciliation in `compare` and `use` modes.
- Price xAI typed server-side tool usage for Web Search, X Search, code
  execution, collection/file search, and attachment search from
  `server_side_tool_usage`, with generic tool-count fallback only when typed
  billable usage is absent.

## 0.1.4

- Price reported Gemini thinking/reasoning tokens at the matching output-token
  rate for direct Google/Vertex Gemini cards when no dedicated reasoning price
  component is present.
- Add explicit ledger metadata for this treatment so downstream reports can
  distinguish priced Gemini thinking tokens from unsupported or unpriced
  reasoning components.
- Add Gemini 3.5 Flash and Gemini 3.1 Flash-Lite regression fixtures across
  Python, JavaScript, and Go.

## 0.1.3

- Correct the bundled xAI Grok catalog so `grok-4.3` only carries true rolling
  aliases (`grok-4.3-latest`, `grok-latest`), while older Grok 3/4/4.1 slugs
  are modeled as separate redirect-priced cards with `redirect_target`
  metadata.
- Prioritize the reviewed `xai-official` source in the default catalog so
  official xAI rows win over stale third-party catalog entries.
- Add catalog checks that prevent redirected Grok slugs from being collapsed
  back into the `grok-4.3` alias list.

## 0.1.2

- Add a bundled reviewed default source-cache catalog generated from
  `llm-prices`, LiteLLM, OpenRouter, and models.dev.
- Add optional default catalog loaders across Python, JavaScript/TypeScript, and
  Go.
- Add drift checks and package install smoke coverage proving the default
  catalog ships with each package.

## 0.1.1

- Publish the repository publicly with community files, issue templates,
  CODEOWNERS, Dependabot, branch protection, secret scanning, and package
  registry metadata.
- Add a public price-data strategy that clarifies fixtures as behavioral
  conformance cases and routes broad catalog data through source adapters and
  reviewed source-cache snapshots.
- Release from current `main` so npm, PyPI, and Go module versions align after
  the earlier private `v0.1.0` tag.

## 0.1.0

- Add package publish-readiness artifacts: MIT license, contribution guide,
  security policy, release process, release-readiness checks, and a guarded
  GitHub Actions release workflow.
- Add installed Python `runcost` CLI commands for price-card conversion and
  single-fixture checks, plus a migration guide for replacing hand-written
  formulas.
- Add OpenAI Responses computer-use and function-call tool pricing fixtures,
  plus consistent unpriced tool/feature warnings across Python, JavaScript, and
  Go.
- Add canonical `storage_gb_days` / `gb_day` feature pricing coverage across
  schemas, types, docs, and shared fixtures.
- Add normalized generated-media, rerank, transcription, and runtime-second
  feature-pricing fixtures, plus unpriced runtime feature warning coverage.
- Add a source-data update process with owner, cadence, review checklist, and
  release guardrails for price-source changes.
- Add the first Milestone 8 alpha smoke harness with deterministic no-network
  sample mode, optional API-key-gated live direct API paths, sanitized evidence
  output, and runbooks for smoke findings plus invoice/dashboard comparison.
- Add optional Vercel AI SDK and LangChain framework smoke scripts with
  sanitized sample/live modes and no new core framework dependencies.
- Add a sanitized invoice/dashboard comparison command, sample input, checked
  report, and validation check covering exact, estimated, and unsupported
  classification.
- Add guarded release workflow rehearsal hardening: no-publish artifact review
  checklist and real remote Go tag verification path without local `replace`
  when a tag exists.
- Add generated contract taxonomy docs and drift checks derived from
  `schemas/taxonomy.json`.
- Add typed Go wrappers for normalized usage ledgers, price cards, discount
  policies, calculator options, and core cost calculation.

## 0.0.0

- Pre-alpha workspace seed.
- Python, JavaScript/TypeScript, and Go prototype cores.
- Shared schemas and conformance fixtures.
- Provider extractors, framework helpers, source adapters, debug traces, and
  package install smoke checks.
