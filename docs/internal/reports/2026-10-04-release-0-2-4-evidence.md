---
title: Release 0.2.4 Evidence
date: 2026-10-04
type: report
status: released
---

# Release 0.2.4 Evidence

RunCost `0.2.4` publishes the completed R1-R11 package improvements across
Python, JavaScript/TypeScript, and Go. The user explicitly authorized commit,
push, pull request, merge, and release on October 4, 2026. This report contains
public release facts and controlled test evidence. The
[machine-readable release evidence](2026-10-04-release-0-2-4-evidence.json) records
the same verified revision, artifact digests, registry installs, and site checks.

## Revision and release objects

- Release PR: [#82](https://github.com/adamallcock/runcost/pull/82).
- Squash merge commit: `95b05360f4b3ee4c3c37b5e663137bd43a4f45f2`.
- Immutable tag: `v0.2.4`; annotated object
  `782311887e4864f535f8b3d42f50df88a6ab99f9` peels to that merge commit.
- [GitHub Release](https://github.com/adamallcock/runcost/releases/tag/v0.2.4):
  published `2026-10-04T16:53:15Z`, neither draft nor prerelease.
- [npm runcost@0.2.4](https://www.npmjs.com/package/runcost/v/0.2.4): `latest`.
- [PyPI runcost-ai 0.2.4](https://pypi.org/project/runcost-ai/0.2.4/): latest.
- [Go source tag](https://github.com/adamallcock/runcost/tree/v0.2.4): verified
  from a clean external module in the release workflow without a local replace.

All six [PR CI jobs](https://github.com/adamallcock/runcost/actions/runs/37217344275)
passed: the full suite, Linux Python 3.9/Node 20, Linux Python 3.14/Node 24,
macOS Python 3.12/Node 22, Windows Python 3.12/Node 22, and Windows timezone
fallback. Installed consumers ran in the compatibility jobs. The identical
merged tree also passed [main CI](https://github.com/adamallcock/runcost/actions/runs/37217589207).
The fixture inventory contains 204 shared core fixtures and 45 expansion cases.

GitHub's normal merge required a separate approval. The owner administrator
merge path was used after all CI jobs passed, under the user's explicit merge
instruction; branch protection settings were unchanged.

## Reviewed reproducible artifacts

The [no-publish rehearsal](https://github.com/adamallcock/runcost/actions/runs/37217912134)
passed against `v0.2.4`. Its downloaded artifacts were reviewed before publication.
Both rehearsal and publishing verification built twice from separate archives
with the pinned toolchain and commit-derived `SOURCE_DATE_EPOCH`, requiring
byte-identical artifacts.

| Artifact | SHA-256 |
| --- | --- |
| `runcost_ai-0.2.4-py3-none-any.whl` | `0dd3d2284bb7190bc68ed6602375955a06f911525c2181104a4dadaacaed8b48` |
| `runcost_ai-0.2.4.tar.gz` | `cb7e349769a9e8f941bcd2c1ea622fae61e6311282a1834faa44ac7037268c83` |
| `runcost-0.2.4.tgz` | `69ed87aad81ab172de1810c334c299fce66f2cb80d971454d9ee24e7eab44bd5` |

The wheel contains `runcost/py.typed` and matching MIT/version metadata. The npm
archive contains the browser and Node entrypoints, declarations, package README,
and repository-identical MIT license. The wheel, sdist, and npm tarball exclude
local AGENTS instructions, internal reports, credentials, and bundled provider
pricing data.

The publishing run's complete artifact set, including `SHA256SUMS`, matches the
reviewed rehearsal byte for byte. Downloaded PyPI artifacts, npm tarball, and all
four GitHub release assets also match these exact bytes. No published version or
tag was replaced.

## Publication and processing retry

The [publish run](https://github.com/adamallcock/runcost/actions/runs/37218088387)
used `publish=true` and `publish_approval=publish-runcost`. PyPI OIDC publication
succeeded, and npm accepted the same tarball with signed provenance. npm then
reported that processing could take a few minutes. Attempt 1 stopped after its
one-minute live-availability gate encountered an npm 404; the GitHub Release
was correctly deferred.

Once npm served the version, only the failed job was rerun. Attempt 2 compared
both existing registries against the original downloaded artifacts, skipped
republishing matching immutable versions, passed live parity, and created the
GitHub Release and exact assets. Both jobs now have successful conclusions.
The subsequent maintenance change expands the availability window to a bounded
five minutes while retaining exact hash checks and fail-closed behavior. Focused
execution of the actual workflow code passed a 12-attempt 404 delay followed by
matching artifacts, rejected persistent digest mismatch after 30 requests, and
failed immediately for a non-404 HTTP error.

npm SHA-1: `a21c68cee9e132ff03344a61a8507ea49f767be4`.

npm integrity: `sha512-sOndOdF9bu99Ojne4++qZHy/as1k0sIEf5BB21Tc0cWENuZVRHEoBxQ8/RvEo916WX8ImTYUwGr9BDvPjckgyA==`.

The registry exposes npm publish and SLSA v1 attestations. The decoded SLSA
statement identifies the exact release source commit above.

## Public installation and site checks

Fresh public-registry Python and JavaScript installations passed the repository's
unchanged consumer assertions outside the checkout: runtime exports, caller-owned
prices, missing-price warnings, auto source selection, CLI quote/cache status,
Python positive and negative typing, NodeNext and bundler compilation, and the
browser entrypoint. The installed Python package also passed the offline
integration/reconciliation recipe with explicitly controlled synthetic evidence.
Both installed versions are `0.2.4`.

Public Go mirror/checksum installation now passes from a fresh external module
using the default `https://proxy.golang.org,direct` and `sum.golang.org`, with
no private-module exclusions and no local replace. All registered Go public
symbols compile and the installed pricing test passes. Its origin hash is the
exact release commit; module checksum is `h1:kGIke870zFD5Ir5HwMSVY/mmIZxvXYQrQXsW8fl4wGQ=` and go.mod checksum is
`h1:Pz7KMxEcpDSXKk8XqLsjmMlMitxniH+Fma2Ve4/HQT8=`. The earlier negative lookup subsequently cleared. The
[Go module service FAQ](https://proxy.golang.org/) documents possible cache delays;
the precise history behind the initial negative response was not established.

[Pages deployment](https://github.com/adamallcock/runcost/actions/runs/37217589314)
from the exact release commit passed. Cache-busted live checks with a Twitterbot
user agent verified all eight routes: HTTP 200, canonical and Open Graph URLs,
Twitter large-image metadata, and crawler access. The shared image is HTTP 200,
`image/png`, 1200x630; robots allows crawling and the sitemap names all routes.

Rendered desktop and 500px mobile QA verified the OpenAI example total
`0.0020712`, separate cached input, visible alias/provenance evidence, and the
retrieval notice. Negative input returned zero with `invalid_usage`. Mobile
content width equals viewport width; no warning/error console messages were
captured. Batch failures remain visible alongside successful items.

## Remaining evidence boundaries

This release remains public beta. The generated V1 stabilization caveat remains
open. Conformance, controlled integration, artifact parity, and successful
installation do not establish independent customer adoption or invoice accuracy
for every provider workflow. Unsupported source units remain explicit warnings;
DeepSeek automatic period selection fails closed for unrepresented holiday
rules, with caller-confirmed periods available.

The earlier [local implementation report](2026-10-04-package-improvements-implementation.md)
and its candidate hashes remain historical evidence collected before the version
bump; they do not identify the published artifacts.
