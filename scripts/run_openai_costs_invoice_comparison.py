#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_SOURCE = ROOT / "fixtures" / "source-files" / "openai-costs-comparison-source.json"
CONVERTER = ROOT / "scripts" / "create_openai_costs_comparison_input.py"
COMPARATOR = ROOT / "scripts" / "compare_invoice_dashboard.py"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_command(args: list[str]) -> None:
    subprocess.run(args, cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def sanitize_openai_costs_page(page: dict[str, Any]) -> dict[str, Any]:
    sanitized = {
        "object": page.get("object", "page"),
        "data": [],
        "has_more": bool(page.get("has_more", False)),
        "next_page": "redacted" if page.get("next_page") else None,
    }
    for bucket in page.get("data", []) if isinstance(page.get("data"), list) else []:
        if not isinstance(bucket, dict):
            continue
        sanitized_bucket = {
            "object": bucket.get("object", "bucket"),
            "start_time": bucket.get("start_time"),
            "end_time": bucket.get("end_time"),
            "results": [],
        }
        for result in bucket.get("results", []) if isinstance(bucket.get("results"), list) else []:
            if not isinstance(result, dict):
                continue
            amount = result.get("amount") if isinstance(result.get("amount"), dict) else {}
            sanitized_bucket["results"].append(
                {
                    "object": result.get("object", "organization.costs.result"),
                    "amount": {
                        "value": amount.get("value", 0),
                        "currency": amount.get("currency", "usd"),
                    },
                    "line_item": result.get("line_item"),
                    "project_alias": "redacted" if result.get("project_id") else "all_projects",
                }
            )
        sanitized["data"].append(sanitized_bucket)
    return sanitized


def fetch_openai_costs(*, admin_key: str, start_time: int, end_time: int | None, limit: int) -> dict[str, Any]:
    query: dict[str, str] = {
        "start_time": str(start_time),
        "limit": str(limit),
    }
    if end_time is not None:
        query["end_time"] = str(end_time)
    url = "https://api.openai.com/v1/organization/costs?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {admin_key}",
            "Content-Type": "application/json",
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def build_live_source(args: argparse.Namespace) -> dict[str, Any]:
    admin_key = os.environ.get("OPENAI_ADMIN_KEY", "")
    if not admin_key:
        raise AssertionError("OPENAI_ADMIN_KEY is required for live OpenAI Costs comparison mode")
    if not args.start_time:
        raise AssertionError("--start-time is required for live OpenAI Costs comparison mode")
    if not args.runcost_ledger:
        raise AssertionError("--runcost-ledger is required for live OpenAI Costs comparison mode")
    ledger = load_json(Path(args.runcost_ledger))
    raw_page = fetch_openai_costs(
        admin_key=admin_key,
        start_time=int(args.start_time),
        end_time=int(args.end_time) if args.end_time else None,
        limit=int(args.limit),
    )
    sanitized_page = sanitize_openai_costs_page(raw_page)
    window_end = args.end_time or "open"
    return {
        "schema_version": "0.1",
        "comparison_id": args.comparison_id,
        "description": "Sanitized OpenAI Costs API live comparison source.",
        "evidence_type": "real_provider_export",
        "safe_to_commit": True,
        "contains_private_billing_export": False,
        "provider": {
            "name": "openai",
            "surface": "openai.organization.costs",
            "model": args.model,
            "source": "openai_costs_api",
            "window": f"{args.start_time}/{window_end}",
        },
        "openai_costs": sanitized_page,
        "expected_line_item_count": str(args.expected_line_item_count) if args.expected_line_item_count else str(
            sum(len(bucket.get("results", [])) for bucket in sanitized_page.get("data", []))
        ),
        "cost_tolerance": args.cost_tolerance,
        "runcost": {
            "source": args.runcost_source,
            "cost_ledger": ledger,
        },
    }


def comparison_from_source(source: dict[str, Any], output: Path) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        source_path = Path(temp_dir) / "openai-costs-source.json"
        comparison_input = Path(temp_dir) / "comparison-input.json"
        write_json(source_path, source)
        run_command(
            [
                sys.executable,
                str(CONVERTER),
                "--input",
                str(source_path),
                "--output",
                str(comparison_input),
            ]
        )
        run_command(
            [
                sys.executable,
                str(COMPARATOR),
                "--input",
                str(comparison_input),
                "--output",
                str(output),
            ]
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an OpenAI Costs API invoice/dashboard comparison.")
    parser.add_argument("--mode", choices=["sample", "live"], default="sample")
    parser.add_argument("--output", required=True, help="Path to write sanitized comparison JSON.")
    parser.add_argument("--allow-sample-prices", action="store_true", help="Required for sample mode to avoid confusing samples with real evidence.")
    parser.add_argument("--runcost-ledger", help="RunCost cost ledger JSON for live comparison mode.")
    parser.add_argument("--runcost-source", default="provided_runcost_ledger")
    parser.add_argument("--start-time", help="Unix start time for live OpenAI Costs API query.")
    parser.add_argument("--end-time", help="Unix end time for live OpenAI Costs API query.")
    parser.add_argument("--limit", default="7")
    parser.add_argument("--model", default="multiple")
    parser.add_argument("--comparison-id", default="openai-costs-live-comparison")
    parser.add_argument("--expected-line-item-count")
    parser.add_argument("--cost-tolerance", default="0")
    args = parser.parse_args()

    if args.mode == "sample":
        if not args.allow_sample_prices:
            raise AssertionError("--allow-sample-prices is required in sample mode")
        source = load_json(SAMPLE_SOURCE)
    else:
        source = build_live_source(args)

    comparison_from_source(source, Path(args.output))
    print(f"Wrote OpenAI Costs invoice/dashboard comparison to {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"OpenAI Costs invoice comparison failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
