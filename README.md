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

- Quickstart: `docs/2026-05-25-quickstart.md`
- Installation: `docs/2026-05-25-package-installation.md`
- API reference: `docs/2026-05-25-api-reference.md`
- Debug trace: `docs/2026-05-25-debug-trace.md`
- Fixture coverage: `docs/2026-05-25-fixture-coverage.md`
- Supported surfaces: `docs/2026-05-25-supported-surfaces.md`
- Custom pricing and discounts: `docs/2026-05-25-custom-pricing-and-discounts.md`
- Source adapters: `docs/2026-05-25-source-adapters.md`
- Aggregation and streaming: `docs/2026-05-25-aggregation-and-streaming.md`
- Warnings and limitations: `docs/2026-05-25-warnings-and-limitations.md`
- Release process: `docs/2026-05-25-release-process.md`
- Contributing: `CONTRIBUTING.md`
- Security policy: `SECURITY.md`
- Changelog: `CHANGELOG.md`

## Project State

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

The implementation is still pre-alpha. The current center of gravity is normalized usage plus price cards in, componentized cost ledger out. Release-readiness scaffolding exists, but first registry publication, provider-specific streaming parsers, and broader tool-call pricing are still ahead.

## Prototype Capabilities

- Python, JavaScript, and Go cores.
- Decimal-safe cost calculation.
- Component ledgers for input, cached input, output, reasoning, tool units, and Gemini/Vertex multimodal token details.
- Raw extractors for OpenAI Responses, OpenAI Chat Completions, and Anthropic Messages.
- Raw extractors for OpenRouter Chat Completions, Cohere Chat, Google Gemini/Vertex generateContent, and AWS Bedrock Converse.
- Final streaming usage extraction for OpenAI Responses `response.completed`, Anthropic Messages SSE event sequences, and Gemini stream chunks with `usageMetadata`.
- Shared OpenAI-compatible chat extraction for Groq, xAI, Mistral, DeepSeek, Azure OpenAI, Hugging Face Inference Providers, and OpenRouter.
- One-call framework helpers for LangChain AIMessage, Vercel AI SDK generateText, and LlamaIndex TokenCountingHandler outputs.
- Framework-native helpers for Python LangChain callback/context-manager usage and JavaScript Vercel AI SDK `wrapGenerate` middleware.
- Documented partial adapter paths for Semantic Kernel, Haystack, AutoGen/AG2, LangSmith export comparison, LiteLLM proxy metadata, and OpenRouter-compatible SDK paths.
- Multi-call/session aggregation for already-calculated cost ledgers, including missing final streaming usage warnings.
- Exact alias resolution through price-card aliases.
- Component-aware discount policies.
- Optional debug traces for price-card, component, alias, discount, and warning decisions.
- Simon Willison `llm-prices` adapter for simple current/historical price feeds.
- LiteLLM, Portkey, OpenRouter models, user compact pricing, and Helicone model-registry source adapter prototypes.
- Strict mode and compatibility mode.
- TypeScript declarations, Python typed contracts, and Go examples.
- Shared JSON fixtures that both implementations must pass.
