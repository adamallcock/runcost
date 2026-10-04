---
title: Package Improvements Implementation and Local Qualification
date: 2026-10-04
type: review
status: locally-validated-unreleased
---

# Package Improvements Implementation and Local Qualification

This records the implementation checkpoint before the user authorized the
`0.2.4` release train. Later release progress is tracked in the
[implementation plan](../plans/2026-10-04-package-improvements.md). The hashes
below identify that earlier `0.2.1`-metadata candidate, before the version bump.

The code, tooling, documentation, and CI changes recommended by the
[package review](2026-10-04-package-improvement-review.md) are implemented and
validated locally. Publication, remote CI execution, and an independent
installation/reconciliation case for this candidate remain open evidence gates.

The [machine-readable evidence summary](2026-10-04-package-improvements-evidence.json)
records tool versions, checks, live source/release state, controlled measurements,
and SHA-256 hashes of the reviewed candidate files.

The starting checkout was already substantially modified. Its non-ignored files
were backed up before implementation. Existing negative-usage, USD-only,
precision, timezone, and product-wording work was retained while reconciling the
reviewed upstream provider and release-workflow changes. The base remains
`b86518fef92215522d8d05819fdc680093e45070`; the reviewed upstream snapshot is
`bc99b18bbd4d9eae73f58ba7cd28ecc4877355c3`. These changes are uncommitted.

Package metadata remains `0.2.1`. The working tree is an **unreleased candidate**,
not the bytes currently published as `0.2.1`. A coordinated release needs a fresh
version and tag from one reviewed commit; existing tags must not be rewritten.

## Implemented recommendations

| Review item | Result |
| --- | --- |
| R1 — integration and release train | Reconciled the upstream DeepSeek and release repairs with local trust work. Kept npm verification at 11.13.0 and artifact packaging at 12.0.2. The performance guard now accepts npm 11's array and npm 12's package-name-keyed object; both real toolchains passed locally. |
| R2 — maintained catalog contract | Migrated all three default resolvers to GenAI Prices v2, with reviewed cache-write, image/video, reasoning, and web-search mappings. Unrepresentable units remain in metadata with warnings. Added schema validation, revision hashes, separate retrieval/generation evidence, a bounded live checker, and a weekly read-only CI check. |
| R3 — strict closure | Response, batch, OTel, and estimate auto helpers enforce strict mode after resolver and aggregate warnings are attached. Go auto helpers return ordinary errors through their existing error channel. |
| R4 — decimal contract | Expansion helpers use isolated Python decimal contexts and canonical 18-place half-even money across languages. Budget, residual, tier, and OTel netting checks cover precision boundaries and hostile ambient decimal contexts. |
| R5 — provenance | Core and aggregate calculations deduplicate source records by name, URL, retrieval time, and version, preserving distinct selected evidence. |
| R6 — consumer contracts | Fixed NodeNext declaration paths and compiled-catalog auto support. Catalogs own their data; public mutation cannot corrupt pricing indexes. Python ships `py.typed` and useful result types. Actual installed consumers compile under NodeNext/bundler and pass positive and negative mypy checks. |
| R7 — schema enforcement | Development checks now use Draft 2020-12 validation with its format checker, including conditional branches and numeric constraints. Negative tests reject a real succeeded batch item with its ledger removed. No JSON Schema dependency was added to RunCost's runtime. |
| R8 — batch coverage | Successful usage is normalized once. Source selection evaluates the entire batch, chooses one catalog under a deterministic coverage policy, and preserves failed/pending items, IDs, context, and order. |
| R9 — resolver and CLI work | Stable internal catalogs eliminate repeated warm compilation. Concurrent source requests coalesce; failure paths release callers. JavaScript bounds reads while streaming. JSONL input is priced incrementally in order, with optional JSONL output, backpressure, and atomic file replacement. |
| R10 — policy validation | Unsupported discount kinds, missing IDs, malformed policy objects, nonnumeric/nonfinite values, and invalid denominators fail before an applied receipt can be returned. Existing supported adjustment semantics remain covered. |
| R11 — dependencies | Updated affected playground transitive dependencies and the root Undici graph through normal compatible lockfile updates. Independent root and playground audits report zero vulnerabilities. |

Follow-ups also implemented: generated warning documentation; allowlist-based
portable ledger export; Go error-returning calculation interfaces; embedded Go
IANA timezone fallback; gradual money/contracts extraction; and full shared
fixture, installed-consumer, and race checks in the Linux/macOS/Windows
compatibility matrix, including Python 3.9 / Node 20.

The [local integration guide](../../guides/2026-10-04-local-integration-and-reconciliation.md)
and `scripts/run_local_integration.py` exercise an installed package, first ledger,
offline reproduction, timings, and reconciliation with a caller-supplied total.
The clean-install gate runs the recipe with controlled synthetic evidence. That
proves the recipe executes; it does not qualify independent adoption or invoice
accuracy for this candidate.

## Important behavior changes

- Strict callers now receive a failure for final refresh/offline/uncertainty
  warnings that previously escaped strict enforcement.
- Official DeepSeek peak rules exclude Chinese public holidays. RunCost does not
  invent that calendar: automatic period selection fails closed with
  `billing_schedule_unsupported`; callers can supply an explicitly confirmed
  `pricing_period`. This limitation is injected even when an older upstream
  snapshot omits it. Source: [DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing).
