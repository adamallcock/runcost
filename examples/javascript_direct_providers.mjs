import { fromResponse } from "../packages/javascript/core/index.js";

const providers = {
  tinker: ["tinker.chat_completions", "thinkingmachines/Inkling", "chat"],
  nvidia: ["nvidia.chat_completions", "nvidia-fixture", "chat"],
  ai21: ["ai21.chat_completions", "jamba-fixture", "chat"],
  arcee: ["arcee.chat_completions", "arcee-fixture", "chat"],
  cohere: ["cohere.chat_completions_compatible", "command-fixture", "chat"],
  dashscope: ["dashscope.chat_completions", "qwen-fixture", "chat"],
  inception: ["inception.chat_completions", "mercury-fixture", "chat"],
  poolside: ["poolside.chat_completions", "poolside-fixture", "chat"],
  xiaomi: ["xiaomi.chat_completions", "mimo-fixture", "chat"],
  zai: ["zai.chat_completions", "glm-fixture", "chat"],
  minimax: ["minimax.messages", "minimax-fixture", "message"]
};

function priceCard(provider, surface, model) {
  return {
    schema_version: "0.1", id: `example:${provider}:${model}`, provider, surface, model,
    components: [
      { usage_component: "input_uncached_tokens", unit: "token", price: { amount: "1", currency: "USD", per: "1000000" } },
      { usage_component: "output_text_tokens", unit: "token", price: { amount: "2", currency: "USD", per: "1000000" } }
    ],
    source: { name: "example" }
  };
}

const totals = {};
for (const [provider, [surface, model, shape]] of Object.entries(providers)) {
  const response = shape === "message"
    ? { id: "msg_example", type: "message", model, usage: { input_tokens: 100, output_tokens: 40 } }
    : { object: "chat.completion", model, choices: [], usage: { prompt_tokens: 100, completion_tokens: 40 } };
  totals[provider] = fromResponse(response, { provider, priceCards: [priceCard(provider, surface, model)] }).total;
}

console.log(JSON.stringify(totals, Object.keys(totals).sort()));
