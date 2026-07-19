from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

from .generated.taxonomy import (
    AliasResolution,
    DebugDecisionType,
    UsageComponentName,
    UsageUnit,
    WarningCode,
)

SchemaVersion = Literal["0.1"]
DecimalString = str
MoneyString = str
CalculationMode = Literal["compatibility", "strict"]


class UsageModel(TypedDict, total=False):
    requested: str
    returned: str
    billed: str
    alias_resolution: AliasResolution


class UsageContext(TypedDict, total=False):
    service_tier: str
    region: str
    priced_at: str
    pricing_period: str
    total_input_tokens: DecimalString
    stale_after_days: int
    price_stale_after_days: int
    request_id: str
    trace_id: str


class Attribution(TypedDict, total=False):
    run_id: str
    session_id: str
    workflow: str
    tenant_id: str
    feature: str
    tags: Dict[str, str]


class UsageTool(TypedDict, total=False):
    provider: str
    name: str
    billing_source: Literal["provider", "gateway", "user", "unknown"]


class UsageComponent(TypedDict, total=False):
    name: UsageComponentName
    quantity: DecimalString
    unit: UsageUnit
    tool: UsageTool
    source_path: str
    billing_model: str
    metadata: Dict[str, Any]


class UsageLedger(TypedDict, total=False):
    schema_version: SchemaVersion
    provider: str
    surface: str
    model: UsageModel
    context: UsageContext
    attribution: Attribution
    components: List[UsageComponent]
    raw_usage: Dict[str, Any]
    metadata: Dict[str, Any]


class EffectiveDateRange(TypedDict, total=False):
    from_: Optional[str]
    to: Optional[str]


class Price(TypedDict):
    amount: MoneyString
    currency: str
    per: DecimalString


class PriceComponentConditions(TypedDict, total=False):
    min_total_input_tokens: DecimalString
    max_total_input_tokens: DecimalString


class PriceComponent(TypedDict, total=False):
    usage_component: str
    unit: UsageUnit
    price: Price
    discount_eligible: bool
    conditions: PriceComponentConditions
    notes: str


class SourceInfo(TypedDict, total=False):
    name: str
    url: str
    retrieved_at: str
    version: str
    license: str


class BillingWindow(TypedDict):
    period: str
    start: str
    end: str


class _BillingScheduleRequired(TypedDict):
    timezone: str
    default_period: str
    windows: List[BillingWindow]


class BillingSchedule(_BillingScheduleRequired, total=False):
    boundary_policy: Literal["start_inclusive_end_exclusive"]


class PriceCard(TypedDict, total=False):
    schema_version: SchemaVersion
    id: str
    provider: str
    surface: str
    model: str
    aliases: List[str]
    service_tier: str
    region: str
    pricing_period: str
    billing_schedule: BillingSchedule
    effective: Dict[str, Optional[str]]
    components: List[PriceComponent]
    source: SourceInfo
    metadata: Dict[str, Any]


class DiscountPolicyMatch(TypedDict, total=False):
    provider: str
    surface: str
    model: str
    service_tier: str
    region: str
    components: List[str]
    exclude_components: List[str]
    tags: Dict[str, str]


class DiscountAdjustment(TypedDict):
    type: Literal["multiplier", "percentage_discount", "percentage_markup"]
    value: DecimalString


class DiscountPolicy(TypedDict, total=False):
    schema_version: SchemaVersion
    id: str
    description: str
    match: DiscountPolicyMatch
    effective: Dict[str, Optional[str]]
    adjustment: DiscountAdjustment
    precedence: int
    metadata: Dict[str, Any]


class CostModel(TypedDict, total=False):
    requested: str
    returned: str
    billed: str
    alias_resolution: str


class CostComponent(TypedDict, total=False):
    name: str
    quantity: DecimalString
    unit: str
    unit_price: MoneyString
    cost: MoneyString
    price_card_id: str
    discount_eligible: bool
    metadata: Dict[str, Any]


class AppliedDiscount(TypedDict):
    policy_id: str
    component: str
    amount: MoneyString


class WarningIdentityMetadata(TypedDict):
    provider: str
    surface: str
    model: str


class AliasInferredWarningMetadata(TypedDict):
    requested_model: str
    billed_model: str


class PriceStaleWarningMetadata(TypedDict):
    source: str
    age_days: int
    threshold_days: int
    retrieved_at: str
    priced_at: str


class PriceSourceDisagreementWarningMetadata(TypedDict):
    component: str
    selected_price_card_id: str
    candidate_price_card_ids: List[str]


class UsageFieldWarningMetadata(TypedDict):
    field: str


class ComponentUnpricedWarningMetadata(TypedDict):
    component: str
    unit: str
    model: str


class SourceCapabilityUnsupportedWarningMetadata(TypedDict):
    component: str
    unit: str
    price_card_id: str
    source: str


class ServiceTierUnsupportedWarningMetadata(TypedDict):
    model: str
    service_tier: str


class LongContextRuleMissingWarningMetadata(TypedDict):
    component: str
    unit: str
    total_input_tokens: DecimalString


class DiscountNotAppliedWarningMetadata(TypedDict):
    policy_id: str


class _StreamUsageMissingRequired(TypedDict):
    actual_ledger_count: int


class StreamUsageMissingWarningMetadata(_StreamUsageMissingRequired, total=False):
    expected_ledger_count: int


class HistoricalPriceMissingWarningMetadata(TypedDict):
    model: str
    priced_at: str


