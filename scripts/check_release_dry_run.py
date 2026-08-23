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
PYTHON_BUILD_TOOLCHAIN = ["build==1.5.0", "setuptools==84.0.0", "wheel==0.47.0", "twine==7.0.0"]


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print(f"$ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def assert_one(path: Path, pattern: str, label: str) -> Path:
    matches = sorted(path.glob(pattern))
    if len(matches) != 1:
        raise AssertionError(f"expected exactly one {label}, found {len(matches)}")
    return matches[0]


def copy_source_tree(workdir: Path, name: str) -> Path:
    source_root = workdir / name
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


def release_environment() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    if "SOURCE_DATE_EPOCH" not in env:
        completed = subprocess.run(
            ["git", "show", "-s", "--format=%ct", "HEAD"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        env["SOURCE_DATE_EPOCH"] = completed.stdout.strip()
    try:
        if int(env["SOURCE_DATE_EPOCH"]) < 0:
            raise ValueError
    except ValueError as exc:
        raise AssertionError("SOURCE_DATE_EPOCH must be a non-negative integer") from exc
    return env


def assert_artifact_directories_identical(first: Path, second: Path, label: str) -> None:
    first_names = sorted(path.name for path in first.iterdir() if path.is_file())
    second_names = sorted(path.name for path in second.iterdir() if path.is_file())
    if first_names != second_names:
        raise AssertionError(f"{label} artifact filenames differ: {first_names!r} != {second_names!r}")
    for name in first_names:
        if (first / name).read_bytes() != (second / name).read_bytes():
            raise AssertionError(f"{label} artifact is not reproducible: {name}")


def check_python_build(source_roots: list[Path], workdir: Path, env: dict[str, str]) -> None:
    venv_dir = workdir / "python-build-venv"
    run(["python3", "-m", "venv", str(venv_dir)], workdir)
    python = venv_dir / "bin" / "python"
    run([str(python), "-m", "pip", "install", "--quiet", *PYTHON_BUILD_TOOLCHAIN], workdir, env=env)
    dist_dirs = []
    for index, source_root in enumerate(source_roots, start=1):
        dist_dir = workdir / f"python-dist-{index}"
        run([str(python), "-m", "build", "--no-isolation", "--outdir", str(dist_dir)], source_root, env=env)
        sdist = assert_one(dist_dir, "runcost_ai-*.tar.gz", "Python source distribution")
        run([str(python), str(source_root / "scripts/normalize_python_sdist.py"), str(sdist)], source_root, env=env)
        dist_dirs.append(dist_dir)

    assert_artifact_directories_identical(dist_dirs[0], dist_dirs[1], "Python")
    print("Python artifacts are byte-identical across two independent builds.", flush=True)
    wheel = assert_one(dist_dirs[0], "runcost_ai-*.whl", "Python wheel")
    sdist = assert_one(dist_dirs[0], "runcost_ai-*.tar.gz", "Python source distribution")
    run([str(python), "-m", "twine", "check", str(wheel), str(sdist)], source_roots[0], env=env)
    run(
        [str(python), "-m", "pip", "install", "--quiet", "--force-reinstall", "--no-deps", "--no-build-isolation", str(sdist)],
        workdir,
        env=env,
    )
    run([str(python), "-c", "import runcost; print(runcost.__name__)"], workdir, env=env)
    print(f"Built Python artifacts: {wheel.name}, {sdist.name}", flush=True)


def check_npm_archive(source_root: Path, tarball: Path) -> None:
    with tarfile.open(tarball, "r:gz") as archive:
        names = set(archive.getnames())
        license_member = archive.extractfile("package/LICENSE") if "package/LICENSE" in names else None
        packaged_license = license_member.read().decode("utf-8") if license_member is not None else None
    if "package/README.md" not in names:
        raise AssertionError("npm package tarball must include README.md")
    if license_member is None:
        raise AssertionError("npm package tarball must include LICENSE")
    repository_license = (source_root / "LICENSE").read_text(encoding="utf-8")
    if packaged_license != repository_license:
        raise AssertionError("npm package LICENSE must exactly match the repository LICENSE")


def check_npm_pack(source_roots: list[Path], workdir: Path, env: dict[str, str]) -> None:
    pack_dirs = []
    for index, source_root in enumerate(source_roots, start=1):
        pack_dir = workdir / f"npm-pack-{index}"
        pack_dir.mkdir()
        run(
            ["npm", "pack", str(source_root / "packages/javascript/core"), "--pack-destination", str(pack_dir)],
            source_root,
            env=env,
        )
        check_npm_archive(source_root, assert_one(pack_dir, "runcost-*.tgz", "npm package tarball"))
        pack_dirs.append(pack_dir)

    assert_artifact_directories_identical(pack_dirs[0], pack_dirs[1], "npm")
    print("npm artifacts are byte-identical across two independent packs.", flush=True)
    tarball = assert_one(pack_dirs[0], "runcost-*.tgz", "npm package tarball")
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
        source_roots = [copy_source_tree(workdir, name) for name in ("source-1", "source-2")]
        env = release_environment()
        check_package_versions(source_roots[0])
        check_python_build(source_roots, workdir, env)
        check_npm_pack(source_roots, workdir, env)
        check_go_module_import(source_roots[0], workdir)
    print("Release dry-run checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
