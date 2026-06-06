---
title: Gemini Thinking Token Costing
date: 2026-06-06
type: decision-record
status: accepted
---

# Gemini Thinking Token Costing

## Decision

Gemini `thoughtsTokenCount` / reasoning tokens are billed at the model's
output-token price unless a more specific source component is present.

## Evidence

- Google Gemini thinking docs state that when thinking is enabled, response
  pricing is the sum of output tokens and thinking tokens, and that
  `thoughtsTokenCount` reports generated thinking tokens:
  https://ai.google.dev/gemini-api/docs/thinking#pricing
- Google Gemini pricing labels Gemini 3.5 Flash output pricing as including
  thinking tokens:
  https://ai.google.dev/gemini-api/docs/pricing#gemini-35-flash
- Google Gemini pricing labels Gemini 3.1 Flash-Lite output pricing as
  including thinking tokens:
  https://ai.google.dev/gemini-api/docs/pricing#gemini-31-flash-lite

## Implementation Contract

- If a Gemini usage ledger has nonzero `output_reasoning_tokens`, RunCost must
  either price that component or emit an explicit warning explaining why it is
  unsupported or intentionally unpriced.
- For direct Google Gemini cards whose source has only `output_text_tokens`,
  RunCost should price `output_reasoning_tokens` at the same unit price and add
  component metadata that marks the pricing treatment as
  `gemini_thinking_tokens_priced_as_output_tokens`.
- Existing Gemini input/output-only ledgers must remain unchanged.
