---
title: RunCost Polyglot Toolchain Decision
date: 2026-05-25
type: decision-record
status: accepted
---

# RunCost Polyglot Toolchain Decision

Status: Accepted for v0.x
Date: 2026-05-24

## Decision

RunCost is a polyglot library by design. Python, JavaScript/TypeScript, and Go are first-class packages that share one canonical contract, one fixture suite, one compatibility policy, and one release train.

For v0.x, the canonical contract is:

- JSON Schema for data shapes.
- Shared JSON fixtures for behavior.
- A small fixture runner that validates schemas and compares outputs across languages.
- Handwritten language cores that stay small, dependency-light, and easy to audit.
- Schema-derived type surfaces where useful, starting with TypeScript declarations and Python `TypedDict` contracts.

The near-term project should not adopt a large SDK generator as the core maintenance model. The important portability surface is not a hosted HTTP API; it is deterministic local behavior across language packages.

Put another way: canonical contracts plus generated types, docs, and validators plus handwritten idiomatic implementations plus shared conformance fixtures is the intended architecture.

## Alignment With Evaluated Alternatives

This decision intentionally separates data contracts from behavior:

- Schemas define data.
- Fixtures define behavior.
- Implementations execute behavior.
- CI prevents drift.

API SDK generators such as Stainless, Fern, Speakeasy, Kiota, and OpenAPI Generator should remain future options for a hosted RunCost API or control plane. They are not the core local-library maintenance model because they do not generate the calculator semantics, extractor behavior, decimal arithmetic, warning policy, or discount logic that make the library trustworthy.

Single-implementation strategies such as jsii, Rust native bindings, Rust/WASM, UniFFI, or SWIG are worth small spikes only if handwritten language implementations begin to drift or packaging remains simple enough for users. They are not the default for v0.x because RunCost needs tiny, boring, idiomatic packages with no hidden runtime machinery in the core path.

## Rationale

The product promise is trust: "this call cost X, here is exactly why." Trust comes from clear contracts and shared conformance, not from maximizing generated code.

The pricing domain also changes in ways that are awkward for blind generation:

- Providers expose different usage fields, cache semantics, service tiers, and tool pricing units.
- Pricing data often comes from third-party source adapters, not a single official API.
- Some behavior is intentionally conservative, such as compatibility warnings and strict failures.
- Users need local custom overrides and discount policies.

JSON Schema plus fixtures gives the project a boring, portable base:

- JSON is natural in every target language.
- Schemas define persisted and public object shapes.
- Fixtures prove behavior at the boundary where users care.
- Language implementations can use native idioms while remaining behaviorally identical.
- Generated types can be added incrementally without making generated code the source of truth.

## Canonical Assets

The canonical assets are:

- `schemas/usage-ledger.schema.json`
- `schemas/price-card.schema.json`
- `schemas/discount-policy.schema.json`
- `schemas/cost-ledger.schema.json`
- `fixtures/*.json`
- `scripts/check_fixtures.py`
- `docs/internal/notes/api-parity-matrix.md`
- `docs/internal/project-plan.md`
- `docs/internal/progress-tracker.md`

Every meaningful behavior change must add or update a shared fixture before it is treated as supported.

## Language Strategy

### JavaScript and TypeScript

The package is authored as small ESM JavaScript today, with `index.d.ts` as the public typed contract.

Near-term expectations:

- Keep runtime dependencies at zero for the core calculator.
- Keep money math decimal-safe through string and `BigInt` arithmetic.
- Export the same public functions as Python and Go where practical.
- Keep taxonomy-bearing TypeScript unions generated from `schemas/taxonomy.json`;
  maintain the handwritten interfaces around those generated aliases until full
  contract generation proves worth the complexity.

Generation candidates:

- `json-schema-to-typescript`
- `quicktype`
- TypeBox or Zod only if runtime validation becomes a package feature, not as a core dependency requirement.

### Python

The package remains dependency-light and typed with `TypedDict` contract models.

Near-term expectations:

- Keep the core calculator dependency-free.
- Use `Decimal` for money arithmetic.
- Export typed dictionaries from `runcost.types`.
- Keep taxonomy-bearing Python literal aliases generated from
  `schemas/taxonomy.json`; maintain the handwritten `TypedDict` models around
  those generated aliases until full contract generation proves worth the
  complexity.
