---
title: Alpha Smoke Runbook
date: 2026-05-26
type: runbook
status: draft
---

# Alpha Smoke Runbook

RunCost alpha smoke runs are optional, API-key-gated checks that prove an
installed package can sit beside real provider or framework calls and emit a
useful sanitized cost ledger.

Normal CI must never require provider credentials. Use the deterministic sample
mode in CI and before live runs:

```bash
npm run smoke:alpha -- --mode sample --output /tmp/runcost-alpha-smoke.json --allow-sample-prices
node scripts/run_vercel_alpha_smoke.mjs --mode sample --output /tmp/runcost-vercel-smoke.json --allow-sample-prices
python3 scripts/run_langchain_alpha_smoke.py --mode sample --output /tmp/runcost-langchain-smoke.json --allow-sample-prices
python3 scripts/check_alpha_smoke.py
```

Sample mode uses checked-in sanitized response shapes from
`fixtures/source-files/alpha-smoke-samples.json`.
Alpha smoke and preflight evidence follow the generated contract documented
from `schemas/alpha-smoke-report.schema.json`; validate that contract with:

```bash
npm run check:alpha-contract
```

The schema has mode-specific rules: aggregate sample/live smoke reports use the
smoke summary counters, single framework reports require `scenario`, `status`,
`sample_prices`, `evidence`, and `next_action`, and preflight reports require
readiness scenarios, preflight summary counters, `live_ready`, and sanitized
next actions.

The aggregate Python smoke runner, the LangChain smoke runner, and the Vercel
smoke runner validate their sanitized report shape before writing output. A
future live script edit that adds a forbidden key, secret-like value, raw
response, or invalid evidence shape should fail closed before producing an
attachable artifact.

When the aggregate runner invokes optional framework smoke scripts, child
process failures are converted into sanitized `needs_product_truth` results.
The aggregate report records the scenario and error type only, not child stdout,
stderr, raw provider bodies, or request data.

Before a live run, check credential and optional dependency readiness without
printing secret values:

```bash
npm run smoke:alpha:preflight
npm run smoke:alpha:preflight -- --output /tmp/runcost-alpha-smoke-preflight.json
npm run smoke:alpha:preflight -- --require-ready
```

The preflight reports scenario readiness, missing environment variable names,
missing command-input names, missing optional package names, and a sanitized
next action for each scenario. It never prints API-key values or local file
paths.

For the OpenAI Costs invoice/dashboard comparison path, include the intended
comparison input names when checking readiness:

```bash
npm run smoke:alpha:preflight -- \
  --openai-costs-start-time 1741476542 \
  --openai-costs-runcost-ledger /tmp/runcost-ledger.json
```

The report records only that `openai_costs_start_time` and
`openai_costs_runcost_ledger` were present, not the timestamp or ledger path.

## Live Runs

Live mode is explicit and still uses sample price cards. That means the output
validates extraction, ledger shape, warnings, and integration ergonomics, but it
is not invoice-exact unless a later comparison uses the provider's actual
pricing and billing export.
Every smoke report must include `sample_prices: true` so sample-price evidence
cannot be mistaken for invoice-exact billing evidence.

```bash
OPENAI_API_KEY=... \
ANTHROPIC_API_KEY=... \
OPENROUTER_API_KEY=... \
npm run smoke:alpha -- --mode live --output /tmp/runcost-alpha-smoke-live.json --allow-sample-prices
```

Limit a run to one scenario:

```bash
npm run smoke:alpha -- --mode live --scenarios openai_responses --output /tmp/openai-smoke.json --allow-sample-prices
```

Current live-capable Python scenarios:

| Scenario | Gate | Purpose |
|---|---|---|
| `openai_responses` | `OPENAI_API_KEY` | Calls the OpenAI Responses API and verifies RunCost can extract sanitized usage evidence. |
| `anthropic_prompt_caching` | `ANTHROPIC_API_KEY` | Calls Anthropic Messages with cache control and verifies cache usage fields when present. |
| `openrouter_cost_compare` | `OPENROUTER_API_KEY` | Calls OpenRouter chat completions and verifies provider-reported usage/cost comparison shape when present. Defaults to `nvidia/nemotron-3-super-120b-a12b:free` unless `RUNCOST_SMOKE_OPENROUTER_MODEL` is set. |
| `multi_provider_discount` | none | Runs a local multi-provider discount ledger using the same sanitized report shape. |
| `openai_costs_invoice_comparison` | `OPENAI_ADMIN_KEY` plus `openai_costs_start_time` and `openai_costs_runcost_ledger` input names | Checks readiness for a sanitized OpenAI Costs API comparison against a supplied RunCost ledger. |

When live mode runs the full scenario set, `multi_provider_discount` must stay
in the same reviewed report as any passed live provider or framework scenario.
`scripts/check_alpha_product_truth.py` enforces this so discount behavior is
reviewed beside real provider evidence rather than only in isolated samples.

Framework live smoke scripts are separate so optional dependencies do not become
core package dependencies:

```bash
OPENAI_API_KEY=... \
node scripts/run_vercel_alpha_smoke.mjs --mode live --output /tmp/runcost-vercel-live.json --allow-sample-prices

OPENAI_API_KEY=... \
python3 scripts/run_langchain_alpha_smoke.py --mode live --output /tmp/runcost-langchain-live.json --allow-sample-prices
```

The Vercel and LangChain scripts can use either `OPENAI_API_KEY` for direct
OpenAI calls or `OPENROUTER_API_KEY` for OpenRouter-compatible routing. The
OpenRouter framework default is `nvidia/nemotron-3-super-120b-a12b:free` unless
`RUNCOST_SMOKE_OPENROUTER_MODEL` is set.

