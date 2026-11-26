"""Draft the customer case report for a ticket from the SQL results (SIMULATED customer, fictional).
    python src/case_report.py --ticket T07
writes docs/customer_case_report_T07.md and site/cases/T07.html (same content). Only counts, never account lists.
The analyst reviews and edits the draft before it is sent (this repository never sends anything).
"""
from __future__ import annotations

import argparse
import html
import sys

import pandas as pd

from common import FOOT, OUT, ROOT, SIM, SITE


def r(name: str) -> pd.DataFrame:
    return pd.read_csv(OUT / f"{name}.csv")


def t07() -> list[tuple]:
    tk = pd.read_parquet(SIM / "tickets.parquet").set_index("ticket_id").loc["T07"]
    e1, ip, e2 = r("e1_summary").iloc[0], r("e1_ip_rate").iloc[0], r("e2_summary").iloc[0]
    al = r("alerts")
    first_alert = al[(al.customer_id == "C03") & (al.status == "alert")].week.min()
    d = r("e1_daily")
    peak = d.loc[d.cluster_attempts.idxmax()]
    return [
        ("h1", "Customer case report - ticket T07 (customer C03, streaming) - SIMULATED"),
        ("p", f"Ticket received {tk.date}: \"{tk.text}\" Priority: {tk.priority}. Report drafted on 2026-10-21 from data up to "
              f"2026-10-20; counts updated with the 23 Nov extract."),
        ("h2", "Summary (5 lines)"),
        ("ol", [f"Yes: C03 was the target of a credential stuffing campaign from {e1.first_day} to {e1.last_day} "
                f"({int(e1.attempts):,} login attempts, {e1.failure_rate:.1%} failed).",
                f"The attempts came from {int(ip.distinct_ips):,} residential and mobile IPs, never more than "
                f"{int(ip.max_attempts_per_ip_hour)} per IP and per hour, so the per-IP limit (5 per hour) never triggered.",
                f"They shared only {int(e1.cluster_devices)} device fingerprints and an old browser version ({e1.ua_family}): "
                f"that is how the campaign is recognised.",
                f"{int(e2.accounts_with_success_from_cluster):,} accounts had a successful login from these devices; "
                f"{int(e2.accounts_taken_over)} of them had their e-mail address changed within the hour (account takeover).",
                "Recommended now: reset passwords and restore the e-mail of the affected accounts, step-up checks on "
                "e-mail changes, and the new device-cluster signal (deployed in monitor mode first)."]),
        ("h2", "Timeline"),
        ("table", ["Date", "What happened"], sorted([
            [str(e1.first_day), "First attempts from the device cluster (low and slow per IP)."],
            [str(peak.day), f"Peak day: {int(peak.cluster_attempts):,} attempts, {int(peak.cluster_successes):,} successful logins."],
            [str((pd.Timestamp(first_alert) + pd.Timedelta(days=7)).date()), "Weekly monitoring (run after the week closes) flags C03 (failure rate, logins, devices per login): alert for the week of "
                               f"{first_alert}. Not escalated to the customer at that time (gap: see recommendations)."],
            [str(e1.last_day), "Last attempts."],
            [str(tk.date), f"Ticket T07: end users report e-mail changes ({int(e2.reported_before_ticket)} takeovers already "
                           "reported by then)."],
            ["2026-10-21", "Analysis: device cluster found, affected accounts counted, this report drafted."]])),
        ("h2", "Affected accounts (counts only)"),
        ("table", ["Group", "Accounts"], [
            ["Successful login from the cluster (credentials known to the attacker)", f"{int(e2.accounts_with_success_from_cluster):,}"],
            ["... of which e-mail changed within 1 hour (taken over)", f"{int(e2.accounts_taken_over)}"],
            ["... of which reported as fraud by 23 Nov", f"{int(e2.taken_over_and_reported)}"]]),
        ("h2", "What the detection saw, and what it missed"),
        ("ul", [f"Missed: {ip.share_recommended_allow:.0%} of the cluster's attempts received an 'allow' recommendation. "
                "The IPs were clean residential addresses and each one stayed under the per-IP rate rule.",
                f"Missed: all {int(e2.accounts_taken_over)} takeover logins were recommended 'allow'; the e-mail change that "
                "followed was not a signal.",
                "Seen: the weekly monitoring flagged C03 from the first week (failure rate +46 %, devices per login -83 %), "
                "but no rule turned that into a customer alert.",
                "Seen in the analysis: 25 device fingerprints on 9,400 IPs with 97 % failures is not human behaviour."]),
        ("h2", "Recommended actions"),
        ("table", ["Owner", "Action", "When"], [
            ["Customer", f"Force a password reset on the {int(e2.accounts_with_success_from_cluster):,} accounts; restore the "
                         f"e-mail of the {int(e2.accounts_taken_over)} taken-over accounts and notify their owners.", "Now"],
            ["Customer", "Ask for a confirmation (old e-mail or second factor) before an e-mail or password change.", "This week"],
            ["Threat Research", "Ship signal S1 'device cluster on many IPs' (monitor mode, then deny) and S2 'success then "
                                "credential change within 1 h' (alert).", "2 weeks"],
            ["Solution Engineer", "Review the per-IP limit with the customer: it cannot stop a low-and-slow campaign.", "Next call"]]),
        ("h2", "What remains uncertain"),
        ("ul", ["Whether the attacker used the other validated accounts later (no e-mail change seen yet): treat them as exposed.",
                "Where the leaked credentials come from (C03 or a third-party breach): the data cannot tell.",
                "Fraud reports arrive 7 to 30 days after the takeover: the count of reported takeovers can still grow.",
                "Simulated case: every number comes from the fictional platform of this study."]),
        ("p", FOOT),
    ]


