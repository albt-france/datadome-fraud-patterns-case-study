"""Simulate 12 weeks (2026-08-31 to 2026-11-22, UTC) of a FICTIONAL anti-fraud platform with 12 FICTIONAL customer sites.
Nothing here is DataDome data or a DataDome customer. Seed 42: the same files every run.

Logic of the platform (mirrors the public Account Protect documentation): for each login or sign-up the platform sends a
RECOMMENDATION (allow / challenge / deny); the customer's application keeps the final decision (customer_action).

Calibration (docs/assumptions.md): human and attack-IP login success rates come from the RBA dataset
(data/output/rba_calibration.csv); bad-bot share ~20% of sessions (web robot dataset) growing +124%/year "as stated by
DataDome" = 2.24 ** (1/52) - 1 = +1.6% per week.

8 hidden events are written to data/_hidden_truth.csv (local only, removed before publishing):
E1 slow credential stuffing (C03), E2 account takeover (C03), E3 fake trial sign-ups (C05), E4 fake Googlebot (C08),
E5 SDK 4.2 data issue (C07), E6 Simpson effect after rule R12 (C04), E7 leakage trap (account snapshot), E8 pre-sale (C01).
Privacy: IP addresses exist only in memory; files keep a salted hash (ip_hash) and a class (ip_type). Keys are fictional.
Run:  python src/simulate_platform.py
"""
from __future__ import annotations

import hashlib
import ipaddress
import re
import sys

import numpy as np
import pandas as pd

from common import DATA, OUT, SIM
from reference_lists import lists

rng = np.random.default_rng(42)
START, DAYS = pd.Timestamp("2026-08-31"), 84
DAY = pd.date_range(START, periods=DAYS, freq="D")
SNAPSHOT = pd.Timestamp("2026-11-23")          # date of the data extract: later reports are not known yet
CAL = pd.read_csv(OUT / "rba_calibration.csv").iloc[0]
P_HUMAN_OK, P_ATTACK_OK = float(CAL.human_success_rate), float(CAL.attack_success_rate)
WEEKLY_GROWTH = 2.24 ** (1 / 52) - 1            # +124 % per year -> per week
SALT = "sim-" + hashlib.sha256(b"seed42").hexdigest()[:8]

CUSTOMERS = pd.DataFrame({
    "customer_id": [f"C{i:02d}" for i in range(1, 13)],
    "sector": ["e-commerce", "e-commerce", "streaming", "streaming", "software trial", "software trial", "classifieds",
               "classifieds", "e-commerce", "ticketing & travel", "ticketing & travel", "ticketing & travel"],
    "daily_requests": [900e3, 600e3, 700e3, 650e3, 250e3, 200e3, 800e3, 750e3, 400e3, 350e3, 300e3, 250e3]})
LOGIN = {"C01": (4000, .35), "C02": (3000, .30), "C03": (5000, .60), "C04": (4500, .60), "C07": (3500, .50), "C10": (2500, .40)}
SIGNUP = {"C01": 1200, "C03": 900, "C04": 800, "C05": 600, "C06": 500, "C07": 1000}   # human sign-ups per day
TRIAL = {"C03", "C04", "C05", "C06"}                                                   # customers with a free trial
HOUR_P = np.array([2, 1.5, 1, 1, 1, 1.5, 2.5, 4, 5, 5, 5, 5, 5.5, 5.5, 5, 5, 5.5, 6.5, 7.5, 8, 7.5, 6, 4.5, 3])
HOUR_P = HOUR_P / HOUR_P.sum()
WEEKDAY = np.array([1.0, .97, .97, 1.0, 1.05, 1.12, 1.15])
BROWSERS = ["Chrome 131", "Chrome 130", "Safari 18", "Firefox 133", "Edge 131", "Samsung Internet 26"]


def h(values) -> np.ndarray:
    """Salted SHA-256 of an IP (or any id), truncated to 10 hex characters."""
    return np.array([hashlib.sha256((SALT + str(v)).encode()).hexdigest()[:10] for v in values])


def draw_ips(prefixes: list[str], n: int) -> list[str]:
    """Random IPv4 addresses inside real published prefixes (used only to derive a class, never written)."""
    nets = [ipaddress.ip_network(p) for p in prefixes if p and ":" not in p]
    out = []
    for i in rng.integers(0, len(nets), n):
        net = nets[i]
        out.append(str(net.network_address + int(rng.integers(0, net.num_addresses))))
    return out


