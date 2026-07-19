#!/usr/bin/env python3
"""Build and validate the static RunCost playground, metadata, and payload."""

from __future__ import annotations

import os
import re
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYGROUND = ROOT / "playground"
DIST = PLAYGROUND / "dist"
ROUTES = [
    "",
    "playground",
    "batch",
    "methodology",
    "openai-cost-calculator",
    "anthropic-cost-calculator",
    "gemini-cost-calculator",
    "batch-api-cost-calculator",
]
PUBLIC_ORIGIN = "https://adamallcock.github.io/runcost"


def require(pattern: str, text: str, message: str) -> None:
    if not re.search(pattern, text, re.IGNORECASE):
        raise AssertionError(message)


def main() -> int:
    subprocess.run(
        ["npm", "run", "build"],
        cwd=PLAYGROUND,
        env={**os.environ, "VITE_BASE_PATH": "/runcost/"},
        check=True,
    )

    for route in ROUTES:
        path = DIST / route / "index.html" if route else DIST / "index.html"
        html = path.read_text(encoding="utf-8")
        canonical = f"{PUBLIC_ORIGIN}/{route + '/' if route else ''}"
        require(r"<title>[^<]+</title>", html, f"{route or '/'}: missing title")
        require(r'<meta name="description" content="[^\"]+"', html, f"{route or '/'}: missing description")
        require(r'<meta property="og:title"', html, f"{route or '/'}: missing og:title")
        require(r'<meta property="og:description"', html, f"{route or '/'}: missing og:description")
        require(re.escape(f'<meta property="og:url" content="{canonical}"'), html, f"{route or '/'}: wrong og:url")
        require(re.escape(f'<link rel="canonical" href="{canonical}"'), html, f"{route or '/'}: wrong canonical")
        require(r'<meta name="twitter:card" content="summary_large_image"', html, f"{route or '/'}: wrong Twitter card")
        require(re.escape(f'{PUBLIC_ORIGIN}/social-preview.png'), html, f"{route or '/'}: social image must be absolute")
        require(r'(?:src|href)="/runcost/(?:assets|favicon)', html, f"{route or '/'}: build did not use Pages base path")

    social = (DIST / "social-preview.png").read_bytes()
    if not social.startswith(b"\x89PNG\r\n\x1a\n"):
        raise AssertionError("social-preview.png is not a PNG")
    width, height = struct.unpack(">II", social[16:24])
    if (width, height) != (1200, 630):
        raise AssertionError(f"social preview must be 1200x630, got {width}x{height}")

    robots = (DIST / "robots.txt").read_text(encoding="utf-8")
    if "Allow: /" not in robots or f"Sitemap: {PUBLIC_ORIGIN}/sitemap.xml" not in robots:
        raise AssertionError("robots.txt must allow crawling and name the sitemap")
    sitemap = (DIST / "sitemap.xml").read_text(encoding="utf-8")
    for route in ROUTES:
        canonical = f"{PUBLIC_ORIGIN}/{route + '/' if route else ''}"
        if f"<loc>{canonical}</loc>" not in sitemap:
            raise AssertionError(f"sitemap missing {canonical}")

    source = "\n".join(path.read_text(encoding="utf-8") for path in sorted((PLAYGROUND / "src").glob("**/*")) if path.is_file())
    for forbidden in ["fetch(", "XMLHttpRequest", "WebSocket("]:
        if forbidden in source:
            raise AssertionError(f"playground must not send pasted responses over the network: found {forbidden}")
    for required in ["fromResponseAuto", "playground-offline-example", "External source (live or cached)"]:
        if required not in source:
            raise AssertionError(f"playground external price resolution is missing {required!r}")
    for forbidden in ["core/data/providers", "Bundled source catalog", "useDefaultCatalog"]:
        if forbidden in source:
            raise AssertionError(f"playground still depends on removed bundled pricing behavior: {forbidden}")

    javascript_bytes = sum(path.stat().st_size for path in (DIST / "assets").glob("*.js"))
    css_bytes = sum(path.stat().st_size for path in (DIST / "assets").glob("*.css"))
    if javascript_bytes > 750_000 or css_bytes > 150_000:
        raise AssertionError(f"playground payload budget exceeded: JS={javascript_bytes}, CSS={css_bytes}")

    print(
        f"playground site passed ({len(ROUTES)} pages, 1200x630 social card, "
        f"JS={javascript_bytes} bytes, CSS={css_bytes} bytes)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
