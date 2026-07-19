#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import process from "node:process";

import {
  DEFAULT_EXTERNAL_PRICE_SOURCES,
  canonicalJSONString,
  clearPriceCache,
  fromBatchResults,
  fromBatchResultsAuto,
  fromResponse,
  fromResponseAuto,
  priceCacheStatus,
  resolvePriceCatalog,
  verifyCatalogManifest
} from "./index.js";

function fail(message, code = 1) {
  process.stderr.write(`runcost: ${message}\n`);
  process.exitCode = code;
}

function parseArgs(argv) {
  const [command, ...tokens] = argv;
  const options = { command, positional: [] };
  const values = new Set([
    "--provider", "--surface", "--model", "--batch-provider", "--endpoint",
    "--batch-id", "--output", "--root", "--price-source", "--cache-dir",
    "--max-age-seconds", "--now"
  ]);
  for (let index = 0; index < tokens.length; index += 1) {
    const token = tokens[index];
    if (values.has(token)) {
      if (index + 1 >= tokens.length) throw new Error(`${token} requires a value`);
      const key = token.slice(2).replaceAll("-", "_");
      const value = tokens[++index];
      if (token === "--price-source") options.price_source = [...(options.price_source || []), value];
      else options[key] = value;
    } else if (["--jsonl", "--offline", "--refresh", "--no-resolve"].includes(token)) {
      options[token.slice(2).replaceAll("-", "_")] = true;
    } else if (token.startsWith("--")) {
      throw new Error(`unknown option: ${token}`);
    } else {
      options.positional.push(token);
    }
  }
  return options;
}

function writeResult(value, output) {
  const encoded = canonicalJSONString(value);
  if (output) fs.writeFileSync(output, encoded, "utf8");
  else process.stdout.write(encoded);
}

function readInput(input, forceJSONL = false) {
  const text = !input || input === "-" ? fs.readFileSync(0, "utf8") : fs.readFileSync(input, "utf8");
  if (!text.trim()) throw new Error("quote input is empty");
  if (!forceJSONL) {
    try {
      const value = JSON.parse(text);
      return { values: Array.isArray(value) ? value : [value], multi: Array.isArray(value) };
    } catch {
      // Fall through to JSONL so piping provider batch files needs no extra flag.
    }
  }
  const values = [];
  text.split(/\r?\n/).forEach((line, index) => {
    if (!line.trim()) return;
    try {
      values.push(JSON.parse(line));
    } catch (error) {
      throw new Error(`invalid JSONL at line ${index + 1}: ${error.message}`);
    }
  });
  if (!values.length) throw new Error("quote input contains no JSON objects");
  return { values, multi: true };
}

function resolverOptions(options) {
  const result = {};
  if (options.price_source) result.sources = options.price_source;
  if (options.cache_dir) result.cacheDir = options.cache_dir;
  if (options.offline) result.offline = true;
  if (options.refresh) result.refresh = true;
  if (options.max_age_seconds !== undefined) result.maxAgeSeconds = Number(options.max_age_seconds);
  if (options.now !== undefined) result.now = options.now;
  return result;
}

async function quoteOne(value, options) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("each quote input must be a JSON object");
  }
  const response = value.raw_response ?? value.response ?? value;
  if (!response || typeof response !== "object" || Array.isArray(response)) {
    throw new Error("quote response must be a JSON object");
  }
  const embedded = value.options && typeof value.options === "object" ? value.options : {};
  const quoteOptions = { ...embedded };
  for (const key of ["provider", "surface", "model"]) {
    if (options[key] !== undefined) quoteOptions[key] = options[key];
  }
  if (Array.isArray(value.price_cards)) quoteOptions.priceCards = value.price_cards;
  if (Array.isArray(value.discount_policies)) quoteOptions.discountPolicies = value.discount_policies;
  if (value.attribution && typeof value.attribution === "object") quoteOptions.attribution = value.attribution;
  return options.no_resolve
    ? fromResponse(response, quoteOptions)
    : fromResponseAuto(response, { ...quoteOptions, ...resolverOptions(options) });
}

