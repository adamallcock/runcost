#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print(f"$ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def copy_source_tree(workdir: Path) -> Path:
    source_root = workdir / "source"
    shutil.copytree(
        ROOT,
        source_root,
        ignore=shutil.ignore_patterns(
            ".git",
            "node_modules",
            "build",
            "dist",
            "*.egg-info",
            "__pycache__",
            ".pytest_cache",
        ),
    )
    return source_root


def check_python_install(source_root: Path, workdir: Path) -> None:
    venv_dir = workdir / "python-venv"
    run(["python3", "-m", "venv", str(venv_dir)], workdir)
    python = venv_dir / "bin" / "python"
    pip_env = os.environ.copy()
    pip_env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    run([str(python), "-m", "pip", "install", "--quiet", str(source_root)], workdir, env=pip_env)
    run(
        [
            str(python),
            "-c",
            "from pathlib import Path; from runcost import aggregate_cost_ledgers, calculate_cost, from_response, extract_bedrock_invoke_model_usage, extract_openai_embeddings_usage, from_ag2_usage_summary, from_haystack_generator_result, from_litellm_response, track_langchain_costs, price_cards_from_helicone, price_cards_from_json_file, price_cards_from_yaml_file, price_cards_from_models_dev, price_cards_from_official_snapshot, price_cards_from_source_cache, price_cards_from_user_pricing; p=Path('prices.json'); p.write_text('{\"provider\":\"test\",\"models\":[{\"id\":\"test\",\"prices\":{\"input\":\"1\"}}]}'); y=Path('prices.yaml'); y.write_text('provider: test\\nmodels:\\n  - id: test\\n    prices:\\n      input: \"1\"\\n'); print(aggregate_cost_ledgers, calculate_cost, from_response, extract_bedrock_invoke_model_usage, extract_openai_embeddings_usage, from_ag2_usage_summary, from_haystack_generator_result, from_litellm_response, track_langchain_costs, price_cards_from_helicone, price_cards_from_json_file(p), price_cards_from_yaml_file(y), price_cards_from_models_dev, price_cards_from_official_snapshot, price_cards_from_source_cache, price_cards_from_user_pricing)",
        ],
        workdir,
    )


def check_javascript_install(source_root: Path, workdir: Path) -> None:
    pack_dir = workdir / "npm-pack"
    project_dir = workdir / "npm-project"
    pack_dir.mkdir()
    project_dir.mkdir()
    run(["npm", "pack", str(source_root / "packages/javascript/core"), "--pack-destination", str(pack_dir)], source_root)
    tarballs = sorted(pack_dir.glob("runcost-*.tgz"))
    if len(tarballs) != 1:
        raise AssertionError(f"expected exactly one runcost tarball, found {len(tarballs)}")
    (project_dir / "package.json").write_text(
        '{"name":"runcost-install-check","version":"0.0.0","type":"module"}\n',
        encoding="utf-8",
    )
    run(["npm", "install", "--silent", str(tarballs[0])], project_dir)
    run(
        [
            "node",
            "--input-type=module",
            "-e",
            'import fs from "node:fs"; import { aggregateCostLedgers, calculateCost, fromResponse, extractBedrockInvokeModelUsage, extractOpenAIEmbeddingsUsage, fromAG2UsageSummary, fromHaystackGeneratorResult, fromLiteLLMResponse, createRunCostVercelMiddleware, priceCardsFromHelicone, priceCardsFromJSONFile, priceCardsFromYAMLFile, priceCardsFromModelsDev, priceCardsFromOfficialSnapshot, priceCardsFromSourceCache, priceCardsFromUserPricing } from "runcost"; fs.writeFileSync("prices.json", JSON.stringify({ provider: "test", models: [{ id: "test", prices: { input: "1" } }] })); fs.writeFileSync("prices.yaml", "provider: test\\nmodels:\\n  - id: test\\n    prices:\\n      input: \\"1\\"\\n"); console.log(typeof aggregateCostLedgers, typeof calculateCost, typeof fromResponse, typeof extractBedrockInvokeModelUsage, typeof extractOpenAIEmbeddingsUsage, typeof fromAG2UsageSummary, typeof fromHaystackGeneratorResult, typeof fromLiteLLMResponse, typeof createRunCostVercelMiddleware, typeof priceCardsFromHelicone, priceCardsFromJSONFile("prices.json").length, priceCardsFromYAMLFile("prices.yaml").length, typeof priceCardsFromModelsDev, typeof priceCardsFromOfficialSnapshot, typeof priceCardsFromSourceCache, typeof priceCardsFromUserPricing);',
        ],
        project_dir,
    )


