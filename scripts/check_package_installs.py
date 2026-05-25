#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print(f"$ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def check_python_install(workdir: Path) -> None:
    venv_dir = workdir / "python-venv"
    run(["python3", "-m", "venv", str(venv_dir)], workdir)
    python = venv_dir / "bin" / "python"
    pip_env = os.environ.copy()
    pip_env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    run([str(python), "-m", "pip", "install", "--quiet", str(ROOT)], workdir, env=pip_env)
    run(
        [
            str(python),
            "-c",
            "from runcost import calculate_cost, from_response, track_langchain_costs, price_cards_from_helicone, price_cards_from_user_pricing; print(calculate_cost, from_response, track_langchain_costs, price_cards_from_helicone, price_cards_from_user_pricing)",
        ],
        workdir,
    )


def check_javascript_install(workdir: Path) -> None:
    pack_dir = workdir / "npm-pack"
    project_dir = workdir / "npm-project"
    pack_dir.mkdir()
    project_dir.mkdir()
    run(["npm", "pack", str(ROOT / "packages/javascript/core"), "--pack-destination", str(pack_dir)], ROOT)
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
            'import { calculateCost, fromResponse, createRunCostVercelMiddleware, priceCardsFromHelicone, priceCardsFromUserPricing } from "runcost"; console.log(typeof calculateCost, typeof fromResponse, typeof createRunCostVercelMiddleware, typeof priceCardsFromHelicone, typeof priceCardsFromUserPricing);',
        ],
        project_dir,
    )


def check_go_install(workdir: Path) -> None:
    project_dir = workdir / "go-project"
    project_dir.mkdir()
    (project_dir / "ledger_test.go").write_text(
        """package installcheck

import (
    "testing"

    ledger "github.com/adamallcock/runcost/packages/go/ledger"
)

func TestImport(t *testing.T) {
    value := ledger.Object{"ok": true}
    if value["ok"] != true {
        t.Fatalf("unexpected import check value: %#v", value)
    }
}
""",
        encoding="utf-8",
    )
    run(["go", "mod", "init", "runcost-install-check"], project_dir)
    run(["go", "mod", "edit", "-replace", f"github.com/adamallcock/runcost={ROOT}"], project_dir)
    run(["go", "get", "github.com/adamallcock/runcost/packages/go/ledger"], project_dir)
    run(["go", "test", "./..."], project_dir)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="runcost-install-check-") as temp:
        workdir = Path(temp)
        check_python_install(workdir)
        check_javascript_install(workdir)
        check_go_install(workdir)
    print("Package install checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
