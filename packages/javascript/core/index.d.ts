export type MoneyString = string;
export type DecimalString = string;
export type SchemaVersion = "0.1";
export type CalculationMode = "compatibility" | "strict";

export type UsageUnit =
  | "token"
  | "request"
  | "call"
  | "session"
  | "search"
  | "file"
  | "image"
  | "video"
  | "audio"
  | "second"
  | "hour"
  | "gb_day"
  | "usd"
  | "custom";

export type UsageComponentName =
  | "input_uncached_tokens"
  | "input_cache_read_tokens"
  | "input_cache_write_tokens"
  | "input_cache_write_1h_tokens"
  | "input_image_units"
  | "input_audio_tokens"
  | "input_image_tokens"
  | "input_video_tokens"
  | "output_text_tokens"
  | "output_reasoning_tokens"
  | "output_audio_tokens"
  | "output_image_tokens"
  | "output_video_tokens"
  | "embedding_tokens"
  | "request_units"
  | "web_search_units"
  | "file_search_units"
  | "code_interpreter_session_units"
  | "code_interpreter_call_units"
  | "computer_use_action_units"
  | "tool_call_units"
  | "tool_execution_seconds"
  | "rerank_search_units"
  | "image_generation_units"
  | "video_generation_units"
  | "audio_generation_units"
  | "transcription_seconds"
  | "endpoint_runtime_seconds"
  | "endpoint_instance_hours"
  | "custom_units";

export type AliasResolution =
  | "none"
  | "user_exact"
  | "source_exact"
  | "package_exact"
  | "provider_heuristic"
  | "unknown";

export interface UsageModel {
  requested: string;
  returned?: string;
  billed?: string;
  alias_resolution?: AliasResolution;
}

export interface UsageContext {
  service_tier?: string;
  region?: string;
  priced_at?: string;
  total_input_tokens?: number | string;
  stale_after_days?: number | string;
  price_stale_after_days?: number | string;
  request_id?: string;
  trace_id?: string;
  [key: string]: unknown;
}

export interface UsageTool {
  provider?: string;
  name?: string;
  billing_source?: "provider" | "gateway" | "user" | "unknown";
}

export interface UsageComponent {
  name: UsageComponentName;
  quantity: DecimalString;
  unit: UsageUnit;
  tool?: UsageTool;
  source_path?: string;
  metadata?: Record<string, unknown>;
}

