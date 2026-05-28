#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_COMMAND = ROOT / "scripts" / "run_alpha_smoke_preflight.py"
SMOKE_COMMAND = ROOT / "scripts" / "run_alpha_smoke.py"
VERCEL_COMMAND = ROOT / "scripts" / "run_vercel_alpha_smoke.mjs"
LANGCHAIN_COMMAND = ROOT / "scripts" / "run_langchain_alpha_smoke.py"
INVOICE_COMPARE_COMMAND = ROOT / "scripts" / "compare_invoice_dashboard.py"
INVOICE_SAMPLE = ROOT / "fixtures" / "source-files" / "invoice-dashboard-comparison-sample.json"
BUNDLE_CHECK_COMMAND = ROOT / "scripts" / "check_alpha_evidence_bundle.py"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_command(args: list[str]) -> None:
    subprocess.run(args, cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def artifact(path: Path, kind: str, description: str, root: Path) -> dict[str, str]:
    return {
        "kind": kind,
        "path": str(path.relative_to(root)),
        "description": description,
    }


def build_preflight_args(args: argparse.Namespace, output: Path) -> list[str]:
    command = [sys.executable, str(PREFLIGHT_COMMAND), "--output", str(output)]
    if args.openai_costs_start_time:
        command.extend(["--openai-costs-start-time", args.openai_costs_start_time])
    if args.openai_costs_runcost_ledger:
        command.extend(["--openai-costs-runcost-ledger", args.openai_costs_runcost_ledger])
    return command


def copy_invoice_comparison(source: str, destination: Path) -> None:
    source_path = Path(source)
    if not source_path.exists():
        raise AssertionError(f"invoice comparison does not exist: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, destination)


def produce_sample_invoice_comparison(output: Path) -> None:
    run_command(
        [
            sys.executable,
            str(INVOICE_COMPARE_COMMAND),
            "--input",
            str(INVOICE_SAMPLE),
            "--output",
            str(output),
        ]
    )


def validate_bundle(smoke_reports: list[Path], invoice_comparison: Path, require_real: bool) -> None:
    command = [sys.executable, str(BUNDLE_CHECK_COMMAND)]
    for report in smoke_reports:
        command.extend(["--smoke-report", str(report)])
    command.extend(["--invoice-comparison", str(invoice_comparison)])
    if require_real:
        command.append("--require-real")
    run_command(command)


def collect(args: argparse.Namespace) -> dict[str, Any]:
    if not args.allow_sample_prices:
        raise AssertionError("--allow-sample-prices is required so bundle output is not mistaken for invoice-exact pricing")
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    preflight_report = output_dir / "alpha-smoke-preflight.json"
    aggregate_report = output_dir / "alpha-smoke-aggregate.json"
    vercel_report = output_dir / "alpha-smoke-vercel.json"
    langchain_report = output_dir / "alpha-smoke-langchain.json"
    invoice_comparison = output_dir / "invoice-dashboard-comparison.json"
    manifest_path = output_dir / "alpha-evidence-bundle-manifest.json"

    run_command(build_preflight_args(args, preflight_report))
    run_command(
        [
            sys.executable,
            str(SMOKE_COMMAND),
            "--mode",
            args.mode,
            "--output",
            str(aggregate_report),
            "--allow-sample-prices",
        ]
    )
    run_command(
        [
            "node",
            str(VERCEL_COMMAND),
            "--mode",
            args.mode,
            "--output",
            str(vercel_report),
            "--allow-sample-prices",
        ]
    )
    run_command(
        [
            sys.executable,
            str(LANGCHAIN_COMMAND),
            "--mode",
            args.mode,
            "--output",
            str(langchain_report),
            "--allow-sample-prices",
        ]
    )

    if args.invoice_comparison:
        copy_invoice_comparison(args.invoice_comparison, invoice_comparison)
    else:
        produce_sample_invoice_comparison(invoice_comparison)

    smoke_reports = [aggregate_report, vercel_report, langchain_report]
    validate_bundle(smoke_reports, invoice_comparison, require_real=args.require_real)

    manifest = {
        "schema_version": "0.1",
        "generated_at": utc_now(),
        "mode": args.mode,
        "sanitized": True,
        "safe_to_attach_to_issue": True,
        "sample_prices": True,
        "require_real": bool(args.require_real),
        "bundle_complete": True,
        "artifacts": [
            artifact(preflight_report, "preflight_report", "Sanitized readiness report.", output_dir),
            artifact(aggregate_report, "smoke_report", "Aggregate provider smoke report.", output_dir),
            artifact(vercel_report, "smoke_report", "Vercel AI SDK smoke report.", output_dir),
            artifact(langchain_report, "smoke_report", "LangChain smoke report.", output_dir),
            artifact(invoice_comparison, "invoice_comparison", "Invoice/dashboard comparison report.", output_dir),
        ],
        "validation": {
            "command": "python3 scripts/check_alpha_evidence_bundle.py",
            "require_real": bool(args.require_real),
        },
    }
    write_json(manifest_path, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect a sanitized RunCost alpha evidence bundle.")
    parser.add_argument("--mode", choices=["sample", "live"], default="sample")
    parser.add_argument("--output-dir", required=True, help="Directory for sanitized evidence artifacts.")
    parser.add_argument("--allow-sample-prices", action="store_true", help="Required because smoke ledgers use sample price cards.")
    parser.add_argument("--invoice-comparison", help="Existing sanitized invoice/dashboard comparison JSON to include.")
    parser.add_argument("--require-real", action="store_true", help="Require live smoke evidence and real invoice comparison.")
    parser.add_argument("--openai-costs-start-time", help="Sanitized input-name readiness for OpenAI Costs comparison preflight.")
    parser.add_argument("--openai-costs-runcost-ledger", help="Sanitized input-name readiness for OpenAI Costs comparison preflight.")
    args = parser.parse_args()

    manifest = collect(args)
    print(f"Wrote sanitized alpha evidence bundle to {Path(args.output_dir).resolve()}")
    print(f"Bundle artifacts: {len(manifest['artifacts'])}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"Alpha evidence bundle collection failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
