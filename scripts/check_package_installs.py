#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "fixtures" / "source-files" / "public-api-registry.json"


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print(f"$ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def runtime_names(language: str) -> list[str]:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return sorted(
        {
            name
            for capability in registry["capabilities"]
            for name in capability["languages"][language]["runtime"]
        }
    )


def copy_source_tree(workdir: Path) -> Path:
    source_root = workdir / "source"
    shutil.copytree(
        ROOT,
        source_root,
        ignore=shutil.ignore_patterns(".git", "node_modules", "build", "dist", "*.egg-info", "__pycache__", ".pytest_cache"),
    )
    return source_root


def write_quote_fixture(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "response": {
                    "model": "install-model",
                    "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
                },
                "options": {"provider": "openai", "surface": "openai.chat_completions"},
                "price_cards": [
                    {
                        "schema_version": "0.1",
                        "id": "openai:install-model:user",
                        "provider": "openai",
                        "model": "install-model",
                        "components": [
                            {"usage_component": "input_uncached_tokens", "unit": "token", "price": {"amount": "1", "currency": "USD", "per": "1000000"}},
                            {"usage_component": "output_text_tokens", "unit": "token", "price": {"amount": "2", "currency": "USD", "per": "1000000"}},
                        ],
                        "source": {"name": "user", "url": "https://example.com/contract", "retrieved_at": "2026-07-18T00:00:00Z"},
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def check_python_install(source_root: Path, workdir: Path) -> None:
    venv_dir = workdir / "python-venv"
    run(["python3", "-m", "venv", str(venv_dir)], workdir)
    python = venv_dir / "bin" / "python"
    environment = os.environ.copy()
    environment.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    run([str(python), "-m", "pip", "install", "--quiet", str(source_root)], workdir, env=environment)
    names = runtime_names("python")
    smoke = workdir / "python-package-smoke.py"
    smoke.write_text(
        f"""
import pathlib
import runcost

names = {names!r}
missing = [name for name in names if not hasattr(runcost, name)]
assert not missing, missing
package_root = pathlib.Path(runcost.__file__).parent
for path in package_root.rglob('*'):
    assert path.name != 'default-source-cache.json', path
    assert 'providers' not in path.parts or path.suffix != '.json', path

card = {{
    'schema_version': '0.1', 'id': 'openai:install-model:user', 'provider': 'openai', 'model': 'install-model',
    'components': [
        {{'usage_component': 'input_uncached_tokens', 'unit': 'token', 'price': {{'amount': '1', 'currency': 'USD', 'per': '1000000'}}}},
        {{'usage_component': 'output_text_tokens', 'unit': 'token', 'price': {{'amount': '2', 'currency': 'USD', 'per': '1000000'}}}},
    ],
    'source': {{'name': 'user', 'url': 'https://example.com/contract', 'retrieved_at': '2026-07-18T00:00:00Z'}},
}}
response = {{'model': 'install-model', 'usage': {{'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150}}}}
ledger = runcost.from_response(response, provider='openai', surface='openai.chat_completions', price_cards=[card])
assert ledger['total'] == '0.0002', ledger
implicit = runcost.from_response(response, provider='openai', surface='openai.chat_completions')
assert implicit['total'] == '0' and implicit['warnings'], implicit
auto = runcost.from_response_auto(response, provider='openai', surface='openai.chat_completions', price_cards=[card])
assert auto['total'] == '0.0002' and auto['metadata']['price_resolution']['selected_source'] == 'user', auto
assert tuple(runcost.DEFAULT_EXTERNAL_PRICE_SOURCES) == ('genai-prices', 'models.dev', 'litellm')
print('Python installed-package smoke passed')
""",
        encoding="utf-8",
    )
    run([str(python), str(smoke)], workdir)
    quote = workdir / "quote.json"
    write_quote_fixture(quote)
    run([str(venv_dir / "bin" / "runcost"), "quote", str(quote), "--no-resolve"], workdir)
    run([str(venv_dir / "bin" / "runcost"), "prices", "status", "--cache-dir", str(workdir / "python-cache")], workdir)


def check_javascript_install(source_root: Path, workdir: Path) -> None:
    pack_dir = workdir / "npm-pack"
    project_dir = workdir / "npm-project"
    pack_dir.mkdir()
    project_dir.mkdir()
    run(["npm", "pack", str(source_root / "packages/javascript/core"), "--pack-destination", str(pack_dir), "--silent"], source_root)
    tarballs = sorted(pack_dir.glob("runcost-*.tgz"))
    if len(tarballs) != 1:
        raise AssertionError(f"expected exactly one runcost tarball, found {len(tarballs)}")
    with tarfile.open(tarballs[0], "r:gz") as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        if any("default-source-cache" in name or "/data/providers/" in name or "/catalog/" in name for name in names):
            raise AssertionError(f"npm tarball contains bundled provider pricing: {names}")
        if max((member.size for member in members if member.isfile()), default=0) > 2_000_000:
            raise AssertionError("npm tarball contains an unexpectedly large file")
    (project_dir / "package.json").write_text('{"name":"runcost-install-check","version":"0.0.0","type":"module"}\n', encoding="utf-8")
    run(["npm", "install", "--silent", str(tarballs[0])], project_dir)
    javascript_names = runtime_names("javascript")
    smoke = project_dir / "package-smoke.mjs"
    smoke.write_text(
        f"""
import * as runcost from 'runcost';
import * as browser from 'runcost/browser';
const names = {json.dumps(javascript_names)};
const missing = names.filter((name) => !(name in runcost));
if (missing.length) throw new Error(`missing runtime APIs: ${{missing.join(', ')}}`);
const card = {{
  schema_version: '0.1', id: 'openai:install-model:user', provider: 'openai', model: 'install-model',
  components: [
    {{ usage_component: 'input_uncached_tokens', unit: 'token', price: {{ amount: '1', currency: 'USD', per: '1000000' }} }},
    {{ usage_component: 'output_text_tokens', unit: 'token', price: {{ amount: '2', currency: 'USD', per: '1000000' }} }}
  ],
  source: {{ name: 'user', url: 'https://example.com/contract', retrieved_at: '2026-07-18T00:00:00Z' }}
}};
const response = {{ model: 'install-model', usage: {{ prompt_tokens: 100, completion_tokens: 50, total_tokens: 150 }} }};
const ledger = runcost.fromResponse(response, {{ provider: 'openai', surface: 'openai.chat_completions', priceCards: [card] }});
if (ledger.total !== '0.0002') throw new Error(JSON.stringify(ledger));
const implicit = runcost.fromResponse(response, {{ provider: 'openai', surface: 'openai.chat_completions' }});
if (implicit.total !== '0' || !implicit.warnings.length) throw new Error(JSON.stringify(implicit));
const auto = await runcost.fromResponseAuto(response, {{ provider: 'openai', surface: 'openai.chat_completions', priceCards: [card] }});
if (auto.total !== '0.0002' || auto.metadata.price_resolution.selected_source !== 'user') throw new Error(JSON.stringify(auto));
const browserAuto = await browser.fromResponseAuto(response, {{ provider: 'openai', surface: 'openai.chat_completions', priceCards: [card] }});
if (browserAuto.total !== '0.0002') throw new Error(JSON.stringify(browserAuto));
if (runcost.DEFAULT_EXTERNAL_PRICE_SOURCES.join(',') !== 'genai-prices,models.dev,litellm') throw new Error('default source order mismatch');
console.log('JavaScript installed-package smoke passed');
""",
        encoding="utf-8",
    )
    run(["node", str(smoke)], project_dir)
    quote = project_dir / "quote.json"
    write_quote_fixture(quote)
    run(["node", "node_modules/runcost/cli.js", "quote", str(quote), "--no-resolve"], project_dir)
    run(["node", "node_modules/runcost/cli.js", "prices", "status", "--cache-dir", str(workdir / "javascript-cache")], project_dir)


def check_go_install(source_root: Path, workdir: Path) -> None:
    project_dir = workdir / "go-project"
    project_dir.mkdir()
    references = "\n".join(f"    _ = ledger.{name}" for name in runtime_names("go"))
    (project_dir / "go.mod").write_text(
        f"module runcost-install-check\n\ngo 1.26\n\nrequire github.com/adamallcock/runcost v0.0.0\n\nreplace github.com/adamallcock/runcost => {source_root}\n",
        encoding="utf-8",
    )
    (project_dir / "ledger_test.go").write_text(
        f"""package installcheck

import (
    "context"
    "testing"
    ledger "github.com/adamallcock/runcost/packages/go/ledger"
)

func TestInstalledPackage(t *testing.T) {{
{references}
    card := ledger.Object{{
        "schema_version": "0.1", "id": "openai:install-model:user", "provider": "openai", "model": "install-model",
        "components": []any{{
            ledger.Object{{"usage_component": "input_uncached_tokens", "unit": "token", "price": ledger.Object{{"amount": "1", "currency": "USD", "per": "1000000"}}}},
            ledger.Object{{"usage_component": "output_text_tokens", "unit": "token", "price": ledger.Object{{"amount": "2", "currency": "USD", "per": "1000000"}}}},
        }},
        "source": ledger.Object{{"name": "user", "url": "https://example.com/contract", "retrieved_at": "2026-07-18T00:00:00Z"}},
    }}
    response := ledger.Object{{"model": "install-model", "usage": ledger.Object{{"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}}}}
    priced := ledger.FromResponse(response, ledger.Object{{"provider": "openai", "surface": "openai.chat_completions"}}, []any{{card}}, nil)
    if priced["total"] != "0.0002" {{ t.Fatalf("unexpected total: %#v", priced) }}
    implicit := ledger.FromResponse(response, ledger.Object{{"provider": "openai", "surface": "openai.chat_completions"}}, nil, nil)
    if implicit["total"] != "0" || len(implicit["warnings"].([]any)) == 0 {{ t.Fatalf("implicit pricing occurred: %#v", implicit) }}
    auto, err := ledger.FromResponseAuto(context.Background(), response, ledger.Object{{"provider": "openai", "surface": "openai.chat_completions"}}, []any{{card}}, nil)
    if err != nil || auto["total"] != "0.0002" {{ t.Fatalf("auto pricing failed: %#v %v", auto, err) }}
    if len(ledger.DefaultExternalPriceSources) != 3 || ledger.DefaultExternalPriceSources[0] != "genai-prices" {{ t.Fatalf("source order mismatch: %#v", ledger.DefaultExternalPriceSources) }}
}}
""",
        encoding="utf-8",
    )
    run(["go", "test", "./..."], project_dir)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="runcost-package-check-") as temporary:
        workdir = Path(temporary)
        source_root = copy_source_tree(workdir)
        check_python_install(source_root, workdir)
        check_javascript_install(source_root, workdir)
        check_go_install(source_root, workdir)
    print("Package install checks passed without bundled provider pricing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
