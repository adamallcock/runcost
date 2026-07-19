import { fromOTelGenAISpan, otelCostAttributes, priceCardsFromGenAIPrices } from "../packages/javascript/core/index.js";

const catalog = { providers: [{ id: "openai", models: [{ id: "otel-example", prices: [{ constraint: {}, prices: { input_mtok: "1", cache_read_mtok: "0.1", output_mtok: "2" } }] }] }] };
const priceCards = priceCardsFromGenAIPrices(catalog, { retrievedAt: "2026-07-18T00:00:00Z", version: "example" });
const span = { trace_id: "trace_example", attributes: { "gen_ai.provider.name": "openai", "gen_ai.operation.name": "chat", "gen_ai.request.model": "otel-example", "gen_ai.usage.input_tokens": 100, "gen_ai.usage.cache_read.input_tokens": 20, "gen_ai.usage.output_tokens": 50 } };
const ledger = fromOTelGenAISpan(span, { priceCards, attribution: { project: "docs-example" } });
console.log(JSON.stringify({ total: ledger.total, attributes: otelCostAttributes(ledger) }));
