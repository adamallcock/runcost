---
title: Alpha Smoke Live Direct
date: 2026-05-27
type: report
status: evidence
---

# Alpha Smoke Live Direct

This report records a sanitized live alpha smoke run for direct API paths that
were ready from local Keychain credentials.

Evidence file:

- `fixtures/source-files/alpha-smoke-live-direct-2026-05-27.json`

Command shape:

```bash
ANTHROPIC_API_KEY=<from keychain> \
OPENROUTER_API_KEY=<from keychain> \
python3 scripts/run_alpha_smoke.py \
  --mode live \
  --scenarios anthropic_prompt_caching,openrouter_cost_compare,multi_provider_discount \
  --output /tmp/runcost-alpha-smoke-live-keychain-direct.json \
  --allow-sample-prices
```

Sanitization:

- raw provider responses were not retained;
- prompts, messages, headers, account identifiers, and API keys were not
  written to the evidence file;
- evidence uses sample price cards and is not invoice-exact.

Results:

| Scenario | Status | Evidence summary |
|---|---|---|
| `anthropic_prompt_caching` | passed | Anthropic Messages returned live usage with input/output token fields plus cache-related fields, and RunCost produced a sanitized cost ledger with no warnings. |
| `openrouter_cost_compare` | passed | OpenRouter chat completions returned live usage and provider cost fields for `nvidia/nemotron-3-super-120b-a12b:free`, and RunCost produced a sanitized cost ledger with no warnings. |
| `multi_provider_discount` | passed | The local discount scenario passed in the same reviewed evidence set as live provider scenarios. |

Limitations:

- This is not a complete Milestone 8 evidence bundle because OpenAI Responses,
  Vercel AI SDK streaming, LangChain live framework smoke, and a real
  invoice/dashboard comparison remain pending.
- The costs in this smoke report use sample price cards, so they prove
  extraction and ledger shape rather than invoice-exact billing.
