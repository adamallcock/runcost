#!/usr/bin/env python3
"""Create a privacy-preserving RunCost comparison from OpenAI dashboard CSVs."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "python"))

from runcost import aggregate_cost_ledgers, estimate_cost_auto  # noqa: E402

from compare_invoice_dashboard import (  # noqa: E402
    build_comparison,
    validate_input_contract,
    validate_input_safety,
)

COST_REQUIRED_COLUMNS = {
    "start_time_iso",
    "end_time_iso",
    "amount_value",
    "amount_currency",
}
ACTIVITY_REQUIRED_COLUMNS = {
    "start_time_iso",
    "end_time_iso",
    "model",
    "batch",
    "service_tier",
    "num_model_requests",
    "input_tokens",
    "output_tokens",
    "input_cached_tokens",
    "input_cache_write_tokens",
    "input_uncached_tokens",
}
INCOMPLETE_WARNING_CODES = {
    "unknown_provider",
    "unknown_model",
    "price_not_found",
    "component_unpriced",
    "tool_component_unpriced",
    "source_capability_unsupported",
    "service_tier_unsupported",
    "long_context_rule_missing",
    "historical_price_missing",
    "pricing_period_required",
    "pricing_period_unsupported",
    "billing_schedule_unsupported",
}
KNOWN_EXPORT_TIERS = {"default", "flex-tier", "incentivized-tier"}


def decimal_text(value: Any) -> str:
    return format(Decimal(str(value)).normalize(), "f")


def normalized_ratio(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def nonnegative_decimal(value: Any, *, field: str) -> Decimal:
    try:
        parsed = Decimal(str(value or "0"))
    except Exception as exc:  # pragma: no cover - Decimal error types vary by runtime
        raise AssertionError(f"{field} must be numeric") from exc
    if not parsed.is_finite() or parsed < 0:
        raise AssertionError(f"{field} must be a finite non-negative number")
    return parsed


def read_csv(path: Path, *, required_columns: set[str], kind: str) -> list[dict[str, str]]:
    if not path.is_file():
        raise AssertionError(f"{kind} CSV does not exist")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = sorted(required_columns - columns)
        if missing:
            raise AssertionError(f"{kind} CSV is missing required columns: {', '.join(missing)}")
        rows = [dict(row) for row in reader]
    if not rows:
        raise AssertionError(f"{kind} CSV must contain at least one data row")
    return rows


def export_window(cost_rows: list[dict[str, str]], activity_rows: list[dict[str, str]]) -> str:
    starts = {
        str(row.get("start_time_iso") or "").strip()
        for row in [*cost_rows, *activity_rows]
    }
    ends = {
        str(row.get("end_time_iso") or "").strip()
        for row in [*cost_rows, *activity_rows]
    }
    if "" in starts or "" in ends:
        raise AssertionError("dashboard exports must include ISO start and end times")
    return f"{min(starts)}/{max(ends)}"


def provider_cost(cost_rows: list[dict[str, str]]) -> tuple[Decimal, str]:
    currencies = {
        str(row.get("amount_currency") or "").strip().upper()
        for row in cost_rows
    }
    if currencies != {"USD"}:
        raise AssertionError("dashboard cost comparison currently requires exactly one USD currency")
    total = sum(
        (nonnegative_decimal(row.get("amount_value"), field="amount_value") for row in cost_rows),
        Decimal("0"),
    )
    if total <= 0:
        raise AssertionError("dashboard cost export total must be positive")
    return total, "USD"


def parse_boolean(value: Any, *, field: str) -> bool:
    normalized = str(value or "").strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise AssertionError(f"{field} must be a boolean")


def warning_codes(ledger: dict[str, Any]) -> set[str]:
    return {
        str(warning.get("code"))
        for warning in ledger.get("warnings", [])
        if isinstance(warning, dict) and warning.get("code")
    }


def only_cache_write_is_unpriced(ledger: dict[str, Any]) -> bool:
    incomplete = warning_codes(ledger) & INCOMPLETE_WARNING_CODES
    if incomplete != {"component_unpriced"}:
        return False
    unpriced = [
        warning
        for warning in ledger.get("warnings", [])
        if isinstance(warning, dict) and warning.get("code") == "component_unpriced"
    ]
    return bool(unpriced) and all(
        warning.get("metadata", {}).get("component") == "input_cache_write_tokens"
        for warning in unpriced
    )


def tier_policy(row: dict[str, str]) -> tuple[str, list[dict[str, Any]], str]:
    is_batch = parse_boolean(row.get("batch"), field="batch")
    raw_tier = str(row.get("service_tier") or "").strip().lower()
    if raw_tier not in KNOWN_EXPORT_TIERS:
        raise AssertionError(f"unsupported OpenAI dashboard service tier: {raw_tier or 'missing'}")

    if is_batch:
        label = "batch"
    elif raw_tier == "flex-tier":
        label = "flex"
    elif raw_tier == "incentivized-tier":
        label = "incentivized"
    else:
        label = "standard"

    policies: list[dict[str, Any]] = []
    if label in {"batch", "flex"}:
        policies.append(
            {
                "schema_version": "0.1",
                "id": f"openai-{label}-public-fifty-percent",
                "match": {"provider": "openai"},
                "adjustment": {"type": "percentage_discount", "value": "50"},
            }
        )
    return label, policies, raw_tier


def activity_ledger(
    row: dict[str, str],
    *,
    price_cards: list[dict[str, Any]] | None,
    offline: bool,
    refresh: bool,
) -> tuple[dict[str, Any], bool, str]:
    model = str(row.get("model") or "").strip()
    if not model:
        raise AssertionError("activity CSV model must be present")
    requests = nonnegative_decimal(row.get("num_model_requests"), field="num_model_requests")
    input_tokens = nonnegative_decimal(row.get("input_tokens"), field="input_tokens")
    uncached = nonnegative_decimal(row.get("input_uncached_tokens"), field="input_uncached_tokens")
    cached = nonnegative_decimal(row.get("input_cached_tokens"), field="input_cached_tokens")
    cache_write = nonnegative_decimal(
        row.get("input_cache_write_tokens"), field="input_cache_write_tokens"
    )
    output = nonnegative_decimal(row.get("output_tokens"), field="output_tokens")
    if uncached + cached + cache_write != input_tokens:
        raise AssertionError("activity input token components must equal input_tokens")

    tier, discount_policies, raw_tier = tier_policy(row)
    average_input = (
        (input_tokens / requests).to_integral_value(rounding=ROUND_CEILING)
        if requests > 0
        else input_tokens
    )
    context = {
        # External catalogs express public list prices. The export-specific
        # batch/flex reduction is applied as an explicit policy below so a
        # generic source card cannot silently double-discount the row.
        "service_tier": "standard",
        # Dashboard rows are aggregated. Average per-request input is the only
        # available signal for selecting a long-context pricing condition.
        "total_input_tokens": decimal_text(average_input),
        "priced_at": str(row.get("start_time_iso") or ""),
    }
    components = {
        "input_uncached_tokens": decimal_text(uncached),
        "input_cache_read_tokens": decimal_text(cached),
        "input_cache_write_tokens": decimal_text(cache_write),
        "output_text_tokens": decimal_text(output),
    }
    components = {
        name: quantity
        for name, quantity in components.items()
        if Decimal(quantity) > 0
    }
    resolver_options: dict[str, Any] = {"offline": offline, "refresh": refresh}
    if price_cards is not None:
        resolver_options["price_cards"] = price_cards

    ledger = estimate_cost_auto(
        provider="openai",
        surface="openai.usage.completions",
        model=model,
        components=components,
        context=context,
        discount_policies=discount_policies,
        **resolver_options,
    )
    cache_write_folded = False
    if cache_write > 0 and only_cache_write_is_unpriced(ledger):
        cache_write_folded = True
        fallback_components = dict(components)
        fallback_components["input_uncached_tokens"] = decimal_text(uncached + cache_write)
        fallback_components.pop("input_cache_write_tokens")
        ledger = estimate_cost_auto(
            provider="openai",
            surface="openai.usage.completions",
            model=model,
            components=fallback_components,
            context=context,
            discount_policies=discount_policies,
            **resolver_options,
        )

    incomplete = warning_codes(ledger) & INCOMPLETE_WARNING_CODES
    if incomplete:
        raise AssertionError(
            f"RunCost could not fully price activity model {model}: {', '.join(sorted(incomplete))}"
        )
    metadata = dict(ledger.get("metadata") or {})
    metadata["openai_dashboard_export"] = {
        "reported_tier": raw_tier,
        "pricing_baseline": "public_standard",
        "applied_tier_policy": tier,
        "average_input_tokens_used_for_context_tier": decimal_text(average_input),
        "cache_write_folded_into_uncached_input": cache_write_folded,
    }
    ledger["metadata"] = metadata
    return ledger, cache_write_folded, tier


def load_price_cards(path: Path | None) -> list[dict[str, Any]] | None:
    if path is None:
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    cards = data.get("price_cards") if isinstance(data, dict) else data
    if not isinstance(cards, list):
        raise AssertionError("price-card file must contain an array or price_cards array")
    return [dict(card) for card in cards]


def normalized_comparison(
    *,
    cost_rows: list[dict[str, str]],
    activity_rows: list[dict[str, str]],
    comparison_id: str,
    tolerance: str,
    price_cards: list[dict[str, Any]] | None,
    offline: bool,
    refresh: bool,
) -> dict[str, Any]:
    provider_total, currency = provider_cost(cost_rows)
    ledgers: list[dict[str, Any]] = []
    folded_rows = 0
    tier_policies: set[str] = set()
    for row in activity_rows:
        ledger, cache_write_folded, tier = activity_ledger(
            row,
            price_cards=price_cards,
            offline=offline,
            refresh=refresh,
        )
        ledgers.append(ledger)
        folded_rows += int(cache_write_folded)
        tier_policies.add(tier)

    aggregate = aggregate_cost_ledgers(
        ledgers,
        provider="openai",
        surface="openai.dashboard.usage_export",
        model="multiple",
        expected_ledger_count=len(activity_rows),
    )
    estimated_total = nonnegative_decimal(aggregate.get("total"), field="RunCost total")
    normalized_total = normalized_ratio(estimated_total / provider_total)
    source_names = sorted(
        {
            str(source.get("name"))
            for source in aggregate.get("price_sources", [])
            if isinstance(source, dict) and source.get("name")
        }
    )
    aggregate_warning_codes = sorted(warning_codes(aggregate))
    sanitized_ledger = {
        "schema_version": "0.1",
        "provider": "openai",
        "surface": "openai.dashboard.usage_export",
        "model": {
            "requested": "multiple",
            "returned": "multiple",
            "billed": "multiple",
            "alias_resolution": "mixed",
        },
        "currency": "NORMALIZED_PROVIDER_COST",
        "components": [],
        "total": decimal_text(normalized_total),
        "price_sources": [{"name": name} for name in source_names],
        "applied_discounts": [],
        "warnings": [{"code": code} for code in aggregate_warning_codes],
        "metadata": {
            "absolute_provider_and_runcost_costs_omitted": True,
            "normalization": "provider_reported_cost_equals_1",
            "all_activity_rows_fully_priced": len(ledgers) == len(activity_rows),
            "cache_write_fallback_used": folded_rows > 0,
            "applied_export_tier_policies": sorted(tier_policies),
        },
    }
    coverage = Decimal(len(ledgers)) / Decimal(len(activity_rows))
    comparison_input = {
        "schema_version": "0.1",
        "comparison_id": comparison_id,
        "description": (
            "Normalized comparison generated locally from matching real OpenAI dashboard cost "
            "and activity CSV exports; absolute costs, token totals, and identifiers are omitted."
        ),
        "evidence_type": "real_provider_export",
        "safe_to_commit": True,
        "contains_private_billing_export": False,
        "provider": {
            "name": "openai",
            "surface": "openai.dashboard.cost_and_activity_exports",
            "model": "multiple",
            "source": "sanitized_openai_dashboard_csv_exports",
            "window": export_window(cost_rows, activity_rows),
            "values": {
                "matching_nonempty_export_pair": "1",
                "priced_activity_coverage": decimal_text(coverage),
                "normalized_provider_cost": "1",
                "normalized_runcost_cost": decimal_text(normalized_total),
                "currency_is_usd": "1" if currency == "USD" else "0",
            },
        },
        "runcost": {
            "source": "runtime_external_price_resolution_with_explicit_public_tier_policies",
            "cost_ledger": sanitized_ledger,
        },
        "field_mappings": [
            {
                "field": "matching_nonempty_export_pair",
                "provider_path": "$.provider.values.matching_nonempty_export_pair",
                "runcost_value": "1",
                "status_rule": "exact",
                "notes": (
                    "Matching cost and activity exports were present. Their row counts, identifiers, "
                    "and absolute values are omitted."
                ),
            },
            {
                "field": "priced_activity_coverage",
                "provider_path": "$.provider.values.priced_activity_coverage",
                "runcost_value": decimal_text(coverage),
                "status_rule": "exact",
                "notes": (
                    "Coverage is the fully priced activity-row share; row counts and token volumes "
                    "are omitted."
                ),
            },
            {
                "field": "currency_is_usd",
                "provider_path": "$.provider.values.currency_is_usd",
                "runcost_value": "1",
                "status_rule": "exact",
                "notes": "The local converter requires one USD cost-export currency.",
            },
            {
                "field": "normalized_provider_cost",
                "provider_path": "$.provider.values.normalized_provider_cost",
                "runcost_path": "$.runcost.cost_ledger.total",
                "status_rule": "estimated",
                "tolerance": tolerance,
                "notes": (
                    "Absolute costs are withheld. The provider total is normalized to 1. RunCost uses "
                    "external public prices, explicit published batch/flex reductions, average input per "
                    "request for long-context selection, and a standard public-price baseline for the "
                    "provider-internal incentivized-tier label."
                ),
            },
            {
                "field": "normalized_runcost_cost",
                "provider_path": "$.provider.values.normalized_runcost_cost",
                "runcost_path": "$.runcost.cost_ledger.total",
                "status_rule": "exact",
                "notes": "Records the normalized RunCost ledger used by this comparison.",
            },
        ],
    }
    validate_input_safety(comparison_input)
    validate_input_contract(comparison_input)
    comparison = build_comparison(comparison_input)
    # Defense in depth: none of the raw export identifier column names may
    # appear in the durable comparison artifact.
    serialized = json.dumps(comparison, sort_keys=True)
    for forbidden in ("project_id", "organization_id", "api_key_id", "user_id", "user_email"):
        if forbidden in serialized:
            raise AssertionError(f"sanitized comparison unexpectedly contains {forbidden}")
    return comparison


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a normalized, sanitized RunCost comparison from OpenAI dashboard CSV exports."
    )
    parser.add_argument("--cost-export", required=True, help="Raw OpenAI dashboard cost CSV (local only).")
    parser.add_argument("--activity-export", required=True, help="Raw OpenAI activity CSV (local only).")
    parser.add_argument("--output", required=True, help="Sanitized comparison JSON to write.")
    parser.add_argument(
        "--confirm-private-inputs-stay-local",
        action="store_true",
        help="Required acknowledgement that raw CSVs stay local and only normalized output is retained.",
    )
    parser.add_argument("--comparison-id", default="openai-dashboard-export-comparison")
    parser.add_argument(
        "--normalized-cost-tolerance",
        default="0.01",
        help="Allowed normalized cost delta before the cost row is classified unsupported.",
    )
    parser.add_argument("--price-cards", help="Optional deterministic price-card JSON for tests or review.")
    parser.add_argument("--offline", action="store_true", help="Require cached external price data.")
    parser.add_argument("--refresh", action="store_true", help="Refresh external public price data.")
    args = parser.parse_args()

    if not args.confirm_private_inputs_stay_local:
        raise AssertionError("--confirm-private-inputs-stay-local is required")
    if args.offline and args.refresh:
        raise AssertionError("--offline and --refresh are mutually exclusive")
    tolerance = nonnegative_decimal(
        args.normalized_cost_tolerance, field="normalized cost tolerance"
    )
    cost_rows = read_csv(
        Path(args.cost_export), required_columns=COST_REQUIRED_COLUMNS, kind="cost export"
    )
    activity_rows = read_csv(
        Path(args.activity_export),
        required_columns=ACTIVITY_REQUIRED_COLUMNS,
        kind="activity export",
    )
    comparison = normalized_comparison(
        cost_rows=cost_rows,
        activity_rows=activity_rows,
        comparison_id=args.comparison_id,
        tolerance=decimal_text(tolerance),
        price_cards=load_price_cards(Path(args.price_cards) if args.price_cards else None),
        offline=args.offline,
        refresh=args.refresh,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote normalized sanitized OpenAI dashboard comparison to {output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"OpenAI dashboard comparison failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
