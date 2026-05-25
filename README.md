# RunCost

Draft project for a small, multi-language cost ledger for LLM and agent API calls.

The goal is to answer:

> What did this call cost, and why?

Current repo state:

- Market validation: `VALIDATION_REPORT.md`
- Product requirements: `PRODUCT_REQUIREMENTS.md`
- Architecture: `ARCHITECTURE.md`
- Full project plan: `PROJECT_PLAN.md`
- Polyglot toolchain decision: `docs/POLYGLOT_TOOLCHAIN_DECISION.md`
- Public API parity matrix: `docs/API_PARITY_MATRIX.md`
- Provider extractor notes: `docs/PROVIDER_EXTRACTOR_NOTES.md`
- Framework adapter notes: `docs/FRAMEWORK_ADAPTER_NOTES.md`
- Progress tracker: `PROGRESS_TRACKER.md`
- Shared schemas: `schemas/`
- Shared conformance fixtures: `fixtures/`
- Tiny reference cores:
  - Python: `packages/python/runcost/`
  - JavaScript: `packages/javascript/core/`
  - Go: `packages/go/ledger/`

Run the current fixture check:

```bash
npm test
```

Run the current examples:

```bash
npm run example:js
npm run example:py
```

The implementation is intentionally minimal: normalized usage plus price cards in, componentized cost ledger out. Provider SDK extractors, price-source adapters, framework integrations, and packaging come next.

## Prototype Capabilities

- Python, JavaScript, and Go cores.
- Decimal-safe cost calculation.
- Component ledgers for input, cached input, output, reasoning, tool units, and Gemini/Vertex multimodal token details.
- Raw extractors for OpenAI Responses, OpenAI Chat Completions, and Anthropic Messages.
- Raw extractors for OpenRouter Chat Completions, Cohere Chat, Google Gemini/Vertex generateContent, and AWS Bedrock Converse.
- Shared OpenAI-compatible chat extraction for Groq, xAI, Mistral, DeepSeek, Azure OpenAI, Hugging Face Inference Providers, and OpenRouter.
- One-call framework helpers for LangChain AIMessage, Vercel AI SDK generateText, and LlamaIndex TokenCountingHandler outputs.
- Exact alias resolution through price-card aliases.
- Component-aware discount policies.
- Simon Willison `llm-prices` adapter for simple current/historical price feeds.
- LiteLLM, Portkey, and OpenRouter models source adapter prototypes.
- Strict mode and compatibility mode.
- TypeScript declarations, Python typed contracts, and Go examples.
- Shared JSON fixtures that both implementations must pass.
