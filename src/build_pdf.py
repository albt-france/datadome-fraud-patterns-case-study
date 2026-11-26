"""Build site/report/datadome_fraud_analyst_case_study.pdf: 7 pages (0 to 6), via pdf_kit (Edge headless).
The build fails if a card overflows or if the page count is not 7. Run from the repository root:  python src/build_pdf.py
Title = conclusion; every chart card carries a PUBLIC DATA / SIMULATED / ILLUSTRATIVE tag; numbers come from data/output.
"""
from __future__ import annotations

import json

import matplotlib.pyplot as plt
import pandas as pd

from common import AI, COMPANY, OUT, PUBLIC, TITLE, key_numbers
from pdf_kit import BLUE, GREY, ORANGE, RED, card, col, grid, kpi, page, render, setup_matplotlib, svg

setup_matplotlib()
K = key_numbers()
LABEL = f"{COMPANY} · Fraud Analyst case study"
F = json.loads((PUBLIC / "sources_facts.json").read_text(encoding="utf-8"))


def r(name: str) -> pd.DataFrame:
    return pd.read_csv(OUT / f"{name}.csv")


def fig(w: float = 4.2, h: float = 1.9):
    f, ax = plt.subplots(figsize=(w, h))
    return f, ax


def leg(ax, handles=None, labels=None):
    """Legend above the plot area, so it never covers the data."""
    kw = dict(frameon=False, fontsize=7, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, borderaxespad=0.2)
    return ax.legend(handles, labels, **kw) if handles else ax.legend(**kw)