- Keep runtime input validation in tests and optional developer tooling, not mandatory calculator dependencies.

Generation candidates:

- `datamodel-code-generator`
- Pydantic models as optional validation extras, not required by the tiny core package.
- Python `jsonschema` for development and CI if the no-dependency validator becomes insufficient.

### Go

The Go package uses native exported functions and object maps in the prototype, then graduates to typed structs once the v0.1 schema settles.

Near-term expectations:

- Keep the core small and standard-library only.
- Use `math/big.Rat` for decimal-safe arithmetic.
- Provide public doc comments and examples for exported APIs.
- Continue running the same fixture suite through Go tests.
- Keep taxonomy-bearing Go slices generated from `schemas/taxonomy.json`; keep
  typed core wrappers handwritten around the conformance-tested calculator.

Generation candidates:

- JSON Schema to Go struct generators after schema churn slows.
- Handwritten structs if generators produce unclear or fragile code.

## Tooling Decisions

### Adopt Now

- JSON Schema as the canonical data contract.
- Shared fixtures as the canonical behavior contract.
- Package-level TypeScript declarations.
- Python `TypedDict` contracts.
- Go exported function docs and examples.
- Generated taxonomy-bearing language type artifacts for Python,
  TypeScript, and Go.
- CI that runs fixture tests, Go tests, examples, JSON parsing, and hygiene checks.
- A public API parity matrix.

### Evaluate Later

- TypeSpec if schemas become repetitive or if the project adds a public service API.
- Buf and Protocol Buffers if binary serialization, RPC, or generated strongly typed clients become necessary.
- OpenAPI, Stainless, Fern, Speakeasy, Kiota, or OpenAPI Generator if RunCost ships a hosted API or control plane.
- jsii, Rust native bindings, Rust/WASM, UniFFI, or SWIG only if fixture evidence shows handwritten language implementations are drifting enough to justify package-install complexity.
- Full generated language models after schemas settle and generator output is readable enough to maintain.

### Avoid for Core v0.x

- Provider SDK dependencies inside the core calculator.
- Runtime network access during cost calculation.
- A heavy validation dependency required for normal use.
- One language serving as the hidden source of truth for the others.
- Auto-generated business logic that is difficult to audit.

## Maintenance Model

Every supported language follows the same change sequence:

1. Add or update a schema field if the public contract changes.
2. Add or update fixtures that prove the behavior.
3. Update the Python, JavaScript/TypeScript, and Go implementations.
4. Update type declarations or typed contract models.
5. Regenerate `docs/generated/contract-taxonomy.md` and
   `docs/generated/schema-fields.md` when schemas or taxonomy change.
6. Keep Python, TypeScript, and Go taxonomy-bearing type surfaces aligned with
   `schemas/taxonomy.json`; `scripts/check_type_taxonomy_parity.py` enforces
   this for the current manual type surfaces.
7. Update `docs/internal/notes/api-parity-matrix.md` if public APIs changed.
8. Run the full verification battery.
9. Release all language packages together or explicitly mark a language as unsupported for that feature.

This sequence is intentionally mechanical. The project should make drift obvious, boring to fix, and difficult to publish by accident.

## Versioning and Release Policy

All first-class language packages share the same semantic version.

Rules:

- Patch releases may fix bugs, add source data mappings, or add fixtures without public API changes.
- Minor releases may add provider extractors, components, warning codes, source adapters, and typed fields.
- Major releases may change schema semantics, warning behavior, or public API names.
- If a language package cannot support a feature in a release, the parity matrix must say so before release.
- Schemas include `schema_version` and should remain backward compatible within a minor line when practical.

## Drift Controls

The project treats drift as a CI failure.

Required checks:

- All JSON files parse.
- All fixtures pass across supported languages.
- Expected and actual ledgers validate against schemas.
- Type artifacts exist and are referenced by package metadata.
- Public APIs appear in the parity matrix.
- Examples run.
- Go examples compile as part of tests.

Future generated artifacts should add exact regeneration commands and checked-in diff tests.

## Current Outcome

The v0.x foundation remains lightweight:

- Core calculator logic is handwritten per language.
- Data and behavior are shared through schemas and fixtures.
- Types are maintained near the packages that expose them.
- CI and hygiene checks enforce the cross-language contract.

This keeps the library simple enough for developers to trust and small enough for maintainers to update when providers change pricing behavior.
