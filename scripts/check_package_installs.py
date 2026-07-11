#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print(f"$ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def copy_source_tree(workdir: Path) -> Path:
    source_root = workdir / "source"
    shutil.copytree(
        ROOT,
        source_root,
        ignore=shutil.ignore_patterns(
            ".git",
            "node_modules",
            "build",
            "dist",
            "*.egg-info",
            "__pycache__",
            ".pytest_cache",
        ),
    )
    return source_root


def check_python_install(source_root: Path, workdir: Path) -> None:
    venv_dir = workdir / "python-venv"
    run(["python3", "-m", "venv", str(venv_dir)], workdir)
    python = venv_dir / "bin" / "python"
    pip_env = os.environ.copy()
    pip_env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    run([str(python), "-m", "pip", "install", "--quiet", str(source_root)], workdir, env=pip_env)
    cli_fixture = workdir / "cli-fixture.json"
    cli_fixture.write_text(
        """{
  "input": {
    "usage_ledger": {
      "schema_version": "0.1",
      "provider": "test",
      "surface": "test.responses",
      "model": {
        "requested": "test-model",
        "billed": "test-model",
        "alias_resolution": "none"
      },
      "components": [
        {
          "name": "input_uncached_tokens",
          "quantity": "100",
          "unit": "token"
        }
      ]
    },
    "price_cards": [
      {
        "schema_version": "0.1",
        "id": "test:test-model",
        "provider": "test",
        "surface": "test.responses",
        "model": "test-model",
        "components": [
          {
            "usage_component": "input_uncached_tokens",
            "unit": "token",
            "price": {
              "amount": "1",
              "currency": "USD",
              "per": "1000000"
            }
          }
        ],
        "source": {
          "name": "fixture"
        }
      }
    ]
  },
  "expected": {
    "cost_ledger": {
      "total": "0.0001"
    }
  }
}
""",
        encoding="utf-8",
    )
    run(
        [
            str(python),
            "-c",
            "from pathlib import Path; from runcost import aggregate_cost_ledgers, calculate_cost, from_response, default_price_cards, default_source_cache, DEFAULT_PRICE_SOURCE_PRIORITY, extract_google_interactions_usage, extract_bedrock_invoke_model_usage, extract_cohere_rerank_usage, extract_meta_chat_completions_usage, extract_meta_responses_usage, extract_openai_audio_transcription_usage, extract_openai_embeddings_usage, extract_openai_images_usage, extract_openai_usage_audio_speeches_usage, extract_openai_usage_audio_transcriptions_usage, extract_openai_usage_code_interpreter_sessions_usage, extract_openai_usage_completions_usage, extract_openai_usage_embeddings_usage, extract_openai_usage_images_usage, extract_openai_vector_store_storage_usage, from_ag2_usage_summary, from_haystack_generator_result, from_langsmith_run, from_litellm_response, from_openai_agents_usage, from_openrouter_sdk_response, from_semantic_kernel_telemetry, from_vercel_ai_sdk_stream_finish, track_langchain_costs, price_cards_from_helicone, price_cards_from_json_file, price_cards_from_yaml_file, price_cards_from_models_dev, price_cards_from_official_snapshot, price_cards_from_source_cache, price_cards_from_user_pricing; from runcost.types import UsageLedger, WarningCode; p=Path('prices.json'); p.write_text('{\"provider\":\"test\",\"models\":[{\"id\":\"test\",\"prices\":{\"input\":\"1\"}}]}'); y=Path('prices.yaml'); y.write_text('provider: test\\nmodels:\\n  - id: test\\n    prices:\\n      input: \"1\"\\n'); print(aggregate_cost_ledgers, calculate_cost, from_response, len(default_price_cards()), default_source_cache()['metadata']['price_card_count'], DEFAULT_PRICE_SOURCE_PRIORITY[0], extract_google_interactions_usage, extract_bedrock_invoke_model_usage, extract_cohere_rerank_usage, extract_meta_chat_completions_usage, extract_meta_responses_usage, extract_openai_audio_transcription_usage, extract_openai_embeddings_usage, extract_openai_images_usage, extract_openai_usage_audio_speeches_usage, extract_openai_usage_audio_transcriptions_usage, extract_openai_usage_code_interpreter_sessions_usage, extract_openai_usage_completions_usage, extract_openai_usage_embeddings_usage, extract_openai_usage_images_usage, extract_openai_vector_store_storage_usage, from_ag2_usage_summary, from_haystack_generator_result, from_langsmith_run, from_litellm_response, from_openai_agents_usage, from_openrouter_sdk_response, from_semantic_kernel_telemetry, from_vercel_ai_sdk_stream_finish, track_langchain_costs, price_cards_from_helicone, price_cards_from_json_file(p), price_cards_from_yaml_file(y), price_cards_from_models_dev, price_cards_from_official_snapshot, price_cards_from_source_cache, price_cards_from_user_pricing, UsageLedger, WarningCode)",
        ],
        workdir,
    )
    run([str(python), "-c", "from runcost import extract_gemini_live_usage, extract_google_interactions_usage; print(extract_gemini_live_usage, extract_google_interactions_usage)"], workdir)
    python_live_check = workdir / "python-live-check.py"
    python_live_check.write_text(
        """
from runcost import DEFAULT_PRICE_SOURCE_PRIORITY, default_price_cards, from_response

model = "gemini-3.5-live-translate-preview"
ledger = from_response(
    {
        "modelVersion": model,
        "usageMetadata": {
            "promptTokenCount": 250,
            "promptTokensDetails": [{"modality": "AUDIO", "tokenCount": 250}],
            "responseTokenCount": 500,
            "responseTokensDetails": [{"modality": "AUDIO", "tokenCount": 500}],
            "totalTokenCount": 750,
        },
    },
    provider="google",
    surface="google.gemini.live",
    model=model,
    price_cards=default_price_cards(),
    price_source_priority=DEFAULT_PRICE_SOURCE_PRIORITY,
)
components = {component["name"]: component for component in ledger["components"]}
sources = {source["name"] for source in ledger["price_sources"]}
assert ledger["total"] == "0.011375", ledger
assert components["input_audio_tokens"]["quantity"] == "250", ledger
assert components["output_audio_tokens"]["quantity"] == "500", ledger
assert sources == {"google-official"}, ledger
print("python gemini live package smoke passed")
""",
        encoding="utf-8",
    )
    run([str(python), str(python_live_check)], workdir)
    python_provider_check = workdir / "python-provider-check.py"
    python_provider_check.write_text(
        """
from runcost import DEFAULT_PRICE_SOURCE_PRIORITY, default_price_cards, from_response

cards = default_price_cards()
cache_write = from_response(
    {
        "model": "gpt-5.6",
        "usage": {
            "input_tokens": 1000,
            "input_tokens_details": {"cached_tokens": 200, "cache_write_tokens": 100},
            "output_tokens": 100,
            "output_tokens_details": {"reasoning_tokens": 20},
        },
    },
    provider="openai",
    surface="openai.responses",
    price_cards=cards,
    price_source_priority=DEFAULT_PRICE_SOURCE_PRIORITY,
)
assert cache_write["total"] == "0.007225", cache_write

def luna(input_tokens):
    return from_response(
        {
            "model": "gpt-5.6-luna",
            "usage": {
                "input_tokens": input_tokens,
                "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
                "output_tokens": 1,
                "output_tokens_details": {"reasoning_tokens": 0},
            },
        },
        provider="openai",
        surface="openai.responses",
        price_cards=cards,
        price_source_priority=DEFAULT_PRICE_SOURCE_PRIORITY,
    )

assert luna(272000)["total"] == "0.272006"
assert luna(272001)["total"] == "0.544011"
priority = from_response(
    {
        "model": "gpt-5.6-sol",
        "service_tier": "priority",
        "usage": {
            "input_tokens": 272001,
            "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
            "output_tokens": 1,
            "output_tokens_details": {"reasoning_tokens": 0},
        },
    },
    provider="openai",
    surface="openai.responses",
    price_cards=cards,
    price_source_priority=DEFAULT_PRICE_SOURCE_PRIORITY,
)
assert priority["total"] == "0", priority
assert "long_context_rule_missing" in {warning["code"] for warning in priority["warnings"]}, priority

meta_card = {
    "schema_version": "0.1",
    "id": "meta:muse-spark-1.1:install-smoke",
    "provider": "meta",
    "surface": "meta.chat_completions",
    "model": "muse-spark-1.1",
    "components": [
        {"usage_component": "input_uncached_tokens", "unit": "token", "price": {"amount": "1", "currency": "USD", "per": "1000000"}},
        {"usage_component": "input_cache_read_tokens", "unit": "token", "price": {"amount": "0.1", "currency": "USD", "per": "1000000"}},
        {"usage_component": "output_text_tokens", "unit": "token", "price": {"amount": "4", "currency": "USD", "per": "1000000"}},
        {"usage_component": "output_reasoning_tokens", "unit": "token", "price": {"amount": "4", "currency": "USD", "per": "1000000"}},
    ],
    "source": {"name": "install-smoke"},
}
meta = from_response(
    {
        "model": "muse-spark-1.1",
        "usage": {
            "prompt_tokens": 100,
            "prompt_tokens_details": {"cached_tokens": 20},
            "completion_tokens": 40,
            "completion_tokens_details": {"reasoning_tokens": 10},
        },
    },
    provider="meta",
    surface="meta.chat_completions",
    price_cards=[meta_card],
)
assert meta["total"] == "0.000242", meta
assert from_response({"model": "muse-spark-1.1", "usage": None}, provider="meta", surface="meta.responses", price_cards=[])["total"] == "0"
print("python GPT-5.6 and Meta package smoke passed")
""",
        encoding="utf-8",
    )
    run([str(python), str(python_provider_check)], workdir)
    run(
        [
            str(venv_dir / "bin" / "runcost"),
            "price-cards",
            "--source-type",
            "user-pricing",
            "--input",
            "prices.json",
        ],
        workdir,
    )
    run([str(venv_dir / "bin" / "runcost"), "fixture-check", str(cli_fixture)], workdir)


