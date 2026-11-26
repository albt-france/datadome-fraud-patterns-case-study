"""Shared constants and helpers for the DataDome case study.
Every builder (PDF, dashboard, workbook, README check) reads its key numbers from one file,
data/output/key_numbers.json, so the same figure is shown everywhere.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"          # cache of downloaded pages and build files, never pushed
PUBLIC = DATA / "public"    # derived public tables, pushed (re-run without collecting)
SIM = DATA / "sim"          # simulated data, pushed
OUT = DATA / "output"       # SQL results, pushed
SITE = ROOT / "site"

COMPANY = "DataDome"
TITLE = "DataDome: from a customer's fraud ticket to a better detection signal"
REPO = "datadome-fraud-patterns-case-study"
PDF_NAME = "datadome_fraud_analyst_case_study.pdf"
PAGES_URL = f"https://albt-france.github.io/{REPO}"
USER_AGENT = "datadome-case-study/1.0"
FOOT = f"Independent case study based on public data · not affiliated with or endorsed by {COMPANY}"
# keep on ONE line, word for word (rule 0.5; tools/check_release.py looks for this exact sentence)
AI = "AI-assisted workflow: I used Claude, mainly to write scripts faster. I drove the project: I defined the questions, chose and validated the data sources, made the analytical decisions and checked every result."


# ------------------------------------------------------------------ key numbers
def save_key_numbers(numbers: dict[str, str]) -> None:
    """numbers = {"id": "display string"}, e.g. {"median_gap": "33 days"}.
    tools/check_release.py checks that each display string appears in README.md and in the PDF."""
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "key_numbers.json").write_text(json.dumps(numbers, indent=1, ensure_ascii=False), encoding="utf-8")


def key_numbers() -> dict[str, str]:
    return json.loads((OUT / "key_numbers.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ polite collection
_last: dict[str, float] = {}


def polite_get(url: str, *, delay: float = 1.0, headers: dict | None = None, cache: bool = True,
               timeout: int = 60) -> bytes:
    """GET with a neutral User-Agent, a per-host delay and a disk cache in data/raw/http/.
    No retries on 403/429/202: those mean 'blocked', and the study does not insist."""
    import requests  # noqa: PLC0415
    from urllib.parse import urlparse  # noqa: PLC0415

    key = hashlib.sha1((url + json.dumps(headers or {}, sort_keys=True)).encode()).hexdigest()[:16]
    path = RAW / "http" / key
    if cache and path.exists():
        return path.read_bytes()
    host = urlparse(url).netloc
    wait = delay - (time.time() - _last.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    h = {"User-Agent": USER_AGENT, **(headers or {})}
    r = requests.get(url, headers=h, timeout=timeout)
    _last[host] = time.time()
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code} for {url} (blocked or missing: use the fallback, do not insist)")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(r.content)
    return r.content
