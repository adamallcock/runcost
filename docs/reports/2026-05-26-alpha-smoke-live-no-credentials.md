---
title: Alpha Smoke Live No Credentials Report
date: 2026-05-26
type: report
status: draft
---

# Alpha Smoke Live No Credentials Report

Command:

```bash
npm run smoke:alpha -- --mode live --output /tmp/runcost-alpha-live.json --allow-sample-prices
```

Result summary:

| Scenario | Status | Product-truth classification |
|---|---|---|
| `openai_responses` | skipped | documented limitation: `OPENAI_API_KEY` is not set |
| `anthropic_prompt_caching` | skipped | documented limitation: `ANTHROPIC_API_KEY` is not set |
| `openrouter_cost_compare` | skipped | documented limitation: `OPENROUTER_API_KEY` is not set |
| `vercel_ai_sdk_stream_text` | skipped | documented limitation: `OPENAI_API_KEY` is not set |
| `langchain_agent_run` | skipped | documented limitation: `OPENAI_API_KEY` is not set |
| `multi_provider_discount` | passed | no action; local sanitized ledger path matched existing behavior |

No provider API call was made in this environment because the required API-key
environment variables were absent. No prompts, messages, provider response
content, headers, account IDs, or raw responses were written.

This report does not satisfy the Milestone 8 live-provider-run gate. It proves
the live harness is safe to execute without credentials and that missing
credentials are classified as documented limitations instead of opaque failures.

Next required evidence:

- run at least one credentialed provider/API smoke;
- attach only the sanitized smoke report;
- convert any non-passing live finding into a fixture, structured warning,
  documented limitation, extractor/source-adapter fix, or price-source update;
- complete one invoice/dashboard comparison report.
