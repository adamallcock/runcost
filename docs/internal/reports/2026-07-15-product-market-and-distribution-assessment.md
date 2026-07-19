---
title: RunCost Product-Market and Distribution Assessment
date: 2026-07-15
type: research
status: final
---

# RunCost Product-Market and Distribution Assessment

## Executive conclusion

RunCost should continue, but it should stop presenting itself primarily as a
generic LLM cost calculator. That category is crowded, and several alternatives
have materially stronger distribution. The defensible product is narrower and
more valuable:

> RunCost is the auditable cost ledger and conformance layer for LLM and agent
> usage: it explains which usage field, price row, tier, discount, and warning
> produced every amount.

The project already has unusually deep accounting behavior: component-level
line items, warnings, strict mode, provenance, effective dates, service tiers,
discounts, raw-response extractors, framework adapters, three language
implementations, and a large cross-language fixture corpus. That is real product
substance. The problem is that the first-use experience and public positioning
hide it.

There is competition. Developers commonly use one of four substitutes:

1. a gateway or observability product such as LiteLLM, Langfuse, Helicone,
   LangSmith, or Portkey;
2. an ecosystem-specific helper such as `ai-sdk-cost-calculator`;
3. a price-data library such as Pydantic's `genai-prices`;
4. a small arithmetic package, provider dashboard, provider-reported cost, or
   hand-written multiplication.

RunCost should not build a gateway, dashboard, router, or another universal
price database. It should own strict calculation, reconciliation, provenance,
cache policy, and conformance, while adapting strong upstream price sources. In particular,
Pydantic's `genai-prices` is now a Python and JavaScript package with strong
adoption and active price maintenance; the market gap described in May 2026 has
narrowed substantially.

At the July 15 baseline, the immediate constraint was activation, not missing
provider breadth. A new user could not see the core value in one copy-pasteable
command, the JavaScript entrypoint was not browser/edge safe, implicit package
pricing created a stale maintenance burden, and the registry-facing
documentation undersold the product. Distribution work was gated on fixing
those activation defects.

### Implementation update — July 18, 2026

The expansion branch now closes the identified activation defects: one-call
external-source pricing with a transparent managed cache, matching Python/npm
quote CLIs, a browser/edge-safe entrypoint, compiled catalog lookup, generic
caller-owned manifests, enforced performance budgets, current-runtime CI,
registry-facing quickstarts, and a static public playground are implemented and locally verified. Distribution
can begin after merge, package release, and Pages deployment; this update does
not retroactively change the July 15 market measurements.

## Decision

**Decision: continue as a focused build-and-wrap product.**

- **Build and own:** normalized usage, component ledgers, warnings, strictness,
  price-row provenance, policy application, reconciliation, cross-language
  parity, and the conformance fixture suite.
- **Wrap or adapt:** maintained price catalogs, provider/framework usage
  surfaces, and OpenTelemetry GenAI semantic conventions.
- **Do not build:** a hosted dashboard, proxy/gateway, model router, tokenizer,
  billing system, or hand-maintained catalog crawler unless direct user evidence
  overturns the current boundary.

The next public milestone should be a beta that proves the simple path,
browser/edge compatibility, catalog performance, and one real sanitized
invoice/dashboard reconciliation. It should not be another provider-count
release.

## Scope and method

This assessment was performed on July 15, 2026. It combines:

- repository architecture, requirements, generated support matrices, release
  gates, package contents, and local validation scripts;
- live GitHub, npm, PyPI, and Go release checks;
- live package-search and public-code-search checks;
- source and documentation review of the closest current alternatives;
- small local import/catalog/calculation timing probes, used only as diagnostic
  signals rather than formal benchmarks.

Download counts are treated as directional, not as users. Registry mirrors,
security scanners, CI, dependency caches, release automation, and transitive
dependencies can all inflate them.

## The intended product

The repository's intent is coherent. Its core question is:

> What did this LLM or agent API call cost, and why?

The architecture deliberately separates raw provider/framework extraction,
normalized usage, price data, cost policy, and a deterministic component
ledger. The project explicitly rejects becoming a gateway, dashboard,
observability platform, router, tokenizer, or pricing database.

This is a good boundary. The important distinction is not that RunCost can
multiply tokens by prices; many packages can do that. It is that RunCost can
preserve enough billing semantics to make the result inspectable, testable, and
reconcilable.

