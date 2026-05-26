#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / "scripts" / "run_alpha_smoke.py"
VERCEL_COMMAND = ROOT / "scripts" / "run_vercel_alpha_smoke.mjs"
LANGCHAIN_COMMAND = ROOT / "scripts" / "run_langchain_alpha_smoke.py"

EXPECTED_SCENARIOS = {
    "openai_responses",
    "anthropic_prompt_caching",
    "vercel_ai_sdk_stream_text",
    "langchain_agent_run",
    "openrouter_cost_compare",
    "multi_provider_discount",
}

FORBIDDEN_KEYS = {
    "api_key",
    "authorization",
    "headers",
    "prompt",
    "messages",
    "input",
    "output",
    "content",
    "raw_response",
    "request_body",
}


def walk(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = key.lower().replace("-", "_")
            assert normalized not in FORBIDDEN_KEYS, f"forbidden key {path}.{key}"
            walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk(child, f"{path}[{index}]")


def main() -> int:
    assert VERCEL_COMMAND.exists(), "missing Vercel AI SDK alpha smoke script"
    assert LANGCHAIN_COMMAND.exists(), "missing LangChain alpha smoke script"
    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / "alpha-smoke.json"
        subprocess.run(
            [
                sys.executable,
                str(COMMAND),
                "--mode",
                "sample",
                "--output",
                str(output),
                "--allow-sample-prices",
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        report = json.loads(output.read_text(encoding="utf-8"))
        vercel_output = Path(temp_dir) / "vercel-alpha-smoke.json"
        subprocess.run(
            [
                "node",
                str(VERCEL_COMMAND),
                "--mode",
                "sample",
                "--output",
                str(vercel_output),
                "--allow-sample-prices",
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        vercel_report = json.loads(vercel_output.read_text(encoding="utf-8"))
        langchain_output = Path(temp_dir) / "langchain-alpha-smoke.json"
        subprocess.run(
            [
                sys.executable,
                str(LANGCHAIN_COMMAND),
                "--mode",
                "sample",
                "--output",
                str(langchain_output),
                "--allow-sample-prices",
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        langchain_report = json.loads(langchain_output.read_text(encoding="utf-8"))
        live_output = Path(temp_dir) / "alpha-smoke-live-without-keys.json"
        env = dict(os.environ)
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"]:
            env.pop(key, None)
        subprocess.run(
            [
                sys.executable,
                str(COMMAND),
                "--mode",
                "live",
                "--output",
                str(live_output),
                "--allow-sample-prices",
            ],
            cwd=ROOT,
            env=env,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        live_report = json.loads(live_output.read_text(encoding="utf-8"))

    assert report["schema_version"] == "0.1"
    assert report["mode"] == "sample"
    assert report["sanitized"] is True
    assert report["safe_to_attach_to_issue"] is True
    assert sorted(item["scenario"] for item in report["scenarios"]) == sorted(EXPECTED_SCENARIOS)
    assert report["summary"]["total"] == len(EXPECTED_SCENARIOS)
    assert report["summary"]["passed"] == len(EXPECTED_SCENARIOS)
    assert report["summary"]["needs_product_truth"] == 0
    assert "generated_at" in report

    for item in report["scenarios"]:
        assert item["status"] == "passed"
        assert item["evidence"]["raw_response_retained"] is False
        assert item["evidence"]["component_names"]
        assert "total" in item["evidence"]
        assert set(item["next_action"].keys()) == {"type", "reason"}
        walk(item)

    for framework_report, scenario in [
        (vercel_report, "vercel_ai_sdk_stream_text"),
        (langchain_report, "langchain_agent_run"),
    ]:
        assert framework_report["schema_version"] == "0.1"
        assert framework_report["mode"] == "sample"
        assert framework_report["sanitized"] is True
        assert framework_report["safe_to_attach_to_issue"] is True
        assert framework_report["scenario"] == scenario
        assert framework_report["status"] == "passed"
        assert framework_report["evidence"]["raw_response_retained"] is False
        assert framework_report["evidence"]["component_names"]
        assert framework_report["next_action"]["type"] == "none"
        walk(framework_report)

    live_by_scenario = {item["scenario"]: item for item in live_report["scenarios"]}
    assert live_by_scenario["vercel_ai_sdk_stream_text"]["status"] == "skipped"
    assert live_by_scenario["vercel_ai_sdk_stream_text"]["next_action"]["reason"] == "OPENAI_API_KEY is not set."
    assert live_by_scenario["langchain_agent_run"]["status"] == "skipped"
    assert live_by_scenario["langchain_agent_run"]["next_action"]["reason"] == "OPENAI_API_KEY is not set."
    walk(live_report)

    print("Alpha smoke sample checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
