#!/usr/bin/env python3
"""Run sanitized OpenAI Responses, Batch, and Costs-access expansion smokes."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "packages" / "python"))

from runcost import from_batch_results_auto, from_response_auto  # noqa: E402

API_ROOT = "https://api.openai.com"
MODEL_PREFERENCES = (
    "gpt-5.6-luna",
    "gpt-5.4-nano",
    "gpt-5-nano",
    "gpt-4.1-nano",
    "gpt-4o-mini",
)
TERMINAL_BATCH_STATUSES = {"completed", "failed", "expired", "cancelled", "canceled"}


class OpenAIHTTPError(Exception):
    def __init__(self, status: int, error_type: str = "", error_code: str = "") -> None:
        super().__init__(f"OpenAI HTTP {status}")
        self.status = status
        self.error_type = error_type
        self.error_code = error_code

    def sanitized(self) -> Dict[str, Any]:
        return {
            "http_status": self.status,
            "error_type": self.error_type or "unknown",
            "error_code": self.error_code or "unknown",
        }


def _error_from_http(exc: urllib.error.HTTPError) -> OpenAIHTTPError:
    error_type = ""
    error_code = ""
    try:
        payload = json.loads(exc.read().decode("utf-8"))
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict):
            error_type = str(error.get("type") or "")
            error_code = str(error.get("code") or "")
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass
    return OpenAIHTTPError(exc.code, error_type, error_code)


def api_bytes(
    api_key: str,
    method: str,
    path: str,
    *,
    body: Optional[bytes] = None,
    content_type: str = "application/json",
    timeout: int = 60,
) -> Tuple[bytes, str]:
    request = urllib.request.Request(
        API_ROOT + path,
        data=body,
        method=method,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": content_type},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read(), response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        raise _error_from_http(exc) from None


def api_json(api_key: str, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8") if payload is not None else None
    raw, _ = api_bytes(api_key, method, path, body=body)
    return json.loads(raw.decode("utf-8"))


def multipart_file(filename: str, contents: bytes, purpose: str = "batch") -> Tuple[bytes, str]:
    boundary = f"runcost-{uuid.uuid4().hex}"
    chunks = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"purpose\"\r\n\r\n{purpose}\r\n".encode(),
        (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
            "Content-Type: application/jsonl\r\n\r\n"
        ).encode(),
        contents,
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def public_request_body(model: str) -> Dict[str, Any]:
    return {
        "model": model,
        "input": "Reply with exactly OK.",
        "max_output_tokens": 64,
        "store": False,
    }


def choose_and_run_response(api_key: str) -> Tuple[str, Dict[str, Any]]:
    models_page = api_json(api_key, "GET", "/v1/models")
    available = {
        str(model.get("id"))
        for model in models_page.get("data", [])
        if isinstance(model, dict) and model.get("id")
    }
    candidates = [model for model in MODEL_PREFERENCES if model in available]
    if not candidates:
        candidates = ["gpt-4.1-nano"]
    last_error: Optional[OpenAIHTTPError] = None
    for model in candidates:
        try:
            return model, api_json(api_key, "POST", "/v1/responses", public_request_body(model))
        except OpenAIHTTPError as exc:
            last_error = exc
            if exc.status not in {400, 403, 404}:
                raise
    if last_error:
        raise last_error
    raise AssertionError("no OpenAI model candidate was available")


def sanitized_ledger(ledger: Dict[str, Any]) -> Dict[str, Any]:
    components = ledger.get("components", []) if isinstance(ledger.get("components"), list) else []
    return {
        "provider": ledger.get("provider"),
        "surface": ledger.get("surface"),
        "billed_model": (ledger.get("model") or {}).get("billed") if isinstance(ledger.get("model"), dict) else None,
        "priced": str(ledger.get("total", "0")) != "0",
        "component_count": len(components),
        "components": [
            {
                "name": component.get("name"),
                "quantity": component.get("quantity"),
                "unit": component.get("unit"),
                "has_nonzero_cost": str(component.get("cost", "0")) != "0",
            }
            for component in components
            if isinstance(component, dict)
        ],
        "price_sources": sorted(
            {
                str(source.get("name"))
                for source in ledger.get("price_sources", [])
                if isinstance(source, dict) and source.get("name")
            }
        ),
        "warning_codes": [
            str(warning.get("code"))
            for warning in ledger.get("warnings", [])
            if isinstance(warning, dict) and warning.get("code")
        ],
    }


def parse_jsonl(raw: bytes) -> list[Dict[str, Any]]:
    items = []
    for line in raw.decode("utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise AssertionError("OpenAI batch output line must be an object")
            items.append(value)
    return items


def delete_file(api_key: str, file_id: Optional[str]) -> bool:
    if not file_id:
        return True
    try:
        result = api_json(api_key, "DELETE", f"/v1/files/{urllib.parse.quote(file_id, safe='')}")
        return bool(result.get("deleted"))
    except OpenAIHTTPError:
        return False


def costs_access_probe(api_key: str) -> Dict[str, Any]:
    start_of_day = int(datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    path = "/v1/organization/costs?" + urllib.parse.urlencode({"start_time": start_of_day, "limit": 1})
    try:
        api_json(api_key, "GET", path)
        return {
            "attempted": True,
            "accessible": True,
            "reconciliation_status": "blocked_no_matched_sanitized_usage_export",
        }
    except OpenAIHTTPError as exc:
        return {
            "attempted": True,
            "accessible": False,
            "reconciliation_status": "blocked_admin_scope_or_endpoint_permission",
            **exc.sanitized(),
        }


def run_batch(
    api_key: str,
    model: str,
    *,
    max_wait_seconds: int,
    poll_seconds: int,
) -> Tuple[Dict[str, Any], Iterable[str]]:
    request_line = {
        "custom_id": "runcost-public-smoke-1",
        "method": "POST",
        "url": "/v1/responses",
        "body": public_request_body(model),
    }
    upload_body, content_type = multipart_file(
        "runcost-public-smoke.jsonl",
        (json.dumps(request_line, separators=(",", ":")) + "\n").encode("utf-8"),
    )
    raw_upload, _ = api_bytes(api_key, "POST", "/v1/files", body=upload_body, content_type=content_type)
    upload = json.loads(raw_upload.decode("utf-8"))
    input_file_id = str(upload["id"])
    cleanup_ids = [input_file_id]
    batch_id: Optional[str] = None
    started = time.monotonic()
    try:
        batch = api_json(
            api_key,
            "POST",
            "/v1/batches",
            {
                "input_file_id": input_file_id,
                "endpoint": "/v1/responses",
                "completion_window": "24h",
                "metadata": {"purpose": "runcost-public-smoke"},
            },
        )
        batch_id = str(batch["id"])
        status = str(batch.get("status") or "unknown")
        last_reported = None
        while status not in TERMINAL_BATCH_STATUSES and time.monotonic() - started < max_wait_seconds:
            if status != last_reported:
                print(f"OpenAI batch smoke status={status}", flush=True)
                last_reported = status
            time.sleep(poll_seconds)
            batch = api_json(api_key, "GET", f"/v1/batches/{urllib.parse.quote(batch_id, safe='')}")
            status = str(batch.get("status") or "unknown")
        if status not in TERMINAL_BATCH_STATUSES:
            batch = api_json(api_key, "POST", f"/v1/batches/{urllib.parse.quote(batch_id, safe='')}/cancel")
            status = str(batch.get("status") or "cancelling")
            return {
                "created": True,
                "terminal": False,
                "status": status,
                "timed_out_and_cancelled": True,
            }, cleanup_ids

        output_file_id = batch.get("output_file_id")
        error_file_id = batch.get("error_file_id")
        cleanup_ids.extend(str(value) for value in (output_file_id, error_file_id) if value)
        report: Dict[str, Any] = {
            "created": True,
            "terminal": True,
            "status": status,
            "timed_out_and_cancelled": False,
        }
        if status == "completed" and output_file_id:
            raw_output, _ = api_bytes(
                api_key,
                "GET",
                f"/v1/files/{urllib.parse.quote(str(output_file_id), safe='')}/content",
            )
            rows = parse_jsonl(raw_output)
            ledger = from_batch_results_auto(rows, provider="openai", endpoint="/v1/responses")
            report.update(
                {
                    "result_rows": len(rows),
                    "summary": {
                        "total": ledger["summary"]["total"],
                        "succeeded": ledger["summary"]["succeeded"],
                        "failed": ledger["summary"]["failed"],
                        "pending": ledger["summary"]["pending"],
                        "priced": ledger["summary"]["total_cost"] != "0",
                    },
                    "aggregate": sanitized_ledger(ledger["aggregate"]),
                    "warning_codes": [warning["code"] for warning in ledger["warnings"]],
                }
            )
        return report, cleanup_ids
    except Exception:
        if batch_id:
            try:
                api_json(api_key, "POST", f"/v1/batches/{urllib.parse.quote(batch_id, safe='')}/cancel")
            except OpenAIHTTPError:
                pass
        for file_id in cleanup_ids:
            delete_file(api_key, file_id)
        raise


def safe_write(path: Path, report: Dict[str, Any]) -> None:
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    forbidden = ("sk-", "resp_", "batch_", "file-", "org-", "proj_", "Reply with exactly OK")
    if any(value in encoded for value in forbidden):
        raise AssertionError("sanitized report contained a forbidden identifier or payload")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(encoded, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--max-wait-seconds", type=int, default=1800)
    parser.add_argument("--poll-seconds", type=int, default=5)
    args = parser.parse_args()
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY was not injected")

    report: Dict[str, Any] = {
        "schema_version": "0.1",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "evidence_type": "sanitized_live_provider_smoke",
        "safe_to_commit": True,
        "contains_private_payloads": False,
        "contains_account_or_request_identifiers": False,
        "provider": "openai",
        "privacy": {
            "prompt_was_public_fixed_text": True,
            "response_text_retained": False,
            "remote_identifiers_retained": False,
            "credential_retained": False,
            "cost_amounts_retained": False,
        },
    }
    cleanup_ids: list[str] = []
    exit_code = 1
    try:
        model, response = choose_and_run_response(api_key)
        response_ledger = from_response_auto(response, provider="openai", surface="openai.responses")
        report["responses"] = {
            "status": "passed",
            "selected_model": model,
            "usage_present": isinstance(response.get("usage"), dict),
            "ledger": sanitized_ledger(response_ledger),
        }
        report["costs_api"] = costs_access_probe(api_key)
        batch_report, cleanup = run_batch(
            api_key,
            model,
            max_wait_seconds=args.max_wait_seconds,
            poll_seconds=max(args.poll_seconds, 1),
        )
        cleanup_ids.extend(cleanup)
        report["batch"] = batch_report
        exit_code = 0 if batch_report.get("status") == "completed" and batch_report.get("summary", {}).get("succeeded") == 1 else 1
        report["status"] = "passed" if exit_code == 0 else "partial"
    except OpenAIHTTPError as exc:
        report["status"] = "failed"
        report["failure"] = {"stage": "openai_api", **exc.sanitized()}
    except Exception as exc:
        report["status"] = "failed"
        report["failure"] = {"stage": "local_smoke", "error_type": type(exc).__name__}
    finally:
        cleanup_results = [delete_file(api_key, file_id) for file_id in cleanup_ids]
        report["remote_files_cleanup"] = {
            "attempted": len(cleanup_ids),
            "all_deleted": bool(cleanup_ids) and all(cleanup_results),
        }
        safe_write(Path(args.report), report)
    print(f"Wrote sanitized OpenAI expansion smoke report to {args.report}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
