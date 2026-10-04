---
title: RunCost Package Installation
date: 2026-05-25
type: guide
status: active
---

# RunCost Package Installation

RunCost `0.2.x` is published as a public-beta package for Python,
JavaScript/TypeScript, and Go. Source checkout install paths remain useful for
local development and release verification.

The current release is `0.2.4` / Go tag `v0.2.4`. Its
[release evidence](../internal/reports/2026-10-04-release-0-2-4-evidence.md)
records exact artifact parity, platform CI, public registry consumer checks,
and any remaining distribution check. CI exercises Python 3.9 and Node 20 as
the minimum runtime lane, alongside newer runtimes and macOS/Windows.

For a reproducible installation, pin the coordinated version:

```bash
python3 -m pip install runcost-ai==0.2.4
npm install runcost@0.2.4
go get github.com/adamallcock/runcost/packages/go/ledger@v0.2.4
```

## Current Support Matrix

| Language | Current install path | Validation |
|---|---|---|
| Python | `python3 -m pip install runcost-ai` or `python3 -m pip install .` from repo root | Fresh virtual environment import smoke test |
| JavaScript/TypeScript | `npm install runcost` or pack/install the local tarball from a checkout | Fresh npm project import smoke test |
| Go | `go get github.com/adamallcock/runcost/packages/go/ledger` | Fresh Go module import smoke test |

## Python

From a cloned checkout:

```bash
python3 -m pip install .
python3 -c "from runcost import from_response; print(from_response)"
runcost --help
```

The Python distribution name is `runcost-ai`, while the import package and CLI
remain `runcost`. The root `pyproject.toml` loads package sources from
`packages/python`.

```bash
python3 -m pip install runcost-ai
```

The installed Python package includes a small `runcost` CLI:

```bash
runcost price-cards --source-type user-pricing --input prices.json
runcost fixture-check fixtures/my-case.json
```

The CLI is intentionally lightweight. It is useful for checking one fixture or
converting one local price source; the repository conformance suite remains the
full multi-language validation gate.

## JavaScript And TypeScript

From a cloned checkout:

```bash
PKG_TGZ=$(npm pack ./packages/javascript/core --silent)
npm install "./$PKG_TGZ"
node --input-type=module -e 'import { fromResponse } from "runcost"; console.log(typeof fromResponse)'
```

The JavaScript package lives in `packages/javascript/core`. It exposes ESM JavaScript and `index.d.ts` TypeScript declarations.

```bash
npm install runcost
```

## Go

From another Go module:

```bash
go get github.com/adamallcock/runcost/packages/go/ledger
```

Import path:

```go
import ledger "github.com/adamallcock/runcost/packages/go/ledger"
```

The Go module path is `github.com/adamallcock/runcost`.

## CI Package Check

Run the clean install smoke test locally:

```bash
npm run check:packages
```

That command creates temporary projects for Python, npm, and Go and verifies that the public package entry points and Python CLI can be used without relying on the repo working directory.

## Release Readiness Checklist

- MIT license and package license metadata are present.
- Guarded registry publish workflow exists for PyPI and npm and has published
  `0.2.4` through the release environment with matching reviewed artifact bytes.
- Go module tags, PyPI publishing, and npm publishing are guarded by the maintainer release process.
- `npm run check:release` verifies package version sync, license metadata, changelog presence, registry README policy, and release workflow guardrails.
- The npm package ships a package-facing README aligned with the root public README.
