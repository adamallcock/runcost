---
title: RunCost Package Improvement Review
date: 2026-10-04
type: review
status: complete
---

# RunCost Package Improvement Review

RunCost needs another correctness and release-consolidation pass before broader promotion or a v1 claim. Its existing fixture, packaging, browser, and language-parity checks provide a useful foundation. Additional probes nevertheless found failures in source freshness, strict mode, decimal arithmetic, provenance, consumer types, and automatic batch resolution. These affect the package's central promise: explaining an estimate with trustworthy inputs and evidence.

The recommendation is to complete the existing trust work, fix the gaps below, and qualify one coherent release candidate. Additional providers, a hosted dashboard, and further policy features should follow demonstrated user demand. This review makes no package implementation or publication changes.

## Reviewed states and evidence boundaries

Verification date: **2026-10-04**. These are separate states, not interchangeable release evidence.

| Surface | Verified state | Qualification |
| --- | --- | --- |
| Local checkout | `main`, base commit `b86518fef92215522d8d05819fdc680093e45070`; package metadata `0.2.1`; substantial existing uncommitted changes | Full local checks and additional probes ran against the working tree, not just its base commit. |
| GitHub main | `bc99b18bbd4d9eae73f58ba7cd28ecc4877355c3`, with `0.2.3` metadata | Downloaded this exact source snapshot; ran its Python/JavaScript fixture checks and selected probes. It contains newer DeepSeek and release-workflow changes. |
| npm | `runcost@0.2.1`, published 2026-07-31 | Downloaded the registry tarball, checked its registry digest, and ran probes against its extracted package. |
| PyPI | `runcost-ai==0.2.1`, published 2026-07-31 | Downloaded the wheel, checked its registry digest, and ran probes against its extracted package. |
| GitHub Release | Latest release object is `v0.2.1`, published 2026-07-31 | A `v0.2.2` tag exists, but the corresponding release-object endpoint returned 404. |
| Go module proxy | Includes `v0.2.2` | Verified the public proxy version list. Local Go probes used a local module replacement; this review did not run those probes against a downloaded published Go module. |
| Public website | Rendered GitHub Pages homepage and playground | Compared them with the rendered local production build. Local wording improvements are not evidence of a deployed change. |

