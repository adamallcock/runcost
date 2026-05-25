---
title: RunCost Package Installation
date: 2026-05-25
type: guide
status: draft
---

# RunCost Package Installation

RunCost is currently validated as a source-installable pre-alpha package. Registry publishing is intentionally not marked done until the first release is cut through the guarded release workflow.

## Current Support Matrix

| Language | Current install path | Validation |
|---|---|---|
| Python | `python3 -m pip install .` from repo root | Fresh virtual environment import smoke test |
| JavaScript/TypeScript | `npm pack ./packages/javascript/core` then install the tarball | Fresh npm project import smoke test |
| Go | `go get github.com/adamallcock/runcost/packages/go/ledger` | Fresh Go module import smoke test with local replace in CI |

## Python

From a cloned checkout:

```bash
python3 -m pip install .
python3 -c "from runcost import from_response; print(from_response)"
```

The Python package is defined by the root `pyproject.toml` and loads package sources from `packages/python`.

## JavaScript And TypeScript

From a cloned checkout:

```bash
npm pack ./packages/javascript/core
npm install ./runcost-0.0.0.tgz
node --input-type=module -e 'import { fromResponse } from "runcost"; console.log(typeof fromResponse)'
```

The JavaScript package lives in `packages/javascript/core`. It exposes ESM JavaScript and `index.d.ts` TypeScript declarations.

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

That command creates temporary projects for Python, npm, and Go and verifies that the public package entry points can be imported without relying on the repo working directory.

## Release Readiness Checklist

- MIT license and package license metadata are present.
- Guarded registry publish workflow exists for PyPI and npm.
- Go module tag policy is documented in `docs/process/release-process.md`.
- `npm run check:release` verifies release docs, package version sync, license metadata, changelog presence, and release workflow guardrails.
- Decide whether the npm package remains in `packages/javascript/core` or moves to a publish-oriented root package.
- Add changelog automation.
- Add package README files if registry pages should differ from the monorepo README.