def to_md(blocks: list[tuple]) -> str:
    out = []
    for b in blocks:
        k = b[0]
        if k == "h1":
            out.append(f"# {b[1]}\n")
        elif k == "h2":
            out.append(f"## {b[1]}\n")
        elif k == "p":
            out.append(b[1] + "\n")
        elif k in ("ul", "ol"):
            out.append("\n".join(f"{i + 1}. {x}" if k == "ol" else f"- {x}" for i, x in enumerate(b[1])) + "\n")
        elif k == "table":
            out.append("| " + " | ".join(b[1]) + " |\n|" + "---|" * len(b[1]) + "\n"
                       + "\n".join("| " + " | ".join(row) + " |" for row in b[2]) + "\n")
    return "\n".join(out)


def to_html(blocks: list[tuple]) -> str:
    e = html.escape
    body = []
    for b in blocks:
        k = b[0]
        if k in ("h1", "h2", "p"):
            body.append(f"<{k}>{e(b[1])}</{k}>")
        elif k in ("ul", "ol"):
            body.append(f"<{k}>" + "".join(f"<li>{e(x)}</li>" for x in b[1]) + f"</{k}>")
        elif k == "table":
            body.append("<table><tr>" + "".join(f"<th>{e(x)}</th>" for x in b[1]) + "</tr>"
                        + "".join("<tr>" + "".join(f"<td>{e(x)}</td>" for x in row) + "</tr>" for row in b[2]) + "</table>")
    css = ("body{font-family:'Segoe UI',Arial,sans-serif;max-width:860px;margin:32px auto;padding:0 16px;color:#222;line-height:1.5}"
           "table{border-collapse:collapse;width:100%;font-size:14px}td,th{border-bottom:1px solid #ddd;padding:6px;text-align:left;"
           "vertical-align:top}h1{font-size:24px}h2{font-size:18px;margin-top:28px}")
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, '
            f'initial-scale=1"><title>Case report T07</title><style>{css}</style></head><body>{"".join(body)}</body></html>')


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticket", default="T07")
    a = ap.parse_args()
    if a.ticket != "T07":
        raise SystemExit("only T07 has a report template in this study")
    blocks = t07()
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "customer_case_report_T07.md").write_text(to_md(blocks), encoding="utf-8")
    (SITE / "cases").mkdir(parents=True, exist_ok=True)
    (SITE / "cases" / "T07.html").write_text(to_html(blocks), encoding="utf-8")
    print("written docs/customer_case_report_T07.md and site/cases/T07.html")