The Vercel script requires optional packages `ai` and `@ai-sdk/openai` in the
current Node environment. The LangChain script requires optional packages
`langchain-openai` and `langchain-core` in the current Python environment. These
can be installed for local smoke work with:

```bash
npm install
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install '.[smoke]'
```

If credentials or optional packages are missing, the scripts emit sanitized
skipped reports instead of failing normal validation.

## Safety Rules

Smoke output may be attached to issues only if all of these remain true:

- no API keys, headers, organization IDs, account IDs, prompts, messages,
  response content, raw provider responses, or request bodies are written;
- output contains only provider, surface, model identifiers, usage field names,
  component names, warning codes, totals, price-source names, and next-action
  classification;
- failures are reported by sanitized error type, not by raw provider body;
- smoke scripts validate the sanitized report contract before writing output;
- framework child-script failures become sanitized `needs_product_truth`
  findings rather than raw aggregate-runner crashes;
- every live discrepancy is classified as a fixture, structured warning,
  documented limitation, or extractor/source-adapter fix.

## Product Truth Loop

Every non-passing live result must become one of:

| Next action | When to use |
|---|---|
| Fixture | The provider returned a supported shape that was missing from the suite. |
| Structured warning | RunCost can detect a condition but cannot price it safely. |
| Documented limitation | The behavior is intentionally out of scope or depends on unavailable billing data. |
| Extractor/source fix | RunCost should already support the shape and failed to do so. |

Do not leave live smoke findings only in a terminal log. Add the fixture,
warning, limitation, or fix in the same branch when practical.

The machine-readable product-truth register lives at
`fixtures/source-files/alpha-smoke-product-truth-register.json`. It ties each
known live smoke outcome to the artifact that resolved it. Validate the current
no-credential live path or a specific live report with:

```bash
npm run check:alpha-truth
python3 scripts/check_alpha_product_truth.py --smoke-report /tmp/runcost-alpha-smoke-live.json
```

The register follows the generated contract documented from
`schemas/alpha-smoke-product-truth-register.schema.json`.

For a non-passing credentialed live finding, add or update one register entry
with the scenario, status, next-action type, classification, artifact path, and
resolution. The artifact must be one of the product-truth outcomes above: a
fixture, structured warning, documented limitation, extractor/source-adapter
fix, or price-source update.

Use the entry helper to build the register JSON from the sanitized smoke report
instead of hand-authoring fields:

```bash
npm run alpha:truth-entry -- \
  --smoke-report /tmp/runcost-alpha-smoke-live.json \
  --scenario openai_responses \
  --status needs_product_truth \
  --classification extractor_source_fix \
  --artifact packages/python/runcost/core.py \
  --resolution "The live response exposed a supported usage field that the extractor now maps."
```

The helper validates the smoke-report contract, copies the scenario status and
next-action type from the sanitized report, infers `artifact_kind` when it can,
and prints one register entry to stdout by default. To update the checked-in
register intentionally, add `--write-register`; use `--replace-existing` only
when revising an existing scenario/status entry.

Non-passing register entries cannot use `classification: none`. Passed entries
must use `classification: none` and `next_action_type: none`. The checker also
verifies that `classification` and `artifact_kind` agree, for example
documented limitations must point at docs or reports, extractor/source fixes at
code, and price-source updates at source data.

## Evidence Bundle Gate

Use the collector when you want one command to create the reviewed evidence
directory shape:

```bash
npm run alpha:bundle -- \
  --mode sample \
  --output-dir /tmp/runcost-alpha-evidence-bundle \
  --allow-sample-prices
```

For a live review, pass `--mode live` and provide a real sanitized
invoice/dashboard comparison with `--invoice-comparison`. Add `--require-real`
only when the bundle is expected to close Milestone 8:

```bash
npm run alpha:bundle -- \
  --mode live \
  --output-dir /tmp/runcost-alpha-evidence-bundle-live \
  --allow-sample-prices \
  --invoice-comparison /tmp/runcost-real-invoice-comparison.json \
  --require-real
```

The collector writes a manifest plus preflight, aggregate smoke, Vercel,
LangChain, and invoice comparison artifacts, then runs the same bundle checker
described below. Sample mode deliberately remains non-completion evidence.

After collecting the aggregate provider smoke report, the optional framework
reports, and a sanitized real invoice/dashboard comparison, validate the whole
Milestone 8 evidence set together:

```bash
python3 scripts/check_alpha_evidence_bundle.py \
  --smoke-report /tmp/runcost-alpha-smoke-live.json \
  --smoke-report /tmp/runcost-vercel-live.json \
  --smoke-report /tmp/runcost-langchain-live.json \
  --invoice-comparison /tmp/runcost-real-invoice-comparison.json \
  --require-real
```

The bundle check requires passing evidence for OpenAI Responses, Anthropic
prompt caching, Vercel `streamText`, LangChain agent usage, OpenRouter cost
comparison, and the multi-provider discount case. It also validates
product-truth classification for every non-passing smoke item and rejects
sample invoice comparisons as Milestone 8 completion evidence.

## Source Anchors

- OpenAI Responses API reference: https://developers.openai.com/api/reference/resources/responses/methods/create
- Anthropic prompt caching usage fields: https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- OpenRouter chat completion API: https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request
- Vercel AI SDK `streamText` `onFinish` / usage reference: https://ai-sdk.dev/docs/reference/ai-sdk-core/stream-text