async function commandQuote(options) {
  if (options.positional.length > 1) throw new Error("quote accepts at most one input path");
  const input = options.positional[0] || "-";
  const { values, multi } = readInput(input, options.jsonl);
  let result;
  if (options.batch_provider) {
    const items = values.length === 1 && Array.isArray(values[0]?.items) ? values[0].items : values;
    const batchOptions = {
      provider: options.batch_provider,
      surface: options.surface,
      endpoint: options.endpoint,
      model: options.model,
      batchId: options.batch_id,
      ...resolverOptions(options)
    };
    result = options.no_resolve ? fromBatchResults(items, batchOptions) : await fromBatchResultsAuto(items, batchOptions);
  } else {
    const results = await Promise.all(values.map((value) => quoteOne(value, options)));
    result = multi ? results : results[0];
  }
  writeResult(result, options.output);
}

async function commandCatalogVerify(options) {
  if (options.positional.length > 1) throw new Error("catalog-verify accepts exactly one manifest path");
  const manifestPath = options.positional[0];
  if (!manifestPath) throw new Error("catalog-verify requires a manifest path");
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  const root = options.root || path.dirname(manifestPath);
  const entries = [manifest.catalog, ...(Array.isArray(manifest.shards) ? manifest.shards : [])].filter(
    (entry) => entry && typeof entry === "object" && typeof entry.path === "string"
  );
  const artifacts = {};
  for (const entry of entries) {
    const artifactPath = path.resolve(root, entry.path);
    const exists = fs.existsSync(artifactPath) && fs.statSync(artifactPath).isFile();
    if (exists) artifacts[entry.path] = fs.readFileSync(artifactPath);
  }
  const result = await verifyCatalogManifest(manifest, artifacts);
  writeResult(result, options.output);
  if (!result.valid) process.exitCode = 1;
}

async function commandPrices(options) {
  const subcommand = options.positional.shift();
  if (options.positional.length) throw new Error(`prices ${subcommand || ""} accepts no positional arguments`);
  const common = { cacheDir: options.cache_dir, now: options.now };
  if (subcommand === "status") {
    writeResult(await priceCacheStatus(common), options.output);
    return;
  }
  if (subcommand === "clear") {
    writeResult(await clearPriceCache({ ...common, sources: options.price_source }), options.output);
    return;
  }
  if (subcommand === "refresh") {
    const sources = options.price_source || [...DEFAULT_EXTERNAL_PRICE_SOURCES];
    const resolutions = [];
    let succeeded = true;
    for (const source of sources) {
      const resolution = await resolvePriceCatalog({
        ...common,
        sources: [source],
        refresh: true,
        maxAgeSeconds: options.max_age_seconds === undefined ? undefined : Number(options.max_age_seconds)
      });
      resolutions.push({
        source,
        selected_source: resolution.selected_source,
        card_count: resolution.price_cards.length,
        sources: resolution.sources,
        warnings: resolution.warnings,
        resolved_at: resolution.resolved_at
      });
      succeeded = succeeded && resolution.selected_source === source;
    }
    writeResult({ schema_version: "0.1", resolutions }, options.output);
    if (!succeeded) process.exitCode = 1;
    return;
  }
  throw new Error("prices requires one of: refresh, status, clear");
}

function usage() {
  return `Usage:
  runcost quote [FILE|-] [--provider NAME] [--surface NAME] [--model NAME]
                [--jsonl] [--batch-provider NAME] [--price-source NAME]
                [--cache-dir DIR] [--offline] [--refresh] [--no-resolve] [--now RFC3339]
  runcost prices refresh|status|clear [--price-source NAME] [--cache-dir DIR] [--now RFC3339]
  runcost catalog-verify MANIFEST [--root DIRECTORY]
`;
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.command === "quote") return commandQuote(options);
  if (options.command === "prices") return commandPrices(options);
  if (options.command === "catalog-verify") return commandCatalogVerify(options);
  if (["help", "--help", "-h", undefined].includes(options.command)) {
    process.stdout.write(usage());
    return;
  }
  throw new Error(`unknown command: ${options.command}`);
}

main().catch((error) => fail(error.message));
