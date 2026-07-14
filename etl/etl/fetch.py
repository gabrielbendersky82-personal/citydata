"""Cached HTTP downloads for bulk source files.

Some environments (like the Claude Code sandbox) sit behind an egress policy
that blocks most data hosts. Callers can pass `mirrors` — public mirror URLs
(GitHub raw / S3 open-data) tried after the official URL. The URL actually
used is returned alongside the path so provenance can be recorded.
"""
from __future__ import annotations

import os

import requests

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")

UA = "citydata-etl/0.1 (open-data neighborhood analytics; contact: gabrielbendersky82@gmail.com)"


class AllSourcesBlocked(RuntimeError):
    pass


def _ext_of(url: str) -> str:
    stem = url.split("?")[0].rstrip("/")
    tail = stem.rsplit("/", 1)[-1]
    return "." + tail.rsplit(".", 1)[-1] if "." in tail else ""


def download(
    url: str,
    filename: str,
    mirrors: list[str] | None = None,
    timeout: int = 300,
) -> tuple[str, str]:
    """Download to etl/cache/<filename><ext-of-source-used> unless cached.

    `filename` is a stem; the extension comes from the URL that actually served
    the file (mirrors may use a different format than the official source).
    Returns (path, url_used).
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    candidates = [url, *(mirrors or [])]
    for candidate in candidates:
        p = os.path.join(CACHE_DIR, filename + _ext_of(candidate))
        if os.path.exists(p) and os.path.getsize(p) > 0:
            meta = p + ".src"
            used = open(meta).read().strip() if os.path.exists(meta) else candidate
            return p, used

    errors: list[str] = []
    for candidate in candidates:
        path = os.path.join(CACHE_DIR, filename + _ext_of(candidate))
        meta = path + ".src"
        tmp = path + ".part"
        try:
            with requests.get(
                candidate, stream=True, timeout=timeout, headers={"User-Agent": UA}
            ) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        f.write(chunk)
            os.replace(tmp, path)
            with open(meta, "w") as f:
                f.write(candidate)
            if candidate != url:
                print(f"WARN: fetched from mirror {candidate} (official source unreachable)")
            return path, candidate
        except requests.RequestException as e:
            errors.append(f"{candidate}: {e.__class__.__name__}")
            if os.path.exists(tmp):
                os.remove(tmp)
    raise AllSourcesBlocked(f"all sources failed for {filename}: " + "; ".join(errors))
