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

- No unreleased changes yet.

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
