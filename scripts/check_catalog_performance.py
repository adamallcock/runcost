#!/usr/bin/env python3
"""Enforce conservative runtime and package-size budgets without bundled prices."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUDGET_PATH = ROOT / "fixtures" / "source-files" / "performance-budgets.json"
REPORT_PATH = ROOT / "docs" / "internal" / "reports" / "2026-07-18-catalog-performance-baseline.json"
MB = 1024 * 1024


def command_json(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=ROOT, check=True, text=True, capture_output=True)
    return json.loads(completed.stdout)


def tree_bytes(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file()) if path.exists() else 0


def measurements() -> dict[str, float]:
    python = command_json(
        [
            "python3",
            "-c",
            (
                "import json,resource,sys,time;sys.path.insert(0,'packages/python');"
                "start=time.perf_counter();import runcost;import_ms=(time.perf_counter()-start)*1000;"
                "cards=[{'schema_version':'0.1','id':f'openai:model-{i}:perf','provider':'openai',"
                "'surface':'openai.chat_completions','model':f'model-{i}','components':["
                "{'usage_component':'input_uncached_tokens','unit':'token','price':{'amount':'1','currency':'USD','per':'1000000'}},"
                "{'usage_component':'output_text_tokens','unit':'token','price':{'amount':'2','currency':'USD','per':'1000000'}}],"
                "'source':{'name':'performance-fixture'}} for i in range(10000)];"
                "start=time.perf_counter();catalog=runcost.compile_price_catalog(cards);compile_ms=(time.perf_counter()-start)*1000;"
                "response={'object':'chat.completion','model':'model-9999','choices':[],"
                "'usage':{'prompt_tokens':100,'completion_tokens':40}};"
                "start=time.perf_counter();[runcost.from_response(response,provider='openai',surface='openai.chat_completions',"
                "price_cards=catalog) for _ in range(500)];warm=(time.perf_counter()-start)*1000;"
                "start=time.perf_counter();[runcost.from_response_auto(response,provider='openai',surface='openai.chat_completions',"
                "price_cards=cards) for _ in range(100)];auto=(time.perf_counter()-start)*1000;"
                "rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss;rss_mb=rss/1024/1024 if sys.platform=='darwin' else rss/1024;"
                "print(json.dumps({'import_ms':import_ms,'compile_ms':compile_ms,'warm_ms':warm,'auto_ms':auto,'rss_mb':rss_mb,'cards':len(catalog)}))"
            ),
        ]
    )
    javascript = command_json(
        [
            "node",
            "--input-type=module",
            "-e",
            (
                "const start=performance.now();const m=await import('./packages/javascript/core/index.js');"
                "const importMs=performance.now()-start;const cards=Array.from({length:10000},(_,i)=>({schema_version:'0.1',"
                "id:`openai:model-${i}:perf`,provider:'openai',surface:'openai.chat_completions',model:`model-${i}`,components:["
                "{usage_component:'input_uncached_tokens',unit:'token',price:{amount:'1',currency:'USD',per:'1000000'}},"
                "{usage_component:'output_text_tokens',unit:'token',price:{amount:'2',currency:'USD',per:'1000000'}}],"
                "source:{name:'performance-fixture'}}));const compileStart=performance.now();const catalog=m.compilePriceCatalog(cards);"
                "const compileMs=performance.now()-compileStart;const response={object:'chat.completion',model:'model-9999',choices:[],"
                "usage:{prompt_tokens:100,completion_tokens:40}};const warmStart=performance.now();for(let i=0;i<500;i++)"
                "m.fromResponse(response,{provider:'openai',surface:'openai.chat_completions',priceCards:catalog});"
                "const warmMs=performance.now()-warmStart;const autoStart=performance.now();for(let i=0;i<100;i++)await m.fromResponseAuto(response,"
                "{provider:'openai',surface:'openai.chat_completions',priceCards:cards});const autoMs=performance.now()-autoStart;"
                "console.log(JSON.stringify({import_ms:importMs,compile_ms:compileMs,warm_ms:warmMs,auto_ms:autoMs,"
                "rss_mb:process.memoryUsage().rss/1024/1024,cards:catalog.priceCards.length}));"
            ),
        ]
    )
    npm_data = json.loads(
        subprocess.run(
            ["npm", "pack", "./packages/javascript/core", "--dry-run", "--json"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        ).stdout
    )[0]
    return {
        "python_import_ms": round(float(python["import_ms"]), 3),
        "python_compile_10000_cards_ms": round(float(python["compile_ms"]), 3),
        "python_warm_500_quotes_ms": round(float(python["warm_ms"]), 3),
        "python_warm_100_auto_quotes_ms": round(float(python["auto_ms"]), 3),
        "python_rss_mb": round(float(python["rss_mb"]), 3),
        "javascript_import_ms": round(float(javascript["import_ms"]), 3),
        "javascript_compile_10000_cards_ms": round(float(javascript["compile_ms"]), 3),
        "javascript_warm_500_quotes_ms": round(float(javascript["warm_ms"]), 3),
        "javascript_warm_100_auto_quotes_ms": round(float(javascript["auto_ms"]), 3),
        "javascript_rss_mb": round(float(javascript["rss_mb"]), 3),
        "python_bundled_price_data_mb": round(tree_bytes(ROOT / "packages/python/runcost/data") / MB, 3),
        "javascript_bundled_price_data_mb": round(tree_bytes(ROOT / "packages/javascript/core/data") / MB, 3),
        "go_bundled_price_data_mb": round(tree_bytes(ROOT / "packages/go/ledger/data") / MB, 3),
        "browser_entrypoint_mb": round((ROOT / "packages/javascript/core/browser.js").stat().st_size / MB, 3),
        "npm_pack_mb": round(float(npm_data["size"]) / MB, 3),
        "npm_unpacked_mb": round(float(npm_data["unpackedSize"]) / MB, 3),
        "synthetic_catalog_cards": int(python["cards"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    budget_data = json.loads(BUDGET_PATH.read_text(encoding="utf-8"))
    budgets = budget_data["budgets"]
    measured = measurements()
    failures = [f"{name}={measured[name]} exceeds {limit}" for name, limit in budgets.items() if measured[name] > limit]
    report = {
        "schema_version": "0.1",
        "measured_on": "2026-07-18",
        "measurements": measured,
        "budgets": budgets,
        "status": "failed" if failures else "passed",
        "failures": failures,
        "notes": [
            "Latency and RSS are conservative regression guards, not cross-machine benchmarks.",
            "The synthetic 10,000-card caller-owned catalog exercises indexing without shipping provider prices.",
            "Auto timings use explicit cards so the benchmark never depends on network availability.",
            "All bundled price-data measurements must remain zero.",
            budget_data["update_policy"],
        ],
    }
    if args.write_report:
        REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if failures:
        raise SystemExit("catalog performance budgets failed: " + "; ".join(failures))
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
