import expansionFixture from "../../fixtures/expansion/cases.json";

const price = (usageComponent, amount) => ({
  usage_component: usageComponent,
  unit: "token",
  price: { amount, currency: "USD", per: "1000000" }
});

// The playground prefers RunCost's external resolver. These three small cards
// are an explicitly labelled offline demo fallback, not package defaults.
const DEMO_FALLBACK_CARDS = {
  openai: [{
    schema_version: "0.1",
    id: "playground:openai:gpt-4.1-mini",
    provider: "openai",
    surface: "openai.responses",
    model: "gpt-4.1-mini",
    aliases: ["gpt-4.1-mini-2025-04-14"],
    components: [price("input_uncached_tokens", "0.4"), price("input_cache_read_tokens", "0.1"), price("output_text_tokens", "1.6"), price("output_reasoning_tokens", "1.6")],
    source: { name: "playground-offline-example", url: "https://platform.openai.com/docs/pricing", retrieved_at: "2026-06-19T01:24:34Z" }
  }],
  anthropic: [{
    schema_version: "0.1",
    id: "playground:anthropic:claude-sonnet-4",
    provider: "anthropic",
    surface: "anthropic.messages",
    model: "claude-sonnet-4-20250514",
    components: [price("input_uncached_tokens", "3"), price("input_cache_read_tokens", "0.3"), price("input_cache_write_tokens", "3.75"), price("output_text_tokens", "15")],
    source: { name: "playground-offline-example", url: "https://platform.claude.com/docs/en/about-claude/pricing", retrieved_at: "2026-06-19T01:24:34Z" }
  }],
  google: [{
    schema_version: "0.1",
    id: "playground:google:gemini-2.5-flash",
    provider: "google",
    surface: "google.gemini.generate_content",
    model: "gemini-2.5-flash",
    service_tier: "standard",
    components: [price("input_uncached_tokens", "0.30"), price("input_cache_read_tokens", "0.03"), price("output_text_tokens", "2.50"), price("output_reasoning_tokens", "2.50")],
    source: { name: "playground-offline-example", url: "https://ai.google.dev/gemini-api/docs/pricing", retrieved_at: "2026-06-23T00:00:00Z" }
  }]
};

export const PROVIDERS = {
  openai: {
    label: "OpenAI",
    endpointLabel: "Responses",
    surface: "openai.responses",
    model: "gpt-4.1-mini",
    priceCards: DEMO_FALLBACK_CARDS.openai,
    response: {
      id: "resp_public_demo",
      object: "response",
      created_at: 1747062483,
      model: "gpt-4.1-mini-2025-04-14",
      usage: {
        input_tokens: 1842,
        input_tokens_details: { cached_tokens: 1024 },
        output_tokens: 1026,
        output_tokens_details: { reasoning_tokens: 0 },
        total_tokens: 2868
      }
    }
  },
  anthropic: {
    label: "Anthropic",
    endpointLabel: "Messages",
    surface: "anthropic.messages",
    model: "claude-sonnet-4-20250514",
    priceCards: DEMO_FALLBACK_CARDS.anthropic,
    response: {
      id: "msg_public_demo",
      type: "message",
      model: "claude-sonnet-4-20250514",
      usage: {
        input_tokens: 818,
        cache_read_input_tokens: 1024,
        output_tokens: 1026
      }
    }
  },
  google: {
    label: "Gemini",
    endpointLabel: "generateContent",
    surface: "google.gemini.generate_content",
    model: "gemini-2.5-flash",
    priceCards: DEMO_FALLBACK_CARDS.google,
    response: {
      modelVersion: "gemini-2.5-flash",
      usageMetadata: {
        promptTokenCount: 1842,
        cachedContentTokenCount: 1024,
        candidatesTokenCount: 800,
        thoughtsTokenCount: 226,
        totalTokenCount: 2868
      }
    }
  }
};

export const PROVIDER_FIXTURES = Object.entries(PROVIDERS).map(([id, value]) => ({
  id,
  label: `${value.label} / ${value.endpointLabel} / ${value.model}`
}));

const batchCaseIds = [
  "openai-chat-batch-partial",
  "anthropic-message-batch-partial",
  "gemini-developer-batch-partial",
  "vertex-gemini-batch",
  "bedrock-model-invocation-batch",
  "kimi-batch",
  "dashscope-batch"
];

export const BATCH_CASES = batchCaseIds.map((id) => {
  const fixtureCase = expansionFixture.cases.find((candidate) => candidate.id === id);
  const input = fixtureCase.input;
  return {
    id,
    label: ({ openai: "OpenAI", anthropic: "Anthropic", google: "Gemini", vertex: "Vertex", bedrock: "Bedrock", kimi: "Kimi", dashscope: "DashScope" })[input.provider],
    input,
    priceCards: expansionFixture.price_card_sets[input.price_cards_ref]
  };
});

export const COMPONENT_LABELS = {
  input_uncached_tokens: ["Input", "Billable uncached input"],
  input_cache_read_tokens: ["Cached input", "Discounted cached input"],
  input_cache_write_tokens: ["Cache write", "Prompt cache creation"],
  output_text_tokens: ["Output", "Generated output"],
  output_reasoning_tokens: ["Reasoning output", "Hidden thinking tokens"],
  input_image_tokens: ["Image input", "Input image tokens"],
  output_image_tokens: ["Image output", "Generated image tokens"],
  embedding_tokens: ["Embeddings", "Embedding input tokens"]
};

export const PROBLEM_CONTENT = {
  home: {
    heading: "Explain the exact cost of every LLM response.",
    body: "Paste the response you already receive. RunCost separates cached input, reasoning output, tools, tiers, and batch discounts—then shows every rate and source.",
    provider: "OpenAI"
  },
  openai: {
    heading: "Calculate the cost of an OpenAI response.",
    body: "Paste the response you already receive. RunCost separates cached input, reasoning output, tools, tiers, and batch discounts—then shows every rate and source.",
    provider: "OpenAI"
  },
  anthropic: {
    heading: "Calculate the cost of an Anthropic response.",
    body: "Separate uncached input, cache reads, cache writes, output, and Message Batch discounts from the usage object Claude already returns.",
    provider: "Anthropic"
  },
  gemini: {
    heading: "Calculate the cost of a Gemini response.",
    body: "Turn usageMetadata into a ledger for cached content, thinking tokens, media modalities, service tiers, and Batch API pricing.",
    provider: "Gemini"
  },
  "batch-problem": {
    heading: "Calculate the cost of an LLM batch.",
    body: "Normalize OpenAI, Anthropic, Gemini, Vertex, Bedrock, Kimi, and DashScope result files without hiding failed or pending items.",
    provider: "Batch APIs"
  }
};
