"""Build site/dashboard/index.html (5 tabs, self-contained) with dash_kit.
Every chart card carries a PUBLIC DATA / SIMULATED tag. Run from the repository root:  python src/build_dashboard.py
"""
from __future__ import annotations

import json

import pandas as pd

from common import OUT, PUBLIC, TITLE, key_numbers
from dash_kit import build


def rec(name: str) -> list[dict]:
    return json.loads(pd.read_csv(OUT / f"{name}.csv").to_json(orient="records"))


K = key_numbers()
PUB, SIMT = '<span class="tag pub">PUBLIC DATA</span>', '<span class="tag sim">SIMULATED</span>'


def card(title: str, tag: str, plot_id: str, note: str) -> str:
    return f'<div class="card"><h2>{title} {tag}</h2><div id="{plot_id}" class="plot"></div><p>{note}</p></div>'


def table(df: pd.DataFrame) -> str:
    head = "".join(f"<th>{c}</th>" for c in df.columns)
    rows = "".join("<tr>" + "".join(f"<td>{v}</td>" for v in r) + "</tr>" for r in df.astype(str).values)
    return f'<div class="scroll"><table><tr>{head}</tr>{rows}</table></div>'


alerts = pd.read_csv(OUT / "alerts.csv")[["week", "customer_id", "status", "moved"]]
facts = json.loads((PUBLIC / "sources_facts.json").read_text(encoding="utf-8"))
rules = pd.read_csv(OUT / "rba_rules.csv").query("period == 'test'")[["rule", "precision", "recall", "alerts_per_day", "false_alerts_per_ato"]]
models = pd.read_csv(OUT / "webrobots_models.csv")
e2 = pd.read_csv(OUT / "e2_summary.csv").iloc[0]
lab = pd.read_csv(OUT / "lab_scores.csv")[["visitor", "kind", "NUMBER_OF_REQUESTS", "AVERAGE_TIME", "IMAGES", "robot_score"]]
sig = pd.read_csv(OUT / "signal_offline.csv")[["signal", "alerts_per_day", "precision", "recall", "baseline_alerts_per_day"]]

kpis = "".join(f'<div class="card"><h2>{t} {tag}</h2><div class="big">{v}</div><p>{p}</p></div>' for t, tag, v, p in [
    ("Accounts taken over", SIMT, K["e2_accounts"], f"customer C03, ticket T07; {K['e2_validated']} had their credentials validated"),
    ("AUC with signal S1", SIMT, K["auc_s1"], f"against {K['auc_existing']} with existing signals (test period); {K['auc_leaky']} with leakage"),
    ("RBA takeovers in the top 1,000", PUB, K["rba_topk"], "of 2,950,315 successful logins, Sep-Nov 2020, ranked by a train-learned score"),
    ("False alerts in 12 weeks", SIMT, K["false_alerts"], "12 customers; the pre-sale of C01 is classified as explained")])

