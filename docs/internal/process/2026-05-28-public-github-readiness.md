---
title: Public GitHub Readiness
date: 2026-05-28
type: runbook
status: active
---

# Public GitHub Readiness

This repo can be prepared for public release while remaining private. Do not
change visibility until the final review says so.

## Repository Metadata

Configured while private:

- Description: `Small polyglot cost ledger for LLM and agent API calls`
- Homepage: `https://github.com/adamallcock/runcost#readme`
- Topics: `llm`, `ai`, `pricing`, `tokens`, `cost`, `openai`, `anthropic`,
  `agents`
- Issues: enabled
- Wiki: disabled
- Projects: disabled
- Delete head branches after merge: enabled
- Update branch button: enabled
- Squash and rebase merges: enabled

Verify with:

```bash
gh repo view adamallcock/runcost \
  --json description,homepageUrl,isPrivate,repositoryTopics,deleteBranchOnMerge,hasIssuesEnabled,hasWikiEnabled,hasProjectsEnabled
```

## Branch Protection

Branch protection and repository rulesets were blocked while the repository was
private on the current GitHub plan:

```text
Upgrade to GitHub Pro or make this repository public to enable this feature.
```

After the repo is public or protection becomes available, protect `main` with:

- Require pull request before merging.
- Require at least one approval.
- Dismiss stale approvals when new commits are pushed.
- Require status check `test` from workflow `ci`.
- Require branches to be up to date before merging.
- Require conversation resolution before merging.
- Restrict force pushes and deletions.
- Allow administrators to bypass only for emergency release repair.

## Public Community Files

Required files:

- `README.md`
- `LICENSE`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `CODE_OF_CONDUCT.md`
- `SUPPORT.md`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/ISSUE_TEMPLATE/bug_report.yml`
- `.github/ISSUE_TEMPLATE/feature_request.yml`
- `.github/ISSUE_TEMPLATE/price_source_update.yml`
- `.github/CODEOWNERS`
- `.github/dependabot.yml`

## Package Registry Readiness

Do not publish yet.

Name checks on May 28, 2026:

- npm `runcost`: `npm view runcost` returned `E404`, so the package name
  appears available.
- PyPI `runcost-ai`: `python3 -m pip index versions runcost-ai` returned no
  matching distribution, so the package name appears available.
- PyPI `runcost`: already exists, so the Python distribution remains
  `runcost-ai` while the import package and CLI remain `runcost`.

Before publishing:

- Confirm PyPI trusted publishing for `runcost-ai`.
- Confirm npm trusted publishing for `runcost`.
- Run `npm run check:release-dry-run`.
- Review Python wheel/sdist and npm tarball contents.
- Run the release workflow with `publish=false`.
- Publish only with explicit typed approval in the workflow.

## Price Data Readiness

RunCost fixtures are behavioral conformance tests, not a complete model-price
database. Public price data should flow through source adapters and reviewed
source-cache envelopes. See `docs/reference/price-data-strategy.md`.
