---
title: Release 0.1.11 Evidence
date: 2026-07-02
type: report
status: evidence
---

# Release 0.1.11 Evidence

This report records the sanitized release evidence for RunCost `0.1.11`.

## Release Objects

- GitHub Release: `v0.1.11`, published at `2026-07-02T15:07:50Z`
  - <https://github.com/adamallcock/runcost/releases/tag/v0.1.11>
- No-publish rehearsal workflow run: `28600250729`, completed successfully from
  `v0.1.11` at `2026-07-02T15:04:12Z`
  - <https://github.com/adamallcock/runcost/actions/runs/28600250729>
- Publish workflow run: `28600349626`, completed successfully from `v0.1.11` at
  `2026-07-02T15:05:38Z`
  - <https://github.com/adamallcock/runcost/actions/runs/28600349626>

The publish workflow run included successful `verify` and `publish` jobs. The
publish job completed both `Publish Python package` and `Publish npm package`.

## Registry State

Verified on 2026-07-02:

```bash
npm view runcost version dist-tags time --json
python3 -m pip index versions runcost-ai --index-url https://pypi.org/simple
curl -fsSL https://pypi.org/pypi/runcost-ai/json
go list -m -versions github.com/adamallcock/runcost
gh release view --repo adamallcock/runcost --json tagName,name,publishedAt,isDraft,isPrerelease,url
```

Results:

| Surface | Verified result |
|---|---|
| GitHub Release | `v0.1.11`, not draft, not prerelease |
| npm | `runcost@0.1.11` is the `latest` dist-tag |
| npm provenance | `runcost@0.1.11` exposes npm attestations with SLSA provenance |
| PyPI | `runcost-ai 0.1.11` is available |
| Go | `go list -m -versions github.com/adamallcock/runcost` includes `v0.1.11` |

## Post-Publish Install Smoke

Verified from clean temporary projects on 2026-07-02:

```bash
python3 -m venv /tmp/runcost-registry-smoke-*/py-venv
/tmp/runcost-registry-smoke-*/py-venv/bin/python -m pip install runcost-ai==0.1.11
/tmp/runcost-registry-smoke-*/py-venv/bin/python -c 'from runcost import from_response, default_price_cards; print(from_response.__name__, len(default_price_cards()))'

npm init -y
npm install runcost@0.1.11
node --input-type=module -e 'import { fromResponse, defaultPriceCards } from "runcost"; console.log(typeof fromResponse, defaultPriceCards().length)'

go mod init runcost-registry-smoke
go get github.com/adamallcock/runcost/packages/go/ledger@v0.1.11
go test github.com/adamallcock/runcost/packages/go/ledger
```

Results:

- Python imported `from_response` and loaded `7751` default price cards.
- npm imported `fromResponse` and loaded `7751` default price cards.
- Go downloaded `github.com/adamallcock/runcost v0.1.11` and package tests
  passed.

## Remaining Gates

Registry publishing, npm provenance, PyPI OIDC publishing, and Go module
availability are no longer release blockers for `0.1.11`.

The remaining public-beta blocker is the real invoice/dashboard comparison gate:
`milestone8_invoice_dashboard_real_comparison`.