def dates(ax, s):
    ax.set_xticks(s[:: max(1, len(s) // 4)])
    ax.set_xticklabels([pd.Timestamp(x).strftime("%d %b") for x in s[:: max(1, len(s) // 4)]])


def tbl(head: list[str], rows: list[list]) -> str:
    return ("<table><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows) + "</table>")


# ------------------------------------------------------------------ charts
def ch_dd():
    f, ax = fig(3.3, 2.4)
    items = [("Bad bot traffic growth, 12 months", 124), ("AI traffic growth", 82.3), ("Scraping share of bad bots", 70.9),
             ("Sites tested with no protection", 65.3), ("Sites fully protected", 2.4)]
    ax.barh([i[0] for i in items][::-1], [i[1] for i in items][::-1], color=BLUE)
    for i, v in enumerate([i[1] for i in items][::-1]):
        ax.text(v + 2, i, f"{v} %", va="center", fontsize=7.5)
    ax.set_xlim(0, 150)
    ax.set_xlabel("%")
    return svg(f)


def ch_rba_signals():
    s = r("rba_signal_rates").set_index("is_ato")
    cols = [("new_country", "new country"), ("new_browser", "new browser"), ("new_device_type", "new device type"),
            ("attack_ip", "IP on attack list")]
    f, ax = fig(4.2, 2.0)
    x = range(len(cols))
    ax.bar([i - .2 for i in x], [s.loc[False, c] * 100 for c, _ in cols], .4, color=GREY, label="normal logins")
    ax.bar([i + .2 for i in x], [s.loc[True, c] * 100 for c, _ in cols], .4, color=RED, label="takeovers (140)")
    ax.set_xticks(list(x))
    ax.set_xticklabels([n.replace(" ", chr(10), 1) for _, n in cols])
    ax.set_ylabel("% of successful logins")
    leg(ax)
    return svg(f)


def ch_e1(h=2.0):
    d = r("e1_daily")
    d = d[(d.day >= "2026-09-28") & (d.day <= "2026-10-25")]
    f, ax = fig(4.2, h)
    ax.bar(d.day, d.other_attempts, color=GREY, label="other logins")
    ax.bar(d.day, d.cluster_attempts, bottom=d.other_attempts, color=RED, label="25-device cluster")
    dates(ax, list(d.day))
    ax.set_ylabel("attempts / day")
    leg(ax)
    return svg(f)


def ch_e3():
    d = r("e3_weekly")
    f, ax = fig(4.2, 2.0)
    ax.bar(d.week, d.other_signups, color=GREY, label="other sign-ups")
    ax.bar(d.week, d.cluster_signups, bottom=d.other_signups, color=RED, label="40 devices")
    dates(ax, list(d.week))
    ax.set_ylabel("sign-ups / week")
    leg(ax)
    return svg(f)


def ch_e4():
    d = r("e4_daily").fillna(0)
    f, ax = fig(4.2, 2.0)
    ax.plot(pd.to_datetime(d.day), d.verified_requests / 1e3, color=BLUE, label="IP in Google's ranges")
    ax.plot(pd.to_datetime(d.day), d.unverified_requests / 1e3, color=RED, label="not verified")
    ax.set_ylabel("k requests / day")
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%d %b"))
    leg(ax)
    return svg(f)


def ch_t07():
    d = r("e1_daily")
    d = d[(d.day >= "2026-09-28") & (d.day <= "2026-10-25")]
    f, ax = fig(4.6, 2.3)
    x = pd.to_datetime(d.day)
    ax.bar(x, d.cluster_attempts / 1e3, color=RED, label="cluster attempts (k)")
    ax2 = ax.twinx()
    ax2.plot(x, d.cluster_successes, color=ORANGE, label="cluster successes")
    ax2.spines["right"].set_visible(True)
    ax.set_ylim(0, d.cluster_attempts.max() / 1e3 * 1.3)
    ax2.set_ylim(0, d.cluster_successes.max() * 1.3)
    for day, txt in (("2026-10-12", "weekly alert"), ("2026-10-20", "ticket T07")):
        ax.axvline(pd.Timestamp(day), color=BLUE, ls=":", lw=1)
        ax.text(pd.Timestamp(day), ax.get_ylim()[1] * .9, " " + txt, fontsize=7, color=BLUE)
    ax.set_xticks(pd.to_datetime(["2026-09-28", "2026-10-05", "2026-10-12", "2026-10-19"]))
    ax.set_ylabel("k attempts / day")
    ax2.set_ylabel("successes / day")
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%d %b"))
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    leg(ax, h1 + h2, l1 + l2)
    return svg(f)


def ch_e5():
    d = r("e5_dedup_effect")
    f, ax = fig(4.2, 1.95)
    ax.plot(pd.to_datetime(d.week), d.deny_rate_raw * 100, color=RED, marker="o", ms=3, label="raw events")
    ax.plot(pd.to_datetime(d.week), d.deny_rate_clean * 100, color=BLUE, marker="o", ms=3, label="deduplicated")
    ax.axvline(pd.Timestamp("2026-10-12"), color=GREY, ls=":")
    ax.text(pd.Timestamp("2026-10-12"), 8.6, " SDK 4.2", fontsize=7)
    ax.set_ylim(6.5, 9)
    ax.set_ylabel("deny rate C07, %")
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%d %b"))
    leg(ax)
    return svg(f)


def ch_e6():
    d = r("e6_simpson")
    f, ax = fig(4.2, 1.95)
    per = sorted(d.period.unique())
    for i, (ch, c) in enumerate((("web", GREY), ("app", BLUE), ("total", ORANGE))):
        v = [d[(d.period == p) & (d.channel == ch)].pass_rate.iloc[0] * 100 for p in per]
        bars = ax.bar([j + (i - 1) * .26 for j in range(2)], v, .26, color=c, label=ch)
        for b, val in zip(bars, v):
            ax.text(b.get_x() + b.get_width() / 2, val + 1, f"{val:.0f}", ha="center", fontsize=7)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["before R12 (5-25 Oct)", "after R12 (2-22 Nov)"])
    ax.set_ylim(0, 105)
    ax.set_ylabel("challenge pass rate, %")
    leg(ax)
    return svg(f)


def ch_e7():
    d = r("e7_auc")
    f, ax = fig(4.2, 1.95)
    lab = ["A leaky snapshot\n(no split)", "B existing signals\n(as of login, test)", "C B + S1 device\ncluster (test)"]
    bars = ax.bar(lab, d.auc, color=[RED, GREY, BLUE])
    for b, v in zip(bars, d.auc):
        ax.text(b.get_x() + b.get_width() / 2, v + .01, f"{v:.3f}", ha="center", fontsize=7.5)
    ax.set_ylim(.5, 1.08)
    ax.set_ylabel("AUC")
    return svg(f)


def ch_wr():
    d = r("webrobots_feature_auc").head(8)[::-1]
    f, ax = fig(4.2, 1.8)
    ax.barh(d.feature.str.replace("_", " ").str.lower(), d.auc, color=[RED if h == "robots" else BLUE for h in d.higher_for])
    ax.set_xlim(.5, 1)
    ax.set_xlabel("AUC of the feature alone (red: higher for robots)")
    return svg(f)


# ------------------------------------------------------------------ numbers used in the text
cal = r("rba_calibration").iloc[0]
e1, ip, e2, e3 = r("e1_summary").iloc[0], r("e1_ip_rate").iloc[0], r("e2_summary").iloc[0], r("e3_summary").iloc[0]
sig = r("signal_offline").set_index(r("signal_offline").signal.str[:2])
sirene, job = F["sirene"], F["job"]

pages = []
# ---------------------------------------------------------------- page 0
pages.append(page(0, f"Overview · {COMPANY} · Fraud Analyst case study",
    "A device cluster and a post-login check catch what per-IP rules miss, if alerts are read at the analyst's budget",
    f"Real public data ({K['rba_logins']} RBA logins, 67,352 labelled web sessions, DataDome's published facts) plus a "
    "SIMULATED anti-fraud platform with 12 fictional customers and 8 hidden events. Nothing here is DataDome data.",
    '<div class="kpis">'
    + kpi(K["e2_accounts"], f"taken over in the customer case T07; {K['e2_validated']} had their credentials validated", "sim")
    + kpi(K["auc_s1"], f"AUC of the takeover model with the new device-cluster signal, against {K['auc_existing']} without it", "sim")
    + kpi(K["rba_topk"], "in the top 1,000 of 2,950,315 synthesized logins (RBA, Sep-Nov 2020) ranked by a train-learned score", "pub")
    + kpi(K["false_alerts"], "in 12 weeks x 12 customers: the C01 pre-sale is explained by its campaign, not escalated", "sim")
    + "</div>"
    + grid("1fr 1.3fr 1fr",
           card("Five questions", "<ol><li>Which fraud patterns show up across customers, and what ties their events together? (M1)</li>"
                "<li>A customer writes \"accounts are being stolen\": how do we go from the ticket to a clear report? (M3)</li>"
                "<li>How do we keep detection-quality numbers honest: data bugs, mix effects, campaigns? (M2)</li>"
                "<li>Which new signals would have caught what was missed, measured offline? (M4)</li>"
                "<li>What do Solution Engineers need to set the customer's expectations? (M5)</li></ol>"),
           card("Five recommendations", "<ol>"
                f"<li><b>Ship S1 device cluster</b> in monitor mode: alerts per day 2,256 to 129 at the same recall (SIMULATED).</li>"
                "<li><b>Add S2</b> \"success then credential change within 1 h\" as a customer alert: recall 99.1 %.</li>"
                "<li><b>Verify crawler claims by published IP ranges</b> instead of the user-agent (S3): "
                f"{K['e4_requests']} let through on one customer.</li>"
                "<li><b>Triage before alerting</b>: data-quality check, declared campaigns, rule changes, then alert.</li>"
                f"<li><b>Report precision at the alert budget</b>, not AUC: the best simple RBA rule gives {K['rba_best_rule']}.</li></ol>"),
           card("Method in three lines",
                "<p>1. Profile the public data (DuckDB SQL): takeover signals known at login time, rules tuned on Feb-Aug 2020 and "
                "tested on Sep-Nov 2020; behavioural bot signals with scikit-learn.</p>"
                "<p>2. Simulate 12 weeks of a fictional platform (seed 42) with 8 hidden events; find each one with a rule and a test "
                f"({K['tests']} pass).</p>"
                "<p>3. Write what a Fraud Analyst delivers: a customer report, a pattern library, signal proposals, KQL / ES|QL queries.</p>")),
    LABEL))
# ---------------------------------------------------------------- page 1
pages.append(page(1, f"1 · {COMPANY} and the job",
    "The role sits in Threat Research: turn customer traffic into fraud patterns, reports and better detection signals",
    f"Facts as stated by {COMPANY} (web pages read on 26 Nov 2026) and the posting (first published 13 Oct 2026). French register data from SIRENE.",
    grid("1fr 1.05fr 1.25fr",
         col(card(f"{COMPANY} in published facts",
                  "<ul><li>Posting: 5 trillion signals a day, 20,000+ attacks stopped per second, 30+ points of presence, 80+ integrations.</li>"
                  "<li>Account Protect documentation: the API returns a <b>recommendation</b> (allow or deny) on a login or a sign-up; "
                  "the customer's application keeps the final decision.</li>"
                  "<li>The ATO page lists login velocity, device fingerprinting, IP reputation and post-login changes as signals.</li>"
                  f"<li>SIRENE: {sirene['name']}, SIREN {sirene['siren'][:3]} {sirene['siren'][3:6]} {sirene['siren'][6:]}, created 2015, Paris, "
                  "100-199 employees band; 2024 French-entity revenue EUR 14.0 M, net result EUR -10.5 M.</li></ul>", "pub"),
             card("The posting", "<ul><li>Fraud Analyst, Threat Research team, France - Remote; first published 13 Oct 2026 on "
                  f"the company's own job board ({F['open_jobs']} open jobs there on 26 Nov 2026).</li>"
                  "<li>Fraud named: account takeover and fake subscriptions.</li>"
                  "<li>Asks for Python and SQL, automation with scripts and AI, experience in web threats or fraud; "
                  "a plus: coding bots, Kibana and Elasticsearch, technical support.</li></ul>")),
         card("Report 2026, as stated by DataDome (Jul 2025 - Jun 2026)", ch_dd(), "pub",
              "Also stated: fake account creation +34.5 %; credential stuffing \"cyclical rather than declining\"; "
              "AI bot requests to login pages up more than 8x in H1 2026. Quoted from the report web page, not recomputed."),
         card("What the job asks, and where this study answers it", tbl(["Mission in the posting", "In this study"], [
             ["M1 Know the fraud patterns seen in customer traffic (ATO, fake subscriptions)", "Page 2 · pattern library (5 cards)"],
             ["M2 Improve detection quality over time", "Page 4 · monitoring, data checks, Simpson, leakage"],
             ["M3 Handle customer requests: fraud case analysis and reports", "Page 3 · ticket T07 report generated by script"],
             ["M4 Power user: interface changes, new detection signals", "Page 5 · signals S1-S3, two interface mock-ups"],
             ["M5 Work with Solution Engineers on performance expectations", "Pages 4-5 · runbook, precision at the alert budget"],
             ["Python, SQL, scripts; Kibana / Elasticsearch; coding bots", "DuckDB SQL, scikit-learn, KQL / ES|QL spec, local robot lab"]]),
              "", "The posting's processes include a technical test with a presentation: pages 3 and 5 are built to be presented in 5 minutes.")),
    LABEL))
# ---------------------------------------------------------------- page 2
pages.append(page(2, "2 · Fraud patterns across customers (M1)",
    "Takeovers look like normal logins one by one; what gives them away is what links them: a new country, a device, a cluster",
    f"PUBLIC DATA: RBA logins, synthesized from real SSO logins (Feb 2020 - Feb 2021, values artificial). SIMULATED: events E1-E4 on fictional customers.",
    grid("1fr 1fr 1fr",
         col(card("Takeovers in the RBA data carry rare signals", ch_rba_signals(), "pub",
                  f"141 takeover logins in {K['rba_logins']}. A new country for the user is seen in 47.9 % of takeovers and 0.5 % of normal logins."),
             card("What ties the events together", "<ul>"
                  f"<li><b>Credential stuffing</b> (E1): {K['e1_ips']}, never more than 1 attempt per IP-hour, but 25 devices.</li>"
                  f"<li><b>Takeover</b> (E2): {K['e2_accounts']} logged in from the cluster then changed the e-mail within 1 h.</li>"
                  "<li><b>Fake sign-ups</b> (E3): 40 devices, disposable e-mail, prepaid cards, 0 % conversion.</li>"
                  "<li><b>Fake crawler</b> (E4): Googlebot user-agent, hosting IPs outside Google's ranges.</li></ul>")),
         col(card("E1 low-and-slow credential stuffing on C03", ch_e1(), "sim",
                  f"400,278 attempts, 97.4 % failed; 86 % recommended allow: the per-IP rule (more than 5 an hour) never fired."),
             card("E3 fake trial sign-ups on C05 (fake subscriptions)", ch_e3(), "sim",
                  f"{K['e3_signups']}; usernames almost sequential (entropy 1.6 against 3.3).")),
         col(card("E4 fake Googlebot on C08", ch_e4(), "sim",
                  f"{K['e4_requests']} not verified, allowed by a user-agent allow-list. Real crawlers stay inside the published ranges."),
             card("Pattern library (docs/fraud_pattern_library.md)",
                  "<p>One card per pattern: how to recognise it, signals known at login time, the query, the false-positive risk "
                  "(shared devices, travellers, privacy relays, stale range lists) and the response. Scraping, the largest category "
                  "as stated by DataDome (70.9 % of bad bot traffic), is covered with the web robot sessions on page 5.</p>"))),
    LABEL))
# ---------------------------------------------------------------- page 3
pages.append(page(3, "3 · A customer fraud case, end to end (M3)",
    f"Ticket T07: {K['e2_accounts']} taken over, {K['e2_validated']} exposed, and the per-IP limit could not have stopped it",
    "SIMULATED customer C03 (streaming). The report is drafted by src/case_report.py from the SQL results; the analyst reviews it before sending.",
    grid("1.25fr 1fr 1fr",
         col(card("C03 logins from the cluster, and what the team knew when", ch_t07(), "sim",
                  "The weekly monitoring flagged C03 on 12 Oct (failure rate +46 %, devices per login -83 %), but no rule turned it "
                  "into a customer alert: the ticket came from end users 8 days later."),
             card("From ticket to report", tbl(["Step", "What was done"], [
                 ["Ticket, 20 Oct", "\"Unknown e-mail changes on accounts. Are we under attack?\" Priority high."],
                 ["Qualify", "Window, flow (login), changes on the customer side (none), our recommendations vs their actions."],
                 ["Analyse", "Failure rate up, then device hashes across IPs: 25 devices, 9,400 IPs, Chrome 109."],
                 ["Report, 21 Oct", "5-line summary, timeline, counts, seen / missed, actions, uncertainty."]]))),
         col(card("Affected accounts (counts only, never lists)", tbl(["Group", "Accounts"], [
                 ["Success from the cluster (credentials known)", f"{int(e2.accounts_with_success_from_cluster):,}"],
                 ["... e-mail changed within 1 h (taken over)", f"{int(e2.accounts_taken_over)}"],
                 ["... reported as fraud before the ticket", f"{int(e2.reported_before_ticket)}"],
                 ["... reported by the 23 Nov extract", f"{int(e2.taken_over_and_reported)}"]]), "sim",
                  "Reports arrive 7 to 30 days after a takeover: counting only reports would have shown 27 accounts on 20 Oct."),
             card("What the detection saw and missed", "<ul>"
                  "<li><b>Missed</b>: 86 % of the attempts and every takeover login were recommended \"allow\".</li>"
                  "<li><b>Missed</b>: the e-mail change right after a login from a new device.</li>"
                  "<li><b>Seen</b>: the weekly KPI deviation, the device cluster in the analysis.</li></ul>")),
         col(card("Recommended actions", tbl(["Owner", "Action"], [
                 ["Customer, now", f"Reset passwords on the {K['e2_validated']}; restore the e-mail of the 214, notify owners."],
                 ["Customer, this week", "Confirm e-mail or password changes with the old address or a second factor."],
                 ["Threat Research", "S1 device cluster (monitor, then deny) and S2 post-login alert."],
                 ["Solution Engineer", "Explain why a per-IP limit cannot stop a low-and-slow campaign."]])),
             card("What remains uncertain", "<ul><li>Whether the other validated accounts will be used later: treat them as exposed.</li>"
                  "<li>Where the leaked credentials come from: the data cannot tell.</li>"
                  "<li>Late reports: the count of reported takeovers can still grow.</li></ul>"))),
    LABEL))
# ---------------------------------------------------------------- page 4
alerts = r("alerts")
arow = [[a.week[5:], a.customer_id, a.status.replace("explained by the customer's campaign", "explained (campaign)")
         .replace(" (review its effect)", ""), a.moved.split(",")[0] if isinstance(a.moved, str) else ""] for a in alerts.itertuples()]
pages.append(page(4, "4 · Keeping detection quality honest (M2, M5)",
    "Three numbers would have misled the customer: a falling deny rate, a rising pass rate and a login spike; none was what it seemed",
    "SIMULATED: weekly KPIs per customer against their own last 6 weeks (robust z-score), then triage before any alert.",
    grid("1.05fr 1fr 1fr",
         col(card("Flagged customer-weeks after triage", tbl(["Week", "Cust.", "Status", "Main move"], arow), "sim",
                  f"Order of triage: data quality, declared campaign, recent rule change, then alert. Result: {K['false_alerts']} "
                  "outside the 8 events; the C01 pre-sale (logins +98 % for the week) is not escalated (test F1).")),
         col(card("E5 C07 deny rate: a data bug, not weaker protection", ch_e5(), "sim",
                  "SDK 4.2 sends 23 % of its events twice and leaves 38 % of device hashes empty. Deduplicate by event_id first."),
             card("E6 rule R12 on C04: Simpson's paradox", ch_e6(), "sim",
                  f"Total pass rate {K['simpson']}, but lower on the web and in the app: challenges moved to the app, where users pass more. "
                  "Answer to ticket T12: R12 did not improve the experience.")),
         col(card("What Solution Engineers get", "<ul>"
                  "<li>The KPI per customer with its baseline and the reason for any move (data, campaign, rule, attack).</li>"
                  "<li>Precision and alerts per day at the agreed threshold, not an AUC.</li>"
                  "<li>The report delay: takeovers are reported 7 to 30 days later, so the last 4 weeks are incomplete.</li>"
                  "<li>The data checks owed by the customer: SDK version, duplicates, empty device hashes.</li></ul>"),
             card("Checks that run with every refresh", "<ul>"
                  f"<li>{K['tests']} in sql/99_tests.sql: keys, consistency between traffic and events, privacy (no IP, no group under "
                  "5 accounts), each event found (E1-E8) and the false signal not escalated (F1).</li>"
                  "<li>Data issues are logged with evidence and a decision (docs/data_issues_log.md, 15 entries).</li></ul>"))),
    LABEL))
# ---------------------------------------------------------------- page 5
s = r("signal_offline")
pages.append(page(5, "5 · New detection signals (M4)",
    f"A device-cluster signal lifts the honest takeover model from {K['auc_existing']} to {K['auc_s1']} and cuts alerts per day by 94 %",
    "SIMULATED offline tests (weights learned on 31 Aug - 11 Oct, scored on 12 Oct - 22 Nov) and PUBLIC DATA behavioural signals.",
    grid("1.1fr 1fr 1fr",
         col(card("Three proposed signals, measured offline", tbl(["Signal", "Alerts / day", "Precision", "Recall"], [
                 ["S1 device cluster on many IPs (with existing signals)", "129 (was 2,256)", "2.03 % (was 0.12 %)", "97.3 %"],
                 ["S2 success then credential change within 1 h", "42", "6.3 %", "99.1 %"],
                 ["S3 crawler claim not verified by published ranges", "54 sessions", "-", "-"]]), "sim",
                  "S1 AND S2 together: 214 alerts, all of them takeovers. S1 precision looks low because the 9,716 other accounts with a "
                  "success from the cluster are real exposures without a report yet."),
             card("Two interface ideas", "<ul><li><b>Cluster view</b>: device hash, IPs, accounts, failures, first seen, one-click "
                  "challenge and export of counts for the customer report.</li><li><b>Filter \"crawler claims not verified\"</b>: shows "
                  "customers whose allow-list trusts the user-agent alone.</li></ul>", "ill",
                  "Mock-ups in docs/detection_signal_proposals.md.")),
         col(card("E7 the leakage trap: an AUC near 1 that could never run live", ch_e7(), "sim",
                  f"Model A uses the account table extracted on 23 Nov, where taken-over accounts are already locked: AUC {K['auc_leaky']}. "
                  "B and C use only what is known at login time, with a time split.")),
         col(card("Behavioural bot signals on public web sessions", ch_wr(), "pub",
                  f"67,352 sessions, March 2018 (not current traffic), robots \"as labelled by the dataset\". Gradient boosting on 35 "
                  f"features: AUC {K['robots_auc']} (5-fold, spread 0.001)."),
             card("Local robot lab (127.0.0.1 only), generated traffic", tbl(["Visitor", "Robot score"], [
                 [v.visitor, f"{v.robot_score:.2f}"] for v in r("lab_scores").itertuples()]), "sim",
                  "Scored by a model trained on the public sessions. The login burst gets only 0.55: login attacks need login signals."))),
    LABEL))
# ---------------------------------------------------------------- page 6
pages.append(page(6, "6 · Methods, limits and AI note",
    "Every number is reproducible from public sources or from a seeded simulation, and every simulated item is labelled as such",
    "Sources read on 26 Nov 2026. Repository: DuckDB SQL, Python, one notebook, business documents, dashboard, local robot lab.",
    grid("1.2fr 1fr 1fr",
         card("Sources and licences", tbl(["Source", "Use · terms"], [
             ["Login Data Set for Risk-Based Authentication, Zenodo", "31.3 M synthesized logins · DOI 10.5281/zenodo.6782156 · CC BY 4.0"],
             ["Web robot detection - Server logs, Zenodo", "67,352 sessions, March 2018 · DOI 10.5281/zenodo.3477932 · CC BY 4.0"],
             ["DataDome report 2026 and ATO page (browser), docs.datadome.co", "quoted as stated · read 26 Nov 2026"],
             ["Greenhouse job API; SIRENE register", "posting facts · public; Licence Ouverte"],
             ["crawler-user-agents; Googlebot, GPTBot, AWS ranges; Tor exit list", "MIT; published lists · used on simulated traffic only"]]), "pub"),
         card("Method", "<ul><li>RBA: IP hashed and user ID replaced at ingestion; signals computed on the past only; thresholds "
              "and weights learned on Feb-Aug 2020, tested on Sep-Nov 2020 (no takeover label after Nov 2020).</li>"
              "<li>Simulation: seed 42, calibrated on RBA rates and on +124 % a year as stated by DataDome; 8 hidden events found "
              "by rules and tests.</li><li>Kibana / Elasticsearch queries are a specification, not run.</li></ul>"
              "<h2 style='margin-top:2mm'>How to re-run (repository root)</h2>"
              "<ol style='font-family: Consolas, monospace; font-size: 7pt;'><li>pip install -r requirements.txt</li>"
              "<li>python run_all.py (1.1 GB download, about 15 min)</li><li>python run_all.py --skip-download</li></ol>"),
         col(card("Limits", "<ul><li>RBA values are synthesized and artificial; 38 test takeovers only.</li>"
                  "<li>The web robot sessions date from March 2018 and have no time order.</li>"
                  "<li>The platform, customers and events are simulated: they show method, not DataDome results.</li>"
                  "<li>No cause is claimed for any real trend; DataDome figures are quoted, not checked.</li></ul>"),
             card("AI note", f"<p>{AI}</p><p>The study calls no language model; automation is done by scripts.</p>"))),
    LABEL))

render(pages, TITLE)
