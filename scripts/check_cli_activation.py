#!/usr/bin/env python3
"""Check Python/npm quote CLI parity without relying on network pricing."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "fixtures" / "kimi-k3-response.json"
PYTHON_ENV = {**os.environ, "PYTHONPATH": str(ROOT / "packages" / "python")}


def run(command: list[str], *, input_text: str | None = None, env: dict[str, str] | None = None) -> bytes:
    return subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        input=input_text.encode() if input_text is not None else None,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def python_cli(arguments: list[str], input_text: str | None = None) -> bytes:
    return run(["python3", "-m", "runcost.cli", *arguments], input_text=input_text, env=PYTHON_ENV)


def javascript_cli(arguments: list[str], input_text: str | None = None) -> bytes:
    return run(["node", "packages/javascript/core/cli.js", *arguments], input_text=input_text)


def assert_both_reject(arguments: list[str]) -> None:
    commands = [
        (["python3", "-m", "runcost.cli", *arguments], PYTHON_ENV),
        (["node", "packages/javascript/core/cli.js", *arguments], None),
    ]
    for command, env in commands:
        completed = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if completed.returncode == 0:
            raise AssertionError(f"CLI unexpectedly accepted invalid arguments: {command}")


def assert_equal(arguments: list[str], input_text: str | None = None) -> dict:
    python = python_cli(arguments, input_text)
    javascript = javascript_cli(arguments, input_text)
    if python != javascript:
        raise AssertionError(f"CLI outputs differ for {arguments}:\npython={python[:500]!r}\njavascript={javascript[:500]!r}")
    return json.loads(python)


def main() -> int:
    fixed_clock = ["--now", "2026-07-18T12:00:00Z"]
    with tempfile.TemporaryDirectory(prefix="runcost-cli-") as directory:
        response = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        card = {
            "schema_version": "0.1",
            "id": "cli:kimi-k3:explicit",
            "provider": "kimi",
            "surface": "kimi.chat_completions",
            "model": "kimi-k3",
            "components": [
                {"usage_component": "input_uncached_tokens", "unit": "token", "price": {"amount": "1", "currency": "USD", "per": "1000000"}},
                {"usage_component": "input_cache_read_tokens", "unit": "token", "price": {"amount": "0.5", "currency": "USD", "per": "1000000"}},
                {"usage_component": "output_text_tokens", "unit": "token", "price": {"amount": "2", "currency": "USD", "per": "1000000"}},
            ],
            "source": {"name": "cli-explicit-test"},
        }
        quote_path = Path(directory) / "quote-input.json"
        envelope = {"response": response, "price_cards": [card]}
        quote_path.write_text(json.dumps(envelope), encoding="utf-8")
        quoted = assert_equal(["quote", str(quote_path), "--provider", "kimi", "--surface", "kimi.chat_completions", *fixed_clock])
        if quoted["total"] != "0.00017" or quoted["warnings"]:
            raise AssertionError(quoted)

        raw = json.dumps(envelope, separators=(",", ":"))
        jsonl = assert_equal(["quote", "-", "--jsonl", "--provider", "kimi", "--surface", "kimi.chat_completions", *fixed_clock], raw + "\n" + raw + "\n")
        if len(jsonl) != 2 or any(item["total"] != "0.00017" for item in jsonl):
            raise AssertionError(jsonl)

        empty_path = Path(directory) / "explicit-empty.json"
        empty_path.write_text(json.dumps({"response": response, "price_cards": []}), encoding="utf-8")
        explicit_empty = assert_equal(["quote", str(empty_path), "--provider", "kimi", "--surface", "kimi.chat_completions", *fixed_clock])
        if explicit_empty["total"] != "0" or explicit_empty.get("metadata", {}).get("price_resolution", {}).get("selected_source") != "user":
            raise AssertionError(explicit_empty)

        no_resolve = assert_equal(["quote", str(EXAMPLE), "--provider", "kimi", "--surface", "kimi.chat_completions", "--no-resolve"])
        if no_resolve["total"] != "0" or "unknown_model" not in {warning["code"] for warning in no_resolve["warnings"]}:
            raise AssertionError(no_resolve)

        output = Path(directory) / "quote.json"
        python_cli(["quote", str(quote_path), "--provider", "kimi", "--surface", "kimi.chat_completions", "--output", str(output)])
        if json.loads(output.read_text(encoding="utf-8"))["total"] != "0.00017":
            raise AssertionError("Python --output did not write the expected ledger")
    assert_both_reject(["quote", str(EXAMPLE), str(EXAMPLE)])
    print("Python/npm quote CLI parity passed for explicit, empty, JSONL, output, no-resolve, and invalid-arity paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
