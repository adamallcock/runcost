#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / "scripts" / "run_meta_model_api_smoke.py"
LIVE_EVIDENCE = ROOT / "fixtures" / "source-files" / "meta-model-api-live-smoke-2026-07-09.json"
META_PREVIEW_SOURCE_NAME = "Meta Model API reviewed public-preview pricing snapshot"

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


def assert_passed_report(report: dict[str, object], mode: str) -> None:
    assert report["schema_version"] == "0.1"
    assert report["mode"] == mode
    assert report["provider"] == "meta"
    assert report["status"] == "passed"
    assert report["sanitized"] is True
    assert report["safe_to_attach_to_issue"] is True
    assert report["secret_values_emitted"] is False
    assert report["raw_response_retained"] is False
    assert report["pricing_authority"] == "reviewed_preview_not_primary_source_verified"
    assert report["models"]["model_count"] >= 1  # type: ignore[index]
    assert "muse-spark-1.1" in report["models"]["model_ids"]  # type: ignore[index]
    for key, surface in [
        ("chat_completions", "meta.chat_completions"),
        ("responses", "meta.responses"),
    ]:
        item = report[key]  # type: ignore[index]
        assert item["surface"] == surface
        assert item["ledger"]["provider"] == "meta"
        assert item["ledger"]["surface"] == surface
        assert item["ledger"]["warning_codes"] == []
        assert item["ledger"]["raw_response_retained"] is False
        assert item["ledger"]["component_names"]
        assert item["ledger"]["price_source_names"] == [META_PREVIEW_SOURCE_NAME]
    walk(report)


def main() -> int:
    assert COMMAND.exists(), "missing Meta Model API smoke script"
    assert LIVE_EVIDENCE.exists(), "missing Meta Model API live evidence"
    with tempfile.TemporaryDirectory() as temp_dir:
        sample_output = Path(temp_dir) / "meta-model-api-sample.json"
        subprocess.run(
            [
                sys.executable,
                str(COMMAND),
                "--mode",
                "sample",
                "--output",
                str(sample_output),
                "--require-passed",
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        sample_report = json.loads(sample_output.read_text(encoding="utf-8"))

        live_output = Path(temp_dir) / "meta-model-api-live-no-key.json"
        env = dict(os.environ)
        env.pop("META_API_KEY", None)
        subprocess.run(
            [
                sys.executable,
                str(COMMAND),
                "--mode",
                "live",
                "--output",
                str(live_output),
            ],
            cwd=ROOT,
            env=env,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        live_report = json.loads(live_output.read_text(encoding="utf-8"))

    assert_passed_report(sample_report, "sample")
    live_evidence_report = json.loads(LIVE_EVIDENCE.read_text(encoding="utf-8"))
    assert_passed_report(live_evidence_report, "live")
    assert live_report["schema_version"] == "0.1"
    assert live_report["mode"] == "live"
    assert live_report["status"] == "skipped"
    assert live_report["reason"] == "META_API_KEY is not set."
    assert live_report["secret_values_emitted"] is False
    assert live_report["raw_response_retained"] is False
    walk(live_report)
    print("Meta Model API smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
