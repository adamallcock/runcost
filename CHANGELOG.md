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

## 0.0.0

- Pre-alpha workspace seed.
- Python, JavaScript/TypeScript, and Go prototype cores.
- Shared schemas and conformance fixtures.
- Provider extractors, framework helpers, source adapters, debug traces, and
  package install smoke checks.
