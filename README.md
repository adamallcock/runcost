# RunCost

RunCost is a small, multi-language cost ledger for LLM and agent API calls.

The goal is to answer:

> What did this call cost, and why?

It takes provider SDK responses, framework usage objects, or normalized usage ledgers and returns a componentized cost ledger: input cost, cached input cost, output cost, reasoning cost, tool and feature units, discounts, price sources, and warnings.

## Quickstart

Python from a cloned checkout:

```bash
python3 -m pip install .
```

JavaScript/TypeScript from a cloned checkout:

```bash
npm pack ./packages/javascript/core
npm install ./runcost-0.0.0.tgz
```

Go:

```bash
go get github.com/adamallcock/runcost/packages/go/ledger
```

Run the current checks:

```bash
npm test
npm run check:coverage
npm run check:packages
npm run check:release
npm run example:js
npm run example:py
```

## Documentation

- Quickstart: `docs/guides/quickstart.md`
- Installation: `docs/guides/package-installation.md`
- API reference: `docs/reference/api-reference.md`
- Debug trace: `docs/reference/debug-trace.md`
- Fixture coverage: `docs/reports/fixture-coverage.md`
- Supported surfaces: `docs/reference/supported-surfaces.md`
- Custom pricing and discounts: `docs/reference/custom-pricing-and-discounts.md`
- Source adapters: `docs/reference/source-adapters.md`
- Aggregation and streaming: `docs/reference/aggregation-and-streaming.md`
- Warnings and limitations: `docs/reference/warnings-and-limitations.md`
- Release process: `docs/process/release-process.md`
- Contributing: `CONTRIBUTING.md`
- Security policy: `SECURITY.md`
- Changelog: `CHANGELOG.md`

## Project State

- Market validation: `VALIDATION_REPORT.md`
- Product requirements: `PRODUCT_REQUIREMENTS.md`
- Architecture: `ARCHITECTURE.md`
- Full project plan: `PROJECT_PLAN.md`
- Polyglot toolchain decision: `docs/decisions/polyglot-toolchain-decision.md`
- Public API parity matrix: `docs/notes/api-parity-matrix.md`
- Provider extractor notes: `docs/notes/provider-extractor-notes.md`
- Framework adapter notes: `docs/notes/framework-adapter-notes.md`
- Progress tracker: `PROGRESS_TRACKER.md`
- Shared schemas: `schemas/`
- Shared conformance fixtures: `fixtures/`
- Tiny reference cores:
  - Python: `packages/python/runcost/`
  - JavaScript: `packages/javascript/core/`
  - Go: `packages/go/ledger/`

The implementation is still pre-alpha. The current center of gravity is normalized usage plus price cards in, componentized cost ledger out. Release-readiness scaffolding exists, but first registry publication, provider-specific streaming parsers, and broader tool-call pricing are still ahead.

## Prototype Capabilities

- Python, JavaScript, and Go cores.
- Decimal-safe cost calculation.
- Component ledgers for input, cached input, output, reasoning, tool units, and Gemini/Vertex multimodal token details.
- Raw extractors for OpenAI Responses, OpenAI Chat Completions, and Anthropic Messages.
- Raw extractors for OpenRouter Chat Completions, Cohere Chat, Google Gemini/Vertex generateContent, and AWS Bedrock Converse.
- Final streaming usage extraction for OpenAI Responses `response.completed`, Anthropic Messages SSE event sequences, and Gemini stream chunks with `usageMetadata`.
- Shared OpenAI-compatible chat extraction for Groq, xAI, Mistral, DeepSeek, Azure OpenAI, Hugging Face Inference Providers, and OpenRouter.
- One-call framework helpers for LangChain AIMessage, Vercel AI SDK generateText, LlamaIndex TokenCountingHandler, Haystack generator metadata, LiteLLM proxy response metadata, and AutoGen/AG2 usage summary outputs.
- Framework-native helpers for Python LangChain callback/context-manager usage and JavaScript Vercel AI SDK `wrapGenerate` middleware.
- Documented partial adapter paths for Semantic Kernel, LangSmith export comparison, and OpenRouter-compatible SDK paths.
- Multi-call/session aggregation for already-calculated cost ledgers, including missing final streaming usage warnings.
- Exact alias resolution through price-card aliases.
- Component-aware discount policies.
- Optional debug traces for price-card, component, alias, discount, and warning decisions.
- Source capability warnings when a pricing source explicitly does not price a usage component.
- Simon Willison `llm-prices` adapter for simple current/historical price feeds.
- LiteLLM, Portkey, OpenRouter models, models.dev, reviewed official snapshots, source-cache, local JSON/YAML file, user compact pricing, and Helicone model-registry source adapter prototypes.
- Explicit `npm run prices:refresh -- ...` command for writing source-cache envelopes from live or reviewed JSON snapshots.
- Strict mode and compatibility mode.
- TypeScript declarations, Python typed contracts, and Go examples.
- Shared JSON fixtures that both implementations must pass.
