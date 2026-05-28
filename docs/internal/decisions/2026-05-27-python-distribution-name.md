---
title: Python Distribution Name
date: 2026-05-27
type: decision-record
status: accepted
---

# Python Distribution Name

## Decision

Use `runcost-ai` as the PyPI distribution name for the Python package, while
keeping the import package and CLI stable:

- install distribution: `runcost-ai`
- import package: `runcost`
- command-line executable: `runcost`

The npm package remains `runcost`.

## Evidence

Registry checks on 2026-05-27 showed:

```bash
npm view runcost name version repository.url --json
npm view runcost-ai name version repository.url --json
python3 -m pip index versions runcost
python3 -m pip index versions runcost-ai
```

Results:

- npm `runcost`: `E404 Not Found`, so the JavaScript package name can proceed
  if registry-side ownership and trusted publishing are configured.
- npm `runcost-ai`: `E404 Not Found`, but not used for the JavaScript package.
- PyPI `runcost`: occupied, with versions through `0.4`.
- PyPI `runcost-ai`: no matching distribution found.

## Rationale

The project brand and cross-language package name should stay `RunCost`.
However, publishing to the occupied PyPI `runcost` project would require
ownership transfer or maintainer access. Using `runcost-ai` avoids delaying
public beta on a registry-ownership dependency while preserving the developer
experience that matters most in code: `from runcost import ...`.

## Release Impact

Trusted publishing should be configured for PyPI project `runcost-ai` and npm
package `runcost`.

Python artifacts use normalized distribution filenames such as
`runcost_ai-0.1.0-py3-none-any.whl`, while the installed import package remains
`runcost`.

Do not publish until trusted publishing is manually verified and the guarded
release workflow is dispatched with explicit publish approval.
