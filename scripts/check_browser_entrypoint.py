#!/usr/bin/env python3
"""Check browser entrypoint drift and Node-builtin-free imports."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_browser_entrypoint import OUTPUT, render  # noqa: E402


def main() -> int:
    if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != render():
        raise SystemExit("browser.js is stale; run python3 scripts/build_browser_entrypoint.py")
    text = OUTPUT.read_text(encoding="utf-8")
    forbidden = [token for token in ('from "node:', "from 'node:", "require(") if token in text]
    if forbidden:
        raise SystemExit(f"browser.js contains Node-only imports: {forbidden}")
    subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            (
                "import('./packages/javascript/core/browser.js').then(m => {"
                "const cards=[{schema_version:'0.1',id:'test',provider:'nvidia',surface:'nvidia.chat_completions',model:'test',"
                "components:[{usage_component:'input_uncached_tokens',unit:'token',price:{amount:'1',currency:'USD',per:'1000000'}}],source:{name:'test'}}];"
                "const out=m.fromResponse({model:'test',choices:[{}],usage:{prompt_tokens:100,completion_tokens:0}},"
                "{provider:'nvidia',surface:'nvidia.chat_completions',priceCards:cards});"
                "if(out.total!=='0.0001')throw new Error(JSON.stringify(out));})"
            ),
        ],
        cwd=ROOT,
        check=True,
    )
    print("browser/edge entrypoint smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
