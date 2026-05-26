#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "fixtures" / "source-files" / "user-pricing-file-basic.json"
COMMAND = ROOT / "scripts" / "refresh_price_sources.py"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / "source-cache.json"
        subprocess.run(
            [
                sys.executable,
                str(COMMAND),
                "--source-type",
                "user-pricing",
                "--input",
                str(SOURCE),
                "--output",
                str(output),
                "--retrieved-at",
                "2026-05-25T12:00:00Z",
                "--generated-at",
                "2026-05-25T12:00:00Z",
            ],
            check=True,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            text=True,
        )
        envelope = json.loads(output.read_text(encoding="utf-8"))
        sources = envelope.get("sources", [])
        assert envelope["schema_version"] == "0.1"
        assert envelope["generated_at"] == "2026-05-25T12:00:00Z"
        assert len(sources) == 1
        assert sources[0]["type"] == "user-pricing"
        assert sources[0]["url"].startswith("file:")
        assert sources[0]["retrieved_at"] == "2026-05-25T12:00:00Z"
        assert sources[0]["checksum"].startswith("sha256:")
        assert len(sources[0]["price_cards"]) == 1
        card = sources[0]["price_cards"][0]
        assert card["id"] == "openai:gpt-file:user-pricing"
        assert card["source"]["name"] == "user-pricing"
        assert card["source"]["url"].startswith("file:")
        assert card["source"]["retrieved_at"] == "2026-05-25T12:00:00Z"
    print("Source refresh command checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
