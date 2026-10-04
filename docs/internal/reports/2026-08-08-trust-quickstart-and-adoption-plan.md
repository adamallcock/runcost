---
title: RunCost Trust, Quickstart, And Adoption Plan
date: 2026-08-08
type: plan
status: active
---

# RunCost Trust, Quickstart, And Adoption Plan

## Objective

Make RunCost the easiest way to turn an existing LLM provider response into a
local, itemized cost ledger, then help independent developers integrate that
ledger into real projects.

This plan does not use an adoption deadline to decide whether RunCost should
continue. It establishes an ongoing operating rhythm: improve first success,
work directly with users, contribute useful integrations upstream, and let
observed use shape subsequent features.

## Product Boundary

RunCost owns:

- provider and framework usage extraction;
- disjoint billable components;
- deterministic USD calculation;
- source provenance, warnings, and strict behavior;
- reconciliation and cross-language conformance.

RunCost does not become a gateway, dashboard, trace store, router, or pricing
database. It consumes maintained price sources and produces an inspectable
ledger locally.

## Decisions For The Current Stage

1. Currency is USD-only. Non-USD price cards and non-USD or mixed-currency
   aggregation must fail explicitly.
2. Contradictory usage totals must never be silently converted into plausible
   costs. Compatibility mode returns a structured warning; strict mode fails.
3. Money calculations use at most 18 fractional decimal places with an explicit
   shared rounding contract across Python, JavaScript, and Go.
4. The README, PyPI page, npm page, landing page, and playground lead with one
   canonical response-to-ledger quickstart and visible output.
5. Packaging, validation, dependency, and release-artifact gaps are corrected
   before another feature release.
6. Internal modularization is a separate stage. It must preserve public APIs and
   byte-equivalent results before and after each extraction.

## Stage One: Trust And First Success

### Correctness

- Enforce USD in schemas, types, calculators, and aggregators.
- Validate non-negative quantities and provider subtotal relationships.
- Distinguish unsupported surfaces from malformed supported payloads.
- Make Go options immutable at public boundaries and accept nil adapter options.
- Standardize 18-place rounding without changing terminating results.
- Add shared adversarial fixtures and direct public-API regression tests.

### Public Presentation

- Use this primary explanation:

  > Provider response in. Local, itemized cost ledger out, with every selected
  > rate, source, assumption, and warning visible.

- Show one input and the resulting component table before broad capability
  matrices.
- Keep Python, JavaScript, CLI, and Go discoverable without making the first
  screen carry four parallel tutorials.
- Move detailed API and provider material into the existing guides and reference
  docs.
- Render the landing-page response from the exact object being calculated.
- Describe the result as an auditable estimate with exact arithmetic, not an
  invoice-exact answer for every response.

### Distribution Packages

- PyPI continues to use distribution name `runcost-ai`, import name `runcost`,
  and the root README. State that distinction beside the install command.
- npm uses the package README and a description centered on a local itemized
  cost ledger rather than a generic calculator.
- Both listings show the same canonical input, result, caveat, project links,
  and public-beta status after the next release.
- The npm archive includes the MIT license text.

### Release And Validation

- Exercise root and playground dependencies in CI.
- Monitor both npm lockfiles and keep security checks explicit.
- Validate the JSON Schemas with their relied-on `oneOf` and date-time rules.
- Build release artifacts once and publish the exact verified wheel, sdist, and
  npm archive.
- Verify the GitHub Release, npm, PyPI, and Go module as one release train.

## Domain Direction

Registry/RDAP checks on 2026-08-08 returned no registration record for the
following candidates. This is a point-in-time availability signal, not a price
quote, trademark clearance, or guarantee that a registrar will complete the
purchase.

| Candidate | Direction | Notes |
| --- | --- | --- |
| `runcostledger.dev` | Recommended | Distinguishes the product from the unrelated `runcost` PyPI project and names the actual wedge. |
| `runcostledger.com` | Defensive alternative | The same differentiated name on the familiar commercial TLD; useful as a redirect if owning both domains is worth the renewal cost. |
| `runcost.dev` | Strong short alternative | Excellent readability, but higher confusion risk because another active software package uses RunCost. |
| `getruncost.dev` | Campaign alternative | Readable and flexible, but weaker as the canonical product identity. |
| `runcost.ai` | Available-looking alternative | Exact brand and category, but likely higher renewal cost and the same naming-conflict risk. |
| `costledger.dev` | Neutral alternative | Clear category name, but gives up the established RunCost identity. |

`runcost.com` is registered. An unrelated project owns the `runcost` PyPI name,
and another RunCost-branded planning product is publicly visible. Before buying
or redirecting a canonical domain, recheck registrar availability and pricing,
then perform a focused name and trademark review. No domain purchase is part of
this implementation stage.

Point-in-time lookup receipts:

