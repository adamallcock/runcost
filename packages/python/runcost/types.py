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
    total_input_tokens: DecimalString
    stale_after_days: int
    price_stale_after_days: int
    request_id: str
    trace_id: str


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
    metadata: Dict[str, Any]


class UsageLedger(TypedDict, total=False):
    schema_version: SchemaVersion
    provider: str
    surface: str
    model: UsageModel
    context: UsageContext
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


class PriceCard(TypedDict, total=False):
    schema_version: SchemaVersion
    id: str
    provider: str
    surface: str
    model: str
    aliases: List[str]
    service_tier: str
    region: str
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
