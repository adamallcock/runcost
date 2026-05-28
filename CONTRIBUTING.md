---
title: Contributing To RunCost
date: 2026-05-25
type: guide
status: draft
---

# Contributing To RunCost

RunCost is fixture-first and schema-first. A contribution is not complete just
because one language implementation works.

## Core Rule

Any new component, warning code, provider extractor, source adapter, discount
behavior, or framework helper needs shared fixture coverage before it is treated
as supported.

## Contribution Flow

1. Add or update the relevant schema if the public contract changes.
2. Add a shared fixture under `fixtures/` with metadata, requirement IDs, tags,
   and expected languages.
3. Implement the behavior in Python, JavaScript/TypeScript, and Go unless the
   fixture explicitly documents a language-specific runtime helper.
4. Update public API docs, support matrices, and the progress tracker.
5. Run the validation battery:

```bash
npm test
npm run check:coverage
npm run check:packages
npm run check:release
npm run example:js
npm run example:py
```

## Provider And Source Pricing Changes

- Use primary provider docs, source repos, official APIs, or preserved source
  snapshots.
- Follow `docs/internal/process/2026-05-26-source-data-update-process.md` for source
  update ownership, cadence, review, and release expectations.
- Preserve source name, URL, retrieval time, and license when available.
- Do not silently infer ambiguous units.
- Prefer a warning or unsupported fixture over a plausible but unverified price.
- Never auto-publish new price data without review.

## Language Parity

Python, JavaScript/TypeScript, and Go should expose the same core concepts even
when helper APIs are idiomatic to a single ecosystem. Update
`docs/internal/notes/api-parity-matrix.md` whenever public APIs change.

## Generated Artifacts

Generated artifacts must be reproducible and checked by CI before they are
committed. The current repository still has manual type surfaces; generated
schema-derived types are a planned hardening item.
