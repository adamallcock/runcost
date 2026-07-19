#!/usr/bin/env python3
"""Validate the sanitized live OpenAI expansion-smoke evidence contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "fixtures" / "source-files" / "openai-expansion-live-smoke-2026-07-18.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-passed",
        action="store_true",
        help="Fail unless the sanitized report proves every live smoke completed.",
    )
    args = parser.parse_args()
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    for key, expected in {
        "schema_version": "0.1",
        "evidence_type": "sanitized_live_provider_smoke",
        "safe_to_commit": True,
        "contains_private_payloads": False,
        "contains_account_or_request_identifiers": False,
        "provider": "openai",
    }.items():
        if report.get(key) != expected:
            raise AssertionError(f"OpenAI smoke {key} must be {expected!r}")
    encoded = json.dumps(report)
    for forbidden in ("sk-", "resp_", "batch_", "file-", "org-", "proj_", "Reply with exactly OK"):
        if forbidden in encoded:
            raise AssertionError(f"OpenAI smoke contains forbidden content: {forbidden}")
    privacy = report.get("privacy", {})
    if not privacy.get("prompt_was_public_fixed_text") or privacy.get("response_text_retained"):
        raise AssertionError("OpenAI smoke privacy declaration is invalid")
    if report.get("status") == "passed":
        if report.get("responses", {}).get("status") != "passed":
            raise AssertionError("OpenAI Responses smoke is not passed")
        batch = report.get("batch", {})
        if batch.get("status") != "completed" or batch.get("summary", {}).get("succeeded") != 1:
            raise AssertionError("OpenAI Batch smoke is not completed")
        if report.get("costs_api", {}).get("attempted") is not True:
            raise AssertionError("OpenAI Costs API access must be attempted after credential injection")
    elif report.get("status") == "blocked":
        credential = report.get("credential", {})
        if credential.get("item_present") is not True or credential.get("injection_succeeded") is not False:
            raise AssertionError("blocked OpenAI smoke must prove item presence and failed injection")
        if credential.get("blocker") != "keychain_authentication_failed":
            raise AssertionError("blocked OpenAI smoke must retain the exact Keychain blocker")
        for surface in ("responses", "batch"):
            if report.get(surface, {}).get("status") != "not_run":
                raise AssertionError(f"{surface} must be not_run when credential injection is blocked")
    else:
        raise AssertionError(f"unexpected OpenAI smoke status: {report.get('status')}")
    if args.require_passed and report.get("status") != "passed":
        raise AssertionError(
            "OpenAI expansion smoke requires live passed evidence; unlock the login Keychain and rerun the sanitized smoke."
        )
    print(f"sanitized OpenAI expansion smoke is valid ({report.get('status')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
