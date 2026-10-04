---
title: Package Improvement Implementation
date: 2026-10-04
type: plan
status: release-in-progress
---

# Package Improvement Implementation

Implement the recommendations in [the package review](../reports/2026-10-04-package-improvement-review.md), preserving existing local changes and the provider-neutral, caller-owned pricing boundary.

## Work and acceptance

- [x] R1: Reconcile newer upstream provider/build fixes with local trust work; qualify one coherent local release candidate. Publication and independent customer evidence are separate final gates.
- [x] R2: Versioned GenAI Prices v2 adapter migration, explicit unsupported capabilities, retrieval versus source freshness, and bounded live source-contract monitoring.
- [x] R3: Final-result strict enforcement across response, batch, OTel, and estimate auto helpers in all languages.
- [x] R4: Context-independent canonical money arithmetic throughout expansion helpers; 17/18/19-place parity and integer conservation.
- [x] R5: Stable source identity preserves all selected provenance.
- [x] R6: Installed NodeNext/bundler consumer compilation and compiled-catalog behavior; Python typed distribution and consumer checks; immutable catalog ownership.
- [x] R7: Standards-complete development-only JSON Schema validation with negative contract cases.
- [x] R8: Batch source selection evaluates all successful item coverage without mixing catalogs; preserves statuses and ordering.
- [x] R9: Stable warm resolver compilation, source fetch coalescing, incremental JSONL output, bounded reads and concurrency, realistic cache benchmarks.
- [x] R10: Discount policy validation rejects unsupported kinds and malformed numeric contracts.
- [x] R11: Patch and independently audit playground dependencies; rebuild and inspect rendered output.
- [x] Follow-ups: warning-doc generation, privacy-preserving export, full compatibility/platform CI, Go error-returning strict APIs, incremental money/contracts modularization, and an executable installation/offline/reconciliation integration recipe.
- [x] Final gates: focused regressions, full suite, clean installed consumers, repeatable artifacts, Go race tests, hygiene/readiness, rendered desktop/mobile behavior, sanitized evidence report.

## Boundaries

The starting checkout has substantial existing uncommitted changes. A content-preserving scratch backup was created before implementation. No existing tag will be rewritten. Real customer adoption and independent invoice accuracy will only be claimed when corresponding evidence exists. Release status documents must distinguish local candidate validation from publication.

## Evidence

Initial base: `b86518fef92215522d8d05819fdc680093e45070`. Reviewed upstream: `bc99b18bbd4d9eae73f58ba7cd28ecc4877355c3`. Local implementation and validation are complete. See [the implementation report](../reports/2026-10-04-package-improvements-implementation.md) for results, behavior changes, and publication/platform/customer evidence gates. No publication or independent candidate qualification is claimed.


## Authorized release train

The user authorized commit, push, PR creation, merge, and release on 2026-10-04.
Target version: `0.2.4`, preserving existing tags and all reviewed trust work.

- [ ] Commit the reviewed public candidate on current upstream main.
- [ ] Push and create a release PR; pass required platform and consumer checks.
- [ ] Merge the reviewed PR and tag that exact merged commit.
- [ ] Complete the pinned no-publish rehearsal and inspect its artifacts.
- [ ] Publish the exact verified artifacts through the approved OIDC workflow.
- [ ] Verify GitHub, npm, PyPI, Go, and the rendered public site.
- [ ] Update completion gates, generated caveats, install/status docs, and sanitized release evidence.
