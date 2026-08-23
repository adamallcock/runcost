#!/usr/bin/env python3
"""Normalize a Python sdist so retries produce the same archive bytes."""

from __future__ import annotations

import argparse
import copy
import gzip
import os
import stat
import tarfile
import tempfile
from pathlib import Path


def source_date_epoch() -> int:
    raw = os.environ.get("SOURCE_DATE_EPOCH")
    if raw is None:
        raise SystemExit("SOURCE_DATE_EPOCH is required")
    try:
        epoch = int(raw)
    except ValueError as exc:
        raise SystemExit("SOURCE_DATE_EPOCH must be an integer Unix timestamp") from exc
    if epoch < 0:
        raise SystemExit("SOURCE_DATE_EPOCH must not be negative")
    return epoch


def normalize_sdist(path: Path, epoch: int) -> None:
    if not path.is_file() or not path.name.endswith(".tar.gz"):
        raise SystemExit(f"expected an existing .tar.gz sdist: {path}")

    original_mode = stat.S_IMODE(path.stat().st_mode)
    with tempfile.NamedTemporaryFile(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)

    try:
        with tarfile.open(path, "r:gz") as source, temporary.open("wb") as raw_output:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw_output, mtime=epoch, compresslevel=9) as gzip_output:
                with tarfile.open(fileobj=gzip_output, mode="w", format=tarfile.PAX_FORMAT) as destination:
                    for member in source.getmembers():
                        normalized = copy.copy(member)
                        normalized.mtime = epoch
                        normalized.uid = 0
                        normalized.gid = 0
                        normalized.uname = ""
                        normalized.gname = ""
                        normalized.pax_headers = {}
                        content = source.extractfile(member) if member.isfile() else None
                        destination.addfile(normalized, content)
        os.chmod(temporary, original_mode)
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sdist", type=Path)
    args = parser.parse_args()
    normalize_sdist(args.sdist, source_date_epoch())
    print(f"Normalized {args.sdist}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
