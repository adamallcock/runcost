---
title: RunCost Security Policy
date: 2026-05-25
type: policy
status: draft
---

# RunCost Security Policy

RunCost is a local library. Core calculation must not make network requests,
read credentials, or send provider responses to external services.

## Reporting Security Issues

Use GitHub private vulnerability reporting when it is enabled for the
repository. If it is not enabled, open a minimal GitHub issue that says a
private security report is needed, without including exploit details or private
data.

Repository: <https://github.com/adamallcock/runcost>

## Sensitive Data

Provider responses can contain prompts, user data, tool arguments, metadata,
and IDs. Do not include private responses in public issues, fixtures, docs, or
logs. Reduce fixtures to the minimal usage and metadata fields needed to prove
pricing behavior.

## Supply Chain

- PyPI and npm publishing should use trusted publishing through OIDC instead of
  long-lived registry tokens.
- npm releases should publish provenance.
- Release workflows should run the full conformance, package, and release
  readiness checks before publishing.
- Go releases are published by signed or protected semantic version tags.

## Supported Versions

RunCost is pre-alpha. Until the first public release, security fixes apply to
the default branch and the latest published pre-release only.
