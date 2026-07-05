---
title: Release 0.1.12 Evidence
date: 2026-07-05
type: report
status: evidence
---

# Release 0.1.12 Evidence

This report records the sanitized release evidence for RunCost `0.1.12`.

## Release Objects

- GitHub Release: `v0.1.12`, published at `2026-07-05T07:10:28Z`
  - <https://github.com/adamallcock/runcost/releases/tag/v0.1.12>
- No-publish rehearsal workflow run: `28732856276`, completed successfully from
  `v0.1.12` at `2026-07-05T07:07:34Z`
  - <https://github.com/adamallcock/runcost/actions/runs/28732856276>
- Publish workflow run: `28732889941`, completed successfully from `v0.1.12` at
  `2026-07-05T07:09:43Z`
  - <https://github.com/adamallcock/runcost/actions/runs/28732889941>

Both workflow runs used tag commit
`367b1180209ad0892eac446504a78d1ca2813128`. The publish workflow run included
successful `verify` and `publish` jobs. The publish job completed both
`Publish Python package` and `Publish npm package`.

## Registry State

Verified on 2026-07-05:

```bash
gh release view v0.1.12 --json tagName,name,publishedAt,isDraft,isPrerelease,url,targetCommitish
npm view runcost@0.1.12 name version dist-tags dist.integrity dist.shasum time --json
python3 -m pip index versions runcost-ai
curl -fsSL https://pypi.org/pypi/runcost-ai/0.1.12/json
go list -m -versions github.com/adamallcock/runcost
curl -fsSL https://registry.npmjs.org/-/npm/v1/attestations/runcost@0.1.12
```

Results:

| Surface | Verified result |
|---|---|
| GitHub Release | `v0.1.12`, not draft, not prerelease |
| npm | `runcost@0.1.12` is the `latest` dist-tag |
| npm integrity | `sha512-jsmkHdgen1zlBcAQVl757O/IPlpk/0HSjalFrm+GK2Su6R+a5c+f7pSqtQ6vrgk5etOPVph4/fIKPjOZbbxy9A==` |
| npm shasum | `79e827d59b965f078bc1d593720f9541d7fbe71b` |
| npm provenance | `runcost@0.1.12` exposes npm attestations with SLSA provenance |
| PyPI | `runcost-ai 0.1.12` is available with wheel and source distribution files |
| Go | `go list -m -versions github.com/adamallcock/runcost` includes `v0.1.12` |

The publish log recorded PyPI upload responses of `200 OK` for both
`runcost_ai-0.1.12-py3-none-any.whl` and `runcost_ai-0.1.12.tar.gz`.

## Post-Publish Install Smoke

Verified from clean temporary projects on 2026-07-05:

```bash
python3 -m venv /tmp/runcost-registry-smoke-*/venv
/tmp/runcost-registry-smoke-*/venv/bin/python -m pip install runcost-ai==0.1.12
/tmp/runcost-registry-smoke-*/venv/bin/python -c 'from runcost import from_response, default_price_cards; print(from_response.__name__, len(default_price_cards()))'

npm init -y
npm install runcost@0.1.12
node -e 'const r=require("runcost"); console.log(typeof r.fromResponse, r.defaultPriceCards().length)'
npm audit signatures

go mod init runcost-registry-smoke
go get github.com/adamallcock/runcost/packages/go/ledger@v0.1.12
go test github.com/adamallcock/runcost/packages/go/ledger
```

Results:

- Python imported `from_response` and loaded `7751` default price cards.
- npm imported `fromResponse` and loaded `7751` default price cards.
- `npm audit signatures` verified one registry signature and one attestation.
- Go downloaded `github.com/adamallcock/runcost v0.1.12` and package tests
  passed.

## Remaining Gates

Registry publishing, npm provenance, PyPI OIDC publishing, and Go module
availability are not release blockers for `0.1.12`.

The remaining public-beta blocker is the real invoice/dashboard comparison gate:
`milestone8_invoice_dashboard_real_comparison`.