def check_javascript_install(source_root: Path, workdir: Path) -> None:
    pack_dir = workdir / "npm-pack"
    project_dir = workdir / "npm-project"
    pack_dir.mkdir()
    project_dir.mkdir()
    run(["npm", "pack", str(source_root / "packages/javascript/core"), "--pack-destination", str(pack_dir)], source_root)
    tarballs = sorted(pack_dir.glob("runcost-*.tgz"))
    if len(tarballs) != 1:
        raise AssertionError(f"expected exactly one runcost tarball, found {len(tarballs)}")
    (project_dir / "package.json").write_text(
        '{"name":"runcost-install-check","version":"0.0.0","type":"module"}\n',
        encoding="utf-8",
    )
    run(["npm", "install", "--silent", str(tarballs[0])], project_dir)
    run(
        [
            "node",
            "--input-type=module",
            "-e",
            'import fs from "node:fs"; import { aggregateCostLedgers, calculateCost, fromResponse, defaultPriceCards, defaultSourceCache, DEFAULT_PRICE_SOURCE_PRIORITY, extractGoogleInteractionsUsage, extractBedrockInvokeModelUsage, extractCohereRerankUsage, extractMetaChatCompletionsUsage, extractMetaResponsesUsage, extractOpenAIAudioTranscriptionUsage, extractOpenAIEmbeddingsUsage, extractOpenAIImagesUsage, extractOpenAIUsageAudioSpeechesUsage, extractOpenAIUsageAudioTranscriptionsUsage, extractOpenAIUsageCodeInterpreterSessionsUsage, extractOpenAIUsageCompletionsUsage, extractOpenAIUsageEmbeddingsUsage, extractOpenAIUsageImagesUsage, extractOpenAIVectorStoreStorageUsage, fromAG2UsageSummary, fromHaystackGeneratorResult, fromLangSmithRun, fromLiteLLMResponse, fromOpenAIAgentsUsage, fromOpenRouterAgentResult, fromOpenRouterSDKResponse, fromSemanticKernelTelemetry, fromVercelAISDKStreamFinish, createRunCostVercelMiddleware, createRunCostVercelOnFinish, priceCardsFromHelicone, priceCardsFromJSONFile, priceCardsFromYAMLFile, priceCardsFromModelsDev, priceCardsFromOfficialSnapshot, priceCardsFromSourceCache, priceCardsFromUserPricing } from "runcost"; fs.writeFileSync("prices.json", JSON.stringify({ provider: "test", models: [{ id: "test", prices: { input: "1" } }] })); fs.writeFileSync("prices.yaml", "provider: test\\nmodels:\\n  - id: test\\n    prices:\\n      input: \\"1\\"\\n"); console.log(typeof aggregateCostLedgers, typeof calculateCost, typeof fromResponse, defaultPriceCards().length, defaultSourceCache().metadata.price_card_count, DEFAULT_PRICE_SOURCE_PRIORITY[0], typeof extractGoogleInteractionsUsage, typeof extractBedrockInvokeModelUsage, typeof extractCohereRerankUsage, typeof extractMetaChatCompletionsUsage, typeof extractMetaResponsesUsage, typeof extractOpenAIAudioTranscriptionUsage, typeof extractOpenAIEmbeddingsUsage, typeof extractOpenAIImagesUsage, typeof extractOpenAIUsageAudioSpeechesUsage, typeof extractOpenAIUsageAudioTranscriptionsUsage, typeof extractOpenAIUsageCodeInterpreterSessionsUsage, typeof extractOpenAIUsageCompletionsUsage, typeof extractOpenAIUsageEmbeddingsUsage, typeof extractOpenAIUsageImagesUsage, typeof extractOpenAIVectorStoreStorageUsage, typeof fromAG2UsageSummary, typeof fromHaystackGeneratorResult, typeof fromLangSmithRun, typeof fromLiteLLMResponse, typeof fromOpenAIAgentsUsage, typeof fromOpenRouterAgentResult, typeof fromOpenRouterSDKResponse, typeof fromSemanticKernelTelemetry, typeof fromVercelAISDKStreamFinish, typeof createRunCostVercelMiddleware, typeof createRunCostVercelOnFinish, typeof priceCardsFromHelicone, priceCardsFromJSONFile("prices.json").length, priceCardsFromYAMLFile("prices.yaml").length, typeof priceCardsFromModelsDev, typeof priceCardsFromOfficialSnapshot, typeof priceCardsFromSourceCache, typeof priceCardsFromUserPricing);',
        ],
        project_dir,
    )
    run(
        ["node", "--input-type=module", "-e", 'import { extractGeminiLiveUsage, extractGoogleInteractionsUsage } from "runcost"; console.log(typeof extractGeminiLiveUsage, typeof extractGoogleInteractionsUsage);'],
        project_dir,
    )
    js_live_check = project_dir / "live-check.mjs"
    js_live_check.write_text(
        """
import { DEFAULT_PRICE_SOURCE_PRIORITY, defaultPriceCards, fromResponse } from "runcost";

if (DEFAULT_PRICE_SOURCE_PRIORITY[0] !== "openai-official") {
  throw new Error(JSON.stringify(DEFAULT_PRICE_SOURCE_PRIORITY));
}
const model = "gemini-3.5-live-translate-preview";
const ledger = fromResponse({
  modelVersion: model,
  usageMetadata: {
    promptTokenCount: 250,
    promptTokensDetails: [{ modality: "AUDIO", tokenCount: 250 }],
    responseTokenCount: 500,
    responseTokensDetails: [{ modality: "AUDIO", tokenCount: 500 }],
    totalTokenCount: 750
  }
}, {
  provider: "google",
  surface: "google.gemini.live",
  model,
  priceCards: defaultPriceCards(),
  priceSourcePriority: DEFAULT_PRICE_SOURCE_PRIORITY
});
const components = Object.fromEntries(ledger.components.map((component) => [component.name, component]));
const sources = new Set(ledger.price_sources.map((source) => source.name));
if (ledger.total !== "0.011375") throw new Error(JSON.stringify(ledger));
if (components.input_audio_tokens.quantity !== "250") throw new Error(JSON.stringify(ledger));
if (components.output_audio_tokens.quantity !== "500") throw new Error(JSON.stringify(ledger));
if (sources.size !== 1 || !sources.has("google-official")) throw new Error(JSON.stringify(ledger));
console.log("javascript gemini live package smoke passed");
""",
        encoding="utf-8",
    )
    run(["node", str(js_live_check)], project_dir)
    js_provider_check = project_dir / "provider-check.mjs"
    js_provider_check.write_text(
        """
import { DEFAULT_PRICE_SOURCE_PRIORITY, defaultPriceCards, fromResponse } from "runcost";

const cards = defaultPriceCards();
const cacheWrite = fromResponse({
  model: "gpt-5.6",
  usage: {
    input_tokens: 1000,
    input_tokens_details: { cached_tokens: 200, cache_write_tokens: 100 },
    output_tokens: 100,
    output_tokens_details: { reasoning_tokens: 20 }
  }
}, {
  provider: "openai",
  surface: "openai.responses",
  priceCards: cards,
  priceSourcePriority: DEFAULT_PRICE_SOURCE_PRIORITY
});
if (cacheWrite.total !== "0.007225") throw new Error(JSON.stringify(cacheWrite));

const luna = (inputTokens) => fromResponse({
  model: "gpt-5.6-luna",
  usage: {
    input_tokens: inputTokens,
    input_tokens_details: { cached_tokens: 0, cache_write_tokens: 0 },
    output_tokens: 1,
    output_tokens_details: { reasoning_tokens: 0 }
  }
}, {
  provider: "openai",
  surface: "openai.responses",
  priceCards: cards,
  priceSourcePriority: DEFAULT_PRICE_SOURCE_PRIORITY
});
if (luna(272000).total !== "0.272006") throw new Error(JSON.stringify(luna(272000)));
if (luna(272001).total !== "0.544011") throw new Error(JSON.stringify(luna(272001)));
const priority = fromResponse({
  model: "gpt-5.6-sol",
  service_tier: "priority",
  usage: {
    input_tokens: 272001,
    input_tokens_details: { cached_tokens: 0, cache_write_tokens: 0 },
    output_tokens: 1,
    output_tokens_details: { reasoning_tokens: 0 }
  }
}, {
  provider: "openai",
  surface: "openai.responses",
  priceCards: cards,
  priceSourcePriority: DEFAULT_PRICE_SOURCE_PRIORITY
});
if (priority.total !== "0" || !priority.warnings.some(({ code }) => code === "long_context_rule_missing")) {
  throw new Error(JSON.stringify(priority));
}

const metaCard = {
  schema_version: "0.1",
  id: "meta:muse-spark-1.1:install-smoke",
  provider: "meta",
  surface: "meta.chat_completions",
  model: "muse-spark-1.1",
  components: [
    { usage_component: "input_uncached_tokens", unit: "token", price: { amount: "1", currency: "USD", per: "1000000" } },
    { usage_component: "input_cache_read_tokens", unit: "token", price: { amount: "0.1", currency: "USD", per: "1000000" } },
    { usage_component: "output_text_tokens", unit: "token", price: { amount: "4", currency: "USD", per: "1000000" } },
    { usage_component: "output_reasoning_tokens", unit: "token", price: { amount: "4", currency: "USD", per: "1000000" } }
  ],
  source: { name: "install-smoke" }
};
const meta = fromResponse({
  model: "muse-spark-1.1",
  usage: {
    prompt_tokens: 100,
    prompt_tokens_details: { cached_tokens: 20 },
    completion_tokens: 40,
    completion_tokens_details: { reasoning_tokens: 10 }
  }
}, {
  provider: "meta",
  surface: "meta.chat_completions",
  priceCards: [metaCard]
});
if (meta.total !== "0.000242") throw new Error(JSON.stringify(meta));
if (fromResponse({ model: "muse-spark-1.1", usage: null }, { provider: "meta", surface: "meta.responses", priceCards: [] }).total !== "0") {
  throw new Error("Meta null usage compatibility failed");
}
console.log("javascript GPT-5.6 and Meta package smoke passed");
""",
        encoding="utf-8",
    )
    run(["node", str(js_provider_check)], project_dir)


