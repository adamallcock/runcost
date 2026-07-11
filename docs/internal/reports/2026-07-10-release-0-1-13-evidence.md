---
title: Release 0.1.13 Evidence
date: 2026-07-10
type: report
status: evidence
---

# Release 0.1.13 Evidence

This report records sanitized release evidence for RunCost `0.1.13`. The
release adds reviewed OpenAI GPT-5.6 pricing and cache-write accounting, plus
Meta Model API response compatibility with opt-in preview pricing.

## Release Objects

- Release commit: `11f8e4b0b65693b0c47195a47cbc966cfbc0d3b2`
- Annotated tag object: `349268ca056b2f6a184c79d32990b53dc6a54500`
  - The `v0.1.13` tag peels to the release commit above.
- GitHub Release: `v0.1.13`, published at `2026-07-11T02:17:05Z`
  - <https://github.com/adamallcock/runcost/releases/tag/v0.1.13>
- No-publish rehearsal workflow run: `29135970834`, completed successfully
  from `main` at `2026-07-11T02:14:09Z`
  - <https://github.com/adamallcock/runcost/actions/runs/29135970834>
- Publish workflow run: `29136027287`, completed successfully from `main` at
  `2026-07-11T02:16:39Z`
  - <https://github.com/adamallcock/runcost/actions/runs/29136027287>

Both workflow runs used release commit
`11f8e4b0b65693b0c47195a47cbc966cfbc0d3b2`. The rehearsal completed its
`verify` job with publishing skipped. The approved publish run completed both
the `verify` and `publish` jobs, including PyPI trusted publishing and npm
trusted publishing with provenance.

## Rehearsal Artifacts

The no-publish artifacts were downloaded and inspected before publishing.

| Artifact | SHA-256 |
|---|---|
| `runcost_ai-0.1.13-py3-none-any.whl` | `9d1e7c481789278edde08e491dbada74bd7141d82bbf5894ffbf95fbf409360d` |
| `runcost_ai-0.1.13.tar.gz` | `9cbd248a6adc5840978da43f387b1fc6e829fb7eff6eaded9fb07d351e0ed1ac` |
| `runcost-0.1.13.tgz` | `a7939e217b88022cd647443c88af5a6efd0f4e0468a7c5da5dcae4dc24722273` |

Wheel metadata, source-distribution contents, npm package contents, and all
embedded version values matched `0.1.13`.

## Registry State

Verified on 2026-07-10 local time:

```bash
gh release view v0.1.13 --json tagName,name,publishedAt,isDraft,isPrerelease,url,targetCommitish
npm view runcost@0.1.13 version dist-tags dist.integrity dist.shasum --json
curl -fsSL https://pypi.org/pypi/runcost-ai/0.1.13/json
go list -m -json github.com/adamallcock/runcost@v0.1.13
curl -fsSL https://registry.npmjs.org/-/npm/v1/attestations/runcost@0.1.13
```

| Surface | Verified result |
|---|---|
| GitHub Release | `v0.1.13`, not draft, not prerelease |
| npm | `runcost@0.1.13` is the `latest` dist-tag |
| npm integrity | `sha512-/J5XKbqDs6pfjaFZhrIf0T9QcZyCUfm6XAT/EFQ3Wrr8AUwHgYPiB1+Tju25f5mwrbY+6PaWvsLiiLCoFNKBzw==` |
| npm shasum | `bfbd57ce9abe64c090685134c116ae84f9737b41` |
| npm provenance | Two attestations are present: npm publish and SLSA provenance |
| PyPI wheel SHA-256 | `88efaa46274c88cc6b891b1c5fa7e8485eaed1e59fb6ba01b07b0aa8dc2deac9` |
| PyPI sdist SHA-256 | `a4b8a9c1601b41af0ede52259918634dc2dc8c5cc5c4ec19a2d4dcb1885e3427` |
| Go | `github.com/adamallcock/runcost@v0.1.13` resolves at the release commit |

## Post-Publish Install Smoke

Clean temporary Python, npm, and Go projects installed the public packages.
The Python and JavaScript packages then priced the same GPT-5.6 Responses usage
sample with 1,000 input tokens, 200 cache-read tokens, 100 cache-write tokens,
and 100 output tokens.

```bash
python3 -m venv /tmp/runcost-pypi-smoke/venv
/tmp/runcost-pypi-smoke/venv/bin/python -m pip install runcost-ai==0.1.13

npm init -y
npm install --ignore-scripts runcost@0.1.13

go mod init smoke.example/runcost
go get github.com/adamallcock/runcost/packages/go/ledger@v0.1.13
go list github.com/adamallcock/runcost/packages/go/ledger
```

Results:

- Python loaded the bundled default catalog and returned total cost
  `0.007225` for the GPT-5.6 cache-write sample.
- JavaScript loaded the bundled default catalog and returned the same
  `0.007225` total.
- Go downloaded `github.com/adamallcock/runcost v0.1.13` and resolved the
  ledger package without a local `replace`.

## Remaining Gates

Registry publishing, npm provenance, PyPI OIDC publishing, and Go module
availability are not release blockers for `0.1.13`.

The remaining public-beta blocker is the sanitized real provider
invoice/dashboard comparison gate:
`milestone8_invoice_dashboard_real_comparison`.
