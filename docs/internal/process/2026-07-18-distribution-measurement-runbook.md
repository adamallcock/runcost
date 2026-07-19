---
title: RunCost Distribution Measurement Runbook
date: 2026-07-18
type: runbook
status: active
---

# RunCost Distribution Measurement Runbook

## Objective

Measure whether RunCost reaches and helps independent developers. Registry
downloads, clones, crawler requests, and CI mirrors are context—not proof of
adoption.

## Primary outcomes

Track these monthly:

1. independent repositories or products with a verified RunCost integration;
2. accepted external fixtures or billing cases from people outside the project;
3. sanitized reconciliations against a provider export/dashboard;
4. repeat human use of the playground or documentation;
5. issue/discussion threads that reach a reproduced outcome.

## Funnel

| Stage | Metric | Evidence source | Guardrail |
| --- | --- | --- | --- |
| Discovery | Search impressions and unique landing-page visits | Search Console and privacy-preserving page analytics | Exclude known bots where possible |
| Activation | Playground fixture/provider changes, quickstart completion, CLI example success | Optional aggregate events or user confirmation | Never collect pasted response data |
| Integration | Public dependency/use, linked project, or maintainer-confirmed private integration | Repository search, issue, case study | Do not infer from installs alone |
| Evidence | External fixture or reconciliation accepted | Git history and review artifact | Must pass redaction checklist |
| Retention | Repeat documentation/playground visits or follow-up contribution | Aggregate analytics and issue history | Report cohorts, not identities |

## Instrumentation boundary

The playground is fully useful without analytics. If analytics are added later,
collect only route views and coarse UI events such as provider-tab selection or
successful local calculation. Never collect response JSON, prompts, outputs,
model payloads, request IDs, attribution fields, errors containing pasted text,
IP-derived identity, or credentials. Document the provider and retention period
before enabling any event.

## Monthly procedure

1. Record the date range and deployed/package versions.
2. Export GitHub traffic, registry counts, Search Console, and page analytics.
3. Search public code for exact package/import/API names.
4. Review issues, discussions, external fixtures, and reconciliation reports.
5. Separate known humans/integrations from bots, mirrors, and unknown traffic.
6. Write a short dated report with counts, evidence links, uncertainty, and the
   next distribution experiment.

## Experiments

Run one at a time for at least two weeks unless evidence is decisive:

- exact-problem page and playground launch;
- one framework/community integration contribution;
- a public sanitized reconciliation case;
- a conformance fixture call for broken cost cases;
- registry description/keyword refresh.

Define the expected primary outcome before publishing. Stop an experiment that
only moves downloads or clone noise without producing qualified activation.

## Reporting template

- Period and versions:
- Verified integrations:
- External fixtures/reconciliations:
- Human discovery/activation signals:
- Registry/clone context:
- Uncertainty and exclusions:
- Experiment verdict: stop / continue / change
- Next action and owner:
