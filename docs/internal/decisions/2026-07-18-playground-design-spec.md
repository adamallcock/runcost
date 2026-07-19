---
title: RunCost Playground Design Specification
date: 2026-07-18
type: decision-record
status: accepted
---

# RunCost Playground Design Specification

## Intent

The public surface must let an engineer paste a sanitized provider response and
immediately answer: what did this call cost, which billing dimensions mattered,
which rates were selected, and what remains uncertain? It is a local browser
tool and must not transmit response data or credentials.

## Accepted references

- Tool screen: `/Users/adamallcock/.codex/generated_images/019f68a7-a3e2-7bf3-8081-51916288d3f3/exec-d6f10598-e2eb-4dfd-910d-ebaeb7f30d4d.png`
- Exact-problem page: `/Users/adamallcock/.codex/generated_images/019f68a7-a3e2-7bf3-8081-51916288d3f3/exec-8d8824b0-f932-422b-b0e4-27e810c5f181.png`

## Design system

- True near-white canvas (`#fbfcfe`), navy ink (`#07142f`), muted slate,
  electric coral action (`#ff4638`), and pale blue-green code surfaces.
- Editorial serif headings paired with disciplined sans-serif UI chrome and a
  monospace response editor.
- Open page bands, thin navy rules, square or lightly rounded controls, and no
  decorative card grid, gradient, glow, fake metric, or stock image.
- Desktop container: 1,440 px reference width with a 42/58 split tool layout.
- Mobile: one column; source and ledger remain readable without horizontal page
  scrolling, while wide data tables get an explicit scroll region.

## Component inventory

- Shared header/footer and one primary coral button.
- Provider, endpoint, model, and fixture controls.
- Sanitized JSON editor, format action, inline validation state, and privacy
  notice.
- Exact total, component table, price source/effective date, warnings, and
  expandable decision trace.
- Batch provider switcher with succeeded/failed/pending items retained.
- Provider-specific problem pages, methodology page, and install band.

## Allowed first-viewport copy

Tool: `RunCost`, `Provider response`, `Cost breakdown`, `Provider`, `Endpoint`,
`Model`, `Fixture`, `Sanitized provider response`, `Format JSON`, `Explain cost`,
`Exact total (USD)`, `Pricing warnings`, and `How this was calculated`.

Problem pages use the provider-specific `Calculate the cost of ...` heading,
the supplied explanatory sentence, `Explain a response`, and
`View the 60-second install`.

## Interaction contract

All calculations run with the browser-safe RunCost core and bundled provider
shards. Fixture switching, JSON formatting, provider routing, cost explanation,
trace expansion, batch provider switching, and install-command copying must
change real local UI state. No response or credential is sent over the network.

## Intentional data correction

The concept's example amount is visual sample data. The implementation must show
the exact total produced by the bundled, dated catalog, even when that differs
from the concept amount; product truth outranks decorative sample fidelity.
