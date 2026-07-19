---
title: Release 0.2.0 Evidence
date: 2026-07-18
type: report
status: evidence
---

# Release 0.2.0 Evidence

This report records sanitized release evidence for RunCost `0.2.0`. The
release replaces the bundled provider catalog with runtime external price
resolution and adds batch normalization, OpenTelemetry GenAI accounting,
budget and reconciliation helpers, additional provider surfaces, and the
public calculator playground.

## Release Objects

- Release commit: `5643ec91b7a9f396d046f02221ef7d98d5393363`
- Annotated tag object: `8eaacea139eea53865aaa83b167c1385d1307381`
  - The `v0.2.0` tag peels to the release commit above.
- GitHub Release: `v0.2.0`, published at `2026-07-19T01:06:38Z`
  - <https://github.com/adamallcock/runcost/releases/tag/v0.2.0>
- No-publish rehearsal workflow run: `29667896599`, completed successfully
  - <https://github.com/adamallcock/runcost/actions/runs/29667896599>
- Publish workflow run: `29667966673`, completed successfully
  - <https://github.com/adamallcock/runcost/actions/runs/29667966673>
- GitHub Pages deployment run: `29667774525`, completed successfully
  - <https://github.com/adamallcock/runcost/actions/runs/29667774525>

The release workflow definition ran from current `main` so the release-safety
fixes were available, but both the verify and publish jobs explicitly checked
out `v0.2.0`. Their logs record release commit
`5643ec91b7a9f396d046f02221ef7d98d5393363` before building or publishing.
The rehearsal completed verification with publishing skipped. The approved
publish run completed verification and both OIDC-backed registry publish steps.

## Rehearsal Artifacts

The no-publish artifact was downloaded from workflow run `29667896599` and
inspected before publishing.

| Artifact | SHA-256 |
|---|---|
| `runcost_ai-0.2.0-py3-none-any.whl` | `53f2f469caf8b3830cc86a531fb4b90dde2a4852a4a2452ae5e2be0f34966f55` |
| `runcost_ai-0.2.0.tar.gz` | `06b299e1bc28855c19ac7523c88c3f6bada84b7ea2fa73369987155ab2db2c15` |
| `runcost-0.2.0.tgz` | `12104e0a04b73f6db207ed4c306805dd0ef91e6653eaf21e82662caf44007a28` |

Wheel metadata, source-distribution contents, npm package contents, and all
embedded version values matched `0.2.0`. Package inspection also confirmed
that no provider price catalog is shipped in the release artifacts.

## Registry State

Verified on 2026-07-18 local time:

```bash
gh release view v0.2.0 --json tagName,name,publishedAt,isDraft,isPrerelease,url,targetCommitish
npm view runcost@0.2.0 version dist-tags dist.integrity dist.shasum --json
curl -fsSL https://pypi.org/pypi/runcost-ai/0.2.0/json
go list -m -json github.com/adamallcock/runcost@v0.2.0
curl -fsSL https://registry.npmjs.org/-/npm/v1/attestations/runcost@0.2.0
```

| Surface | Verified result |
|---|---|
| GitHub Release | `v0.2.0`, not draft, not prerelease |
| npm | `runcost@0.2.0` is the `latest` dist-tag |
| npm integrity | `sha512-bP/RR1j1HEfkvxLbk2n943ccp0bslwxwycRRdU6PZjHndHv0Nng47Z7xeesjeOBkOD8kafU0K8xB36Nk8Muu/g==` |
| npm shasum | `86e0cdf7b4f0fa8e64e3bd18ee919af44c6f57b4` |
| npm provenance | Two attestations are present: npm publish and SLSA provenance |
| PyPI wheel SHA-256 | `399a5e58798ce3e0420a942cd1b56071383c3095b39c1284d155dacbcd50bbdf` |
| PyPI sdist SHA-256 | `cf09ee57949b60f9e3d16ac0b7c0b2f7e4e97b1b2b13d58ed17b3dc3ca38ca30` |
| Go | `github.com/adamallcock/runcost@v0.2.0` resolves at the release commit through the public module proxy |

## Post-Publish Install Smoke

Clean temporary Python, npm, and Go projects installed the public packages.

```bash
python3 -m venv <temp>/venv
<temp>/venv/bin/python -m pip install runcost-ai==0.2.0

npm init -y
npm install --ignore-scripts runcost@0.2.0

go mod init smoke.example/runcost
go get github.com/adamallcock/runcost/packages/go/ledger@v0.2.0
go list github.com/adamallcock/runcost/packages/go/ledger
```

Results:

- Python reported distribution version `0.2.0`, exposed `calculate_cost`,
  `resolve_price_catalog`, and `from_batch_results`, and passed the CLI smoke.
- JavaScript reported package version `0.2.0`, exposed `calculateCost`,
  `resolvePriceCatalog`, and `fromBatchResults`, and passed the CLI smoke.
- Go downloaded `github.com/adamallcock/runcost v0.2.0` and resolved the
  ledger package without a local `replace` directive.

## Public Calculator QA

The deployed site is <https://adamallcock.github.io/runcost/>. Browser QA
verified all eight public routes, desktop and 390-pixel mobile layouts, a live
OpenAI calculation, a Gemini reasoning calculation, and a one-item Bedrock
batch calculation. The page had no console errors or horizontal overflow.

The social image is a real 1200 by 630 PNG served with `image/png`.
`og:image`, `twitter:image`, and `twitter:card=summary_large_image` were visible
to a Twitterbot request. `robots.txt` allows crawling and links the sitemap.

## Post-release Reconciliation

The release, registry, provenance, Go module, and public-site gates are
satisfied for `0.2.0`. A matching real OpenAI dashboard cost and activity
export was subsequently reduced to privacy-preserving normalized evidence and
validated with the strict real-comparison check. The result and its material
provider-internal-tier limitation are documented in
`docs/internal/reports/2026-07-18-openai-dashboard-export-comparison.md`.

That evidence satisfies `milestone8_invoice_dashboard_real_comparison` without
claiming invoice exactness. Milestone 8 and the project completion register's
public-beta gate now pass; the remaining work is distribution and repeated
external validation, not release mechanics.