### Thesis

LLM billing is becoming less like one input rate plus one output rate. Cache
writes and reads, reasoning tokens, service tiers, context bands, time-varying
prices, audio/image/video units, tools, storage, runtime, provider-reported
costs, discounts, and provider-specific exceptions create accounting ambiguity.
A strict ledger that exposes ambiguity is useful infrastructure.

### Anti-thesis

Most developers do not initially shop for accounting correctness. They want a
number, a spend chart, a budget alert, or a framework callback. Gateways and
observability platforms already capture usage in the path of execution, while
small calculators win through one-line ergonomics. A library with better
semantics can still lose if integration looks like work.

Both are true. RunCost's opportunity exists, but only if strictness is available
behind a very simple default path.

## Current product reality

The implementation is substantially more capable than its “small alpha
utility” description suggests.

- The generated conformance inventory now covers 202 realistic cases: 170
  established fixtures plus 32 product-expansion cases.
- Published packages contain no provider price database. A resolver selects one
  of `genai-prices`, models.dev, LiteLLM, or (for OpenRouter-billed usage)
  OpenRouter and records cache/provenance metadata.
- Twenty-one capability groups are represented across Python, JavaScript, and Go,
  with partial parity explicitly documented where it remains.
- The normalized accounting surface contains 34 usage component names,
  including cache, reasoning, multimodal, tool, storage, and runtime units.
- The library supports component line items, warning codes, strict behavior,
  discounts, effective dates, service tiers, historical prices, source
  provenance, and debug traces.
- Raw provider responses and framework metadata can be normalized rather than
  requiring users to reshape every response by hand.

The public release train is current across the intended surfaces: GitHub
Release `v0.1.13`, npm `runcost@0.1.13`, PyPI `runcost-ai==0.1.13`, and the Go
`v0.1.13` tag were live when checked.

The strict completion register still tells the right story. The remaining
product-level gates are not more local fixtures:

- a real sanitized provider invoice, dashboard, or usage-export comparison is
  still `pending_external_evidence`;
- provider/framework breadth and v1 stabilization remain partial;
- beta credibility therefore still depends on external truth, not only the
  internal test harness.

## What other developers are using

The market is fragmented rather than empty.

