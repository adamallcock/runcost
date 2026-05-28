#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { fromVercelAISDKStreamFinish } from "../packages/javascript/core/index.js";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SAMPLE_FILE = path.join(ROOT, "fixtures/source-files/alpha-smoke-samples.json");
const SAMPLE_RETRIEVED_AT = "2026-05-26T00:00:00Z";
const FORBIDDEN_KEYS = new Set([
  "api_key",
  "authorization",
  "headers",
  "prompt",
  "messages",
  "input",
  "output",
  "content",
  "raw_response",
  "request_body"
]);
const SECRET_PATTERNS = [
  /\bsk-[A-Za-z0-9_-]{8,}\b/,
  /\bBearer\s+[A-Za-z0-9._-]{8,}\b/i
];

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

function priceCard(model, provider = "openai") {
  const components = {
    input_uncached_tokens: ["token", "1", "1000000"],
    input_cache_read_tokens: ["token", "0.1", "1000000"],
    input_cache_write_tokens: ["token", "1.25", "1000000"],
    output_text_tokens: ["token", "2", "1000000"],
    output_reasoning_tokens: ["token", "2", "1000000"]
  };
  return {
    schema_version: "0.1",
    id: `${provider}:${model}:vercel-alpha-smoke-sample`,
    provider,
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
    sample_prices: true,
    evidence: evidence(ledger, usageFields, source, exactness),
    next_action: nextAction
  };
}

function assertSanitized(value, location = "$") {
  if (Array.isArray(value)) {
    value.forEach((child, index) => assertSanitized(child, `${location}[${index}]`));
    return;
  }
  if (value && typeof value === "object") {
    for (const [key, child] of Object.entries(value)) {
      const normalized = key.toLowerCase().replaceAll("-", "_");
      if (FORBIDDEN_KEYS.has(normalized)) throw new Error(`Forbidden alpha smoke key ${location}.${key}`);
      assertSanitized(child, `${location}.${key}`);
    }
    return;
  }
  if (typeof value === "string") {
    for (const pattern of SECRET_PATTERNS) {
      if (pattern.test(value)) throw new Error(`Secret-like value found in alpha smoke report at ${location}`);
    }
  }
}

function validateReport(report) {
  if (report.schema_version !== "0.1") throw new Error("Alpha smoke report must use schema_version 0.1");
  if (!["sample", "live"].includes(report.mode)) throw new Error("Alpha smoke report mode must be sample or live");
  if (report.sanitized !== true) throw new Error("Alpha smoke report must be sanitized");
  if (report.safe_to_attach_to_issue !== true) throw new Error("Alpha smoke report must be safe to attach");
  if (!["passed", "skipped", "needs_product_truth", "failed"].includes(report.status)) {
    throw new Error("Alpha smoke report status is invalid");
  }
  if (!report.evidence || typeof report.evidence !== "object") throw new Error("Alpha smoke evidence is required");
  if (report.evidence.raw_response_retained !== false) throw new Error("Alpha smoke report must not retain raw responses");
  if (!["sample", "live"].includes(report.evidence.source)) throw new Error("Alpha smoke evidence source is invalid");
  if (!["synthetic_sample", "sample_prices_not_invoice_exact", "not_run", "requires_review"].includes(report.evidence.exactness)) {
    throw new Error("Alpha smoke evidence exactness is invalid");
  }
  assertSanitized(report);
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
    sample_prices: true,
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
  const openAIKey = process.env.OPENAI_API_KEY;
  const openRouterKey = process.env.OPENROUTER_API_KEY;
  if (!openAIKey && !openRouterKey) return skipped("OPENAI_API_KEY or OPENROUTER_API_KEY is not set.");
  let streamText;
  let createOpenAI;
  try {
    ({ streamText } = await import("ai"));
    ({ createOpenAI } = await import("@ai-sdk/openai"));
  } catch {
    return skipped("Install optional packages `ai` and `@ai-sdk/openai` to run the live Vercel AI SDK smoke.");
  }

  const provider = openAIKey ? "openai" : "openrouter";
  const apiKey = openAIKey || openRouterKey;
  const model = openAIKey
    ? process.env.RUNCOST_SMOKE_OPENAI_MODEL || "gpt-4.1-mini"
    : process.env.RUNCOST_SMOKE_OPENROUTER_MODEL || "nvidia/nemotron-3-super-120b-a12b:free";
  try {
    const openai = createOpenAI({
      apiKey,
      ...(openAIKey ? {} : { baseURL: "https://openrouter.ai/api/v1" })
    });
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
      model: { provider, modelId: model },
      totalUsage: usage
    };
    const ledger = fromVercelAISDKStreamFinish(finish, {
      provider,
      surface: "framework.vercel_ai_sdk",
      priceCards: [priceCard(model, provider)]
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
  validateReport(report);
  fs.mkdirSync(path.dirname(args.output), { recursive: true });
  fs.writeFileSync(args.output, `${JSON.stringify(report, null, 2)}\n`);
  console.log(`Wrote sanitized Vercel alpha smoke report to ${args.output}`);
}

main().catch((error) => {
  console.error(error?.constructor?.name || "Error");
  process.exit(1);
});
