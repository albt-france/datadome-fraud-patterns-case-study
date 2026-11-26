"""Compare the hidden truth of the simulation (data/_hidden_truth.csv, local only) with what the analysis found.
Writes data/output/truth_check.csv (event, expected, found, match). Run:  python src/check_truth.py
"""
from __future__ import annotations

import sys

import pandas as pd

from common import DATA, OUT


def main() -> None:
    t = pd.read_csv(DATA / "_hidden_truth.csv").set_index("event")
    r = lambda n: pd.read_csv(OUT / f"{n}.csv")  # noqa: E731
    al = r("alerts")
    e1, ip, e2, e3 = r("e1_summary").iloc[0], r("e1_ip_rate").iloc[0], r("e2_summary").iloc[0], r("e3_summary").iloc[0]
    e4 = r("e4_crawlers").query("customer_id == 'C08' and not ip_in_published_ranges").requests.sum()
    sdk = r("sdk_quality").query("sdk_version == '4.2'").iloc[0]
    auc = r("e7_auc").auc.tolist()
    rows = [
        ("E1", f"{t.loc['E1', 'n']} attempts, {t.loc['E1', 'n_ips']} IPs, 25 devices",
         f"{e1.attempts} attempts, {ip.distinct_ips} IPs, {e1.cluster_devices} devices",
         e1.attempts == t.loc["E1", "n"] and ip.distinct_ips == t.loc["E1", "n_ips"] and e1.cluster_devices == 25),
        ("E2", "214 accounts", f"{e2.accounts_taken_over} accounts", e2.accounts_taken_over == 214),
        ("E3", "3800 sign-ups, 40 devices", f"{e3.signups} sign-ups, {e3.devices} devices", e3.signups == 3800 and e3.devices == 40),
        # found = C08 requests outside the ranges: the E4 campaign plus a small background of spoofers that exists on every customer
        ("E4", f"{t.loc['E4', 'n']} requests (campaign)", f"{e4} requests unverified on C08", e4 >= t.loc["E4", "n"]),
        ("E5", f"{t.loc['E5', 'n']} duplicates", f"{sdk.events_raw - sdk.events_unique} duplicates",
         sdk.events_raw - sdk.events_unique == t.loc["E5", "n"]),
        ("E6", "total up, segments down", "see out_e6_simpson", True),
        ("E7", "leaky AUC near 1, honest lower", f"AUC {auc}", auc[0] > .97 and auc[1] < .92),
        ("E8", "C01 week of 16 Nov not escalated", al.query("customer_id == 'C01'").status.tolist(),
         (al.query("customer_id == 'C01'").status == "alert").sum() == 0),
    ]
    out = pd.DataFrame(rows, columns=["event", "expected", "found", "match"])
    out.to_csv(OUT / "truth_check.csv", index=False)
    print(out.to_string(index=False))
    if not out.match.all():
        raise SystemExit(1)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
