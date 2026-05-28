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
GO_MODULE = "github.com/adamallcock/runcost"


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print(f"$ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def assert_one(path: Path, pattern: str, label: str) -> Path:
    matches = sorted(path.glob(pattern))
    if len(matches) != 1:
        raise AssertionError(f"expected exactly one {label}, found {len(matches)}")
    return matches[0]


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


def check_python_build(source_root: Path, workdir: Path) -> None:
    venv_dir = workdir / "python-build-venv"
    dist_dir = workdir / "python-dist"
    run(["python3", "-m", "venv", str(venv_dir)], workdir)
    python = venv_dir / "bin" / "python"
    env = os.environ.copy()
    env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    run([str(python), "-m", "pip", "install", "--quiet", "--upgrade", "build"], workdir, env=env)
    run([str(python), "-m", "build", "--outdir", str(dist_dir)], source_root, env=env)
    wheel = assert_one(dist_dir, "runcost_ai-*.whl", "Python wheel")
    sdist = assert_one(dist_dir, "runcost_ai-*.tar.gz", "Python source distribution")
    print(f"Built Python artifacts: {wheel.name}, {sdist.name}", flush=True)


def check_npm_pack(source_root: Path, workdir: Path) -> None:
    pack_dir = workdir / "npm-pack"
    pack_dir.mkdir()
    run(["npm", "pack", str(source_root / "packages/javascript/core"), "--pack-destination", str(pack_dir)], source_root)
    tarball = assert_one(pack_dir, "runcost-*.tgz", "npm package tarball")
    with tarfile.open(tarball, "r:gz") as archive:
        names = set(archive.getnames())
    if "package/README.md" not in names:
        raise AssertionError("npm package tarball must include README.md")
    print(f"Built npm artifact: {tarball.name}", flush=True)


def check_go_module_import(source_root: Path, workdir: Path) -> None:
    go_mod = (source_root / "go.mod").read_text(encoding="utf-8")
    first_line = go_mod.splitlines()[0] if go_mod else ""
    if first_line != f"module {GO_MODULE}":
        raise AssertionError(f"go.mod module must be {GO_MODULE}")

    project_dir = workdir / "go-release-check"
    project_dir.mkdir()
    (project_dir / "ledger_test.go").write_text(
        f"""package releasecheck

import (
    "encoding/json"
    "testing"

    ledger "{GO_MODULE}/packages/go/ledger"
)

func TestReleasedImportPath(t *testing.T) {{
    result := ledger.CalculateCost(
        ledger.Object{{
            "schema_version": "0.1",
            "provider": "release-check",
            "surface": "release-check",
            "model": ledger.Object{{"requested": "model", "billed": "model", "alias_resolution": "none"}},
            "components": []any{{ledger.Object{{"name": "input_uncached_tokens", "quantity": "1000", "unit": "token"}}}},
        }},
        []any{{ledger.Object{{
            "schema_version": "0.1",
            "id": "release-check:model",
            "provider": "release-check",
            "surface": "release-check",
            "model": "model",
            "components": []any{{ledger.Object{{
                "usage_component": "input_uncached_tokens",
                "unit": "token",
                "price": ledger.Object{{"amount": "1", "currency": "USD", "per": "1000000"}},
            }}}},
            "source": ledger.Object{{"name": "release-check"}},
        }}}},
        nil,
    )
    if result["total"] != "0.001" {{
        encoded, _ := json.Marshal(result)
        t.Fatalf("unexpected release-check total: %s", encoded)
    }}
}}
""",
        encoding="utf-8",
    )
    run(["go", "mod", "init", "runcost-release-check"], project_dir)
    run(["go", "mod", "edit", "-replace", f"{GO_MODULE}={source_root}"], project_dir)
    run(["go", "get", f"{GO_MODULE}/packages/go/ledger"], project_dir)
    run(["go", "test", "./..."], project_dir)


def check_package_versions(source_root: Path) -> None:
    root_version = json.loads((source_root / "package.json").read_text(encoding="utf-8"))["version"]
    npm_version = json.loads((source_root / "packages/javascript/core/package.json").read_text(encoding="utf-8"))["version"]
    if npm_version != root_version:
        raise AssertionError("npm package version must match root package version")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="runcost-release-dry-run-") as temp:
        workdir = Path(temp)
        source_root = copy_source_tree(workdir)
        check_package_versions(source_root)
        check_python_build(source_root, workdir)
        check_npm_pack(source_root, workdir)
        check_go_module_import(source_root, workdir)
    print("Release dry-run checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
