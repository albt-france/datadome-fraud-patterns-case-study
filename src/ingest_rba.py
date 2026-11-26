"""Ingest the "Login Data Set for Risk-Based Authentication" (Zenodo, DOI 10.5281/zenodo.6782156, CC BY 4.0).

Steps (each one is skipped if its output already exists):
  1. download rba-dataset.zip (1.09 GB) once into data/raw/, resuming with HTTP Range if interrupted;
  2. extract rba-dataset.csv (9.05 GB) into data/raw/ (only if >= 15 GB are free);
  3. convert it with DuckDB to data/raw/rba.parquet, keeping only useful columns and removing identifiers:
       - the IP address becomes ip_hash (salted SHA-256, 12 hex characters); the salt stays in .env, never pushed;
       - the original User ID becomes a dense key U0000001, U0000002, ...;
  4. delete the CSV.
The dataset is SYNTHESIZED from real logins: values are artificial and must not be used in production.
Run from the repository root:  python src/ingest_rba.py
"""
from __future__ import annotations

import secrets
import shutil
import sys
import time
import zipfile

import duckdb
import requests

from common import RAW, ROOT, USER_AGENT

URL = "https://zenodo.org/records/6782156/files/rba-dataset.zip?download=1"
ZIP = RAW / "rba-dataset.zip"
CSV = RAW / "rba-dataset.csv"
PARQUET = RAW / "rba.parquet"
EXPECTED = 1_093_700_330  # bytes, from the Zenodo record


def salt() -> str:
    """Read RBA_SALT from .env, or create it once (random, local only)."""
    env = ROOT / ".env"
    lines = env.read_text(encoding="utf-8").splitlines() if env.exists() else []
    for ln in lines:
        if ln.startswith("RBA_SALT="):
            return ln.split("=", 1)[1].strip()
    value = secrets.token_hex(16)
    env.write_text("\n".join(lines + [f"RBA_SALT={value}"]) + "\n", encoding="utf-8")
    return value


def download() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    have = ZIP.stat().st_size if ZIP.exists() else 0
    if have == EXPECTED:
        return
    headers = {"User-Agent": USER_AGENT}
    if have:
        headers["Range"] = f"bytes={have}-"  # resume where we stopped
    with requests.get(URL, headers=headers, stream=True, timeout=120) as r:
        if r.status_code not in (200, 206):
            raise SystemExit(f"download refused: HTTP {r.status_code}")
        mode = "ab" if r.status_code == 206 else "wb"
        t0, done = time.time(), (have if mode == "ab" else 0)
        with open(ZIP, mode) as f:
            for chunk in r.iter_content(chunk_size=8 << 20):
                f.write(chunk)
                done += len(chunk)
                if done % (100 << 20) < (8 << 20):
                    print(f"  {done / 1e9:.2f} GB in {time.time() - t0:.0f} s", flush=True)
    if ZIP.stat().st_size != EXPECTED:
        raise SystemExit(f"incomplete download ({ZIP.stat().st_size} bytes): run again to resume")


def extract() -> None:
    if CSV.exists() or PARQUET.exists():
        return
    free = shutil.disk_usage(RAW).free / 1e9
    if free < 15:
        raise SystemExit(f"only {free:.0f} GB free: use the streaming fallback (not needed on this machine)")
    with zipfile.ZipFile(ZIP) as z:
        z.extract("rba-dataset.csv", RAW)


def convert() -> None:
    if PARQUET.exists():
        return
    con = duckdb.connect()
    con.execute("SET preserve_insertion_order = false")
    s = salt()
    # 1) read the CSV once into a typed table (booleans are the text 'True'/'False')
    con.execute(f"""
        CREATE TABLE raw AS
        SELECT "Login Timestamp"::TIMESTAMP              AS ts,
               "User ID"                                 AS uid,
               "Round-Trip Time [ms]"                    AS rtt_ms,
               left(sha256('{s}' || "IP Address"), 12)   AS ip_hash,
               "Country"                                 AS country,
               "ASN"                                     AS asn,
               "Browser Name and Version"                AS browser,
               "OS Name and Version"                     AS os,
               "Device Type"                             AS device_type,
               "Login Successful" = 'True'               AS login_success,
               "Is Attack IP" = 'True'                   AS is_attack_ip,
               "Is Account Takeover" = 'True'            AS is_ato
        FROM read_csv('{CSV.as_posix()}', header = true,
             types = {{'User ID': 'BIGINT', 'ASN': 'BIGINT', 'Round-Trip Time [ms]': 'DOUBLE',
                      'Login Successful': 'VARCHAR', 'Is Attack IP': 'VARCHAR', 'Is Account Takeover': 'VARCHAR'}})
    """)
    # 2) dense user key: the original User ID never leaves this step
    con.execute("""CREATE TABLE users AS
                   SELECT uid, 'U' || lpad(CAST(row_number() OVER (ORDER BY uid) AS VARCHAR), 7, '0') AS user_key
                   FROM (SELECT DISTINCT uid FROM raw)""")
    con.execute(f"""COPY (SELECT r.ts, u.user_key, r.rtt_ms, r.ip_hash, r.country, r.asn, r.browser, r.os,
                                 r.device_type, r.login_success, r.is_attack_ip, r.is_ato
                          FROM raw r JOIN users u USING (uid) ORDER BY r.ts)
                    TO '{PARQUET.as_posix()}' (FORMAT parquet, COMPRESSION zstd)""")
    n = con.execute(f"SELECT COUNT(*) FROM '{PARQUET.as_posix()}'").fetchone()[0]
    print(f"rba.parquet: {n:,} rows")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    t = time.time()
    download(); print(f"zip ok ({time.time() - t:.0f} s)", flush=True)
    extract(); print(f"csv ok ({time.time() - t:.0f} s)", flush=True)
    convert(); print(f"parquet ok ({time.time() - t:.0f} s)", flush=True)
    if CSV.exists() and PARQUET.exists():
        CSV.unlink()  # 9 GB: not kept once the Parquet file exists
        print("csv deleted")