def check_go_install(source_root: Path, workdir: Path) -> None:
    project_dir = workdir / "go-project"
    project_dir.mkdir()
    (project_dir / "ledger_test.go").write_text(
        """package installcheck

import (
    "os"
    "testing"

    ledger "github.com/adamallcock/runcost/packages/go/ledger"
)

func TestImport(t *testing.T) {
    value := ledger.Object{"ok": true}
    if value["ok"] != true {
        t.Fatalf("unexpected import check value: %#v", value)
    }
    result := ledger.AggregateCostLedgers([]any{}, ledger.Object{
        "stream_final_usage_expected": true,
        "stream_final_usage_present": false,
    })
    if result["total"] != "0" {
        t.Fatalf("unexpected aggregate total: %#v", result["total"])
    }
    cards := ledger.PriceCardsFromSourceCache(ledger.Object{"price_cards": []any{
        ledger.Object{
            "schema_version": "0.1",
            "id": "test:test:source-cache",
            "provider": "test",
            "model": "test",
            "components": []any{ledger.Object{
                "usage_component": "input_uncached_tokens",
                "unit": "token",
                "price": ledger.Object{"amount": "1", "currency": "USD", "per": "1000000"},
            }},
            "source": ledger.Object{"name": "test"},
        },
    }})
    if len(cards) != 1 {
        t.Fatalf("unexpected source-cache card count: %d", len(cards))
    }
    if err := os.WriteFile("prices.json", []byte(`{"provider":"test","models":[{"id":"test","prices":{"input":"1"}}]}`), 0o600); err != nil {
        t.Fatal(err)
    }
    fileCards, err := ledger.PriceCardsFromJSONFile("prices.json", "user-pricing")
    if err != nil {
        t.Fatal(err)
    }
    if len(fileCards) != 1 {
        t.Fatalf("unexpected file card count: %d", len(fileCards))
    }
    if err := os.WriteFile("prices.yaml", []byte(`provider: test
models:
  - id: test
    prices:
      input: "1"
`), 0o600); err != nil {
        t.Fatal(err)
    }
    yamlCards, err := ledger.PriceCardsFromYAMLFile("prices.yaml", "user-pricing")
    if err != nil {
        t.Fatal(err)
    }
    if len(yamlCards) != 1 {
        t.Fatalf("unexpected YAML file card count: %d", len(yamlCards))
    }
    modelsDevCards := ledger.PriceCardsFromModelsDev(ledger.Object{
        "test": ledger.Object{
            "models": ledger.Object{
                "test-model": ledger.Object{"cost": ledger.Object{"input": 1}},
            },
        },
    })
    if len(modelsDevCards) != 1 {
        t.Fatalf("unexpected models.dev card count: %d", len(modelsDevCards))
    }
    officialCards := ledger.PriceCardsFromOfficialSnapshot(ledger.Object{
        "provider": "test",
        "rows": []any{ledger.Object{"model": "test-model", "input": 1}},
    })
    if len(officialCards) != 1 {
        t.Fatalf("unexpected official snapshot card count: %d", len(officialCards))
    }
}
""",
        encoding="utf-8",
    )
    run(["go", "mod", "init", "runcost-install-check"], project_dir)
    run(["go", "mod", "edit", "-replace", f"github.com/adamallcock/runcost={source_root}"], project_dir)
    run(["go", "get", "github.com/adamallcock/runcost/packages/go/ledger"], project_dir)
    run(["go", "test", "./..."], project_dir)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="runcost-install-check-") as temp:
        workdir = Path(temp)
        source_root = copy_source_tree(workdir)
        check_python_install(source_root, workdir)
        check_javascript_install(source_root, workdir)
        check_go_install(source_root, workdir)
    print("Package install checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
