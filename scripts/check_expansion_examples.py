#!/usr/bin/env python3
"""Run and validate the public provider, batch, framework, and OTel examples."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def run_json(command: list[str]) -> Any:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return json.loads(completed.stdout)


def main() -> int:
    direct_python = run_json(["python3", "examples/python_direct_providers.py"])
    direct_javascript = run_json(["node", "examples/javascript_direct_providers.mjs"])
    if direct_python != direct_javascript:
        raise AssertionError("direct-provider Python and JavaScript examples differ")
    if len(direct_python) != 11 or set(direct_python.values()) != {"0.00018"}:
        raise AssertionError(f"unexpected direct-provider totals: {direct_python}")

    batch_python = run_json(["python3", "examples/python_batch_endpoints.py"])
    batch_javascript = run_json(["node", "examples/javascript_batch_endpoints.mjs"])
    if batch_python != batch_javascript:
        raise AssertionError("batch Python and JavaScript examples differ")
    if len(batch_python) != 11:
        raise AssertionError(f"expected eleven batch examples, got {len(batch_python)}")
    for case_id, summary in batch_python.items():
        if summary["total"] < 1:
            raise AssertionError(f"{case_id}: expected at least one item")
        if summary["succeeded"] + summary["failed"] + summary["pending"] != summary["total"]:
            raise AssertionError(f"{case_id}: batch summary counts do not reconcile")
    if batch_python["openai-chat-batch-pending"]["pending"] != 1:
        raise AssertionError("pending batch example must remain visibly incomplete")

    otel_python = run_json(["python3", "examples/python_pydantic_genai_prices.py"])
    otel_javascript = run_json(["node", "examples/javascript_genai_prices_otel.mjs"])
    if otel_python != otel_javascript or otel_python["total"] != "0.000182":
        raise AssertionError(f"unexpected OTel/genai-prices output: {otel_python}")

    framework_python = run_json(["python3", "examples/python_framework_adapters.py"])
    framework_javascript = run_json(["node", "examples/javascript_framework_adapters.mjs"])
    if framework_python["openai_agents_total"] != "0.000712":
        raise AssertionError(framework_python)
    if framework_javascript["vercel_total"] != framework_javascript["vercel_on_finish_total"]:
        raise AssertionError(framework_javascript)

    print(
        "expansion examples passed "
        "(11 direct providers, 11 batch cases, genai-prices/OTel, and framework adapters)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
