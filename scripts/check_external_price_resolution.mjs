import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  clearPriceCache,
  fromResponseAuto,
  priceCacheStatus,
  resolvePriceCatalog
} from "../packages/javascript/core/index.js";
import {
  resolvePriceCatalog as resolveBrowserPriceCatalog
} from "../packages/javascript/core/browser.js";

const genaiUnknown = { providers: [{ id: "openai", models: [{ id: "other", match: { equals: "other" }, prices: { input_mtok: "9", output_mtok: "9" } }] }] };
const modelsDevTarget = { openai: { name: "OpenAI", models: { "gpt-test": { cost: { input: "1", output: "2" } } } } };
const usageLedger = {
  schema_version: "0.1", provider: "openai", surface: "openai.chat_completions",
  model: { requested: "gpt-test", returned: "gpt-test", billed: "gpt-test", alias_resolution: "none" },
  components: [
    { name: "input_uncached_tokens", quantity: "1000", unit: "token" },
    { name: "output_text_tokens", quantity: "500", unit: "token" }
  ]
};
const response = { id: "chatcmpl_test", object: "chat.completion", model: "gpt-test", choices: [], usage: { prompt_tokens: 1000, completion_tokens: 500, total_tokens: 1500 } };
const sourceUrls = {
  "genai-prices": "https://example.com/genai.json",
  "models.dev": "https://example.com/models.json"
};
const calls = [];
let mode = "normal";
const fetcher = async (url, init) => {
  calls.push([url, init.headers]);
  if (mode === "fail") throw new Error("fixture failure");
  if (mode === "not-modified") return { status: 304, url, headers: { forEach(callback) { callback('"fixture-v2"', "etag"); } }, body: "" };
  const payload = url.includes("genai") ? genaiUnknown : modelsDevTarget;
  return {
    status: 200,
    url,
    headers: { forEach(callback) { callback('"fixture-v1"', "etag"); callback("Fri, 18 Jul 2026 00:00:00 GMT", "last-modified"); } },
    body: JSON.stringify(payload)
  };
};
const cacheDir = fs.mkdtempSync(path.join(os.tmpdir(), "runcost-js-resolver-"));
try {
  const explicitEmpty = await resolvePriceCatalog({ priceCards: [], fetcher });
  if (explicitEmpty.selected_source !== "user" || explicitEmpty.price_cards.length !== 0 || calls.length !== 0) throw new Error("explicit-empty catalog fetched the network");
  const resolution = await resolvePriceCatalog({ usageLedger, sources: ["genai-prices", "models.dev"], sourceUrls, cacheDir, fetcher, now: "2026-07-18T00:00:00Z" });
  if (resolution.selected_source !== "models.dev" || calls.length !== 2) throw new Error("fallback/source-order contract failed");
  if (new Set(resolution.price_cards.map((card) => card.source.name)).size !== 1) throw new Error("resolver mixed source cards");

  const callCount = calls.length;
  const fresh = await resolvePriceCatalog({ usageLedger, sources: ["models.dev"], sourceUrls, cacheDir, fetcher, now: "2026-07-18T01:00:00Z" });
  if (calls.length !== callCount || fresh.sources[0].status !== "cache_fresh") throw new Error("fresh-cache contract failed");

  mode = "not-modified";
  const validated = await resolvePriceCatalog({ usageLedger, sources: ["models.dev"], sourceUrls, cacheDir, fetcher, refresh: true, now: "2026-07-18T02:00:00Z" });
  if (validated.sources[0].status !== "cache_validated" || calls.at(-1)[1]["If-None-Match"] !== '"fixture-v1"') throw new Error("conditional validation contract failed");

  mode = "fail";
  const stale = await resolvePriceCatalog({ usageLedger, sources: ["models.dev"], sourceUrls, cacheDir, fetcher, refresh: true, now: "2026-07-20T00:00:00Z" });
  if (stale.selected_source !== "models.dev" || !stale.warnings.some((warning) => warning.code === "price_source_refresh_failed")) throw new Error("last-known-good contract failed");

  const beforeOffline = calls.length;
  const ledger = await fromResponseAuto(response, { provider: "openai", surface: "openai.chat_completions", sources: ["models.dev"], sourceUrls, cacheDir, offline: true });
  if (calls.length !== beforeOffline || ledger.total !== "0.002" || ledger.metadata.price_resolution.selected_source !== "models.dev") throw new Error("offline auto-pricing contract failed");
  if (!(await priceCacheStatus({ cacheDir })).entries.length) throw new Error("cache status is empty");
  if (!(await clearPriceCache({ cacheDir, sources: ["models.dev"] })).removed.length) throw new Error("cache clear removed no entries");

  let browserCalls = 0;
  const browserFetcher = async (url) => {
    browserCalls += 1;
    return { status: 200, url, headers: { forEach() {} }, body: JSON.stringify(modelsDevTarget) };
  };
  const browserOptions = { usageLedger, sources: ["models.dev"], sourceUrls, fetcher: browserFetcher, now: "2026-07-18T00:00:00Z" };
  const browserFirst = await resolveBrowserPriceCatalog(browserOptions);
  const browserSecond = await resolveBrowserPriceCatalog({ ...browserOptions, now: "2026-07-18T01:00:00Z" });
  if (browserFirst.selected_source !== "models.dev" || browserSecond.sources[0].status !== "cache_fresh" || browserCalls !== 1) throw new Error("browser in-memory cache contract failed");
} finally {
  fs.rmSync(cacheDir, { recursive: true, force: true });
}

console.log("JavaScript and browser external price resolution checks passed.");
