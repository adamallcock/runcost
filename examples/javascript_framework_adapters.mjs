import {
  createRunCostVercelOnFinish,
  fromOpenRouterSDKResponse,
  fromVercelAISDKStreamFinish
} from "../packages/javascript/core/index.js";

function tokenPriceCard(provider, surface, model) {
  return {
    schema_version: "0.1",
    id: `${provider}:${model}:${surface}`,
    provider,
    surface,
    model,
    components: [
      {
        usage_component: "input_uncached_tokens",
        unit: "token",
        price: { amount: "1", currency: "USD", per: "1000000" }
      },
      {
        usage_component: "input_cache_read_tokens",
        unit: "token",
        price: { amount: "0.1", currency: "USD", per: "1000000" }
      },
      {
        usage_component: "input_cache_write_tokens",
        unit: "token",
        price: { amount: "1.25", currency: "USD", per: "1000000" }
      },
      {
        usage_component: "output_text_tokens",
        unit: "token",
        price: { amount: "2", currency: "USD", per: "1000000" }
      },
      {
        usage_component: "output_reasoning_tokens",
        unit: "token",
        price: { amount: "2", currency: "USD", per: "1000000" }
      }
    ],
    source: { name: "framework-example", retrieved_at: "2026-05-27T00:00:00Z" }
  };
}

const vercelFinish = {
  response: { modelId: "gpt-framework-example" },
  totalUsage: {
    inputTokens: 720,
    inputTokenDetails: {
      cacheReadTokens: 100,
      cacheWriteTokens: 40
    },
    outputTokens: 160,
    outputTokenDetails: {
      reasoningTokens: 35
    }
  }
};

const vercelCards = [tokenPriceCard("openai", "framework.vercel_ai_sdk", "gpt-framework-example")];
const vercelLedger = fromVercelAISDKStreamFinish(vercelFinish, {
  provider: "openai",
  surface: "framework.vercel_ai_sdk",
  model: "gpt-framework-example",
  priceCards: vercelCards
});

const onFinish = createRunCostVercelOnFinish({
  provider: "openai",
  surface: "framework.vercel_ai_sdk",
  model: "gpt-framework-example",
  priceCards: vercelCards
});
onFinish(vercelFinish);

const openRouterResponse = {
  id: "chatcmpl-framework-example",
  model: "openai/gpt-framework-example",
  usage: {
    prompt_tokens: 450,
    prompt_tokens_details: { cached_tokens: 75 },
    completion_tokens: 100,
    completion_tokens_details: { reasoning_tokens: 25 },
    cost: 0.0005575
  }
};

const openRouterLedger = fromOpenRouterSDKResponse(openRouterResponse, {
  surface: "openrouter.chat_completions",
  priceCards: [tokenPriceCard("openrouter", "openrouter.chat_completions", "openai/gpt-framework-example")],
  providerReportedCost: openRouterResponse.usage.cost
});

console.log(
  JSON.stringify(
    {
      vercel_total: vercelLedger.total,
      vercel_on_finish_total: onFinish.latest.total,
      openrouter_total: openRouterLedger.total,
      openrouter_warnings: openRouterLedger.warnings.map((warning) => warning.code)
    },
    null,
    2
  )
);