def in_ranges(ips: list[str], prefixes: list[str]) -> np.ndarray:
    nets = [ipaddress.ip_network(p) for p in prefixes if p and ":" not in p]
    return np.array([any(ipaddress.ip_address(ip) in n for n in nets) for ip in ips])


def timestamps(day_idx: np.ndarray, hourly: bool = True) -> pd.DatetimeIndex:
    hour = rng.choice(24, len(day_idx), p=HOUR_P) if hourly else rng.integers(0, 24, len(day_idx))
    secs = day_idx * 86400 + hour * 3600 + rng.integers(0, 3600, len(day_idx))
    return START + pd.to_timedelta(secs, unit="s")


def daily_counts(base: float, cid: str, kind: str) -> np.ndarray:
    lam = base * WEEKDAY[DAY.dayofweek] * rng.normal(1, .03, DAYS)
    if cid == "C01":   # E8: declared pre-sale 19-22 Nov (+180 % logins, +240 % sign-ups) - real customers, not an attack
        lam = np.where((DAY >= "2026-11-19") & (DAY <= "2026-11-22"), lam * (2.8 if kind == "login" else 3.4), lam)
    if cid == "C10" and kind == "login":   # declared ticket on-sale, one day
        lam = np.where(DAY == "2026-09-18", lam * 1.6, lam)
    return rng.poisson(lam)


# ------------------------------------------------------------------ IP pools (in memory only)
REF = lists()
crawler_rx = re.compile("|".join(REF["crawler_patterns"]), re.I)
N_RES = 400_000
res_ips = [f"res-{i}" for i in range(N_RES)]                 # residential / mobile: synthetic ids, never real IPs
dc_ips = draw_ips(REF["aws"], 600)                           # hosting IPs drawn inside real AWS prefixes
tor_ips = list(rng.choice(REF["tor"], 80, replace=False))    # Tor exit nodes from the public list
dc_in_aws = in_ranges(dc_ips[:50], REF["aws"]).mean()        # sanity check of the drawing (should be 1.0)


def login_rows(cid: str, acc0: int) -> pd.DataFrame:
    """Human logins + background attack logins for one customer."""
    daily, app_share = LOGIN[cid]
    n_acc = daily * 25
    # accounts: each one has a usual device, a usual IP, a browser and a channel preference
    acc_dev = np.arange(n_acc) + acc0
    acc_ip = rng.integers(0, N_RES, n_acc)
    acc_app = rng.random(n_acc) < app_share
    acc_br = rng.choice(BROWSERS, n_acc, p=[.38, .12, .25, .08, .12, .05])
    w = 1 / (np.arange(n_acc) + 10) ** .8
    # humans
    cnt = daily_counts(daily, cid, "login")
    d = np.repeat(np.arange(DAYS), cnt)
    n = len(d)
    a = rng.choice(n_acc, n, p=w / w.sum())
    new_dev = rng.random(n) < .10          # cookie resets, new phones: device ids churn
    roam = rng.random(n) < .15
    app = np.where(rng.random(n) < .9, acc_app[a], ~acc_app[a])
    hum = pd.DataFrame({
        "ts_utc": timestamps(d), "account_key": a + acc0,
        "ip_id": np.where(roam, rng.integers(0, N_RES, n), acc_ip[a]).astype(str),
        "ip_type": np.where(roam & (rng.random(n) < .3), "vpn", np.where(rng.random(n) < .35, "mobile", "residential")),
        "device_id": np.where(new_dev, 9_000_000 + rng.integers(0, 10**6, n), acc_dev[a]),
        "channel": np.where(app, "app", "web"),
        "ua_family": np.where(app, np.where(rng.random(n) < .55, "App iOS", "App Android"), acc_br[a]),
        "new_device": new_dev, "valid": rng.random(n) < P_HUMAN_OK, "actor": "human"})
    # background attacks (~10 % of logins in the RBA data come from attack IPs): hosting, VPN, Tor; few IPs, heavy hitters
    m = int(n * float(CAL.attack_ip_share) / (1 - float(CAL.attack_ip_share)))
    pool = np.array(dc_ips[:300] + [f"vpn-{i}" for i in range(150)] + tor_ips)
    pw = 1 / (np.arange(len(pool)) + 3) ** 1.1
    ip = rng.choice(len(pool), m, p=pw / pw.sum())
    kind = np.where(ip < 300, "datacenter", np.where(ip < 450, "vpn", "tor"))
    att = pd.DataFrame({
        "ts_utc": timestamps(rng.integers(0, DAYS, m), hourly=False),
        "account_key": np.where(rng.random(m) < .6, rng.integers(0, n_acc, m), n_acc + rng.integers(0, n_acc, m)) + acc0,
        "ip_id": pool[ip], "ip_type": kind, "device_id": 8_000_000 + rng.integers(0, 5000, m), "channel": "web",
        "ua_family": rng.choice(["Chrome 131", "python-requests 2.32", "HeadlessChrome 131", "curl 8.4"], m, p=[.5, .2, .2, .1]),
        "new_device": True, "valid": rng.random(m) < P_ATTACK_OK, "actor": "attack"})
    att.loc[att.account_key >= acc0 + n_acc, "valid"] = False      # unknown usernames never succeed
    df = pd.concat([hum, att], ignore_index=True)
    df["customer_id"] = cid
    return df