- Budget and reconciliation amounts now follow the same canonical 18-place
  contract as the core. Inputs exceeding 18 fractional places are rounded before
  comparison, so statuses agree with displayed amounts across languages.
  Invalid negative budgets/tolerances and thresholds outside 0–1 are rejected
  before rounding.
- Sharing exports remove arbitrary metadata, raw usage, attribution, source URLs,
  warning details, and debug content. They retain model/rate/discount IDs and
  amounts so the ledger remains explainable; callers must review those retained
  identifiers before sharing externally.

## Local verification

Host: macOS arm64, Python 3.14.7, Go 1.26.3, Node 26.2.0, plus an isolated
Node 20.20.2 runtime. npm 11.13.0 and the release packaging pin 12.0.2 were
exercised without changing the global installation.

| Gate | Verified result |
| --- | --- |
| Full `npm test` | Final suite passed on Node 20: 204 shared core fixtures and 45 expansion cases, totaling 249 inventory cases, plus source, schema, CLI, browser, framework sample, generated-contract, performance, and hygiene checks. |
| `scripts/check_package_installs.py` | Passed on Node 20 with clean installed Python/npm/Go consumers, NodeNext/bundler compilation, positive/negative Python typing, CLI execution, and the installed offline integration recipe. |
| `go test -race ./packages/go/...` | Passed, including source coalescing, strict errors, catalog ownership, and lock release after invalid catalog input. |
| `scripts/check_release_dry_run.py` | Passed: wheel/sdist and npm artifacts were byte-identical across independent builds/packs, sdist installation worked, and a separate Go consumer passed. The Go check uses the local replacement; it does not test new published bytes. |
| npm 12 packaging and performance | Two independent packs matched byte for byte. The actual npm 12 package metadata passed the same performance/size guard as npm 11. |
| `scripts/check_live_source_contract.py` | Passed against the official v2 slim schema/data: 43 providers, 1,574 models, 1,596 adapted cards. Seven unsupported unit fields remain explicit. Generation time is unknown, rather than inferred from retrieval. |
| Streaming regressions | Both CLIs emit a ledger before input EOF, preserve output on a malformed later row, and fetch one controlled catalog for 60 quotes per language. |
| Dependency audits | Root and playground each report zero vulnerabilities at all severities. |
| Rendered production build | Homepage and playground inspected through Codex's browser. Confirmed estimate wording, retrieval notice, provider switching, invalid-usage warnings, and visible dated fallback warnings. Mobile viewport had 376 CSS pixels and no horizontal overflow. No captured console warnings/errors or runtime exceptions on the final reload. |
| Final static gates | Project hygiene, release readiness, and `git diff --check` pass. |

The dedicated Browser plugin was unavailable; rendered checks used Codex's
in-app browser through CUA. The temporary tab, viewport override, and preview
server were cleaned up after verification. Visual evidence is attached to the
implementation response. No deployment is inferred from this local preview.

### Controlled resolver measurements

The same synthetic 1,000-card Python cache workload was measured before and
after the change. Compile counts are the robust regression evidence; timings
are single-host observations, not production or cross-machine benchmarks.

| Measurement | Before | After |
| --- | ---: | ---: |
| Warm 100 quotes: compilation count | 100 | 0 |
| HTTP 304: compilation count | 1 | 0 |
| Warm 100 quotes: elapsed | 84.004 ms | 18.741 ms |
| Cold fetch and compilation: elapsed | 14.040 ms | 22.385 ms |
| HTTP 304: elapsed | 5.002 ms | 3.892 ms |

The live contract snapshot had revision
`sha256:616bd37dcbd402d1174783c5838aee225cbe42b6e64d73907d5a881e8b376280`.
Its primary inputs are the [v2 slim data](https://raw.githubusercontent.com/pydantic/genai-prices/main/prices/new_data/v2/data_slim.json)
and [v2 slim schema](https://raw.githubusercontent.com/pydantic/genai-prices/main/prices/new_data/v2/data_slim.schema.json).

## Remaining evidence gates

On 2026-10-04, the [GitHub latest release](https://github.com/adamallcock/runcost/releases/tag/v0.2.1),
[npm registry](https://registry.npmjs.org/runcost), and
[PyPI registry](https://pypi.org/pypi/runcost-ai/json) still report 0.2.1. The
[Go proxy](https://proxy.golang.org/github.com/adamallcock/runcost/@latest)
reports v0.2.2 at `381646f4d44664eef427139127871ff34179f86e`. The latest
release workflow remains the failed
[August 23 rehearsal](https://github.com/adamallcock/runcost/actions/runs/32652078026).

No registry publication, tag creation, GitHub Release update, merge, push, or
public-site deployment occurred. Existing release/customer completion gates
were not upgraded on the strength of synthetic tests. Before publication,
review and commit one candidate, select a fresh version, run the remote pinned
release workflow, then verify artifact identity across GitHub, npm, PyPI, Go,
and the rendered public site.

Linux, Windows, Python 3.9, and the exact release OS/Python/Node combination are
configured in CI but were not executed on this macOS host. Their results must
be collected from the candidate's CI run. An independent workflow with matching
provider evidence is still required to qualify this candidate's real billing
accuracy; the executable local recipe is ready for that evidence.