export interface UsageLedger {
  schema_version: SchemaVersion;
  provider: string;
  surface: string;
  model: UsageModel;
  context?: UsageContext;
  components: UsageComponent[];
  raw_usage?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface EffectiveDateRange {
  from?: string | null;
  to?: string | null;
}

export interface Price {
  amount: MoneyString;
  currency: string;
  per: DecimalString;
}

export interface PriceComponent {
  usage_component: string;
  unit: UsageUnit;
  price: Price;
  discount_eligible?: boolean;
  conditions?: PriceComponentConditions;
  notes?: string;
}

export interface PriceComponentConditions {
  min_total_input_tokens?: DecimalString;
  max_total_input_tokens?: DecimalString;
}

export interface SourceInfo {
  name: string;
  url?: string;
  retrieved_at?: string;
  version?: string;
  license?: string;
}

export interface PriceCard {
  schema_version: SchemaVersion;
  id: string;
  provider: string;
  surface?: string;
  model: string;
  aliases?: string[];
  service_tier?: string;
  region?: string;
  effective?: EffectiveDateRange;
  components: PriceComponent[];
  source: SourceInfo;
  metadata?: Record<string, unknown>;
}

export interface DiscountPolicyMatch {
  provider?: string;
  surface?: string;
  model?: string;
  service_tier?: string;
  region?: string;
  components?: string[];
  exclude_components?: string[];
  tags?: Record<string, string>;
}

export interface DiscountAdjustment {
  type: "multiplier" | "percentage_discount" | "percentage_markup";
  value: DecimalString;
}

export interface DiscountPolicy {
  schema_version: SchemaVersion;
  id: string;
  description?: string;
  match?: DiscountPolicyMatch;
  effective?: EffectiveDateRange;
  adjustment: DiscountAdjustment;
  precedence?: number;
  metadata?: Record<string, unknown>;
}

export interface CostModel {
  requested: string;
  returned?: string;
  billed: string;
  alias_resolution?: string;
}

export interface CostComponent {
  name: string;
  quantity: DecimalString;
  unit: string;
  unit_price: MoneyString;
  cost: MoneyString;
  price_card_id?: string;
  discount_eligible?: boolean;
  metadata?: Record<string, unknown>;
}

export interface AppliedDiscount {
  policy_id: string;
  component: string;
  amount: MoneyString;
}

export type WarningCode =
  | "unknown_provider"
  | "unknown_surface"
  | "unknown_model"
  | "alias_inferred"
  | "price_not_found"
  | "price_stale"
  | "price_source_disagreement"
  | "usage_field_ignored"
  | "inclusive_usage_ambiguous"
  | "component_unpriced"
  | "service_tier_unsupported"
  | "long_context_rule_missing"
  | "discount_not_applied"
  | "stream_usage_missing"
  | "historical_price_missing"
  | "tool_component_unpriced"
  | "provider_reported_cost_used"
  | "provider_reported_cost_mismatch";

export interface CostWarning {
  code: WarningCode;
  message: string;
  path?: string;
  metadata?: Record<string, unknown>;
}

export type DebugDecisionType =
  | "price_card_candidates"
  | "price_component_match"
  | "model_alias_resolution"
  | "discount_application"
  | "warning";

export interface DebugDecision {
  type: DebugDecisionType;
  component?: string;
  model?: string;
  from?: string;
  to?: string;
  resolution?: string;
  price_card_id?: string;
  selected_price_card_id?: string;
  selected_source?: string;
  candidate_price_card_ids?: string[];
  source_priority?: string[];
  policy_id?: string;
  amount?: string;
  warning_code?: WarningCode | string;
  message?: string;
  [key: string]: unknown;
}

export interface DebugTraceSummary {
  priced_components: number;
  unpriced_components: number;
  warnings: number;
  applied_discounts: number;
}

export interface DebugTrace {
  schema_version: SchemaVersion;
  decisions: DebugDecision[];
  summary: DebugTraceSummary;
}

export interface CostLedger {
  schema_version: SchemaVersion;
  provider: string;
  surface: string;
  model: CostModel;
  currency: string;
  components: CostComponent[];
  total: MoneyString;
  price_sources?: SourceInfo[];
  applied_discounts?: AppliedDiscount[];
  warnings: CostWarning[];
  debug_trace?: DebugTrace;
  metadata?: Record<string, unknown>;
}

export interface AggregateCostLedgersOptions {
  costLedgers?: CostLedger[];
  cost_ledgers?: CostLedger[];
  provider?: string;
  surface?: string;
  model?: string;
  mode?: CalculationMode;
  expectedLedgerCount?: number;
  expected_ledger_count?: number;
  streamFinalUsageExpected?: boolean;
  stream_final_usage_expected?: boolean;
  streamFinalUsagePresent?: boolean;
  stream_final_usage_present?: boolean;
}

export interface CalculateCostOptions {
  usageLedger: UsageLedger;
  priceCards: PriceCard[];
  discountPolicies?: DiscountPolicy[];
  mode?: CalculationMode;
  staleAfterDays?: number;
  stale_after_days?: number;
  providerReportedCost?: MoneyString;
  provider_reported_cost?: MoneyString;
  providerReportedCostMode?: "compare" | "use";
  provider_reported_cost_mode?: "compare" | "use";
  priceSourcePriority?: string[];
  price_source_priority?: string[];
  debugTrace?: boolean;
  debug_trace?: boolean;
}

export interface ExtractOptions {
  adapter?: string;
  framework?: string;
  provider?: string;
  surface: string;
  model?: string;
  ag2_usage_mode?: "actual" | "total" | "including_cached" | "usage_excluding_cached_inference" | "usage_including_cached_inference";
  usage_mode?: string;
}

export interface FromResponseOptions extends ExtractOptions {
  priceCards?: PriceCard[];
  discountPolicies?: DiscountPolicy[];
  mode?: CalculationMode;
  staleAfterDays?: number;
  stale_after_days?: number;
  providerReportedCost?: MoneyString;
  provider_reported_cost?: MoneyString;
  providerReportedCostMode?: "compare" | "use";
  provider_reported_cost_mode?: "compare" | "use";
  priceSourcePriority?: string[];
  price_source_priority?: string[];
  debugTrace?: boolean;
  debug_trace?: boolean;
}

export interface RunCostVercelMiddlewareOptions extends FromResponseOptions {
  attachCostLedger?: boolean;
  onCostLedger?: (
    ledger: CostLedger,
    context: {
      result: Record<string, unknown>;
      params?: unknown;
      model?: unknown;
    }
  ) => void;
}

export interface RunCostVercelMiddleware {
  ledgers: CostLedger[];
  readonly latest: CostLedger | null;
  wrapGenerate(args: {
    doGenerate: () => Promise<Record<string, unknown>>;
    params?: unknown;
    model?: unknown;
  }): Promise<Record<string, unknown>>;
}

export interface SourceAdapterOptions {
  retrievedAt?: string;
  retrieved_at?: string;
  sourceUrl?: string;
  source_url?: string;
  sourceName?: string;
  source_name?: string;
  provider?: string;
  surface?: string;
}

export function calculateCost(options: CalculateCostOptions): CostLedger;
export function aggregateCostLedgers(options: AggregateCostLedgersOptions): CostLedger;
export function extractUsageLedger(response: Record<string, unknown>, options: ExtractOptions): UsageLedger;
export function extractOpenAIResponsesUsage(response: Record<string, unknown>, options?: Partial<ExtractOptions>): UsageLedger;
export function extractOpenAIChatCompletionsUsage(response: Record<string, unknown>, options?: Partial<ExtractOptions>): UsageLedger;
export function extractOpenAICompatibleChatCompletionsUsage(response: Record<string, unknown>, options?: Partial<ExtractOptions>): UsageLedger;
export function extractOpenRouterChatCompletionsUsage(response: Record<string, unknown>, options?: Partial<ExtractOptions>): UsageLedger;
export function extractAnthropicMessagesUsage(response: Record<string, unknown>, options?: Partial<ExtractOptions>): UsageLedger;
export function extractGeminiGenerateContentUsage(response: Record<string, unknown>, options?: Partial<ExtractOptions>): UsageLedger;
export function extractBedrockConverseUsage(response: Record<string, unknown>, options?: Partial<ExtractOptions>): UsageLedger;
export function extractCohereChatUsage(response: Record<string, unknown>, options?: Partial<ExtractOptions>): UsageLedger;
export function extractLangChainChatUsage(response: Record<string, unknown>, options?: Partial<ExtractOptions>): UsageLedger;
export function extractVercelAISDKUsage(response: Record<string, unknown>, options?: Partial<ExtractOptions>): UsageLedger;
export function extractLlamaIndexTokenCounterUsage(response: Record<string, unknown>, options?: Partial<ExtractOptions>): UsageLedger;
export function extractHaystackGeneratorUsage(response: Record<string, unknown>, options?: Partial<ExtractOptions>): UsageLedger;
export function extractLiteLLMProxyResponseUsage(response: Record<string, unknown>, options?: Partial<ExtractOptions>): UsageLedger;
export function extractAG2UsageSummaryUsage(response: Record<string, unknown>, options?: Partial<ExtractOptions>): UsageLedger;
export function priceCardsFromLlmPrices(data: Record<string, unknown>, options?: SourceAdapterOptions): PriceCard[];
export function priceCardsFromLiteLLM(data: Record<string, unknown>, options?: SourceAdapterOptions): PriceCard[];
export function priceCardsFromOpenRouterModels(data: Record<string, unknown>, options?: SourceAdapterOptions): PriceCard[];
export function priceCardsFromPortkey(data: Record<string, unknown>, options?: SourceAdapterOptions): PriceCard[];
export function priceCardsFromSourceCache(data: Record<string, unknown>, options?: SourceAdapterOptions): PriceCard[];
export function priceCardsFromJSONFile(path: string, options?: SourceAdapterOptions & { sourceType?: string; source_type?: string }): PriceCard[];
export function priceCardsFromUserPricing(data: Record<string, unknown> | PriceCard[], options?: SourceAdapterOptions): PriceCard[];
export function priceCardsFromHelicone(data: Record<string, unknown>, options?: SourceAdapterOptions): PriceCard[];
export function fromResponse(response: Record<string, unknown>, options: FromResponseOptions): CostLedger;
export function fromLangChainMessage(message: Record<string, unknown>, options: FromResponseOptions): CostLedger;
export function fromVercelAISDKResult(result: Record<string, unknown>, options: FromResponseOptions): CostLedger;
export function fromLlamaIndexTokenCounter(counter: Record<string, unknown>, options: FromResponseOptions): CostLedger;
export function fromHaystackGeneratorResult(result: Record<string, unknown>, options: FromResponseOptions): CostLedger;
export function fromLiteLLMResponse(response: Record<string, unknown>, options: FromResponseOptions): CostLedger;
export function fromAG2UsageSummary(summary: Record<string, unknown>, options: FromResponseOptions): CostLedger;
export function createRunCostVercelMiddleware(options: RunCostVercelMiddlewareOptions): RunCostVercelMiddleware;
