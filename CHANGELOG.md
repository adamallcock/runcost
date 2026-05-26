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
