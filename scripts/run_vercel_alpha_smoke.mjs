#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { fromVercelAISDKStreamFinish } from "../packages/javascript/core/index.js";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SAMPLE_FILE = path.join(ROOT, "fixtures/source-files/alpha-smoke-samples.json");
const SAMPLE_RETRIEVED_AT = "2026-05-26T00:00:00Z";

function parseArgs(argv) {
  const args = { mode: "sample", allowSamplePrices: false };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--mode") args.mode = argv[++index];
    else if (arg === "--output") args.output = argv[++index];
    else if (arg === "--allow-sample-prices") args.allowSamplePrices = true;
    else throw new Error(`Unknown argument: ${arg}`);
  }
  if (!["sample", "live"].includes(args.mode)) throw new Error("--mode must be sample or live");
  if (!args.output) throw new Error("--output is required");
  if (!args.allowSamplePrices) {
    throw new Error("--allow-sample-prices is required so smoke output is not mistaken for invoice-exact pricing.");
  }
  return args;
}

function utcNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

function sampleFinish() {
  const samples = JSON.parse(fs.readFileSync(SAMPLE_FILE, "utf8"));
  return samples.scenarios.vercel_ai_sdk_stream_text.finish;
}

function priceCard(model) {
  const components = {
    input_uncached_tokens: ["token", "1", "1000000"],
    input_cache_read_tokens: ["token", "0.1", "1000000"],
    input_cache_write_tokens: ["token", "1.25", "1000000"],
    output_text_tokens: ["token", "2", "1000000"],
    output_reasoning_tokens: ["token", "2", "1000000"]
  };
  return {
    schema_version: "0.1",
    id: `openai:${model}:vercel-alpha-smoke-sample`,
    provider: "openai",
    surface: "framework.vercel_ai_sdk",
    model,
    components: Object.entries(components).map(([name, [unit, amount, per]]) => ({
      usage_component: name,
      unit,
      price: { amount, currency: "USD", per }
    })),
    source: {
      name: "alpha-smoke-sample",
      retrieved_at: SAMPLE_RETRIEVED_AT
    }
  };
}

function evidence(ledger, usageFields, source, exactness = "synthetic_sample") {
  return {
    provider: ledger.provider,
    surface: ledger.surface,
    model: ledger.model,
    component_names: ledger.components.map((component) => component.name),
    warning_codes: ledger.warnings.map((warning) => warning.code),
    total: ledger.total,
    price_source_names: ledger.price_sources.map((priceSource) => priceSource.name),
    usage_fields_present: [...usageFields].sort(),
    raw_response_retained: false,
    exactness,
    source
  };
}

function result(status, ledger, usageFields, source, nextAction, exactness) {
  return {
    schema_version: "0.1",
    generated_at: utcNow(),
    mode: source === "sample" ? "sample" : "live",
    scenario: "vercel_ai_sdk_stream_text",
    status,
    sanitized: true,
    safe_to_attach_to_issue: true,
    evidence: evidence(ledger, usageFields, source, exactness),
    next_action: nextAction
  };
}

function skipped(reason) {
  return {
    schema_version: "0.1",
    generated_at: utcNow(),
    mode: "live",
    scenario: "vercel_ai_sdk_stream_text",
    status: "skipped",
    sanitized: true,
    safe_to_attach_to_issue: true,
    evidence: {
      component_names: [],
      warning_codes: [],
      total: "0",
      usage_fields_present: [],
      raw_response_retained: false,
      exactness: "not_run",
      source: "live"
    },
    next_action: {
      type: "documented_limitation",
      reason
    }
  };
}

function sampleReport() {
  const finish = sampleFinish();
  const model = finish.model.modelId;
  const ledger = fromVercelAISDKStreamFinish(finish, {
    provider: "openai",
    surface: "framework.vercel_ai_sdk",
    priceCards: [priceCard(model)]
  });
  return result(
    "passed",
    ledger,
    [
      "totalUsage.inputTokens",
      "totalUsage.inputTokenDetails.cacheReadTokens",
      "totalUsage.inputTokenDetails.cacheWriteTokens",
      "totalUsage.outputTokenDetails.reasoningTokens"
    ],
    "sample",
    { type: "none", reason: "Sanitized Vercel AI SDK sample matched the streamText extractor path." }
  );
}

async function liveReport() {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) return skipped("OPENAI_API_KEY is not set.");
  let streamText;
  let createOpenAI;
  try {
    ({ streamText } = await import("ai"));
    ({ createOpenAI } = await import("@ai-sdk/openai"));
  } catch {
    return skipped("Install optional packages `ai` and `@ai-sdk/openai` to run the live Vercel AI SDK smoke.");
  }

  const model = process.env.RUNCOST_SMOKE_OPENAI_MODEL || "gpt-4.1-mini";
  try {
    const openai = createOpenAI({ apiKey });
    const response = streamText({
      model: openai(model),
      prompt: "Return exactly the word pong.",
      maxOutputTokens: 16
    });
    await response.text;
    const usage = await response.usage;
    const finishReason = await response.finishReason;
    const finish = {
      finishReason,
      model: { provider: "openai", modelId: model },
      totalUsage: usage
    };
    const ledger = fromVercelAISDKStreamFinish(finish, {
      provider: "openai",
      surface: "framework.vercel_ai_sdk",
      priceCards: [priceCard(model)]
    });
    return result(
      "passed",
      ledger,
      Object.keys(usage || {}).map((key) => `usage.${key}`),
      "live",
      { type: "none", reason: "Live Vercel AI SDK streamText usage produced a sanitized RunCost ledger." },
      "sample_prices_not_invoice_exact"
    );
  } catch (error) {
    return {
      ...skipped(`Live Vercel AI SDK smoke failed with sanitized error type ${error?.constructor?.name || "Error"}.`),
      status: "needs_product_truth",
      next_action: {
        type: "fixture_or_warning_or_limitation",
        reason: `Live Vercel AI SDK smoke failed with sanitized error type ${error?.constructor?.name || "Error"}.`
      }
    };
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const report = args.mode === "sample" ? sampleReport() : await liveReport();
  fs.mkdirSync(path.dirname(args.output), { recursive: true });
  fs.writeFileSync(args.output, `${JSON.stringify(report, null, 2)}\n`);
  console.log(`Wrote sanitized Vercel alpha smoke report to ${args.output}`);
}

main().catch((error) => {
  console.error(error?.constructor?.name || "Error");
  process.exit(1);
});
