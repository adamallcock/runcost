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
- Publish no price-source updates without the owner/cadence/review process in
  `docs/process/2026-05-26-source-data-update-process.md`.

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
npm run check:gates
npm run check:packages
npm run check:release
npm run check:release-dry-run
npm run example:js
npm run example:py
```

4. Confirm the package CLI smoke in `npm run check:packages` covered both
   `runcost price-cards` and `runcost fixture-check`.
5. Confirm `npm run check:gates` passes, then use the stricter completion gate
   checks only when the external evidence is actually available:
   `python3 scripts/check_project_completion_gates.py --require-milestone8`,
   `--require-public-beta`, or `--require-v1`.
6. Confirm source-data updates, if any, followed
   `docs/process/2026-05-26-source-data-update-process.md`.
7. Confirm `git diff --check` is clean.
8. Create and push a semantic version tag, for example `v0.1.0`.
9. Run the manual `release` workflow with publishing disabled first.
10. Review the no-publish artifact review checklist in the workflow summary.
11. Enable publishing only after the dry run artifacts look correct.

`npm run check:release-dry-run` is local and does not publish. It builds the
Python wheel and source distribution, packs the npm package, and verifies the
Go module path through a clean temporary module with a local replace directive.

The manual GitHub `release` workflow is the guarded release rehearsal. Run it
with publishing disabled first. In no-publish mode it builds uploadable Python
and npm artifacts, writes a no-publish artifact review checklist to the workflow
summary, and verifies the real Go tag when `v<version>` already exists on the
remote. If the tag is absent, the workflow explicitly records that real Go tag
verification was skipped for that rehearsal.

GitHub workflow dispatch requires `.github/workflows/release.yml` to exist on
the repository default branch. If the workflow is still only on a feature
branch, `gh workflow run release.yml --ref <branch> ...` can fail with
`workflow release.yml not found on the default branch`. In that case, merge the
workflow to the default branch first, then rerun the no-publish rehearsal.

No-publish artifact review checklist:

- Confirm Python wheel and source distribution are present in workflow artifacts.
- Confirm npm tarball is present in workflow artifacts and includes package
  README.
- Confirm release readiness, dry-run, examples, package checks, and conformance
  tests passed.
- Confirm Go tag verification ran when the real Go tag existed, or was
  explicitly skipped because the tag was absent.
- Confirm the workflow dispatch ran from a workflow file GitHub recognizes on
  the default branch.
- Keep publishing disabled until PyPI/npm trusted publishers are configured and
  artifacts are reviewed.

## Registry README Policy

The root `README.md` is the canonical package overview for GitHub and PyPI.
`pyproject.toml` points PyPI at that root README.

The npm package is published from `packages/javascript/core`, so it carries a
small package-local `README.md` that summarizes the JavaScript entrypoint and
links back to the repository for the full docs. Keep the npm README short; do
not duplicate the full docs tree there.

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

Trusted publisher settings to configure on npm:

- Publisher: GitHub Actions
- Organization or user: `adamallcock`
- Repository: `runcost`
- Workflow filename: `release.yml`
- Environment name: `release`
- Allowed action: `npm publish`

After trusted publishing is verified, restrict token-based publish access where
the registry settings allow it.

## Go Publishing

Go packages are published by pushing semantic version tags. After a tag is
pushed, verify from a clean module:

```bash
go list -m -versions github.com/adamallcock/runcost
go get github.com/adamallcock/runcost/packages/go/ledger@v0.1.0
```

This real Go tag verification must not use a local `replace`. The local dry run
still uses `replace` because unpublished commits are not available through the
Go proxy, but the guarded release workflow verifies the published tag path when
the tag exists.

For a private repository, the guarded workflow configures Git to fetch
`github.com/adamallcock/runcost` with the workflow's read token and sets
`GOPRIVATE=github.com/adamallcock/runcost`. That keeps the verification on the
real semantic version tag while avoiding a local `replace`.

## Rollback

- npm supports deprecating a broken version; do not rely on unpublish.
- PyPI releases generally cannot be replaced safely; publish a new patch
  version.
- Go tags should not be moved after publication. Publish a new tag instead.
