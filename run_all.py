"""Run the whole study in order, from the public downloads to the PDF.
    python run_all.py                  # everything (downloads the 1.1 GB RBA zip once; about 15 minutes in total)
    python run_all.py --skip-download  # re-uses data/public/ and the RBA results in data/output/rba_*.csv
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(*cmd: str) -> None:
    t = time.time()
    print(">", " ".join(cmd), flush=True)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    subprocess.run([sys.executable, *cmd], cwd=ROOT, check=True, env=env)
    print(f"  done in {time.time() - t:.0f} s", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-download", action="store_true")
    a = ap.parse_args()
    if not a.skip_download:
        run("src/reference_lists.py")          # small public sources (cached)
        run("src/ingest_webrobots.py")         # web robot sessions (20 MB)
        run("src/ingest_rba.py")               # RBA logins (1.1 GB zip -> Parquet)
        run("src/run_sql.py", "rba")           # sql/01-03 -> data/output/rba_*.csv
    run("src/simulate_platform.py")            # fictional platform, seed 42 (needs the reference lists, cached)
    run("src/run_sql.py")                      # sql/10-15 + 99_tests.sql
    run("lab/robot_lab.py")                    # local robot lab, 127.0.0.1 only (about 1 minute)
    run("src/signals_eval.py")                 # bot signals (scikit-learn) + lab scores
    run("src/key_numbers.py")
    run("src/case_report.py", "--ticket", "T07")
    run("src/build_dashboard.py")
    run("src/build_pdf.py")
    if (ROOT / "data" / "_hidden_truth.csv").exists():
        run("src/check_truth.py")              # only where the hidden truth exists (not in the published repository)


if __name__ == "__main__":
    main()
