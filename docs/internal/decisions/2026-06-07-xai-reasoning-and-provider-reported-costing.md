---
title: xAI Reasoning And Provider-Reported Costing
date: 2026-06-07
type: decision-record
status: accepted
---

# xAI Reasoning And Provider-Reported Costing

## Context

xAI Responses and Chat Completions usage can report reasoning tokens in
`output_tokens_details.reasoning_tokens` / `completion_tokens_details.reasoning_tokens`.
xAI's pricing page lists reasoning tokens as billed token usage for requests
using server-side tools:

- https://docs.x.ai/developers/pricing
- https://docs.x.ai/developers/model-capabilities/text/reasoning

xAI also returns `usage.cost_in_usd_ticks`, documented as the exact per-request
cost billed by xAI and inclusive of token costs and server-side tool invocation
costs:

- https://docs.x.ai/developers/cost-tracking

xAI documents `server_side_tool_usage` as the billable successful-tool map for
server-side tools, while aggregate attempted or output-visible tool calls can
include failed or less-specific calls:

- https://docs.x.ai/developers/tools/tool-usage-details

## Decision

RunCost treats nonzero xAI `output_reasoning_tokens` as a priced output-token
component when the matching xAI price card publishes `output_text_tokens` but no
separate `output_reasoning_tokens` component, unless the source explicitly marks
reasoning tokens unsupported. The ledger component includes:

- `pricing_policy: xai_reasoning_tokens_priced_as_output_tokens`
- `priced_as_component: output_text_tokens`

RunCost also extracts xAI `usage.cost_in_usd_ticks` as provider-reported cost.
The standard provider-reported cost modes still apply:

- `compare`: keep the component-estimated total and warn on mismatch.
- `use`: use xAI's exact reported total and add a reconciliation component.

xAI `server_side_tool_usage` is the preferred source for billable server-side
tool components. RunCost maps typed usage to explicit components:

- `SERVER_SIDE_TOOL_WEB_SEARCH` -> `web_search_units`
- `SERVER_SIDE_TOOL_X_SEARCH` -> `x_search_units`
- `SERVER_SIDE_TOOL_CODE_EXECUTION` -> `code_interpreter_call_units`
- `SERVER_SIDE_TOOL_COLLECTIONS_SEARCH` -> `file_search_units`
- `SERVER_SIDE_TOOL_ATTACHMENT_SEARCH` -> `attachment_search_units`

When the typed billable map is absent, xAI Responses output items are mapped as
the best available typed fallback. Only then does `usage.num_server_side_tools_used`
fall back to generic `tool_call_units` for the count not already represented by
explicit hosted-tool output items. A price card must explicitly price
`tool_call_units`; otherwise RunCost emits the existing tool-component unpriced
warning.

## Evidence

The behavior is covered by:

- `fixtures/xai-grok-4-3-reasoning-output-pricing.json`
- `fixtures/xai-responses-provider-reported-cost-ticks.json`
- `fixtures/xai-responses-server-side-tool-count.json`
- `fixtures/xai-responses-server-side-tool-usage-map.json`
- `fixtures/xai-responses-output-x-search-call.json`