def check_go_install(source_root: Path, workdir: Path) -> None:
    project_dir = workdir / "go-project"
    project_dir.mkdir()
    (project_dir / "ledger_test.go").write_text(
        """package installcheck

import (
    "os"
    "testing"

    ledger "github.com/adamallcock/runcost/packages/go/ledger"
)

func TestImport(t *testing.T) {
    value := ledger.Object{"ok": true}
    if value["ok"] != true {
        t.Fatalf("unexpected import check value: %#v", value)
    }
    _ = ledger.FromOpenAIAgentsUsage
    _ = ledger.FromVercelAISDKStreamFinish
    _ = ledger.FromLangSmithRun
    _ = ledger.FromSemanticKernelTelemetry
    _ = ledger.FromOpenRouterSDKResponse
    if len(ledger.DefaultPriceCards()) < 7000 {
        t.Fatalf("unexpected bundled default price card count: %d", len(ledger.DefaultPriceCards()))
    }
    if len(ledger.DefaultPriceSourcePriority) == 0 || ledger.DefaultPriceSourcePriority[0] != "openai-official" {
        t.Fatalf("unexpected default price priority: %#v", ledger.DefaultPriceSourcePriority)
    }
    model := "gemini-3.5-live-translate-preview"
    liveResult := ledger.FromResponse(
        ledger.Object{
            "modelVersion": model,
            "usageMetadata": ledger.Object{
                "promptTokenCount": 250,
                "promptTokensDetails": []any{ledger.Object{"modality": "AUDIO", "tokenCount": 250}},
                "responseTokenCount": 500,
                "responseTokensDetails": []any{ledger.Object{"modality": "AUDIO", "tokenCount": 500}},
                "totalTokenCount": 750,
            },
        },
        ledger.Object{
            "provider": "google",
            "surface": "google.gemini.live",
            "model": model,
            "price_source_priority": ledger.DefaultPriceSourcePriority,
        },
        ledger.DefaultPriceCards(),
        nil,
    )
    if liveResult["total"] != "0.011375" {
        t.Fatalf("unexpected Gemini Live total: %#v", liveResult)
    }
    liveComponents := map[string]ledger.Object{}
    for _, rawComponent := range liveResult["components"].([]any) {
        component := rawComponent.(ledger.Object)
        liveComponents[component["name"].(string)] = component
    }
    if liveComponents["input_audio_tokens"]["quantity"] != "250" || liveComponents["output_audio_tokens"]["quantity"] != "500" {
        t.Fatalf("unexpected Gemini Live components: %#v", liveResult)
    }
    liveSources := liveResult["price_sources"].([]any)
    if len(liveSources) != 1 || liveSources[0].(ledger.Object)["name"] != "google-official" {
        t.Fatalf("unexpected Gemini Live price sources: %#v", liveResult)
    }
    cacheWrite := ledger.FromResponse(
        ledger.Object{
            "model": "gpt-5.6",
            "usage": ledger.Object{
                "input_tokens": 1000,
                "input_tokens_details": ledger.Object{"cached_tokens": 200, "cache_write_tokens": 100},
                "output_tokens": 100,
                "output_tokens_details": ledger.Object{"reasoning_tokens": 20},
            },
        },
        ledger.Object{
            "provider": "openai",
            "surface": "openai.responses",
            "price_source_priority": ledger.DefaultPriceSourcePriority,
        },
        ledger.DefaultPriceCards(),
        nil,
    )
    if cacheWrite["total"] != "0.007225" {
        t.Fatalf("unexpected GPT-5.6 cache-write total: %#v", cacheWrite)
    }

    luna := func(inputTokens int) ledger.Object {
        return ledger.FromResponse(
            ledger.Object{
                "model": "gpt-5.6-luna",
                "usage": ledger.Object{
                    "input_tokens": inputTokens,
                    "input_tokens_details": ledger.Object{"cached_tokens": 0, "cache_write_tokens": 0},
                    "output_tokens": 1,
                    "output_tokens_details": ledger.Object{"reasoning_tokens": 0},
                },
            },
            ledger.Object{
                "provider": "openai",
                "surface": "openai.responses",
                "price_source_priority": ledger.DefaultPriceSourcePriority,
            },
            ledger.DefaultPriceCards(),
            nil,
        )
    }
    if short := luna(272000); short["total"] != "0.272006" {
        t.Fatalf("unexpected GPT-5.6 short-boundary total: %#v", short)
    }
    if long := luna(272001); long["total"] != "0.544011" {
        t.Fatalf("unexpected GPT-5.6 long-boundary total: %#v", long)
    }
    priority := ledger.FromResponse(
        ledger.Object{
            "model": "gpt-5.6-sol",
            "service_tier": "priority",
            "usage": ledger.Object{
                "input_tokens": 272001,
                "input_tokens_details": ledger.Object{"cached_tokens": 0, "cache_write_tokens": 0},
                "output_tokens": 1,
                "output_tokens_details": ledger.Object{"reasoning_tokens": 0},
            },
        },
        ledger.Object{
            "provider": "openai",
            "surface": "openai.responses",
            "price_source_priority": ledger.DefaultPriceSourcePriority,
        },
        ledger.DefaultPriceCards(),
        nil,
    )
    priorityWarning := false
    for _, rawWarning := range priority["warnings"].([]any) {
        if rawWarning.(ledger.Object)["code"] == "long_context_rule_missing" {
            priorityWarning = true
        }
    }
    if priority["total"] != "0" || !priorityWarning {
        t.Fatalf("GPT-5.6 Priority long context must fail closed: %#v", priority)
    }

    metaCard := ledger.Object{
        "schema_version": "0.1",
        "id": "meta:muse-spark-1.1:install-smoke",
        "provider": "meta",
        "surface": "meta.chat_completions",
        "model": "muse-spark-1.1",
        "components": []any{
            ledger.Object{"usage_component": "input_uncached_tokens", "unit": "token", "price": ledger.Object{"amount": "1", "currency": "USD", "per": "1000000"}},
            ledger.Object{"usage_component": "input_cache_read_tokens", "unit": "token", "price": ledger.Object{"amount": "0.1", "currency": "USD", "per": "1000000"}},
            ledger.Object{"usage_component": "output_text_tokens", "unit": "token", "price": ledger.Object{"amount": "4", "currency": "USD", "per": "1000000"}},
            ledger.Object{"usage_component": "output_reasoning_tokens", "unit": "token", "price": ledger.Object{"amount": "4", "currency": "USD", "per": "1000000"}},
        },
        "source": ledger.Object{"name": "install-smoke"},
    }
    meta := ledger.FromResponse(
        ledger.Object{
            "model": "muse-spark-1.1",
            "usage": ledger.Object{
                "prompt_tokens": 100,
                "prompt_tokens_details": ledger.Object{"cached_tokens": 20},
                "completion_tokens": 40,
                "completion_tokens_details": ledger.Object{"reasoning_tokens": 10},
            },
        },
        ledger.Object{"provider": "meta", "surface": "meta.chat_completions"},
        []any{metaCard},
        nil,
    )
    if meta["total"] != "0.000242" {
        t.Fatalf("unexpected Meta package total: %#v", meta)
    }
    metaNull := ledger.FromResponse(
        ledger.Object{"model": "muse-spark-1.1", "usage": nil},
        ledger.Object{"provider": "meta", "surface": "meta.responses"},
        []any{},
        nil,
    )
    if metaNull["total"] != "0" {
        t.Fatalf("unexpected Meta null-usage total: %#v", metaNull)
    }
    result := ledger.AggregateCostLedgers([]any{}, ledger.Object{
        "stream_final_usage_expected": true,
        "stream_final_usage_present": false,
    })
    if result["total"] != "0" {
        t.Fatalf("unexpected aggregate total: %#v", result["total"])
    }
    typedResult := ledger.CalculateCostTyped(
        ledger.UsageLedger{
            SchemaVersion: "0.1",
            Provider: "test",
            Surface: "test.responses",
            Model: ledger.ModelIdentity{
                Requested: "test-model",
                Billed: "test-model",
                AliasResolution: "none",
            },
            Components: []ledger.UsageComponent{
                {Name: "input_uncached_tokens", Quantity: "100", Unit: "token"},
            },
        },
        []ledger.PriceCard{
            {
                SchemaVersion: "0.1",
                ID: "test:test-model:typed",
                Provider: "test",
                Surface: "test.responses",
                Model: "test-model",
                Components: []ledger.PriceComponent{
                    {
                        UsageComponent: "input_uncached_tokens",
                        Unit: "token",
                        Price: ledger.Price{Amount: "1", Currency: "USD", Per: "1000000"},
                    },
                },
                Source: ledger.Source{Name: "typed-install-check"},
            },
        },
        nil,
    )
    if typedResult["total"] != "0.0001" {
        t.Fatalf("unexpected typed total: %#v", typedResult["total"])
    }
    cards := ledger.PriceCardsFromSourceCache(ledger.Object{"price_cards": []any{
        ledger.Object{
            "schema_version": "0.1",
            "id": "test:test:source-cache",
            "provider": "test",
            "model": "test",
            "components": []any{ledger.Object{
                "usage_component": "input_uncached_tokens",
                "unit": "token",
                "price": ledger.Object{"amount": "1", "currency": "USD", "per": "1000000"},
            }},
            "source": ledger.Object{"name": "test"},
        },
    }})
    if len(cards) != 1 {
        t.Fatalf("unexpected source-cache card count: %d", len(cards))
    }
    if err := os.WriteFile("prices.json", []byte(`{"provider":"test","models":[{"id":"test","prices":{"input":"1"}}]}`), 0o600); err != nil {
        t.Fatal(err)
    }
    fileCards, err := ledger.PriceCardsFromJSONFile("prices.json", "user-pricing")
    if err != nil {
        t.Fatal(err)
    }
    if len(fileCards) != 1 {
        t.Fatalf("unexpected file card count: %d", len(fileCards))
    }
    if err := os.WriteFile("prices.yaml", []byte(`provider: test
models:
  - id: test
    prices:
      input: "1"
`), 0o600); err != nil {
        t.Fatal(err)
    }
    yamlCards, err := ledger.PriceCardsFromYAMLFile("prices.yaml", "user-pricing")
    if err != nil {
        t.Fatal(err)
    }
    if len(yamlCards) != 1 {
        t.Fatalf("unexpected YAML file card count: %d", len(yamlCards))
    }
    modelsDevCards := ledger.PriceCardsFromModelsDev(ledger.Object{
        "test": ledger.Object{
            "models": ledger.Object{
                "test-model": ledger.Object{"cost": ledger.Object{"input": 1}},
            },
        },
    })
    if len(modelsDevCards) != 1 {
        t.Fatalf("unexpected models.dev card count: %d", len(modelsDevCards))
    }
    officialCards := ledger.PriceCardsFromOfficialSnapshot(ledger.Object{
        "provider": "test",
        "rows": []any{ledger.Object{"model": "test-model", "input": 1}},
    })
    if len(officialCards) != 1 {
        t.Fatalf("unexpected official snapshot card count: %d", len(officialCards))
    }
}
""",
        encoding="utf-8",
    )
    run(["go", "mod", "init", "runcost-install-check"], project_dir)
    run(["go", "mod", "edit", "-replace", f"github.com/adamallcock/runcost={source_root}"], project_dir)
    run(["go", "get", "github.com/adamallcock/runcost/packages/go/ledger"], project_dir)
    run(["go", "test", "./..."], project_dir)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="runcost-install-check-") as temp:
        workdir = Path(temp)
        source_root = copy_source_tree(workdir)
        check_python_install(source_root, workdir)
        check_javascript_install(source_root, workdir)
        check_go_install(source_root, workdir)
    print("Package install checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
