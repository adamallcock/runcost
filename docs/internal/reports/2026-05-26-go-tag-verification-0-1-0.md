---
title: Go Tag Verification 0.1.0
date: 2026-05-26
type: report
status: complete
---

# Go Tag Verification 0.1.0

RunCost's real Go module tag verification was completed for tag `v0.1.0`
without a local `replace`.

## Tag Evidence

- Tag: `v0.1.0`
- Repository: `github.com/adamallcock/runcost`
- Tag pushed to remote: yes
- Verification mode: clean temporary Go module in GitHub Actions
- Local replace directive: not used

## Initial Finding

Run `https://github.com/adamallcock/runcost/actions/runs/26467505077` proved
that the tag existed, but failed because the private repository could not be
fetched anonymously through `go get`:

```text
fatal: could not read Username for 'https://github.com': terminal prompts disabled
```

Product-truth classification: release workflow fix. The guarded release
workflow now configures authenticated private-module fetching with the workflow
read token and `GOPRIVATE=github.com/adamallcock/runcost`.

## Successful Verification

Run `https://github.com/adamallcock/runcost/actions/runs/26467656634` completed
with `publish=false`. The `Verify Go module from published tag` step succeeded.

Evidence from the workflow log:

```text
github.com/adamallcock/runcost v0.1.0
go: downloading github.com/adamallcock/runcost v0.1.0
go: added github.com/adamallcock/runcost v0.1.0
ok  	runcost-release-tag-check	0.002s
```

The same workflow also built the no-publish Python and npm artifacts and kept
the `publish` job skipped.

## Result

The real Go module tag verification gate is satisfied for `v0.1.0`. PyPI and
npm publishing remain disabled and still require separate trusted-publisher
setup plus explicit approval.
