"""Compute every key number ONCE from data/output and save it with save_key_numbers() -> data/output/key_numbers.json.
README, PDF and dashboard copy these strings word for word (tools check it).  Run:  python src/key_numbers.py
"""
from __future__ import annotations

import pandas as pd

from common import OUT, save_key_numbers


def r(name: str) -> pd.DataFrame:
    return pd.read_csv(OUT / f"{name}.csv")


def main() -> None:
    cal = r("rba_calibration").iloc[0]
    topk = r("rba_topk").set_index("k")
    rules = r("rba_rules")
    best = rules[(rules.period == "test") & rules.false_alerts_per_ato.notna()].sort_values("false_alerts_per_ato").iloc[0]
    e1 = r("e1_ip_rate").iloc[0]
    e2 = r("e2_summary").iloc[0]
    e3 = r("e3_summary").iloc[0]
    e4 = r("e4_daily").unverified_requests.sum()
    auc = r("e7_auc").set_index(r("e7_auc").model.str[0]).auc
    s6 = r("e6_simpson").set_index(["period", "channel"]).pass_rate
    wr = r("webrobots_models")
    gb = wr[(wr.model == "gradient boosting") & wr.features.str.startswith("all")].iloc[0]
    tests = r("tests")
    save_key_numbers({
        "rba_logins": f"{int(cal.logins):,}",
        "rba_topk": f"{int(topk.loc[1000, 'ato_in_top_k'])} of {int(topk.loc[1000, 'ato_in_test'])} takeovers",
        "rba_best_rule": f"{int(best.false_alerts_per_ato)} false alerts per caught takeover",
        "e1_ips": f"{int(e1.distinct_ips):,} IPs",
        "e2_accounts": f"{int(e2.accounts_taken_over)} accounts",
        "e2_validated": f"{int(e2.accounts_with_success_from_cluster):,} accounts",
        "e3_signups": f"{int(e3.signups):,} sign-ups from {int(e3.devices)} devices",
        "e4_requests": f"{e4 / 1e6:.2f} M requests",
        "auc_leaky": f"{auc['A']:.3f}", "auc_existing": f"{auc['B']:.3f}", "auc_s1": f"{auc['C']:.3f}",
        "simpson": f"{s6[('1 before R12 (5-25 Oct)', 'total')]:.1%} to {s6[('2 after R12 (2-22 Nov)', 'total')]:.1%}",
        "robots_auc": f"{gb.auc_mean:.3f}",
        "false_alerts": f"{int(tests.set_index('test').detail.filter(like='F2').iloc[0].split()[0])} false alerts",
        "tests": f"{int(tests.passed.astype(str).str.lower().eq('true').sum())}/{len(tests)} tests",
    })
    print(open(OUT / "key_numbers.json", encoding="utf-8").read())


if __name__ == "__main__":
    main()
