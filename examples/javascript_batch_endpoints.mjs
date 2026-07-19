import fs from "node:fs";
import { fromBatchResults } from "../packages/javascript/core/index.js";

const fixture = JSON.parse(fs.readFileSync(new URL("../fixtures/expansion/cases.json", import.meta.url), "utf8"));
const summaries = {};
for (const testCase of fixture.cases.filter((candidate) => candidate.operation === "from_batch_results")) {
  const input = structuredClone(testCase.input);
  const items = input.items;
  const reference = input.price_cards_ref;
  delete input.items;
  delete input.price_cards_ref;
  const ledger = fromBatchResults(items, { ...input, priceCards: fixture.price_card_sets[reference] });
  summaries[testCase.id] = ledger.summary;
}

const orderedSummaries = Object.fromEntries(
  Object.entries(summaries).sort(([left], [right]) => left.localeCompare(right))
);
console.log(JSON.stringify(orderedSummaries));
