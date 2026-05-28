---
title: Release Workflow 0.1.0 No-Publish Rehearsal
date: 2026-05-26
type: report
status: complete
---

# Release Workflow 0.1.0 No-Publish Rehearsal

RunCost's guarded release workflow was dispatched for the intended beta
rehearsal version `0.1.0` with publishing disabled.

## Workflow Evidence

- Workflow: `release`
- Run: https://github.com/adamallcock/runcost/actions/runs/26467232834
- Event: `workflow_dispatch`
- Ref: `main`
- Head SHA: `9f29e920de34566e267c6d2be6cad36295ea79a3`
- Version input: `0.1.0`
- Publish input: `false`
- Result: `success`
- Verify job: `success`
- Publish job: `skipped`

The verify job completed:

- release readiness checks;
- local release dry-run checks;
- conformance tests;
- clean package install checks;
- examples;
- Python package build;
- npm package pack;
- no-publish artifact checklist;
- release artifact upload.

## Artifact Review

Artifact bundle: `runcost-release-artifacts`.

Downloaded files:

| Artifact | Size | Review |
|---|---:|---|
| `runcost-0.1.0-py3-none-any.whl` | 32802 bytes | Contains `runcost/core.py`, generated taxonomy package, and MIT license metadata. Wheel metadata reports `Name: runcost`, `Version: 0.1.0`, and `License-Expression: MIT`. |
| `runcost-0.1.0.tar.gz` | 34116 bytes | Contains 22 source distribution entries and includes `README.md`. |
| `runcost-0.1.0.tgz` | 25457 bytes | npm tarball contains 5 files, includes `README.md` and `package.json`, and package metadata reports `name: runcost`, `version: 0.1.0`. |

## Go Tag Verification

The workflow checked for remote tag `v0.1.0`. No tag existed, so the real Go
tag verification path was explicitly skipped:

```text
No published tag v0.1.0 found; skipping real Go tag verification for this no-publish rehearsal.
```

This is expected for this no-publish rehearsal and does not satisfy the
separate real Go tag verification gate.

## Publishing

No PyPI or npm publishing occurred. The `publish` job was skipped because the
workflow was dispatched with `publish=false`.

## Result

The real-version no-publish release rehearsal for `0.1.0` is complete and
artifact-reviewed. Remaining release blockers are external trusted publishing
configuration, real Go tag verification, and explicit approval before any
registry publication.
