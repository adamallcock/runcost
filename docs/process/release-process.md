---
title: RunCost Release Process
date: 2026-05-25
type: runbook
status: draft
---

# RunCost Release Process

RunCost publishes one coordinated release train across Python,
JavaScript/TypeScript, and Go. The package versions should move together.

## Release Principles

- Release only from a clean commit on `main`.
- Run the same conformance fixtures across all supported languages.
- Keep schemas, docs, changelog, and package versions in sync.
- Prefer trusted publishing and short-lived OIDC identity over stored registry
  tokens.
- Publish no price-source updates without review.

## Version Policy

Use semantic versioning:

- `0.x.y`: pre-1.0 releases; breaking changes are allowed but must be called out.
- `x.y.z`: stable releases after V1; breaking changes require a major version.
- Python and npm package versions must match the root workspace version.
- Go uses repository tags like `v0.1.0`.

The Go module is at the repository root, so normal tags such as `v0.1.0` are
the release mechanism. Do not use subdirectory tags for the current layout.

## Pre-Release Checklist

1. Update `package.json`, `pyproject.toml`, and
   `packages/javascript/core/package.json` to the same version.
2. Update `CHANGELOG.md`.
3. Run:

```bash
npm test
npm run check:coverage
npm run check:packages
npm run check:release
npm run check:release-dry-run
npm run example:js
npm run example:py
```

4. Confirm `git diff --check` is clean.
5. Create and push a semantic version tag, for example `v0.1.0`.
6. Run the manual `release` workflow with publishing disabled first.
7. Enable publishing only after the dry run artifacts look correct.

`npm run check:release-dry-run` is local and does not publish. It builds the
Python wheel and source distribution, packs the npm package, and verifies the
Go module path through a clean temporary module with a local replace directive.

## PyPI Publishing

Configure PyPI trusted publishing for:

- Repository: `adamallcock/runcost`
- Workflow: `.github/workflows/release.yml`
- Environment: `release`

The release workflow uses PyPI OIDC trusted publishing and should not need a
stored PyPI API token.

## npm Publishing

Configure npm trusted publishing for the `runcost` package and the GitHub
Actions workflow. npm provenance should be published with releases.

The JavaScript package is in `packages/javascript/core`, so the workflow runs
publish commands from that directory.

## Go Publishing

Go packages are published by pushing semantic version tags. After a tag is
pushed, verify from a clean module:

```bash
go list -m -versions github.com/adamallcock/runcost
go get github.com/adamallcock/runcost/packages/go/ledger@v0.1.0
```

## Rollback

- npm supports deprecating a broken version; do not rely on unpublish.
- PyPI releases generally cannot be replaced safely; publish a new patch
  version.
- Go tags should not be moved after publication. Publish a new tag instead.