def e1_rows(acc0: int, n_acc: int) -> pd.DataFrame:
    """E1: ~400k attempts on C03, 5-18 Oct, > 9,000 residential IPs, <= 1 attempt per IP per hour (rule R10 allows 5),
    but only 25 device hashes and an old, rare browser version."""
    hours = pd.date_range("2026-10-05", "2026-10-18 23:00", freq="h")
    ips = np.arange(9_400)
    rows = []
    for t in hours:
        k = rng.poisson(400_000 / len(hours))
        rows.append(pd.DataFrame({"ts_utc": t + pd.to_timedelta(rng.integers(0, 3600, k), unit="s"),
                                  "ip_id": "e1-" + pd.Series(rng.choice(ips, k, replace=False)).astype(str)}))
    df = pd.concat(rows, ignore_index=True)
    n = len(df)
    known = rng.random(n) < .25                                       # 25 % of the leaked usernames exist on C03
    df["account_key"] = np.where(known, rng.integers(0, n_acc, n), n_acc * 2 + rng.integers(0, 10**6, n)) + acc0
    df["ip_type"] = np.where(rng.random(n) < .8, "residential", "mobile")
    df["device_id"] = 7_000_000 + rng.integers(0, 25, n)
    df["channel"], df["ua_family"], df["new_device"], df["actor"] = "web", "Chrome 109", True, "e1"
    df["valid"] = known & (rng.random(n) < .12)                        # reused passwords -> ~3 % success overall
    df["customer_id"] = "C03"
    return df


def recommend(df: pd.DataFrame) -> pd.DataFrame:
    """The platform's existing detection (fictional): reputation + per-IP rate rule R10 + challenge on new devices."""
    n = len(df)
    r = rng.random(n)
    web = df.channel.eq("web").to_numpy()
    after_r12 = (df.customer_id.eq("C04") & (df.ts_utc >= "2026-11-02")).to_numpy()
    base = np.where(web, np.where(df.customer_id.eq("C04"), .022, .02), np.where(df.customer_id.eq("C04"), .006, .01))
    boost = np.where(web, .08, np.where(after_r12, .45, .01))         # R12: challenge app logins on a new device (C04)           # R12: challenge every app login on a new device (C04)
    p_ch = base + df.new_device.to_numpy() * boost
    actor = df.actor.to_numpy()
    p_deny = np.select([actor == "attack", actor == "e1"], [.80, .08], .002)
    p_ch = np.select([actor == "attack", actor == "e1"], [.08, .06], p_ch)
    rec = np.where(r < p_deny, "deny", np.where(r < p_deny + p_ch, "challenge", "allow"))
    # challenge pass rate: humans pass more often in the app; R12 adds harder cases in both channels
    p_pass = np.where(web, np.where(after_r12, .66, .70), np.where(after_r12, .89, .92))
    p_pass = np.where(actor == "human", p_pass, .03)
    shown = rec == "challenge"
    passed = shown & (rng.random(n) < p_pass)
    df["recommendation"], df["challenge_shown"], df["challenge_passed"] = rec, shown, np.where(shown, passed, None)
    df["customer_action"] = np.where(rec == "deny", "blocked", np.where(shown & ~passed, "blocked", "allowed"))
    df["login_success"] = df.valid.to_numpy() & (df.customer_action == "allowed").to_numpy()
    return df