class PricingPeriodRequiredWarningMetadata(TypedDict):
    provider: str
    surface: str
    model: str
    pricing_periods: List[str]


class PricingPeriodUnsupportedWarningMetadata(TypedDict):
    provider: str
    surface: str
    model: str
    pricing_period: str


class BillingScheduleUnsupportedWarningMetadata(TypedDict):
    provider: str
    surface: str
    model: str
    timezone: str


class ProviderReportedCostWarningMetadata(TypedDict):
    provider_reported_cost: MoneyString
    calculated_total: MoneyString


WarningMetadata = Union[
    WarningIdentityMetadata,
    AliasInferredWarningMetadata,
    PriceStaleWarningMetadata,
    PriceSourceDisagreementWarningMetadata,
    UsageFieldWarningMetadata,
    ComponentUnpricedWarningMetadata,
    SourceCapabilityUnsupportedWarningMetadata,
    ServiceTierUnsupportedWarningMetadata,
    LongContextRuleMissingWarningMetadata,
    DiscountNotAppliedWarningMetadata,
    StreamUsageMissingWarningMetadata,
    HistoricalPriceMissingWarningMetadata,
    PricingPeriodRequiredWarningMetadata,
    PricingPeriodUnsupportedWarningMetadata,
    BillingScheduleUnsupportedWarningMetadata,
    ProviderReportedCostWarningMetadata,
]


class _CostWarningRequired(TypedDict):
    code: WarningCode
    message: str
    metadata: WarningMetadata


class CostWarning(_CostWarningRequired, total=False):
    path: str


class DebugDecision(TypedDict, total=False):
    type: DebugDecisionType
    component: str
    model: str
    from_: str
    to: str
    resolution: str
    price_card_id: str
    selected_price_card_id: str
    selected_source: str
    pricing_period: str
    period_selection: str
    pricing_window: str
    pricing_timezone: str
    candidate_price_card_ids: List[str]
    source_priority: List[str]
    policy_id: str
    amount: str
    warning_code: str
    message: str


class DebugTraceSummary(TypedDict):
    priced_components: int
    unpriced_components: int
    warnings: int
    applied_discounts: int


class DebugTrace(TypedDict):
    schema_version: SchemaVersion
    decisions: List[DebugDecision]
    summary: DebugTraceSummary


class CostLedger(TypedDict, total=False):
    schema_version: SchemaVersion
    provider: str
    surface: str
    model: CostModel
    currency: str
    components: List[CostComponent]
    total: MoneyString
    price_sources: List[SourceInfo]
    applied_discounts: List[AppliedDiscount]
    warnings: List[CostWarning]
    debug_trace: DebugTrace
    metadata: Dict[str, Any]
    attribution: Attribution


class BatchError(TypedDict, total=False):
    code: Union[str, int]
    message: str
    type: str


class BatchItem(TypedDict, total=False):
    id: str
    status: Literal["succeeded", "errored", "canceled", "expired", "pending"]
    http_status: int
    ledger: CostLedger
    error: BatchError
    attribution: Attribution
    metadata: Dict[str, Any]


class BatchSummary(TypedDict):
    total: int
    succeeded: int
    failed: int
    pending: int
    total_cost: MoneyString


class BatchCostLedger(TypedDict, total=False):
    schema_version: SchemaVersion
    provider: str
    surface: str
    batch_id: str
    currency: str
    items: List[BatchItem]
    summary: BatchSummary
    aggregate: CostLedger
    warnings: List[Dict[str, Any]]
    attribution: Attribution
    metadata: Dict[str, Any]


class BudgetEvaluation(TypedDict, total=False):
    schema_version: SchemaVersion
    status: Literal["within_budget", "warning", "exceeded"]
    estimated_cost: MoneyString
    budget: MoneyString
    remaining: MoneyString
    warning_threshold: DecimalString
    currency: str
    ledger: CostLedger


class CostReconciliation(TypedDict):
    schema_version: SchemaVersion
    status: Literal["matched", "within_tolerance", "mismatch"]
    calculated_total: MoneyString
    reported_total: MoneyString
    signed_residual: MoneyString
    absolute_residual: MoneyString
    tolerance: MoneyString
    currency: str


class CatalogArtifact(TypedDict, total=False):
    provider: str
    path: str
    sha256: str
    bytes: int
    price_card_count: int


class CatalogManifest(TypedDict):
    schema_version: SchemaVersion
    algorithm: Literal["sha256"]
    catalog: CatalogArtifact
    shards: List[CatalogArtifact]


class CatalogVerificationArtifact(TypedDict, total=False):
    path: str
    exists: bool
    sha256: Optional[str]
    matches: bool


class CatalogVerification(TypedDict):
    schema_version: SchemaVersion
    valid: bool
    algorithm: Literal["sha256"]
    artifacts: List[CatalogVerificationArtifact]


class PriceResolutionSource(TypedDict, total=False):
    name: str
    type: Literal["external", "user", "contract"]
    url: str
    cache_key: str
    status: Literal["selected", "refreshed", "cache_fresh", "cache_validated", "cache_stale", "unavailable"]
    retrieved_at: str
    validated_at: str
    checksum: str
    etag: str
    last_modified: str
    card_count: int
    priced_component_count: int
    applicable: bool
    selected: bool


class PriceResolution(TypedDict):
    schema_version: SchemaVersion
    selected_source: Optional[str]
    price_cards: List[PriceCard]
    sources: List[PriceResolutionSource]
    warnings: List[CostWarning]
    resolved_at: str
