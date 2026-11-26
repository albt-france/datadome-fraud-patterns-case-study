"""Ingest "Web robot detection - Server logs" (Zenodo, DOI 10.5281/zenodo.3477932, CC BY 4.0).
Sessions from a university library search engine, 1-31 March 2018 (NOT current traffic).
Only the two feature files are read (the 3.2 GB raw JSON log is not needed and is not downloaded).
The ROBOT label is "as labelled by the dataset" (the labelling method is not described in the notice).
Output: data/public/webrobots_sessions.parquet (one row per session, simple + semantic features).
Run:  python src/ingest_webrobots.py
"""
from __future__ import annotations

import io
import sys

import pandas as pd

from common import PUBLIC, polite_get

BASE = "https://zenodo.org/records/3477932/files/"


def main() -> None:
    simple = pd.read_csv(io.BytesIO(polite_get(BASE + "simple_features.csv?download=1")))
    semantic = pd.read_csv(io.BytesIO(polite_get(BASE + "semantic_features.csv?download=1")))
    # both files share the session ID and the ROBOT label: join on ID, keep one label
    df = simple.merge(semantic.drop(columns=["ROBOT"]), on="ID", how="inner")
    df = df.drop(columns=[c for c in df.columns if c.lower().startswith("unnamed")])
    PUBLIC.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PUBLIC / "webrobots_sessions.parquet", index=False)
    print(df.shape, "robots:", int(df["ROBOT"].sum()), f"({df['ROBOT'].mean():.1%})")
    print("columns:", ", ".join(df.columns))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
