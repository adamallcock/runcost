#!/usr/bin/env node

import fs from "node:fs";

import {
  attachPriceResolution,
  estimateCost,
  evaluateBudget,
  fromBatchResults,
  fromOTelGenAISpan,
  fromResponse,
  priceCardsFromGenAIPrices,
  reconcileCost,
  usageLedgerFromOTelGenAISpan
} from "../packages/javascript/core/index.js";

const fixture = JSON.parse(fs.readFileSync(new URL("../fixtures/expansion/cases.json", import.meta.url), "utf8"));

function resolveInput(raw) {
  const value = structuredClone(raw);
  const reference = value.price_cards_ref;
  delete value.price_cards_ref;
  if (reference) value.priceCards = fixture.price_card_sets[reference];
  if (value.price_cards) {
    value.priceCards = value.price_cards;
    delete value.price_cards;
  }
  return value;
}

function runCase(testCase) {
  const value = resolveInput(testCase.input);
  switch (testCase.operation) {
    case "from_response": {
      const response = value.response;
      delete value.response;
      return fromResponse(response, value);
    }
    case "from_batch_results": {
      const items = value.items;
      delete value.items;
      return fromBatchResults(items, value);
    }
    case "price_cards_from_genai_prices": {
      const data = value.data;
      delete value.data;
      return priceCardsFromGenAIPrices(data, value);
    }
    case "usage_ledger_from_otel": {
      const span = value.span;
      delete value.span;
      return usageLedgerFromOTelGenAISpan(span, value);
    }
    case "from_otel": {
      const span = value.span;
      delete value.span;
      return fromOTelGenAISpan(span, value);
    }
    case "estimate_cost":
      return estimateCost(value);
    case "attach_price_resolution":
      return attachPriceResolution(value.ledger, value.resolution);
    case "evaluate_budget": {
      const total = value.ledger_or_total;
      delete value.ledger_or_total;
      return evaluateBudget(total, value);
    }
    case "reconcile_cost": {
      const total = value.ledger_or_total;
      const reported = value.reported_total;
      delete value.ledger_or_total;
      delete value.reported_total;
      return reconcileCost(total, reported, value);
    }
    default:
      throw new Error(`unsupported operation: ${testCase.operation}`);
  }
}

function expectThrow(callback, message) {
  try {
    callback();
  } catch (error) {
    if (!String(error.message).includes(message)) throw error;
    return;
  }
  throw new Error(`expected error containing: ${message}`);
}

function checkEdgeCases() {
  const empty = fromBatchResults([], { provider: "openai" });
  const expectedSummary = { total: 0, succeeded: 0, failed: 0, pending: 0, total_cost: "0" };
  if (JSON.stringify(empty.summary) !== JSON.stringify(expectedSummary) || empty.warnings.length !== 0) {
    throw new Error(`empty batch summary is unstable: ${JSON.stringify(empty)}`);
  }
  expectThrow(() => fromBatchResults([], { provider: "unsupported" }), "unsupported batch provider");
  if (evaluateBudget("0", { budget: "0" }).status !== "within_budget") {
    throw new Error("an unspent zero budget must remain within budget");
  }
  expectThrow(() => evaluateBudget("0", { budget: "-1" }), "budget must be non-negative");
  expectThrow(() => evaluateBudget("0", { budget: "1", warningThreshold: "1.1" }), "warning_threshold must be between 0 and 1");
  expectThrow(() => reconcileCost("1", "1", { tolerance: "-0.01" }), "tolerance must be non-negative");
  const unknown = fromResponse({ unexpected: true });
  if (JSON.stringify((unknown.warnings || []).map((warning) => warning.code)) !== JSON.stringify(["unknown_surface"])) {
    throw new Error(`ambiguous response did not preserve unknown_surface: ${JSON.stringify(unknown)}`);
  }
  const duplicateCards = priceCardsFromGenAIPrices({ providers: [{
    id: "duplicate-fixture",
    models: [{ id: "model", prices: [
      { constraint: { start_date: "2026-01-01" }, prices: { input_mtok: "1" } },
      { constraint: { start_date: "2026-01-01" }, prices: { input_mtok: "2" } }
    ] }]
  }] });
  const ids = duplicateCards.map((card) => card.id);
  if (ids.length !== 2 || new Set(ids).size !== 2) throw new Error(`genai-prices duplicate IDs were not disambiguated: ${ids}`);
}

checkEdgeCases();
const results = {};
for (const testCase of fixture.cases) {
  if (!(testCase.expected_languages || ["python", "javascript", "go"]).includes("javascript")) continue;
  results[testCase.id] = runCase(testCase);
}
if (process.argv.includes("--json")) process.stdout.write(`${JSON.stringify(results)}\n`);
else process.stdout.write(`JavaScript product expansion cases passed (${Object.keys(results).length})\n`);