| Alternative | What it is good at | Live adoption signal | Where RunCost can differ |
| --- | --- | ---: | --- |
| [LiteLLM](https://github.com/BerriAI/litellm) | Gateway/SDK compatibility, routing, budgets, spend tracking, broad provider catalog | 53,000+ GitHub stars | Independent ledger, no proxy requirement, explainable price-row and policy trace |
| [Pydantic `genai-prices`](https://github.com/pydantic/genai-prices) | Actively maintained price data, historical and tiered pricing, Python and JS calculation | 300+ stars; 100+ public Python dependency-file matches; about 77,000 npm downloads in the checked 30-day window | More complete billing components, warnings, provenance, reconciliation, and Go |
| [`ai-sdk-cost-calculator`](https://github.com/RenKoya1/ai-sdk-cost-calculator) | Excellent Vercel AI SDK ergonomics, provider helpers, trackers, multimodal/tool costs | About 8,500 npm downloads in the checked 30-day window | Framework-independent strict ledger and conformance rather than owning every AI SDK convenience |
| [`tokenlens`](https://github.com/xn1cklas/tokenlens) | Lightweight token/cost estimates in JavaScript | 2 million+ npm downloads in the checked 30-day window, likely including substantial transitive use | Auditable accuracy and richer billing semantics |
| [`tokentally`](https://github.com/steipete/tokentally) | Tiny, simple token and cost math | About 50,000 npm downloads in the checked 30-day window | Strict normalization, warnings, provenance, and reconciliation |
| [`llm-cost`](https://www.npmjs.com/package/llm-cost) | Simple input/output estimates and exact search-term discoverability | About 37,000 npm downloads in the checked 30-day window | Current multidimensional accounting rather than two-rate arithmetic |
| [PriceToken](https://pricetoken.ai/) | Searchable website/API, calculators, price history, cross-modal estimates | Public web product plus Python and npm packages | Raw-response accounting and deterministic evidence trail |
| [Langfuse](https://github.com/langfuse/langfuse), [Helicone](https://github.com/Helicone/helicone), [LangSmith](https://www.langchain.com/langsmith), [Portkey](https://github.com/Portkey-AI/gateway) | Collection, dashboards, traces, budgets, team workflows | Mature communities and in-path distribution | A composable accounting engine they or their users can call, not another UI stack |

These metrics are not directly comparable. A transitive JavaScript dependency
can report far more downloads than an explicitly installed accounting library,
and GitHub stars are not active deployments. They nevertheless disprove the
idea that RunCost has no competition.

### The most important competitive change

Pydantic's `genai-prices` is no longer merely a Python price file. Its current
project provides Python and JavaScript packages and a CLI, raw usage extraction,
cache accounting, historical start dates, time-of-day and tiered pricing, and
an actively maintained provider/model catalog. Its public issue tracker shows
that it is moving into request-level service modifiers, non-token multimodal
units, cache-write TTLs, web search, and a Go package:

- [request-level pricing modifiers](https://github.com/pydantic/genai-prices/issues/429);
- [non-token multimodal units](https://github.com/pydantic/genai-prices/issues/410);
- [Go package](https://github.com/pydantic/genai-prices/issues/407);
- [cache-write TTL](https://github.com/pydantic/genai-prices/issues/295).

That makes it both the closest library competitor and the best potential
upstream data partner. RunCost should add a `genai-prices` source adapter and
make the distinction explicit: `genai-prices` maintains convenient market
prices; RunCost produces a strict, componentized, provenance-preserving ledger.

### The hidden competition

The most common substitute may be no costing package at all. Teams accept a
provider-reported `cost` field, inspect a provider dashboard, multiply token
counts by two prices, or let an observability product calculate the total. This
is sufficient until a bill does not reconcile, a model has special billing
semantics, or a cost number needs to be trusted in software.

RunCost's marketing should therefore sell the failure mode, not “cost
calculation” in the abstract:

- Why did two tools disagree about this call?
- Did cached, reasoning, or tool usage disappear?
- Which historical price was selected?
- Was a service-tier modifier applied?
- Can this number be reproduced in Python, JavaScript, and Go?
- Can the result be compared to a real invoice without hiding residuals?

## Competitive capability matrix

This matrix describes product orientation, not every implementation detail.

| Capability | RunCost | `genai-prices` | AI SDK calculator | LiteLLM | Observability platforms |
| --- | --- | --- | --- | --- | --- |
| One-call estimate | Yes; external resolver and CLIs | Yes | Excellent | Yes | Usually automatic |
| Raw response/framework extraction | Broad and fixture-backed | Some | AI SDK focused | Broad | Through instrumentation/proxy |
| Component line-item ledger | Strong | Mostly aggregate input/output | Provider-specific result | Cost total/usage oriented | Usually aggregate/event views |
| Explicit warnings and strict mode | Strong | Limited | Limited | Limited for accounting ambiguity | Product-specific |
| Price-row provenance/debug trace | Strong | Price match available | Limited | Limited | Usually opaque to library caller |
| Historical/tiered pricing | Yes | Strong | Some | Broad | Product-specific |
| Non-token components | Broad model | Emerging | Broad within supported providers | Broad provider support | Product-specific |
| Cross-language parity | Python, JS, Go | Python, JS | JS/TS | Primarily Python/proxy | HTTP/SDKs |
| Gateway/dashboard/budgets | Intentionally no | No | No | Yes | Yes |
| Public conformance corpus | 202 generated cases plus external-fixture workflow | Tests/data checks | Tests | Tests | Rarely portable |
| Invoice reconciliation | Harness exists; real evidence pending | No | No | Provider-specific tracking | Often the product, but calculation may be opaque |

## Distribution diagnosis — July 15 baseline

The user's impression is correct: confirmed human distribution is very low.

### Evidence

- The public repository showed one star, no forks, and no confirmed external
  implementation usage in public GitHub code search.
- Searches for `runcost-ai` and `from runcost import` primarily found this
  repository or package-indexing data, not independent projects.
- GitHub's 14-day traffic endpoint reported thousands of clones but only five
  page views from five unique visitors. That pattern is consistent with bots,
  mirrors, scanners, and automation rather than a human funnel.
- npm reported 1,188 downloads in the checked 30-day window, but large spikes
  clustered around releases while ordinary days were much smaller. The count
  should not be interpreted as 1,188 users.
- Broad npm searches for “llm cost”, “llm pricing”, “ai cost calculator”, and
  “token cost” did not surface RunCost in the first 250 results, although an
  exact search did.

### Why discovery is weak

1. **The category language is missing.** The npm description is “Alpha cost
   ledger utility for LLM and agent API responses.” It does not contain the
   common phrases “LLM cost calculator”, “AI cost calculator”, or “token cost”.
2. **The package name collides on PyPI.** `pip install runcost` installs a
   separate, active project, [`runcost`](https://pypi.org/project/runcost/).
   This project must consistently teach `pip install runcost-ai` and should use
   a differentiating public subtitle such as “RunCost Ledger”.
3. **The registry README is not an activation surface.** Its basic example uses
   undefined `response` and `priceCards` variables, so it is not copy-pasteable.
4. **The root quickstart led with custom price-card construction.** That is a
   valuable advanced path but was a poor first impression for a package that
   needed an external-resolver convenience path.
5. **The public promise and setup cost disagree.** The project says it belongs
   in one or two lines near an SDK call; the first path shown to a user is much
   longer.
6. **There was no web proof surface.** PriceToken and observability products can
   answer a query on a public page. RunCost asked visitors to understand the
   architecture before seeing the differentiator.
7. **There was no ecosystem insertion point yet.** Competitors are carried by
   AI SDK callbacks, gateways, instrumentation, or a well-known maintainer
   ecosystem. RunCost is currently a destination users must discover unaided.

### Why activation was weak

- The JavaScript module imported Node filesystem/path modules at top level, so
  even pure calculation paths were not safely portable to browsers or edge
  runtimes.
- The same roughly 6.6 MB source-cache JSON was shipped in each language
  implementation. A local diagnostic on this checkout measured roughly 66 ms
  for Python import, 64 ms to load the catalog, 4 ms for the first calculation,
  and 3.4 ms per call across a 100-call loop. JavaScript was faster but still
  paid catalog loading cost. These are single-machine diagnostics, not formal
  benchmarks, but they justify a performance budget and indexed singleton.
- The npm package unpacked to roughly 6.9 MB despite containing only a
  small API surface plus the catalog.
- CI validated Python 3.12 and Node 22, while the public compatibility claims
  cover a wider range. Compatibility is therefore claimed more broadly than it
  is continuously demonstrated.

## Highest-leverage product improvements

### P0: fix activation before promotion

| Improvement | Why now | Suggested acceptance gate |
| --- | --- | --- |
| Make external price resolution the one-call path | The first result should require a response, provider, and model—not a hand-built price schema or a RunCost-owned database | Copy-paste Python and JS examples run unmodified and print total, line items, sources, and warnings |
| Rewrite root, npm, and PyPI quickstarts | Registry pages are the highest-intent landing pages | A clean environment can install and obtain a cost in under two minutes |
| Add `runcost quote` for JSON stdin/files | A CLI exposes the product without framework commitment and creates a demo primitive | One provider-response fixture can be piped to Python and npm CLIs with equivalent JSON output |
| Split browser-safe calculation from Node file-cache persistence | Edge/worker compatibility is important for JavaScript agent apps | Browser, Cloudflare Worker, and Node smoke tests import the intended entrypoints without shims |
| Compile/index and memoize resolved catalogs | Large upstream data shapes impose avoidable parse, search, and memory costs | Defined cold/warm latency, memory, and package-size budgets pass in CI |
| Add a compatibility CI matrix | Package claims should be continuously true | Minimum supported Python/Node versions plus current stable versions run core tests |

The simplest API should remain honest. If provider, model, timestamp, surface,
or tier cannot be inferred safely, the function should ask for the missing
field or return a structured warning; it should not guess silently.

### P1: turn differentiation into integrations

1. **Add a `genai-prices` source adapter.** Avoid duplicating its maintenance
   engine. Preserve upstream identifiers and provenance, and document which
   RunCost-only billing components require other sources.
2. **Add a generic OpenTelemetry GenAI adapter/enricher.** The official
   [OpenTelemetry GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai)
   now define provider/model and cache, reasoning, and token usage attributes.
   Accepting spans—and optionally emitting ledger attributes/events—puts
   RunCost beside existing instrumentation rather than requiring a new capture
   path.
3. **Productize the fixture corpus as a conformance suite.** Publish a fair,
   reproducible matrix showing which billing semantics each calculator
   preserves, warns on, or drops. The fixtures are a stronger moat and a better
   publicity asset than the raw provider count.
4. **Complete one real reconciliation.** Use a sanitized provider export or
   dashboard sample, publish residuals and limitations, and close the external
   evidence gate before calling the product beta.
5. **Make external fixtures easy to contribute.** Provide a redaction-safe
   schema, fixture generator, expected-ledger review checklist, and one-command
   validation. Ask the community for broken billing cases, not stars.

### P2: useful, but only after evidence

- Add optional attribution fields such as run, session, workflow, tenant, or
  feature to ledger output so users can aggregate elsewhere without RunCost
  becoming a datastore.
- Add thin pre-call estimation or budget-policy hooks only if adopters ask for
  them. Stateful budgets and routing quickly turn the project into a gateway.
- Provide signed catalog manifests or reproducible source snapshots if
  regulated or enterprise users demonstrate a need.
- Add provider-reported-cost comparison helpers, but always retain the
  independently calculated ledger and residual rather than replacing it with
  the provider's number.

All four P2 library surfaces were implemented as stateless, schema-backed
helpers on the expansion branch. This does not imply that stateful spend
storage, routing, or a hosted billing system was added.

## What not to prioritize

- More provider logos without activation evidence.
- A hosted dashboard or proxy.
- A custom pricing crawler that competes with active catalog maintainers.
- A tokenizer or generalized usage-estimation engine.
- Raw download-count growth as the main success metric.
- Paid promotion before the quickstart and proof surface convert organic
  visitors.

## Distribution strategy

### Phase 0: make the claim demonstrable

Before a broad launch:

1. ship the runnable two-minute quickstart and CLI;
2. prove browser/edge and supported-runtime compatibility;
3. publish a small interactive or static “explain this response” playground
   using sanitized fixtures;
4. finish one real sanitized invoice/dashboard comparison;
5. promote a beta version and replace blanket “alpha” language with precise
   caveats once the gates permit it.

The playground does not need accounts, storage, or a backend. A visitor should
select a fixture and immediately see normalized usage, selected price rows,
line items, warnings, and the final total.

### Phase 1: borrow distribution from ecosystems

- Integrate with `genai-prices` and participate constructively in its Go and
  request-modifier discussions. Cooperation is more credible than a vague
  comparison page.
- Ship OpenTelemetry GenAI examples and a small collector/enrichment recipe.
- Publish Vercel AI SDK, Pydantic AI, LangChain, and direct-provider examples
  that demonstrate the strict ledger without replacing their normal runtime.
- Submit narrowly useful upstream documentation or example changes where
  maintainers welcome them; do not spray promotional PRs.
- Use one of the maintainer's own public applications to publish a sanitized
  case study: what a simple calculator returned, what RunCost preserved, and
  whether the provider export reconciled.

### Phase 2: launch around evidence, not a repository

Launch the beta with one memorable artifact: the public conformance matrix or
invoice-reconciliation case study. Then share it in relevant communities such
as Hacker News, LocalLLaMA, LLM developer forums, and framework discussions.

Suggested message:

> Most LLM cost helpers return a number. RunCost tells you which usage field,
> price row, tier, discount, and warning produced it—and reproduces the ledger
> in Python, JavaScript, and Go.

The call to action should be “send us a billing response that calculators get
wrong” rather than “star the repo”. This attracts the exact evidence that
improves the moat.

### Phase 3: become the reference for billing edge cases

- Publish short, source-linked notes when providers add a new billing semantic,
  not generic release announcements.
- Maintain indexable pages for “LLM cost calculator”, “OpenAI API cost
  calculator”, “Anthropic cache cost”, “Gemini thinking token cost”, and similar
  exact problems, each backed by executable fixtures.
- Publish a monthly support/conformance matrix with change history.
- Turn external failures into regression fixtures and credit contributors.

## Success metrics

Use a funnel that distinguishes machines from people.

### Discovery

- Search position and impressions for exact problem terms.
- Unique human visits to the quickstart, playground, and conformance matrix.
- Referral sources from ecosystem documentation and discussions.

### Activation

- Percentage of quickstart visitors reaching a successful example.
- CLI example runs or playground fixture interactions, if measured with a
  privacy-respecting mechanism.
- Documentation-to-package-page and package-page-to-repository conversion.

### Trust

- Independent repositories with a real RunCost import.
- External fixtures, issue reporters, and invoice reconciliation cases.
- Ecosystem examples or integrations maintained outside this repository.

### Retention

- Independent dependent projects releasing again with RunCost still present.
- Repeat external contributors or issue reporters.
- New provider billing changes covered through community evidence rather than
  maintainer-only discovery.

Do not use npm/PyPI downloads alone as the north-star metric. They are useful
for anomalies and trend direction, but the current clone/view and release-spike
patterns demonstrate that they do not measure active users reliably.

## Ninety-day sequence

### Days 1–14: activation

- [x] Make first cost calculation copy-pasteable in every registry README.
- [x] Add CLI input/output contracts.
- [x] Separate browser-safe core from Node file-cache persistence.
- [x] Establish catalog performance and package-size budgets.
- [x] Add supported-runtime CI.

### Days 15–35: proof

- Complete one real sanitized reconciliation.
- [x] Publish the initial conformance suite and methodology.
- [x] Add the `genai-prices` source adapter.
- [x] Add an OpenTelemetry GenAI adapter and enricher.

### Days 36–60: beta and ecosystem insertion

- Resolve the explicit beta gates and release a beta with precise caveats.
- [x] Prepare Pydantic AI, Vercel AI SDK, OpenTelemetry, and direct-provider
  examples.
- Invite billing edge-case fixtures from relevant maintainers and users.

### Days 61–90: distribution test

- Launch the conformance/reconciliation artifact publicly.
- [x] Prepare three exact-problem, search-oriented pages backed by fixtures.
- Review real human funnel metrics and independent dependencies.
- Continue only the channels that produce successful integrations, external
  evidence, or repeat visitors.

## Stop, continue, and expansion gates

At 90 days, continue investing if at least two of the following are true:

- three independent public or privately verified projects use RunCost;
- five high-quality external billing fixtures have been contributed;
- one ecosystem integration or example is maintained or linked externally;
- a real invoice/dashboard reconciliation validates a material advantage;
- the quickstart/playground shows repeat human use rather than registry noise.

If none are true after the activation work and a focused launch, keep RunCost as
a high-quality internal/open-source utility and stop broad feature expansion.
That is a valid outcome. It would avoid turning a useful ledger into a large
unsupported platform in search of a market.

## Primary sources

### RunCost surfaces

- [GitHub repository](https://github.com/adamallcock/runcost)
- [GitHub releases](https://github.com/adamallcock/runcost/releases)
- [npm package](https://www.npmjs.com/package/runcost)
- [PyPI package](https://pypi.org/project/runcost-ai/)
- [Go module](https://pkg.go.dev/github.com/adamallcock/runcost/packages/go/ledger)

### Alternatives and standards

- [Pydantic `genai-prices` source](https://github.com/pydantic/genai-prices)
- [Pydantic `genai-prices` on PyPI](https://pypi.org/project/genai-prices/)
- [Pydantic `genai-prices` on npm](https://www.npmjs.com/package/@pydantic/genai-prices)
- [LiteLLM source](https://github.com/BerriAI/litellm)
- [`ai-sdk-cost-calculator` source](https://github.com/RenKoya1/ai-sdk-cost-calculator)
- [`tokenlens` source](https://github.com/xn1cklas/tokenlens)
- [`tokentally` source](https://github.com/steipete/tokentally)
- [PriceToken](https://pricetoken.ai/)
- [OpenTelemetry GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai)
- [OpenTelemetry GenAI attribute registry](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/)
- [PyPI project named `runcost`](https://pypi.org/project/runcost/)

## Evidence limitations

- Public code search misses private repositories and code that vendors or wraps
  dependencies.
- GitHub stars, package downloads, and repository traffic are adoption proxies,
  not active-user counts.
- Competitor counts and package capabilities will change after the assessment
  date.
- Local timing probes were not controlled benchmarks and should be replaced by
  reproducible CI measurements before setting final budgets.
- Hosted platforms can change closed-source behavior without public evidence;
  the comparison therefore focuses on their public product boundary rather
  than claiming internal implementation details.
