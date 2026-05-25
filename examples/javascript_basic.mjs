import { fromResponse } from "../packages/javascript/core/index.js";

const response = {
  id: "resp_example",
  object: "response",
  model: "gpt-5.4-2026-05-24",
  usage: {
    input_tokens: 100,
    input_tokens_details: { cached_tokens: 25 },
    output_tokens: 40,
    output_tokens_details: { reasoning_tokens: 10 },
    total_tokens: 140
  }
};

const priceCards = [
  {
    schema_version: "0.1",
    id: "openai:gpt-5.4:example",
    provider: "openai",
    surface: "openai.responses",
    model: "gpt-5.4",
    aliases: ["gpt-5.4-2026-05-24"],
    components: [
      {
        usage_component: "input_uncached_tokens",
        unit: "token",
        price: { amount: "0.000001", currency: "USD", per: "1" }
      },
      {
        usage_component: "input_cache_read_tokens",
        unit: "token",
        price: { amount: "0.0000001", currency: "USD", per: "1" }
      },
      {
        usage_component: "output_text_tokens",
        unit: "token",
        price: { amount: "0.000004", currency: "USD", per: "1" }
      },
      {
        usage_component: "output_reasoning_tokens",
        unit: "token",
        price: { amount: "0.000004", currency: "USD", per: "1" }
      }
    ],
    source: {
      name: "example",
      retrieved_at: "2026-05-24T00:00:00Z"
    }
  }
];

const ledger = fromResponse(response, {
  provider: "openai",
  surface: "openai.responses",
  model: "gpt-5.4",
  priceCards,
  discountPolicies: [
    {
      schema_version: "0.1",
      id: "openai-four-percent",
      match: { provider: "openai" },
      adjustment: { type: "percentage_discount", value: "4" }
    }
  ]
});

console.log(JSON.stringify(ledger, null, 2));
