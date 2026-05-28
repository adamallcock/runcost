---
title: Live Framework And Billing Review
date: 2026-05-27
type: report
status: evidence
---

# Live Framework And Billing Review

This report records the additional live smoke evidence captured after optional
Vercel AI SDK and LangChain SDK dependencies were installed.

## Evidence Files

- `fixtures/source-files/alpha-smoke-live-all-2026-05-27.json`
- `fixtures/source-files/alpha-smoke-live-openai-responses-2026-05-27.json`
- `fixtures/source-files/alpha-smoke-live-vercel-openai-2026-05-27.json`
- `fixtures/source-files/alpha-smoke-live-langchain-openai-2026-05-27.json`
- `fixtures/source-files/alpha-smoke-live-vercel-openrouter-2026-05-27.json`
- `fixtures/source-files/alpha-smoke-live-langchain-openrouter-2026-05-27.json`
- `fixtures/source-files/billing-export-review-packet-2026-05-27.json`

## Live Smoke Results

| Scenario | Route | Status | Notes |
|---|---|---|---|
| `openai_responses` | OpenAI Responses API | passed | Sanitized usage fields included input, output, and total token fields. |
| `anthropic_prompt_caching` | Anthropic Messages API | passed | Sanitized usage fields included cache-related field names. |
| `openrouter_cost_compare` | OpenRouter chat completions | passed | Used `nvidia/nemotron-3-super-120b-a12b:free`; provider usage/cost fields were present. |
| `vercel_ai_sdk_stream_text` | Vercel AI SDK to OpenAI | passed | Real `streamText` flow produced final usage and a RunCost ledger. |
| `langchain_agent_run` | LangChain ChatOpenAI to OpenAI | passed | Real LangChain call produced usage metadata and a RunCost ledger. |
| `multi_provider_discount` | Local aggregate | passed | Included in the same reviewed live smoke bundle. |

The smoke reports are sanitized: raw provider responses, prompts, messages,
headers, account identifiers, and API keys were not retained.

## Billing Review Packet

The billing/export review packet is:

```text
fixtures/source-files/billing-export-review-packet-2026-05-27.json
```

Use it to check the provider dashboard or usage export around:

```text
2026-05-27T04:45:00Z/2026-05-27T05:00:00Z
```

The packet lists provider, surface, scenario, expected model, expected request
count, and fields to check. It intentionally does not contain private billing
exports.

## Limitations

- Smoke costs use sample price cards and are not invoice-exact.
- The real invoice/dashboard comparison gate still requires a sanitized
  provider export or dashboard reduction. Use
  `docs/internal/process/invoice-dashboard-comparison.md` to convert that reviewed
  evidence into the machine-checkable comparison format.
- PyPI and npm publishing remain intentionally on hold.
