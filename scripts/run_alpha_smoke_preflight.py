#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def env_state(env: dict[str, str], names: list[str]) -> tuple[list[str], list[str]]:
    present = [name for name in names if env.get(name)]
    missing = [name for name in names if not env.get(name)]
    return present, missing


def python_package_available(import_name: str) -> bool:
    return importlib.util.find_spec(import_name) is not None


def node_package_available(package_name: str) -> bool:
    snippet = f"await import({package_name!r});"
    result = subprocess.run(
        ["node", "--input-type=module", "-e", snippet],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def dependency_state(dependencies: list[tuple[str, str]]) -> tuple[list[str], list[str]]:
    present: list[str] = []
    missing: list[str] = []
    for runtime, name in dependencies:
        if runtime == "python":
            ok = python_package_available(name)
        elif runtime == "node":
            ok = node_package_available(name)
        else:
            ok = False
        label = f"{runtime}:{name}"
        if ok:
            present.append(label)
        else:
            missing.append(label)
    return present, missing


def scenario(
    scenario_id: str,
    *,
    required_env: list[str],
    optional_dependencies: list[tuple[str, str]] | None = None,
    env: dict[str, str],
) -> dict[str, Any]:
    present_env, missing_env = env_state(env, required_env)
    present_deps, missing_deps = dependency_state(optional_dependencies or [])
    ready = not missing_env and not missing_deps
    return {
        "scenario": scenario_id,
        "status": "ready" if ready else "not_ready",
        "required_env": required_env,
        "env_present": present_env,
        "env_missing": missing_env,
        "optional_dependencies_present": present_deps,
        "optional_dependencies_missing": missing_deps,
        "secret_values_emitted": False,
    }


def build_report(env: dict[str, str] | None = None) -> dict[str, Any]:
    env = env if env is not None else os.environ
    scenarios = [
        scenario("openai_responses", required_env=["OPENAI_API_KEY"], env=env),
        scenario("anthropic_prompt_caching", required_env=["ANTHROPIC_API_KEY"], env=env),
        scenario("openrouter_cost_compare", required_env=["OPENROUTER_API_KEY"], env=env),
        scenario("multi_provider_discount", required_env=[], env=env),
        scenario(
            "vercel_ai_sdk_stream_text",
            required_env=["OPENAI_API_KEY"],
            optional_dependencies=[("node", "ai"), ("node", "@ai-sdk/openai")],
            env=env,
        ),
        scenario(
            "langchain_agent_run",
            required_env=["OPENAI_API_KEY"],
            optional_dependencies=[("python", "langchain_openai"), ("python", "langchain_core")],
            env=env,
        ),
    ]
    ready = [item["scenario"] for item in scenarios if item["status"] == "ready"]
    not_ready = [item["scenario"] for item in scenarios if item["status"] != "ready"]
    return {
        "schema_version": "0.1",
        "generated_at": utc_now(),
        "mode": "live_preflight",
        "sanitized": True,
        "safe_to_attach_to_issue": True,
        "live_ready": not not_ready,
        "summary": {
            "ready_count": len(ready),
            "not_ready_count": len(not_ready),
            "ready_scenarios": ready,
            "not_ready_scenarios": not_ready,
        },
        "scenarios": scenarios,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check sanitized readiness for optional RunCost alpha live smoke runs.")
    parser.add_argument("--output", help="Optional JSON output path.")
    parser.add_argument("--require-ready", action="store_true", help="Exit nonzero unless every live smoke scenario is ready.")
    args = parser.parse_args()

    report = build_report()
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        print(f"Wrote sanitized alpha smoke preflight report to {output}")
    else:
        print(text, end="")

    if args.require_ready and not report["live_ready"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
