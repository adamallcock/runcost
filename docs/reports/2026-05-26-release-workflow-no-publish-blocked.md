---
title: Release Workflow No-Publish Rehearsal Blocked
date: 2026-05-26
type: report
status: blocked
---

# Release Workflow No-Publish Rehearsal Blocked

Attempted command:

```bash
gh workflow run release.yml --ref package-doc-readiness -f version=0.0.0 -f publish=false
```

Result:

```text
HTTP 404: workflow release.yml not found on the default branch
```

Interpretation:

- The guarded `release` workflow exists on the current feature branch.
- GitHub Actions workflow dispatch requires the workflow file to exist on the
  repository default branch before it can be triggered this way.
- The no-publish release rehearsal cannot be completed from this branch until
  the workflow has landed on the default branch, or until a maintainer triggers
  an equivalent rehearsal from a branch where GitHub recognizes the workflow.

Product-truth classification:

| Finding | Classification | Required outcome |
|---|---|---|
| No-publish workflow dispatch rejected because `release.yml` is not on default branch | documented limitation | Merge the release workflow to the default branch, then rerun with `publish=false`. |

This does not publish anything. The first real no-publish release rehearsal
remains incomplete.