def main() -> None:
    SIM.mkdir(parents=True, exist_ok=True)
    parts, acc0, truth = [], 1, []
    for cid in LOGIN:
        df = login_rows(cid, acc0)
        if cid == "C03":
            df = pd.concat([df, e1_rows(acc0, LOGIN[cid][0] * 25)], ignore_index=True)
        parts.append(df)
        acc0 += LOGIN[cid][0] * 25 * 4
    ev = recommend(pd.concat(parts, ignore_index=True)).sort_values("ts_utc", ignore_index=True)

    # ---- account changes after login, and fraud reports (known 7 to 30 days later)
    ok = ev.login_success.to_numpy()
    ev["account_update_within_1h"] = ok & (ev.actor == "human").to_numpy() & (rng.random(len(ev)) < .004)  # legitimate changes
    e2 = ev.index[(ev.actor == "e1") & ok]
    e2 = rng.choice(e2, 214, replace=False)                            # E2: 214 accounts taken over (email changed)
    bg = ev.index[(ev.actor == "attack") & ok]
    bg = rng.choice(bg, int(round(float(CAL.ato_per_million) * len(ev) / 1e6)), replace=False)
    ev.loc[e2, "account_update_within_1h"] = True
    ev.loc[bg, "account_update_within_1h"] = rng.random(len(bg)) < .7
    ev["is_ato"] = False
    ev.loc[np.r_[e2, bg], "is_ato"] = True
    report = ev.ts_utc + pd.to_timedelta(rng.integers(7, 31, len(ev)), unit="D")
    ev["reported_fraud_date"] = np.where(ev.is_ato & (report < SNAPSHOT), report.dt.date, None)

    # ---- E5: SDK 4.2 for C07's app from 12 Oct (rolled out over a week): 38 % empty device hash, 30 % events sent twice
    ev["sdk_version"] = np.where(ev.channel == "app", "4.1", "js-2.8")
    c07app = (ev.customer_id == "C07") & (ev.channel == "app") & (ev.ts_utc >= "2026-10-12")
    ramp = ((ev.ts_utc - pd.Timestamp("2026-10-12")).dt.days.clip(0, 7) + 1) / 8
    v42 = c07app & (rng.random(len(ev)) < ramp)
    ev.loc[v42, "sdk_version"] = "4.2"
    ev["event_id"] = ["L" + str(i).zfill(9) for i in range(1, len(ev) + 1)]
    ev["device_hash"] = "D" + ev.device_id.astype(str).str.zfill(7)
    ev.loc[v42 & (rng.random(len(ev)) < .38), "device_hash"] = None
    dup = ev[v42 & (rng.random(len(ev)) < .30)].copy()
    dup["ts_utc"] = dup.ts_utc + pd.to_timedelta(rng.integers(2, 20, len(dup)), unit="s")
    ev = pd.concat([ev, dup], ignore_index=True).sort_values("ts_utc", ignore_index=True)

    # ---- privacy: hash the IP id, derive the class; country and ASN class from the IP class
    uniq = pd.unique(ev.ip_id)
    ev["ip_hash"] = ev.ip_id.map(dict(zip(uniq, h(uniq))))
    ev["asn_class"] = ev.ip_type.map({"residential": "isp", "mobile": "mobile_carrier", "datacenter": "hosting",
                                      "vpn": "vpn_provider", "tor": "tor"})
    ev["country"] = np.where(ev.actor == "human", rng.choice(["FR", "BE", "DE", "ES", "IT", "GB"], len(ev),
                                                             p=[.7, .06, .07, .06, .06, .05]),
                             rng.choice(["US", "NL", "DE", "BR", "VN", "FR"], len(ev)))
    ua_set = pd.unique(ev.ua_family)
    ev["ua_claims_crawler"] = ev.ua_family.map({u: bool(crawler_rx.search(u)) for u in ua_set})
    ev["account_key"] = "A" + ev.account_key.astype(str).str.zfill(7)
    cols = ["event_id", "ts_utc", "customer_id", "account_key", "ip_hash", "ip_type", "asn_class", "country", "ua_family",
            "ua_claims_crawler", "device_hash", "sdk_version", "channel", "login_success", "recommendation",
            "customer_action", "challenge_shown", "challenge_passed", "account_update_within_1h", "reported_fraud_date"]
    out = ev[cols].copy()
    out["challenge_passed"] = out.challenge_passed.astype("boolean")
    for cid, g in out.groupby("customer_id"):   # one file per customer keeps every file small
        p = SIM / "login_events" / f"customer_id={cid}"
        p.mkdir(parents=True, exist_ok=True)
        g.drop(columns="customer_id").to_parquet(p / "part.parquet", index=False, compression="zstd")

    # ---- E7 trap: today's account table. Accounts reported as taken over are LOCKED (after the fact): a model that
    # uses this snapshot looks perfect but could never run at login time.
    locked = ev.loc[ev.reported_fraud_date.notna(), ["customer_id", "account_key", "reported_fraud_date"]].drop_duplicates("account_key")
    other = ev.loc[ev.login_success & ~ev.is_ato, ["customer_id", "account_key"]].drop_duplicates("account_key").sample(frac=.003, random_state=42)
    other["reported_fraud_date"] = (START + pd.to_timedelta(rng.integers(0, DAYS, len(other)), unit="D")).date
    snap = pd.concat([locked, other]).rename(columns={"reported_fraud_date": "status_since"})
    snap["status"] = "locked"
    snap["snapshot_date"] = SNAPSHOT.date()
    snap.to_parquet(SIM / "accounts_snapshot.parquet", index=False)

    # ---- sign-ups
    sg = []
    for cid, daily in SIGNUP.items():
        d = np.repeat(np.arange(DAYS), daily_counts(daily, cid, "signup"))
        n = len(d)
        sg.append(pd.DataFrame({"ts_utc": timestamps(d), "customer_id": cid, "actor": "human",
                                "device_id": 5_000_000 + rng.integers(0, 10**6, n),
                                "ip_id": rng.integers(0, N_RES, n).astype(str),
                                "ip_type": rng.choice(["residential", "mobile", "vpn", "datacenter"], n, p=[.6, .33, .05, .02]),
                                "email_domain_type": rng.choice(["free", "corporate", "disposable"], n, p=[.75, .23, .02]),
                                "username_entropy": rng.normal(3.3, .35, n).round(2),
                                "payment_type": rng.choice(["card", "wallet", "prepaid"], n, p=[.82, .15, .03]),
                                "channel": rng.choice(["web", "app"], n, p=[.6, .4]), "fake": rng.random(n) < .01}))
    # E3: ~3,800 fake trial sign-ups on C05, 14 Sep - 11 Oct, 40 devices, disposable e-mail, prepaid cards, no conversion
    d = rng.integers(14, 42, 3800)
    sg.append(pd.DataFrame({"ts_utc": timestamps(d, hourly=False), "customer_id": "C05", "actor": "e3",
                            "device_id": 4_000_000 + rng.integers(0, 40, 3800),
                            "ip_id": "e3-" + pd.Series(rng.integers(0, 2500, 3800)).astype(str),
                            "ip_type": rng.choice(["residential", "mobile"], 3800, p=[.7, .3]),
                            "email_domain_type": rng.choice(["disposable", "free"], 3800, p=[.92, .08]),
                            "username_entropy": rng.normal(1.6, .2, 3800).round(2),
                            "payment_type": rng.choice(["prepaid", "card"], 3800, p=[.95, .05]), "channel": "web", "fake": True}))
    s = pd.concat(sg, ignore_index=True).sort_values("ts_utc", ignore_index=True)
    n = len(s)
    s["event_id"] = ["S" + str(i).zfill(9) for i in range(1, n + 1)]
    s["account_key"] = "A" + (50_000_000 + np.arange(n)).astype(str)
    s["device_hash"] = "D" + s.device_id.astype(str).str.zfill(7)
    uniq = pd.unique(s.ip_id)
    s["ip_hash"] = s.ip_id.map(dict(zip(uniq, h(uniq))))
    r = rng.random(n)
    s["recommendation"] = np.where(s.actor == "e3", np.where(r < .05, "deny", "allow"),
                                   np.where(s.fake & (r < .5), "deny", np.where(r < .01, "challenge", "allow")))
    s["trial_started"] = s.customer_id.isin(TRIAL) & (s.recommendation != "deny") & ((s.actor == "e3") | (rng.random(n) < .6))
    conv_known = s.ts_utc < SNAPSHOT - pd.Timedelta(days=14)            # a 14-day trial converts (or not) at its end
    conv = np.where(s.fake, False, rng.random(n) < .35)
    s["trial_converted"] = pd.array(np.where(s.trial_started & conv_known, conv, None), dtype="boolean")
    flag = s.ts_utc + pd.to_timedelta(rng.integers(10, 41, n), unit="D")
    s["flagged_fake_date"] = np.where(s.fake & (flag < SNAPSHOT), flag.dt.date, None)
    scols = ["event_id", "ts_utc", "customer_id", "account_key", "ip_hash", "ip_type", "device_hash", "channel",
             "email_domain_type", "username_entropy", "payment_type", "recommendation", "trial_started", "trial_converted",
             "flagged_fake_date"]
    s[scols].to_parquet(SIM / "signup_events.parquet", index=False, compression="zstd")

    # ---- crawler sessions (user-agent claims a search or AI crawler). E4: fake Googlebot on C08 from 26 Oct
    cs = []
    for cid in CUSTOMERS.customer_id:
        for bot, pfx, k in (("Googlebot", REF["google"], 30), ("GPTBot", REF["gptbot"], 8)):
            m = rng.poisson(k * DAYS)
            cs.append(pd.DataFrame({"customer_id": cid, "claimed_bot": bot, "actor": "verified",
                                    "day": rng.integers(0, DAYS, m), "ip": draw_ips(pfx, m),
                                    "requests": rng.integers(20, 400, m)}))
        m = rng.poisson(1.5 * DAYS)          # a few spoofers everywhere (background)
        cs.append(pd.DataFrame({"customer_id": cid, "claimed_bot": "Googlebot", "actor": "spoof",
                                "day": rng.integers(0, DAYS, m), "ip": rng.choice(dc_ips, m), "requests": rng.integers(20, 300, m)}))
    m = 3000                                 # E4: ~1.2 M requests, 26 Oct - 22 Nov, AWS-hosted IPs outside Google's ranges
    cs.append(pd.DataFrame({"customer_id": "C08", "claimed_bot": "Googlebot", "actor": "e4", "day": rng.integers(56, DAYS, m),
                            "ip": rng.choice(dc_ips[300:], m), "requests": rng.integers(300, 500, m)}))
    c = pd.concat(cs, ignore_index=True)
    ua = {"Googlebot": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
          "GPTBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; GPTBot/1.2; +https://openai.com/gptbot)"}
    c["ua_claims_crawler"] = c.claimed_bot.map({b: bool(crawler_rx.search(u)) for b, u in ua.items()})
    # verification against the PUBLISHED ranges of the claimed bot (the check the analysis proposes)
    ver = {}
    for bot, pfx in (("Googlebot", REF["google"]), ("GPTBot", REF["gptbot"])):
        ips = pd.unique(c.loc[c.claimed_bot == bot, "ip"])
        ver.update({(bot, ip): bool(v) for ip, v in zip(ips, in_ranges(list(ips), pfx))})
    c["ip_in_published_ranges"] = [ver[(b, ip)] for b, ip in zip(c.claimed_bot, c.ip)]
    in_aws = dict(zip(pd.unique(c.ip), in_ranges(list(pd.unique(c.ip)), REF["aws"])))
    c["ip_type"] = np.where(c.ip.map(in_aws), "datacenter", "search_or_ai_provider")
    c["date"] = (START + pd.to_timedelta(c.day, unit="D")).dt.date
    c["endpoint"] = rng.choice(["search", "product"], len(c), p=[.6, .4])
    c["decision"] = "allow"                                            # rule R07: allow-list by user-agent
    uniq = pd.unique(c.ip)
    c["ip_hash"] = c.ip.map(dict(zip(uniq, h(uniq))))
    c = c.sort_values(["date", "customer_id"], ignore_index=True)
    c["session_id"] = ["K" + str(i).zfill(7) for i in range(1, len(c) + 1)]
    c[["session_id", "date", "customer_id", "claimed_bot", "ua_claims_crawler", "ip_hash", "ip_type",
       "ip_in_published_ranges", "endpoint", "requests", "decision"]].to_parquet(SIM / "crawler_sessions.parquet", index=False)

    # ---- traffic_daily: customer x day x endpoint x class x decision -> requests
    rows = []
    for _, cu in CUSTOMERS.iterrows():
        bad0 = .30 if cu.sector == "classifieds" else .20
        for i, day in enumerate(DAY):
            vol = cu.daily_requests * WEEKDAY[day.dayofweek] * rng.normal(1, .03)
            bad = bad0 * (1 + WEEKLY_GROWTH) ** (i / 7)
            for ep, share in (("search", .35), ("product", .45), ("checkout", .05), ("api", .15)):
                for cls, cs_, dec in (("human", 1 - bad - .03, {"allow": .994, "challenge": .005, "block": .001}),
                                      ("ai_agent", .03, {"allow": .9, "challenge": .1, "block": 0}),
                                      ("bad_bot", bad * (1.6 if ep in ("search", "product") else .5),
                                       {"allow": .03, "challenge": .09, "block": .88})):
                    for dname, p in dec.items():
                        rows.append((cu.customer_id, day.date(), ep, cls, dname, int(vol * share * cs_ * p)))
    td = pd.DataFrame(rows, columns=["customer_id", "date", "endpoint", "traffic_class", "decision", "requests"])
    vb = c.groupby(["customer_id", "date", "endpoint"], as_index=False).requests.sum()
    vb["traffic_class"], vb["decision"] = "verified_bot", "allow"     # what the platform believed (user-agent only)
    # login / sign-up rows come from the raw events (duplicates included: what the platform received)
    lg = out.assign(date=out.ts_utc.dt.date, endpoint="login",
                    traffic_class=np.where(out.recommendation == "deny", "bad_bot", "human"),
                    decision=out.recommendation.map({"allow": "allow", "challenge": "challenge", "deny": "block"}))
    su = s.assign(date=s.ts_utc.dt.date, endpoint="signup",
                  traffic_class=np.where(s.recommendation == "deny", "bad_bot", "human"),
                  decision=s.recommendation.map({"allow": "allow", "challenge": "challenge", "deny": "block"}))
    keys = ["customer_id", "date", "endpoint", "traffic_class", "decision"]
    ev_rows = pd.concat([lg[keys], su[keys]]).value_counts().rename("requests").reset_index()
    td = pd.concat([td, vb[keys + ["requests"]], ev_rows], ignore_index=True)
    td = td[td.requests > 0].sort_values(keys, ignore_index=True)
    td.to_parquet(SIM / "traffic_daily.parquet", index=False)

    # ---- context tables: customers, tickets, rule changes, SDK releases, calendar
    CUSTOMERS.drop(columns="daily_requests").to_parquet(SIM / "customers.parquet", index=False)
    tickets = pd.DataFrame([
        ("T01", "2026-09-02", "C02", "Export of monthly bot report", "Can we get the August bot traffic report as CSV for our board?", "low"),
        ("T02", "2026-09-09", "C10", "Ticket on-sale on 18 Sep", "Heads-up: big on-sale on 18 September, expect a login peak.", "low"),
        ("T03", "2026-09-29", "C05", "Free-trial sign-ups surge", "Our free-trial sign-ups went up in the last two weeks but none of them convert. Fake accounts?", "high"),
        ("T04", "2026-10-01", "C01", "Corporate VPN users challenged", "Some staff on our corporate VPN see challenges at login.", "medium"),
        ("T05", "2026-10-06", "C04", "Dashboard: filter by app version", "Can the dashboard filter traffic by app version?", "low"),
        ("T06", "2026-10-14", "C09", "API latency question", "What latency does the protection add on our checkout API?", "medium"),
        ("T07", "2026-10-20", "C03", "Unknown e-mail changes on accounts", "Several customers report that the e-mail address of their account was changed without their action. Are we under attack?", "high"),
        ("T08", "2026-10-22", "C07", "Deny rate dropped", "Our deny rate fell after our app release. Is the protection weaker?", "medium"),
        ("T09", "2026-10-27", "C11", "Partner crawler access", "A partner price-comparison crawler wants access. How should we allow it?", "low"),
        ("T10", "2026-10-30", "C06", "Challenge wording", "Can we change the language of the challenge page?", "low"),
        ("T11", "2026-11-04", "C08", "Search pages load and SEO crawler", "Server load on search pages is up since late October; logs say it is Googlebot. Should we block it?", "high"),
        ("T12", "2026-11-06", "C04", "Effect of the new app rule", "Did the new rule of 2 November make the login experience better?", "medium"),
        ("T13", "2026-11-10", "C12", "Quarterly review data", "Please prepare traffic numbers for our quarterly business review.", "low"),
        ("T14", "2026-11-12", "C01", "Pre-sale 19-22 November", "Heads-up: Black Friday pre-sale for members from 19 to 22 November.", "medium"),
        ("T15", "2026-11-20", "C01", "Login spike?", "We see many more logins since yesterday. Is this normal or an attack?", "high"),
    ], columns=["ticket_id", "date", "customer_id", "subject", "text", "priority"])
    tickets.to_parquet(SIM / "tickets.parquet", index=False)
    pd.DataFrame([
        ("R07", "2026-03-02", "all", "Allow-list search-engine and AI crawlers by user-agent"),
        ("R09", "2026-06-15", "all", "Deny logins from IPs on the hosting / Tor reputation lists"),
        ("R10", "2026-07-01", "all", "Deny when more than 5 login attempts per IP per hour"),
        ("R11", "2026-09-21", "C01", "Lower challenge rate for returning devices"),
        ("R12", "2026-11-02", "C04", "Challenge every app login from a new device"),
    ], columns=["rule_id", "date", "scope", "description"]).to_parquet(SIM / "rule_changes.parquet", index=False)
    pd.DataFrame([("C07", "app", "4.2", "2026-10-12"), ("C03", "app", "4.1", "2026-07-20"), ("C04", "app", "4.1", "2026-07-28"),
                  ("C01", "web", "js-2.8", "2026-08-10")],
                 columns=["customer_id", "channel", "sdk_version", "release_date"]).to_parquet(SIM / "sdk_releases.parquet", index=False)
    pd.DataFrame([("C10", "2026-09-18", "2026-09-18", "Concert ticket on-sale"),
                  ("C01", "2026-11-19", "2026-11-22", "Black Friday members pre-sale")],
                 columns=["customer_id", "start_date", "end_date", "campaign"]).to_parquet(SIM / "customer_calendar.parquet", index=False)

    # ---- hidden truth (local only)
    truth = pd.DataFrame([
        ("E1", "C03", "2026-10-05", "2026-10-18", "slow credential stuffing", int((ev.actor == "e1").sum()),
         int(ev.loc[ev.actor == "e1", "ip_id"].nunique()), 25),
        ("E2", "C03", "2026-10-05", "2026-10-18", "account takeover, e-mail changed within 1 h", 214, 0, 0),
        ("E3", "C05", "2026-09-14", "2026-10-11", "fake trial sign-ups", 3800, 0, 40),
        ("E4", "C08", "2026-10-26", "2026-11-22", "fake Googlebot", int(c.loc[c.actor == "e4", "requests"].sum()), 0, 0),
        ("E5", "C07", "2026-10-12", "2026-11-22", "SDK 4.2: empty device hash, duplicates", int(len(dup)), 0, 0),
        ("E6", "C04", "2026-11-02", "2026-11-22", "Simpson effect after R12", 0, 0, 0),
        ("E7", "all", "2026-08-31", "2026-11-22", "leakage via account snapshot", int(ev.is_ato.sum()), 0, 0),
        ("E8", "C01", "2026-11-19", "2026-11-22", "declared pre-sale (false signal)", 0, 0, 0),
    ], columns=["event", "customer_id", "start", "end", "what", "n", "n_ips", "n_devices"])
    truth.to_csv(DATA / "_hidden_truth.csv", index=False)
    print(f"login_events {len(out):,} (dupes {len(dup):,}) | signups {n:,} | crawler sessions {len(c):,} | "
          f"traffic rows {len(td):,} | ATO {int(ev.is_ato.sum())} | E1 attempts {int((ev.actor == 'e1').sum()):,} "
          f"from {ev.loc[ev.actor == 'e1', 'ip_id'].nunique():,} IPs | E1 success {int((ev.actor == 'e1').mul(ev.login_success).sum()):,} "
          f"| AWS draw check {dc_in_aws:.2f}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