tabs = [
    ("Overview", f'<div class="kpis">{kpis}</div><div class="grid">'
     + card("Traffic by class, all customers (as labelled by the platform)", SIMT, "p_mix", "Bad-bot share grows about +1.6 % a week (calibrated on +124 % a year as stated by DataDome). Fake Googlebot traffic sits inside 'verified_bot' until the IP check (signal S3).")
     + f'<div class="card"><h2>Flagged customer-weeks and triage {SIMT}</h2>{table(alerts)}<p>Robust z-score against each customer\'s previous 6 weeks; only risky directions count. The pre-sale (C01, 19-22 Nov) is <b>explained by the customer\'s campaign</b>: no alert (test F1).</p></div></div>'),
    ("Fraud patterns", '<div class="grid">'
     + card("E1 credential stuffing on C03: device cluster vs other logins", SIMT, "p_e1", f"{K['e1_ips']}, at most 1 attempt per IP and per hour (the per-IP rule fires above 5), only 25 device hashes.")
     + card("E2 accounts with a success from the cluster, and taken over", SIMT, "p_e2", f"{K['e2_accounts']} changed the e-mail within 1 h; days with fewer than 5 accounts are not shown.")
     + card("E3 fake trial sign-ups on C05", SIMT, "p_e3", f"{K['e3_signups']}, 91 % disposable e-mail, 95 % prepaid cards, 0 % conversion.")
     + card("E4 Googlebot claims on C08: verified vs not verified", SIMT, "p_e4", f"{K['e4_requests']} from hosting IPs outside Google's published ranges, allowed by a user-agent allow-list.")
     + "</div>"),
    ("Customer case T07", '<div class="grid">'
     + card("C03 login attempts per day and successes from the cluster", SIMT, "p_t07", "Ticket T07 arrived on 20 Oct; the weekly monitoring had flagged C03 on 12 Oct but no customer alert followed.")
     + f'<div class="card"><h2>Affected accounts (counts only) {SIMT}</h2><div class="big">{int(e2.accounts_with_success_from_cluster):,}</div><p>accounts with a successful login from the 25 devices (credentials exposed): password reset.</p><div class="big">{int(e2.accounts_taken_over)}</div><p>taken over (e-mail changed within 1 h): restore e-mail, notify the owner. {int(e2.reported_before_ticket)} had been reported before the ticket.</p></div>'
     + f'<div class="card"><h2>What the detection saw and missed {SIMT}</h2><ul><li>Missed: 86 % of the cluster\'s attempts were recommended "allow" (clean residential IPs, under the per-IP limit).</li><li>Missed: every takeover login was recommended "allow"; the e-mail change that followed was not a signal.</li><li>Seen: failure rate +46 %, devices per login -83 % in the weekly monitoring.</li><li>Fix: signals S1 (device cluster) and S2 (success then credential change within 1 h).</li></ul><p>Full report: <a href="../cases/T07.html">case report T07</a>.</p></div>'
     + "</div>"),
    ("Detection quality", '<div class="grid">'
     + card("E6 challenge pass rate on C04 before and after rule R12", SIMT, "p_e6", f"Total {K['simpson']}, yet lower on the web AND in the app: the mix moved to the app. R12 did not make the experience better.")
     + card("E7 account-takeover models: AUC", SIMT, "p_e7", "A uses the account table extracted on 23 Nov (locked after the report): unusable at login time. B and C use signals known at login time, learned on 31 Aug-11 Oct, scored on 12 Oct-22 Nov.")
     + card("E5 C07 deny rate: raw events vs deduplicated", SIMT, "p_e5", "SDK 4.2 (12 Oct) sends 23 % of its events twice and leaves 38 % of device hashes empty: the raw deny rate falls, the clean one does not (ticket T08).")
     + f'<div class="card"><h2>Simple takeover rules on the RBA data, test Sep-Nov 2020 {PUB}</h2>{table(rules)}<p>Thresholds learned on Feb-Aug 2020. The best rule still raises {K["rba_best_rule"]}.</p></div>'
     + f'<div class="card"><h2>Proposed signals, offline {SIMT}</h2>{table(sig)}<p>S1 cuts alerts per day from 2,256 to 129 at the same recall; S2 is known 1 h after the login (an alert, not a login decision).</p></div>'
     + "</div>"),
    ("Public data", '<div class="grid">'
     + card("DataDome report 2026 (as stated by DataDome, read 26 Nov 2026)", PUB, "p_dd", "Source: datadome.co State of Bot & Agent Security Report 2026 web page. Quoted, not recomputed.")
     + card("RBA login dataset: logins and takeover labels per month", PUB, "p_rba", f"{K['rba_logins']} synthesized logins (Feb 2020-Feb 2021), DOI 10.5281/zenodo.6782156, CC BY 4.0. Values are artificial: not for production. No takeover label after Nov 2020.")
     + card("Web robot sessions: AUC of each feature alone (top 10)", PUB, "p_wr", f"67,352 sessions, March 2018 (not current traffic), DOI 10.5281/zenodo.3477932. Gradient boosting on all features: AUC {K['robots_auc']} (5-fold).")
     + f'<div class="card"><h2>Models on the web robot sessions {PUB}</h2>{table(models)}<p>Label "as labelled by the dataset"; no timestamps, so cross-validation rather than a time split.</p></div>'
     + f'<div class="card"><h2>Local robot lab (127.0.0.1 only) scored by the public-data model {PUB}</h2>{table(lab)}<p>The login burst scores only 0.55: a model trained on browsing sessions does not know login attacks; login signals are needed.</p></div>'
     + f'<div class="card"><h2>Reference lists (read 26 Nov 2026)</h2>{table(pd.DataFrame([facts["reference_lists"]]).drop(columns=["list_dates", "read_on"]))}<p>Used only on simulated traffic; no IP or prefix is published.</p></div>'
     + "</div>"),
]

