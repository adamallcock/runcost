---
title: External Pricing Source Resolution
date: 2026-07-18
type: decision-record
status: accepted
---

# External Pricing Source Resolution

## Decision

RunCost will not publish or silently select a broad RunCost-maintained model
price database. The deterministic calculation core consumes explicit canonical
price cards. A separate convenience resolver obtains price data from named,
more frequently maintained upstream sources, stores a checksummed local cache,
and passes one selected source's cards into the core.

This supersedes the expansion branch's earlier decision to make the existing
optional package catalog the implicit default. It also restores the original
product boundary: RunCost owns normalization, selection, accounting, warnings,
and reconciliation; upstream projects own public price maintenance.

## Default Source Profile

The normal cross-provider profile is deterministic:

1. caller-supplied contract or user price cards;
2. Pydantic `genai-prices`;
3. models.dev;
4. LiteLLM.

For an OpenRouter-billed response, the OpenRouter models API is tried before
the general profile. OpenRouter prices are never used as a silent substitute
for a direct provider's prices.

The resolver selects one source for a calculation. It does not silently combine
input pricing from one catalog with output or tool pricing from another. A
secondary source is tried only when the higher-priority source cannot produce a
usable card for the requested provider, surface, model, date, and service mode.

## Runtime Boundary

- `calculate_cost` / `calculateCost` / `CalculateCost` remain synchronous,
  deterministic, and network-free.
- Existing response, batch, telemetry, and estimate functions remain
  deterministic when explicit cards are supplied and no longer load package
  price data implicitly.
- New auto-resolving convenience functions may perform a public catalog GET,
  but never transmit a provider response, prompt, identifier, credential, or
  usage payload.
- CLIs use the auto resolver by default and expose explicit source, cache,
  refresh, and offline controls.
- Browser and edge use an in-memory source cache. Node, Python, and Go use a
  persistent operating-system cache unless the caller supplies another path.

## Cache Contract

Each source cache is a RunCost source-cache envelope containing:

- the canonical upstream URL and source adapter;
- retrieval and generation timestamps;
- raw-source SHA-256 checksum;
- optional HTTP `ETag` and `Last-Modified` validators;
- the normalized canonical price cards;
- source status and card count in resolution metadata.

The default freshness window is 24 hours. A fresh cache avoids the network. A
stale cache is conditionally refreshed. If refresh fails, the last known good
cache may be used with a structured warning. Offline mode never performs a
network request and fails visibly when no cached source is available.

Writes are atomic. A malformed or partially written cache is rejected rather
than treated as an empty catalog.

## Public API Shape

Each language exposes equivalent concepts:

- default external source definitions;
- default cache-directory resolution;
- catalog resolution with source/cache/offline options;
- auto-resolving response, batch, telemetry, and estimate helpers;
- explicit refresh through the CLI;
- the existing source adapters and compiled catalog.

Resolution returns price cards plus attempted-source metadata and operational
warnings. The selected cards retain their upstream source URL, retrieval time,
version when available, and checksum metadata so the resulting cost ledger is
auditable.

## Package And Repository Boundary

- Remove the full default source-cache JSON from Python, npm, and Go packages.
- Remove packaged provider shards whose only purpose is redistributing the
  broad database.
- Retain generic compilation, indexing, sharding, manifest, and verification
  tools for caller-owned or site-build caches.
- Retain small price fixtures and targeted official snapshots only as
  conformance evidence, not as an implicit production catalog.
- Let the public playground use the browser resolver, with a small, visibly
  labelled dated demo card per showcased provider as its offline fallback.

## Failure Semantics

- No matching upstream card: normal `price_not_found` or component warnings.
- All requested sources unavailable with no cache:
  `price_source_unavailable`.
- Refresh fails but a last known good cache is used:
  `price_source_refresh_failed`, with no credential or response data in warning
  metadata.
- Stale cache use remains visible through source timestamps and `price_stale`
  when the configured accounting staleness threshold is crossed.

## Migration

The prepared `0.2.0` release is not yet published, so it can remove the implicit
catalog path before users adopt it. Existing `default_*` catalog loaders are
removed from the new public surface. Users who depended on the previously
published optional catalog should migrate to an explicit source cache or the
auto resolver. The changelog and release notes must call this out directly.
