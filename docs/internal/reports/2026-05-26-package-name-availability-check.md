---
title: Package Name Availability Check
date: 2026-05-26
type: report
status: draft
---

# Package Name Availability Check

Purpose: record registry-name availability before any trusted-publishing setup
or release workflow is allowed to publish.

## Checks

Checked on 2026-05-26 and refreshed on 2026-05-27:

```bash
npm view runcost name version repository.url --json
npm view runcost-ai name version repository.url --json
python3 -m pip index versions runcost
python3 -m pip index versions runcost-ai
```

## Result

| Registry | Name | Result | Evidence |
|---|---|---|---|
| npm | `runcost` | Available or not publicly visible | `npm view` returned `E404 Not Found` for `https://registry.npmjs.org/runcost` on 2026-05-26 and 2026-05-27. |
| npm | `runcost-ai` | Available or not publicly visible | `npm view` returned `E404 Not Found` for `https://registry.npmjs.org/runcost-ai` on 2026-05-27. Not selected for npm. |
| PyPI | `runcost` | Occupied | `pip index versions runcost` returned existing versions through `0.4` on 2026-05-26 and 2026-05-27. |
| PyPI | `runcost-ai` | Available or not publicly visible | `pip index versions runcost-ai` returned `No matching distribution found` on 2026-05-27. Selected for Python distribution. |

## Release Impact

The current JavaScript package name can proceed to npm trusted-publishing setup
if registry-side ownership and organization settings are configured.

The Python distribution-name decision is recorded in
`docs/internal/decisions/2026-05-27-python-distribution-name.md`.

Use:

- PyPI distribution: `runcost-ai`
- Python import package: `runcost`
- Python CLI: `runcost`
- npm package: `runcost`

Before public beta publication:

- configure PyPI trusted publishing for project `runcost-ai`;
- configure npm trusted publishing for package `runcost`;
- verify both registry-side settings with a sanitized trusted-publishing
  verification artifact.

Do not run `publish=true` until registry-side trusted publishing is verified
and explicit publication approval is given.
