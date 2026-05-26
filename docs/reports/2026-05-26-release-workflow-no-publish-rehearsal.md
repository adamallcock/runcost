---
title: Release Workflow No-Publish Rehearsal
date: 2026-05-26
type: report
status: complete
---

# Release Workflow No-Publish Rehearsal

RunCost's guarded release workflow was dispatched from `main` after
`.github/workflows/release.yml` landed on the default branch.

Command:

```bash
gh workflow run release.yml --ref main -f version=0.0.0 -f publish=false
```

Result:

- Workflow run: `https://github.com/adamallcock/runcost/actions/runs/26430180080`
- Head SHA: `13ccb8e953056d2e4c9bd718bd5eef2277776c83`
- Conclusion: success
- Publishing: disabled
- Artifact: `runcost-release-artifacts`
- Artifact URL:
  `https://github.com/adamallcock/runcost/actions/runs/26430180080/artifacts/7208232301`

Artifacts downloaded and reviewed locally:

| Artifact | SHA-256 |
|---|---|
| `runcost-0.0.0-py3-none-any.whl` | `5e9d469e2f68b28787dc753cb8eb39680fcc7e8ceac7f074ff1840c71aeb0a83` |
| `runcost-0.0.0.tar.gz` | `58a5001f903a7b0130abbbbd71122e33431a476fe6001b8f75311bc95d5291e2` |
| `runcost-0.0.0.tgz` | `4a83890c7aa7c0f80a95ec198f061d7bd5b83531c04467e948ea4feb5ffefa6c` |

Artifact shape review:

- Python wheel contains the expected `runcost` package files,
  `dist-info/METADATA`, license metadata, and CLI entry point metadata.
- Python source distribution contains `LICENSE`, `README.md`, `pyproject.toml`,
  and the `packages/python/runcost` source tree.
- npm tarball contains `index.js`, `index.d.ts`, `README.md`, and
  `package.json`.
- Workflow release readiness, package checks, conformance checks, Python build,
  npm pack, and artifact upload all passed.

Go tag verification note:

- The workflow checked whether remote tag `v0.0.0` existed.
- No such tag existed, so the real Go tag import verification was explicitly
  skipped for this no-publish rehearsal.
- This is expected for the unpublished rehearsal. A real semantic version tag
  still needs to be created and verified before registry publication is called
  complete.

Warnings observed:

- GitHub Actions emitted a platform warning that several `actions/*@v4/v5`
  actions currently run on Node.js 20, which GitHub has scheduled for removal.
  This did not fail the rehearsal but should be tracked before a production
  release if newer action versions or Node 24 migration guidance is available.
  Follow-up: CI and release workflows now set
  `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` to opt into the upcoming runner
  behavior early.
- `actions/setup-go` warned that no `go.sum` file exists for cache restore.
  This did not fail the rehearsal and is expected while the Go package has no
  external module dependencies. Follow-up: CI and release workflows now disable
  Go module caching for this dependency-free module.

Remaining release gates:

- Configure PyPI trusted publishing externally.
- Configure npm trusted publishing externally.
- Run the guarded workflow against a real release version with `publish=false`.
- Review those real-version artifacts.
- Create/push the real semantic version tag and verify Go import from that tag.
- Keep `publish=true` disabled until the registry trust setup and artifact
  review are complete.
