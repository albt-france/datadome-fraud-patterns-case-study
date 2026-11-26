# Fraud pattern library (defender's view)

One card per pattern: how to recognise it, the signals, the query that finds it, the false-positive risk, the response.
Numbers marked SIMULATED come from the fictional platform of this study (12 fictional customers, 31 Aug - 22 Nov 2026);
numbers marked PUBLIC DATA come from the RBA login dataset (synthesized, Feb 2020 - Feb 2021) or the web robot dataset (March 2018).
This library describes what to detect. It contains no technique to get around any protection.

---

## 1. Credential stuffing (including "low and slow")

**What it is.** Automated login attempts with username / password pairs leaked elsewhere, betting on password reuse.

**How to recognise it**
- Failure rate on the login endpoint jumps for one customer (SIMULATED C03: failure rate +46 % in the week of 5 Oct).
- Many accounts tried, most of them unknown to the site, few successes (SIMULATED: 97.4 % failures).
- "Low and slow": each IP stays under the per-IP rate limit (SIMULATED: 9,400 IPs, at most 1 attempt per IP and per hour,
  while the rule fires above 5), but the attempts share a **small set of device fingerprints** (25) and a **rare browser version**.

**Signals**
| Signal | Known at login time? | Note |
|---|---|---|
| Distinct IPs per device hash (24 h / 14 days) | yes | strongest in the simulation: 25 devices on 9,400 IPs |
| Failed logins per device hash (1 h) | yes | proposed signal S1 |
| Share of unknown usernames per device / per ASN | yes | needs the customer to send the outcome |
| Rare user-agent version compared with the customer's last 7 days | yes | weak alone (updates, niche browsers) |
| Failed logins per IP (1 h) | yes | blind to residential proxy rotation (PUBLIC DATA: 0 takeovers caught on Sep-Nov 2020) |

**Query** - `sql/12_sim_patterns.sql` (tables `e1_dev`, `e1_cluster`, `out_e1_ip_rate`); KQL / ES|QL version in `kibana_es_queries.md` (Q1).

**False-positive risk.** Shared devices (family tablets, kiosks, call centres) and corporate NAT put several accounts on one
device or IP. A failure rate of 90 % or more across hundreds of IPs is not compatible with them.

**Response.** Challenge then deny the cluster's device hashes; tell the customer; force a password reset on the accounts that
had a successful login from the cluster; review the per-IP limit.

---

## 2. Account takeover (ATO)

**What it is.** A login that succeeds with the real credentials but not by the real owner, usually followed by an action that
locks the owner out (e-mail or password change) or monetises the account.

**How to recognise it**
- PUBLIC DATA (RBA): 141 takeover logins out of 31,269,264. On successful logins, 47.9 % of takeovers come from a **country new
  for the user** against 0.5 % of normal logins; 54.3 % come from an IP on the attack list against 6.4 %.
- SIMULATED (C03): 214 accounts logged in from the credential stuffing cluster and **changed the e-mail within the hour**.

**Signals**
| Signal | Known when | Evidence |
|---|---|---|
| New country for the user | at login | RBA: best simple rule, but 531 to 648 false alerts per caught takeover |
| New device / browser for the user | at login | frequent for real users (device churn) |
| Login from a device cluster (S1) | at login | SIMULATED: alerts/day 2,256 -> 129 at the same recall |
| Success then credential change within 1 h (S2) | 1 h after login | SIMULATED: recall 99.1 %, precision 6.3 %; with S1: 214 of 214 |

**Query** - `out_e2_summary`, `out_signal_offline`; KQL / ES|QL Q2.

**False-positive risk.** Travellers (new country), new phones (new device), people who change their e-mail on purpose.
Precision must be read at the alert budget, not as an AUC.

**Response.** Freeze sensitive changes, restore the e-mail, reset the password, notify the owner; report counts (never account
lists) to the customer; add S2 as an alert and S1 as a login signal.

---

## 3. Fake accounts and free-trial abuse (fake subscriptions)

**What it is.** Accounts created in bulk to abuse free trials, promotions or referral credits.

**How to recognise it** (SIMULATED C05, 14 Sep - 11 Oct): 3,800 sign-ups from 40 devices; 91.4 % disposable e-mail domains;
95.5 % prepaid cards; near-sequential usernames (entropy 1.6 against 3.3); **0 % trial conversion**; 94.9 % recommended "allow".

**Signals.** Sign-ups per device (7 / 28 days); disposable-domain share; username entropy; prepaid share; conversion of the
cohort (known only at the end of the trial: a lagging signal).

**Query** - `out_e3_summary`, `out_e3_weekly`; KQL / ES|QL Q3.

**False-positive risk.** Shared devices in schools or shops; privacy-minded users with relay e-mail addresses. Combine several
signals; never block on the e-mail domain alone.

**Response.** Challenge sign-ups from devices above the threshold; delay trial benefits until a payment check; tell the customer
which cohort to review (counts and dates).

---

## 4. Fake search-engine or AI crawler

**What it is.** A bot that copies a known crawler's user-agent to be allowed through.

**How to recognise it** (SIMULATED C08 from 26 Oct): 1.22 M requests on search and product pages with a Googlebot user-agent from
hosting IPs **outside the ranges Google publishes**; allowed by the user-agent allow-list (rule R07).

**Signal (S3).** The user-agent claims crawler X and the IP is not in crawler X's published ranges (Googlebot JSON list,
GPTBot list). Known crawler user-agents come from a public list (1,510 patterns).

**Query** - `out_e4_crawlers`, `out_e4_daily`; KQL / ES|QL Q4.

**False-positive risk.** Out-of-date range lists (refresh daily); other official crawlers of the same company published in
separate lists; crawlers that publish no list. When no list exists, check the reverse DNS of the IP instead.

**Response.** Replace "allow by user-agent" with "allow by user-agent AND verified IP"; treat unverified claims as ordinary
traffic (bot detection applies); tell the customer the server-load cause.

---

## 5. Scraping

**What it is.** Automated copying of content or prices; the largest bad-bot category as stated by DataDome (70.9 % of bad bot
traffic, report 2026, read 26 Nov 2026).

**How to recognise it** (PUBLIC DATA, web robot sessions, March 2018): robots make few requests per session (median 1 against 30
for humans), load no images, and do not send a referrer. Gradient boosting on 35 session features: AUC 0.996 (5-fold).

**Signals.** Requests per session, image share, HTML share, time between requests and its spread, repeated requests, 4xx share,
HEAD requests; page-topic diversity.

**False-positive risk.** Accessibility tools, text browsers, aggressive caching. The 2018 library logs are not today's traffic.

**Response.** Rate and challenge by session behaviour; protect search and product endpoints first (classifieds, e-commerce).