- Google Registry RDAP returned no registration record for
  [`runcostledger.dev`](https://pubapi.registry.google/rdap/domain/runcostledger.dev),
  [`runcost.dev`](https://pubapi.registry.google/rdap/domain/runcost.dev), and
  [`getruncost.dev`](https://pubapi.registry.google/rdap/domain/getruncost.dev), and
  [`costledger.dev`](https://pubapi.registry.google/rdap/domain/costledger.dev).
- Identity Digital RDAP returned no registration record for
  [`runcost.ai`](https://rdap.identitydigital.services/rdap/domain/runcost.ai).
- Verisign RDAP returns the active registration record for
  [`runcost.com`](https://rdap.verisign.com/com/v1/domain/RUNCOST.COM), while it
  returned no registration record for
  [`runcostledger.com`](https://rdap.verisign.com/com/v1/domain/RUNCOSTLEDGER.COM).
- The naming-conflict check is the active, unrelated
  [`runcost` project on PyPI](https://pypi.org/project/runcost/). RunCost's
  Python distribution remains [`runcost-ai`](https://pypi.org/project/runcost-ai/).

## Adoption Operating Plan

### Who To Help First

1. **Application developers** already holding an OpenAI, Anthropic, Gemini, or
   compatible response who need a trustworthy total without adding a proxy.
2. **Framework and observability maintainers** who can emit or attach a RunCost
   ledger from callbacks, spans, or run metadata.
3. **AI platform and FinOps engineers** debugging disagreements between local
   calculations, provider-reported costs, dashboards, and invoices.

### First-Success Path

Every public entry point should lead through the same sequence:

1. install or open the playground;
2. pass the response already available to the application;
3. see cached input, reasoning output, and other billable components separated;
4. inspect the chosen source and warnings;
5. copy an integration pattern appropriate to the application.

The first result should require no account, hosted service, proxy, or manually
assembled price card.

### Integration Work

- Maintain small recipes for OpenAI Responses, Anthropic Messages, Vercel AI
  SDK `onFinish`, OpenTelemetry GenAI spans, Langfuse/Helicone metadata, batch
  output, and caller-owned custom prices.
- Contribute examples, fixtures, or narrowly useful adapters to upstream
  projects when their maintainers welcome them. Prefer an upstream-owned recipe
  over another RunCost-only demo repository.
- Invite external billing responses as sanitized fixtures, with clear redaction
  instructions and no prompts, outputs, account identifiers, or credentials.
- Offer hands-on integration help for a small set of real projects and record
  installation friction, warnings, missing billing dimensions, and whether the
  ledger remains in use.

### Evidence-Led Communication

- Publish short, executable billing cases rather than broad feature lists:
  cached plus uncached input, reasoning plus visible output, service or batch
  tiers, and provider-reported versus calculated totals.
- Show the input, selected price rows, ledger output, and limitation for every
  case.
- Write ecosystem-specific posts or contributions. Do not repost one generic
  launch message everywhere.
- Keep comparison material neutral and source-bound. The purpose is to teach
  when an evidence ledger matters, not to manufacture a leaderboard.

### Discovery And Measurement

- Create focused pages or sections for phrases developers actually search:
  `OpenAI response cost`, `Anthropic cached token cost`, `LLM cost ledger`, and
  `Vercel AI SDK cost calculation`.
- Keep package descriptions, repository topics, examples, and page titles
  consistent with those jobs.
- Measure route views, quickstart interaction, successful local calculations,
  repeat visits, confirmed integrations, external fixtures, and reconciliations.
- Treat registry downloads, stars, clones, and crawler traffic only as context.
- Never collect pasted responses, prompts, outputs, request IDs, attribution,
  credentials, or errors containing user payloads.

### Working Rhythm

- **Foundation:** land the trust and quickstart release, then verify every public
  package and rendered surface.
- **Integration cycles:** choose one ecosystem at a time, produce a working
  recipe or upstream contribution, and support developers who try it.
- **Case cycles:** turn sanitized real disagreements into fixtures, tests, and a
  short public explanation.
- **Monthly review:** summarize confirmed use, first-run friction, useful
  warnings, missing integrations, and the next small distribution experiment.

The roadmap follows repeated user needs. A requested feature becomes stronger
when it appears in more than one real integration, but it is not governed by a
calendar-based continuation gate.

## Stage Two: Parity-Locked Modularization

Modularization starts only after Stage One is merged and verified.

Before moving code:

1. freeze canonical JSON outputs for the full conformance corpus and the new
   adversarial cases;
2. snapshot public exports, signatures, package contents, CLI help, browser
   exports, warning ordering, and representative performance;
3. establish an automated before/after differential runner for Python,
   JavaScript, browser, and Go.

Then extract one seam at a time:

1. validation and decimal utilities;
2. provider extractors;
3. price matching and calculation;
4. aggregation and reconciliation;
5. external resolution and framework adapters.

Each extraction must preserve canonical output bytes for unchanged inputs,
public API compatibility, package-install behavior, and performance budgets.
Intentional behavior changes require their own fixture-backed change before or
after the structural refactor, never hidden inside it.

## Remaining External Actions

- Recheck registrar price and availability, complete a focused name/trademark
  review, and purchase the chosen domain only after explicit approval. No domain
  was purchased in this stage.
- Verify and, if necessary, enable Dependabot alerts and security updates in the
  repository's GitHub Settings. The repository API check did not confirm that
  alerts are enabled, and this setting cannot be corrected through the tracked
  Dependabot configuration alone.
- Publish the refreshed npm and PyPI listing content only as part of the next
  explicitly approved, coordinated GitHub/npm/PyPI/Go release train. This stage
  did not publish or alter live registry packages.

## Immediate Completion Evidence

The current stage is complete when:

- focused regression tests cover every corrected boundary;
- the complete repository suite passes from a clean dependency install;
- package dry runs show the intended metadata and license contents;
- Python, JavaScript, Go, CLI, and browser examples produce aligned results;
- the local website passes desktop and mobile browser review;
- this plan records remaining external actions, including domain purchase and
  any GitHub security setting that cannot be changed in the repository.
