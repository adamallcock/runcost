---
title: Release 0.2.1 Evidence
date: 2026-07-30
type: report
status: evidence
---

# Release 0.2.1 Evidence

This report records sanitized release evidence for RunCost `0.2.1`. The release
adds attempt-level Anthropic fallback attribution, time-based GPT-5.6 Terra and
Luna pricing, and independent OpenAI Fast and Priority service tiers with an
auditable one-way Fast-to-Priority compatibility fallback.

## Release Objects

- Pull request: [#68](https://github.com/adamallcock/runcost/pull/68), merged
  after all three required CI jobs passed.
- Release commit: `50ab8a2ba3e5ee0cf30a0961281eec53684792fa`.
- Annotated tag object: `5f77c9e7431faff14be68ade9ccfeca413bd721e`.
  - The `v0.2.1` tag peels to the release commit above.
- GitHub Release: `v0.2.1`, published at `2026-07-31T01:41:09Z`.
  - <https://github.com/adamallcock/runcost/releases/tag/v0.2.1>
- No-publish rehearsal workflow run: `30596802459`, completed successfully.
  - <https://github.com/adamallcock/runcost/actions/runs/30596802459>
- Approved publish workflow run: `30596879567`, completed successfully.
  - <https://github.com/adamallcock/runcost/actions/runs/30596879567>

Both workflow runs checked out `v0.2.1`. The rehearsal completed the full
release-readiness suite, built all artifacts, verified the real Go tag, uploaded
the artifact bundle, and skipped publishing. The second run repeated
verification and published Python and npm through the `release` environment
using OIDC-backed trusted publishing.

## Rehearsal Artifacts

The artifact bundle from rehearsal run `30596802459` was downloaded and
inspected before publishing.

| Artifact | SHA-256 |
|---|---|
| `runcost_ai-0.2.1-py3-none-any.whl` | `11e8a15f5941fe2a9a81019b6875518a4eed4e44728ffc9561234cd88c8162f7` |
| `runcost_ai-0.2.1.tar.gz` | `4b5417de9cc0cead7b12756de0db5442828084fa24d608c37476c58193cfd096` |
| `runcost-0.2.1.tgz` | `27241cc6231532755e92c2b6d49c383f08eb1dace6654677071d3c306c5ffbe1` |

Wheel metadata identified `runcost-ai` version `0.2.1` with the MIT license.
The source distribution contained its `pyproject.toml` and README. The npm
tarball identified `runcost` version `0.2.1` and contained only its intended
JavaScript/browser entrypoints, CLI, declarations, taxonomy, package metadata,
and package README.

## Registry State

Verified on July 30, 2026 local time, after the workflow completed on July 31
UTC:

```bash
gh release view v0.2.1 --json tagName,name,publishedAt,isDraft,isPrerelease,url,targetCommitish
npm view runcost@0.2.1 version dist-tags dist.integrity dist.shasum --json
curl -fsSL https://pypi.org/pypi/runcost-ai/0.2.1/json
go list -m -json github.com/adamallcock/runcost@v0.2.1
curl -fsSL https://registry.npmjs.org/-/npm/v1/attestations/runcost@0.2.1
```

| Surface | Verified result |
|---|---|
| GitHub Release | `v0.2.1`, not draft, not prerelease |
| npm | `runcost@0.2.1` is the `latest` dist-tag |
| npm integrity | `sha512-+t34HDxIxdZcQ7PYACx/DNlMpYKOVu0/svwCtpPC1fpV1Nkyb0xhSwm1gkRVTeKlHpm/pB2W2kPnssspCCzHlA==` |
| npm shasum | `6b97b5aa494db70e8ef1d7b2d5dcd7c7a993adc2` |
| npm provenance | Two attestations are present: npm publish and SLSA provenance |
| PyPI wheel SHA-256 | `d4786126259faa038b70c5426159cb56ea0602a2338567e1d5f2007b76e05506` |
| PyPI sdist SHA-256 | `4c9ef602c41501c1db745c1b2634267cf560627f05cee4c319f80ce1df629219` |
| Go | `github.com/adamallcock/runcost@v0.2.1` resolves to release commit `50ab8a2ba3e5ee0cf30a0961281eec53684792fa` through the public module path |

## Post-Publish Install Smoke

Fresh temporary projects installed the public Python, npm, and Go releases
without local path replacement.

- Python installed `runcost-ai==0.2.1` with `--no-cache-dir`, selected an exact
  Fast card ahead of a Priority card, then selected Priority when it was the
  only compatible card and emitted `service_tier_resolution.fallback: true`.
- npm installed `runcost@0.2.1` with scripts disabled and selected the exact
  Fast card in the equivalent calculation.
- Go downloaded `github.com/adamallcock/runcost v0.2.1` and resolved
  `github.com/adamallcock/runcost/packages/go/ledger` without a local
  `replace` directive.

The release train is therefore live and mutually consistent across GitHub,
npm, PyPI, and Go. No credentials, account identifiers, private payloads, or
raw provider responses are retained in this report.
