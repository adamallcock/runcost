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

Before a live run, check credential and optional dependency readiness without
printing secret values:

```bash
npm run smoke:alpha:preflight
npm run smoke:alpha:preflight -- --output /tmp/runcost-alpha-smoke-preflight.json
npm run smoke:alpha:preflight -- --require-ready
```

The preflight reports scenario readiness, missing environment variable names,
and missing optional package names only. It never prints API-key values.

## Live Runs

Live mode is explicit and still uses sample price cards. That means the output
validates extraction, ledger shape, warnings, and integration ergonomics, but it
is not invoice-exact unless a later comparison uses the provider's actual
pricing and billing export.

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
| `openrouter_cost_compare` | `OPENROUTER_API_KEY` | Calls OpenRouter chat completions and verifies provider-reported usage/cost comparison shape when present. |
| `multi_provider_discount` | none | Runs a local multi-provider discount ledger using the same sanitized report shape. |

Framework live smoke scripts are separate so optional dependencies do not become
core package dependencies:

```bash
OPENAI_API_KEY=... \
node scripts/run_vercel_alpha_smoke.mjs --mode live --output /tmp/runcost-vercel-live.json --allow-sample-prices

OPENAI_API_KEY=... \
python3 scripts/run_langchain_alpha_smoke.py --mode live --output /tmp/runcost-langchain-live.json --allow-sample-prices
```

The Vercel script requires optional packages `ai` and `@ai-sdk/openai` in the
current Node environment. The LangChain script requires optional packages
`langchain-openai` and `langchain-core` in the current Python environment. If
credentials or optional packages are missing, the scripts emit sanitized skipped
reports instead of failing normal validation.

## Safety Rules

Smoke output may be attached to issues only if all of these remain true:

- no API keys, headers, organization IDs, account IDs, prompts, messages,
  response content, raw provider responses, or request bodies are written;
- output contains only provider, surface, model identifiers, usage field names,
  component names, warning codes, totals, price-source names, and next-action
  classification;
- failures are reported by sanitized error type, not by raw provider body;
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

For a non-passing credentialed live finding, add or update one register entry
with the scenario, status, next-action type, classification, artifact path, and
resolution. The artifact must be one of the product-truth outcomes above: a
fixture, structured warning, documented limitation, extractor/source-adapter
fix, or price-source update.

## Source Anchors

- OpenAI Responses API reference: https://developers.openai.com/api/reference/resources/responses/methods/create
- Anthropic prompt caching usage fields: https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- OpenRouter chat completion API: https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request
- Vercel AI SDK `streamText` `onFinish` / usage reference: https://ai-sdk.dev/docs/reference/ai-sdk-core/stream-text