Primary release evidence: [npm registry](https://registry.npmjs.org/runcost), [PyPI registry](https://pypi.org/pypi/runcost-ai/json), [GitHub latest release](https://api.github.com/repos/adamallcock/runcost/releases/latest), [Go proxy version list](https://proxy.golang.org/github.com/adamallcock/runcost/@v/list), and [reviewed GitHub source](https://github.com/adamallcock/runcost/tree/bc99b18bbd4d9eae73f58ba7cd28ecc4877355c3).

All pre-existing non-ignored files were recorded by content hash before the review. Existing source, fixtures, and documentation were preserved. Probe inputs were synthetic or public catalog data; no private invoices, provider credentials, or customer prompts were used.

## Validation completed

| Check | Result and practical limit |
| --- | --- |
| Full local `npm test` | Passed: 204 shared fixtures across Python/JavaScript/Go, 40 expansion cases, generated contracts, source resolution checks, examples, CLI/browser checks, performance guards, site build, and hygiene. The generated inventory reports 244 conformance cases. |
| `python3 scripts/check_package_installs.py` | Passed local clean package installation and import checks, including browser and Go replacement consumers. This is not a clean-install test of every published registry artifact. |
| `python3 scripts/check_release_readiness.py` | Passed its local/static checks. It does not establish that registries are synchronized or that the new probes below pass. |
| `python3 scripts/check_release_dry_run.py` | Passed repeatable Python/npm artifact checks, sdist installation, and Go replacement checks. The host used npm 11.13.0; the local workflow pins npm 12.0.2. |
| `go test -race ./packages/go/...` | Passed. |
| Exact remote snapshot fixture check | Passed 192 Python/JavaScript fixtures. The full remote release pipeline was not rerun. |
| TypeScript consumer compilation | Failed with TS2834 under strict NodeNext resolution, for both local and published declarations. Bundler resolution compiled successfully, including a call that subsequently failed at runtime. Compiler: TypeScript 7.0.2. |
| Dependency audit | Root lockfile: no reported vulnerabilities. Playground lockfile: one high-severity affected package and one moderate-severity affected package. |
| Rendered website and README example | Inspected live/local pages. The local README response example priced successfully from public source data at `0.0001518` USD with zero warnings. This is source-example evidence, not invoice reconciliation. |

Host: macOS arm64, Python 3.14.7, Node 26.2.0, npm 11.13.0, Go 1.26.3. The first full-suite attempt encountered npm cache permissions; rerunning with a scratch cache passed. That infrastructure failure is not counted as a package defect.

## Ranked improvements

Priority is review judgment: **P1** means complete before promoting the package's reliability or a consolidated release; **P2** means the next maintenance lane. These are not vulnerability severity ratings.

| ID | Priority | Improvement | Confirmed evidence |
| --- | --- | --- | --- |
| R1 | P1 | Integrate existing trust fixes and reconcile the release train | Published Python/JavaScript and current remote source accept negative normalized usage in strict mode; local changes reject it. Registry versions differ. |
| R2 | P1 | Replace the frozen default feed through a reviewed adapter migration | The default GenAI Prices URL points to upstream's frozen v1 data. |
| R3 | P1 | Enforce strict mode after attaching resolver warnings | Python, JavaScript, and Go auto APIs return a successful strict result carrying `price_source_refresh_failed`. |
| R4 | P1 | Apply the decimal contract to every public arithmetic helper | Ambient Python decimal precision changes budget, reconciliation, and OTel results; precision-boundary parity also fails. |
| R5 | P1 | Preserve distinct selected source records | Two used sources sharing a name collapse into one record without a warning. |
| R6 | P1 | Test consumer types against actual runtime behavior | NodeNext declarations fail; a type-accepted compiled-catalog auto call throws. |
| R7 | P2 | Use a standards-complete schema validator in development checks | The fixture validator accepts a succeeded batch item without its required ledger. |
| R8 | P2 | Select batch price sources using actual batch coverage | A usable fallback is skipped and the batch total becomes zero with `unknown_model`. |
| R9 | P2 | Fix real resolver/CLI caching and bound work | Warm Python resolution retains 32 duplicate compiled catalogs; 60 JavaScript JSONL records cause 60 identical source fetches. |
| R10 | P2 | Reject unsupported discount adjustments at the API boundary | An unknown adjustment kind is accepted in strict mode and recorded as a zero-value applied discount. |
| R11 | P2 | Update and audit the playground dependency graph | Locked Browserslist and baseline-browser-mapping versions match published advisories. |

### R1: Complete existing trust work and reconcile releases

The local working tree already contains important improvements: USD-only validation, rejection of invalid/inconsistent usage, isolated core decimal arithmetic, additional timezone fixtures, more honest estimate wording, and repeatable packaging checks. These should be preserved and integrated, not implemented again.

The published Python/JavaScript packages and the reviewed remote main snapshot still return total `-1` with no warnings for a normalized input quantity of `-1`, unit price `1`, and strict mode. They also accept an EUR price card through that path. The local working tree rejects both inputs. This is a concrete difference between existing local progress and consumer behavior.

Release state also diverges: npm/PyPI/GitHub Release remain at 0.2.1, Go exposes v0.2.2, and main has 0.2.3 metadata. The [2026-08-23 no-publish workflow](https://github.com/adamallcock/runcost/actions/runs/32652078026) failed with `KeyError: 0` while indexing the `npm pack --json` result in the performance check under npm 12. Current remote main already separates npm 11.13.0 verification from npm 12.0.2 packaging. The local workflow retains a single npm 12.0.2 pin and the array-indexing assumption. A successful local dry run under npm 11 does not qualify that workflow combination.

**Recommended change:** reconcile the preserved local changes with the exact current remote revision, including its provider updates and release repair. Prepare a fresh, reviewed version from one merged commit, rather than rewriting an existing tag. Once publication is authorized, verify GitHub Release, npm, PyPI, Go, and rendered documentation against that same release candidate.

**Acceptance:** the negative-usage and currency checks pass against clean consumer installations of the candidate artifacts; the exact pinned CI toolchain completes a no-publish rehearsal; published versions and release evidence agree. Update the existing completion gates only with actual release evidence.

### R2: The default catalog no longer receives updates

Python, JavaScript, and Go default to `https://raw.githubusercontent.com/pydantic/genai-prices/main/prices/data_slim.json`. Upstream now documents this as frozen v1 data and directs new consumers to `prices/new_data/v2/data_slim.json`. [GenAI Prices download documentation](https://github.com/pydantic/genai-prices#download-data).

The downloaded v1 snapshot had 34 providers and 1,285 model records; v2 had 43 providers and 1,574 model records. Passing v2 through the current Python adapter produced cards, but that alone does not establish semantic compatibility: v2 contains units such as one-hour cache writes, image input, reasoning output, and web searches that need explicit mapping or unsupported-capability handling. Different model price blocks are not automatically proof of changed numeric rates.

A recent retrieval timestamp can therefore accompany obsolete data. The public UI's snapshot date and cache freshness need to distinguish **when RunCost fetched a file** from **when the catalog/rates were generated or became effective**.

**Recommended change:** make a versioned v2 adapter migration with schema detection, reviewed unit mappings, preserved temporal/tier semantics, and language-parity fixtures. Retain explicit warnings for unrepresentable billing behavior. Record upstream revision or generation evidence separately from retrieval time. Add a bounded source-contract check so a frozen feed or changed schema becomes visible before another release.

**Acceptance:** reviewed v2 examples yield equivalent ledgers in all languages; unsupported units remain visibly unsupported; fallback behavior is explicit; refreshing a frozen snapshot cannot imply newly verified rates.

Entry points: [Python resolver](../../../packages/python/runcost/price_resolver.py), [JavaScript resolver](../../../packages/javascript/core/index.js), and [Go resolver](../../../packages/go/ledger/price_resolver.go).

### R3: Strict auto pricing can succeed with warnings

Reproduction: warm a synthetic source cache, force the next refresh to fail, then call `from_response_auto` / `fromResponseAuto` / `FromResponseAuto` with strict mode. All three local implementations return total `0.000001` and the warning `price_source_refresh_failed`; Go returns a nil error. Published Python and JavaScript reproduce the same behavior.

The calculator checks strict mode before the resolver adds operational warnings. This contradicts the documented rule that strict mode fails when compatibility mode would return warnings. [Mode contract](../../reference/warnings-and-limitations.md).

**Recommended change:** make the strict decision against the final result, after source resolution, calculation, and aggregation warnings have been attached. Apply the same rule to response, batch, OTel, and estimation auto APIs. Compatibility mode can retain its documented last-known-good behavior.

**Acceptance:** shared cases cover successful refresh, HTTP 304, failed refresh with an existing cache, unavailable sources, and later usable fallbacks. Strict mode fails consistently on final warnings; compatibility returns the same warnings and provenance. Explicitly test Go's error-returning auto interface.

Entry points: Python `attach_price_resolution` and auto helpers, JavaScript `attachPriceResolution` and auto helpers, and their Go equivalents.

### R4: Decimal consistency stops at the core boundary

Python's expansion helpers use the application's ambient `decimal` context. With `getcontext().prec = 6`:

| Operation | Observed Python result | Expected exact subtraction / JavaScript result |
| --- | --- | --- |
| Budget `1` minus cost `0.123456789123456789` | `0.876543` | `0.876543210876543211` |
| Reconcile calculated `0.123456789123456789` with reported `1.23456789123456789` | Residual `1.11111` | `1.111111102111111101` |
| OTel input `123456789`, cached input `1` | Uncached quantity `123457000` | `123456788` |

These reproduce in local, remote, and published Python. Independently, with default context, a cost of `0.0000000000000000001` against budget `1` produces remaining `0.9999999999999999999` in local Python and `1` in JavaScript/Go. Go also normalizes the estimated cost to `0`, while JavaScript retains the input string. This exposes an incomplete contract at the 18-place boundary.

**Recommended change:** use the same isolated arithmetic and canonical formatting policy for budgets, reconciliation, OTel token netting, and other helper arithmetic. Specify where rounding occurs for inputs, rates, products, residuals, and totals. Do not repair parity by reducing precision or widening tolerances.

**Acceptance:** actual public API tests under altered precision, rounding modes, and traps; shared 17/18/19-place cases; integer token conservation; exact residual and budget status checks. Typical default-context fixture success remains useful, but does not cover host-context interference.

Entry points: [Python expansion helpers](../../../packages/python/runcost/expansion.py), especially `_nonnegative_difference`, `evaluate_budget`, and `reconcile_cost`.

### R5: Selected source provenance is lost

Supply separate input/output cards, each actually selected, with the same `source.name` and different URLs. A strict calculation produces total `2` with no warnings, but `price_sources` contains only the second URL. Local Python/JavaScript/Go and remote/published Python/JavaScript reproduce this.

The core collects sources by name, overwriting the earlier record. Aggregation already uses a richer source identity. The arithmetic in this example is correct; the audit trail is incomplete.

**Recommended change:** deduplicate by a stable source identity including the relevant URL, revision, and timestamp fields, consistently with aggregation. Preserve the relationship between each selected price card and its source evidence. A source name should not be required to act as a globally unique identifier.

**Acceptance:** two distinct source records survive a single calculation and subsequent aggregation; equal records deduplicate deterministically; ordering and serialized parity stay stable; a warning is not substituted for evidence that can be preserved.

Entry points: Python `sources_by_name`, JavaScript `sourceByName`, and Go `sourceByName` in the core calculators.

### R6: Declaration checks do not exercise real consumers

Strict TypeScript NodeNext compilation fails because `index.d.ts` imports and re-exports `./generated/taxonomy` without an explicit extension. Both the local declarations and published npm 0.2.1 are affected. Existing checks confirm generated names and parity without compiling this consumer configuration.

Bundler resolution accepts `fromResponseAuto(response, { provider: "openai", priceCards: compilePriceCatalog(cards) })`, but runtime throws `TypeError: explicitCards is not iterable`. The public option type permits a compiled catalog; the resolver assumes an array or iterable. Current remote main has the same runtime mismatch.

The local and published Python package trees also lack `py.typed`. The Python typing specification requires that marker for inline typed package distribution. [Python typing distribution specification](https://typing.python.org/en/latest/spec/distributing.html).

**Recommended change:** repair ESM declaration paths and make compiled-catalog support match the declared auto API, or narrow the declaration deliberately. Add `py.typed` to Python artifacts and incrementally improve useful public result types. Clarify ownership of compiled catalogs: freezing an outer JavaScript object does not make its nested cards and indexes immutable.

**Acceptance:** clean installed npm consumer projects compile under NodeNext and bundler resolution and execute the accepted calls; installed Python typing discovery works with a real checker; wheel/sdist/tarball contents include the intended type files. Keep this coverage focused on consumer contracts.

### R7: Schema checks silently ignore conditional requirements

The custom validator in `scripts/check_fixtures.py` handles a subset of JSON Schema, but skips `allOf`, `if`, `then`, and `else`. It also lacks complete numeric type handling. The batch schema requires a ledger for succeeded items through a conditional, yet this direct check succeeds:

```python
validate_schema(
    {"id": "synthetic", "status": "succeeded"},
    batch_schema["$defs"]["batch_item"],
    batch_schema,
)
```

This proves a validation blind spot, not that the package currently emits a malformed succeeded batch item. [Conditional JSON Schema semantics](https://json-schema.org/understanding-json-schema/reference/conditionals).

**Recommended change:** use a standards-complete Draft 2020-12 validator with explicit format checking in development/CI. Keep it out of the runtime dependency graph. Add a small set of negative cases that exercise real schema requirements, including succeeded/failed batch branches and numeric constraints.

**Acceptance:** the example is rejected, valid fixtures remain accepted, and every keyword used in repository schemas is enforced or deliberately documented as annotation-only.

### R8: Batch source selection ignores the successful items

With a first GenAI catalog containing only a different model and a second LiteLLM catalog containing the requested model, a successful OpenAI batch item selects the first source, never fetches the fallback, and produces aggregate total `0` with `unknown_model`. Local, remote, and published Python/JavaScript reproduce the case. Go follows the same source-selection structure, but this particular fallback probe was not executed in Go.

The batch auto helper resolves using only the provider before extracting usage. Response auto resolution, by comparison, has usage available to assess applicability.

**Recommended change:** normalize successful items once, assess model/component/context coverage across the batch, and select one applicable source under a documented partial-coverage policy. Preserve failed/pending item semantics and deterministic order. Avoid silently mixing rates from different catalogs.

**Acceptance:** a complete fallback is selected when the first source cannot price the successful items; mixed models, partial coverage, all-failed batches, generator inputs, and strict behavior are covered across languages.

Entry point: Python `from_batch_results_auto` and the corresponding JavaScript/Go helpers.

### R9: Benchmark actual cache paths and bound CLI work

Fifty offline Python auto quotes against one warmed synthetic 10,000-model catalog retained 32 distinct compiled catalogs, reaching the cache cap. Local elapsed time was approximately 644 ms; remote/published probes also retained 32. The resolver copies the cached card list, then keys compilation by list identity. These single-host timings are indicative; the duplicate-index count is the stronger result.

The existing auto performance guard intentionally uses explicit cards, so it misses this external-cache path. Separately, 60 JSONL records sent to the JavaScript CLI against a controlled loopback source caused 60 catalog GETs; the Python CLI made one. The JavaScript CLI starts all quotes with an unbounded `Promise.all`. Both CLIs read and retain whole input/result collections.

**Recommended change:** retain an internal immutable compiled catalog per validated cache revision; coalesce concurrent fetches for the same source/URL; process JSONL incrementally with bounded concurrency and stable output order. Measure cold fetch, revalidation, and real warm-cache paths independently. JavaScript should also enforce response-size limits while reading rather than after allocating the whole `arrayBuffer`.

**Acceptance:** repeated warm quotes do not compile duplicate indexes; one cold concurrent batch performs one source fetch; JSONL memory does not grow with the whole file; refresh failures release waiting callers; existing explicit-catalog performance remains within its budgets. Preserve the zero bundled-provider-data boundary.

Entry points: [Python resolver](../../../packages/python/runcost/price_resolver.py), [JavaScript CLI](../../../packages/javascript/core/cli.js), and JavaScript external fetch handling.

### R10: Unknown discount kinds are silently accepted

An explicit discount policy with `adjustment.type = "typo"` and value `50` is accepted in strict mode in all three local languages. The total is unchanged, and the policy is recorded as an applied zero-value discount. The declared schema allows specific supported kinds; runtime does not enforce that enum through this path.

**Recommended change:** validate supported adjustment kinds before calculation and reject malformed policies with actionable errors. Extend focused boundary coverage for finite numeric values and valid denominators. Decide credit/negative-rate semantics explicitly rather than assuming every negative financial amount is invalid.

**Acceptance:** unsupported kinds cannot produce an applied receipt; valid percentage/fixed/unit adjustments retain their existing behavior; errors are consistent across languages and appear before any misleading ledger is returned.

### R11: Patch playground build dependencies

The playground locks `browserslist@4.28.6` and `baseline-browser-mapping@2.10.43`; the reviewed remote snapshot contains the same versions. npm audit reports Browserslist as high severity and baseline-browser-mapping as moderate. Fixes are available at Browserslist 4.28.7 and baseline-browser-mapping 2.11.0. [Browserslist cache advisory](https://github.com/advisories/GHSA-c83g-rgw3-j3cx), [Browserslist custom-stats advisory](https://github.com/advisories/GHSA-73wf-gq98-2v4g), and [baseline-browser-mapping advisory](https://github.com/advisories/GHSA-w5vr-8v7q-w6rv).

These are playground build dependencies. This review does not establish an exploitable vulnerability in the installed RunCost core or its rendered production runtime.

**Recommended change:** update the affected lockfile graph, review generated changes, and run the site build plus rendered checks. Audit the root and playground graphs independently in CI; the root's clean audit does not cover the playground.

**Acceptance:** the resolved versions fall outside affected ranges, the audit is clean at the intended threshold, and the rendered site still works.

## Further improvements after the corrective pass

1. **Make public explanations match the shipped package.** The live homepage still promises “the exact cost of every LLM response” and labels its result “Exact total”; its visible sample simplifies cached-token placement. The local build already uses estimate wording and a real response shape. Finish this existing work through the release/publication process, with live crawler and rendered verification. Generate the manual warning inventory from taxonomy or check it for completeness: the handwritten page omits `billing_schedule_unsupported`, `invalid_usage`, `pricing_period_required`, `pricing_period_unsupported`, and `usage_inconsistent`.
2. **Offer a privacy-conscious portable ledger.** OTel unknown attributes are retained under `metadata.otel_genai.unknown_attributes`; a synthetic `gen_ai.input.messages` value therefore survives into the result. This is documented retention, and no external transmission was observed. An allowlist/redaction export option would make cost-ledger sharing safer without removing caller-controlled debug data. Cover raw usage and provider identifiers as well as unknown attributes.
3. **Exercise the advertised compatibility floor.** Run the full shared fixtures and installed type consumers on minimum supported Python/Node versions, not only smoke/expansion subsets. Cover Linux/macOS/Windows and consumer timezone availability, especially Go IANA lookups. This review ran on macOS and did not reproduce a Windows timezone defect.
4. **Improve Go failure ergonomics deliberately.** Consider typed, error-returning strict calculation interfaces for callers that need ordinary error handling. Existing panic behavior should remain documented during any compatibility transition. This is API design work, separate from the confirmed strict auto bug.
5. **Split large implementation files gradually.** The local Python core is roughly 6,100 lines, JavaScript core 7,300, and Go ledger 8,300. Extract money/contracts, provider normalization, and adapter boundaries incrementally, retaining public exports, generated browser output, and serialized golden fixtures. File size alone is not evidence of a runtime defect and does not justify a rewrite.
6. **Validate adoption with a focused integration.** GenAI Prices now offers Python, JavaScript/TypeScript, Go, and CLIs, so language breadth is not sufficient differentiation. [Upstream package documentation](https://github.com/pydantic/genai-prices#usage). RunCost's stronger candidate is a local, itemized, provider-neutral estimate with caller-owned source evidence, explicit uncertainty, and reconciliation. After the fixes, validate one independent workflow: install to first ledger, reproduce it offline, reconcile against independently supplied evidence, and identify an actionable discrepancy. Measure that journey before committing to additional CostContract/Collector features or a hosted product. This is a product recommendation; no new adoption or conversion evidence was collected.

The existing beta/v1 checklist and evidence machinery should remain the place to record real qualifications. Passing their structure checks is not equivalent to having completed independent validation or a coherent publication train.

## Recommended implementation sequence

1. Preserve the dirty checkout and reconcile it with the exact remote revision. Establish one candidate revision that retains existing trust work, newer provider support, and the npm workflow repair.
2. Add focused regression cases for R2–R6 and fix the adapter, final strict decision, decimal helper policy, source identity, and consumer types. Include R8/R10 where those same public boundary contracts are touched.
3. Replace incomplete schema validation, fix actual resolver/CLI caching, and update the playground graph. Add targeted gates that would have detected the reproduced failures; retain the existing meaningful suite.
4. Qualify clean candidate artifacts with the pinned release toolchains and real consumer configurations. Review supported-platform evidence and unresolved beta limitations.
5. When release publication is authorized, publish from the same reviewed commit, verify every registry and release object, refresh completion gates and generated caveats, and verify rendered public documentation. Do not treat this review as publication authorization.
6. Revisit product expansion after one independent installation/reconciliation workflow demonstrates a concrete unmet need.

## Limits of the conclusion

This was a broad package review covering repository implementation, synthetic behavioral probes, published Python/npm artifacts, current remote source, release surfaces, source freshness, declarations, packaging, dependencies, documentation, and rendered UI. It was not a formal exhaustive security audit, a verification of every upstream provider price, an audit of customer invoices, or a full execution of every supported OS/runtime combination. Source catalogs and registry state can change after the verification date.

The passing baseline is valuable. The reproduced gaps are sufficient evidence to recommend a corrective release lane; they do not imply that every ordinary calculation is wrong or that RunCost should abandon its existing architecture.