data = {"mix": rec("traffic_weekly"), "e1": rec("e1_daily"), "e2": rec("e2_timeline"), "e3": rec("e3_weekly"),
        "e4": rec("e4_daily"), "e6": rec("e6_simpson"), "e7": rec("e7_auc"), "e5": rec("e5_dedup_effect"),
        "rba": rec("rba_monthly"), "wr": rec("webrobots_feature_auc")[:10]}
js = """
const cls = ['human','verified_bot','ai_agent','bad_bot'], col = {human:C.grey, verified_bot:C.a, ai_agent:C.vio, bad_bot:C.bad};
P('p_mix', cls.map(c => ({type:'scatter', mode:'lines', stackgroup:'a', name:c, line:{color:col[c]},
  x:D.mix.filter(r=>r.traffic_class===c).map(r=>r.week), y:D.mix.filter(r=>r.traffic_class===c).map(r=>r.requests)})), {yaxis:{title:'requests per week'}});
P('p_e1', [{type:'bar', name:'device cluster', x:D.e1.map(r=>r.day), y:D.e1.map(r=>r.cluster_attempts), marker:{color:C.bad}},
           {type:'bar', name:'other logins', x:D.e1.map(r=>r.day), y:D.e1.map(r=>r.other_attempts), marker:{color:C.grey}}], {barmode:'stack', yaxis:{title:'attempts'}});
P('p_e2', [{type:'bar', name:'success from cluster', x:D.e2.map(r=>r.day), y:D.e2.map(r=>r.accounts_with_success), marker:{color:C.grey}},
           {type:'bar', name:'taken over', x:D.e2.map(r=>r.day), y:D.e2.map(r=>r.taken_over), marker:{color:C.bad}, yaxis:'y2'}],
  {yaxis:{title:'accounts with success'}, yaxis2:{title:'taken over', overlaying:'y', side:'right'}});
P('p_e3', [{type:'bar', name:'from 40 devices', x:D.e3.map(r=>r.week), y:D.e3.map(r=>r.cluster_signups), marker:{color:C.bad}},
           {type:'bar', name:'other sign-ups', x:D.e3.map(r=>r.week), y:D.e3.map(r=>r.other_signups), marker:{color:C.grey}}], {barmode:'stack', yaxis:{title:'sign-ups per week'}});
P('p_e4', [{type:'scatter', mode:'lines', name:'verified (IP in published ranges)', x:D.e4.map(r=>r.day), y:D.e4.map(r=>r.verified_requests), line:{color:C.a}},
           {type:'scatter', mode:'lines', name:'not verified', x:D.e4.map(r=>r.day), y:D.e4.map(r=>r.unverified_requests), line:{color:C.bad}}], {yaxis:{title:'requests per day'}});
P('p_t07', [{type:'bar', name:'cluster attempts', x:D.e1.map(r=>r.day), y:D.e1.map(r=>r.cluster_attempts), marker:{color:C.bad}},
            {type:'scatter', mode:'lines', name:'cluster successes', x:D.e1.map(r=>r.day), y:D.e1.map(r=>r.cluster_successes), yaxis:'y2', line:{color:C.yel}}],
  {yaxis:{title:'attempts'}, yaxis2:{title:'successes', overlaying:'y', side:'right'},
   shapes:[{type:'line', x0:'2026-10-20', x1:'2026-10-20', y0:0, y1:1, yref:'paper', line:{dash:'dot', color:C.a}}],
   annotations:[{x:'2026-10-20', y:1, yref:'paper', text:'ticket T07', showarrow:false, yanchor:'bottom'}]});
const per = ['1 before R12 (5-25 Oct)', '2 after R12 (2-22 Nov)'];
P('p_e6', ['web','app','total'].map((ch,i) => ({type:'bar', name:ch, x:per.map(p=>p.slice(2)),
  y:per.map(p => (D.e6.find(r=>r.period===p && r.channel===ch)||{}).pass_rate), marker:{color:[C.grey, C.a, C.org][i]}})),
  {yaxis:{title:'challenge pass rate', tickformat:'.0%'}});
P('p_e7', [{type:'bar', x:D.e7.map(r=>r.model), y:D.e7.map(r=>r.auc), marker:{color:[C.bad, C.grey, C.ok]}, text:D.e7.map(r=>r.auc), textposition:'outside'}],
  {yaxis:{title:'AUC', range:[0.5,1.05]}, xaxis:{tickfont:{size:10}}});
P('p_e5', [{type:'scatter', mode:'lines+markers', name:'deny rate, raw', x:D.e5.map(r=>r.week), y:D.e5.map(r=>r.deny_rate_raw), line:{color:C.bad}},
           {type:'scatter', mode:'lines+markers', name:'deny rate, deduplicated', x:D.e5.map(r=>r.week), y:D.e5.map(r=>r.deny_rate_clean), line:{color:C.a}},
           {type:'bar', name:'empty device share', x:D.e5.map(r=>r.week), y:D.e5.map(r=>r.empty_device_share), yaxis:'y2', marker:{color:C.grey}, opacity:0.4}],
  {yaxis:{title:'deny rate', tickformat:'.1%'}, yaxis2:{title:'empty device share', overlaying:'y', side:'right', tickformat:'.0%'}});
const dd = [['Bad bot traffic growth (12 months)',124],['Scraping share of bad bot traffic',70.9],['AI traffic growth',82.3],
            ['Sites with no protection (of 20,000+ tested)',65.3],['Sites fully protected',2.4]];
P('p_dd', [{type:'bar', orientation:'h', y:dd.map(d=>d[0]), x:dd.map(d=>d[1]), marker:{color:C.a}, text:dd.map(d=>d[1]+' %'), textposition:'outside'}],
  {margin:{l:260,r:40,t:10,b:40}, xaxis:{title:'%'}});
P('p_rba', [{type:'bar', name:'logins', x:D.rba.map(r=>r.month), y:D.rba.map(r=>r.logins), marker:{color:C.grey}},
            {type:'scatter', mode:'lines+markers', name:'takeover labels', x:D.rba.map(r=>r.month), y:D.rba.map(r=>r.ato_logins), yaxis:'y2', line:{color:C.bad}}],
  {yaxis:{title:'logins'}, yaxis2:{title:'takeover labels', overlaying:'y', side:'right'}});
P('p_wr', [{type:'bar', orientation:'h', y:D.wr.map(r=>r.feature).reverse(), x:D.wr.map(r=>r.auc).reverse(),
  marker:{color:D.wr.map(r=>r.higher_for==='robots'?C.bad:C.a).reverse()}}], {margin:{l:170,r:20,t:10,b:40}, xaxis:{title:'AUC alone (red: higher for robots)', range:[0.5,1]}});
"""
build(TITLE, "Companion to the case study. Real public sources (PUBLIC DATA) and a fictional anti-fraud platform with 12 fictional "
      "customers (SIMULATED), labelled on every view. Not DataDome data.", tabs, data, js)
