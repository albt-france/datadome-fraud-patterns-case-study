# Detection signal proposals (M4, M5)

Three new signals and two interface ideas, each measured offline on the SIMULATED platform (fictional customers) and, where
possible, compared with the PUBLIC DATA. Results: `data/output/signal_offline.csv`, `e7_auc.csv`, `s3_volume.csv`.
Signals are described by what they detect, not by how to avoid them.

## Summary
| Signal | What it detects | Offline gain (SIMULATED) | False-positive cost | Rollout |
|---|---|---|---|---|
| S1 device cluster on many IPs | credential stuffing spread over residential IPs | ATO model AUC 0.872 -> 0.994 on the test period; alerts per day 2,256 -> 129 at the same recall (98.2 % -> 97.3 %); precision 0.12 % -> 2.03 % | shared devices (kiosks, families): needs >= 50 attempts in 24 h or >= 5 failures in 1 h | monitor mode 2 weeks, then challenge, then deny |
| S2 success then credential change within 1 h | account takeover that locks the owner out | recall 99.1 %, precision 6.3 %, 42 alerts per day across 6 customers; S1 AND S2: 214 alerts, all takeovers | legitimate e-mail changes (0.4 % of logins) | alert to the customer, not a block |
| S3 crawler claim not verified | bots using a search-engine or AI crawler user-agent | 1.45 M requests over 12 weeks that the user-agent allow-list let through (1.22 M on C08) | stale range lists, official crawlers missing from a list | refresh lists daily; reverse DNS when no list exists |

Why AUC is not enough: on the RBA data (PUBLIC DATA), the best single rule still raises 531 false alerts per caught takeover on
Sep-Nov 2020. What matters is precision at the alert budget an analyst can review, and the time the signal is known (S2 is
known 1 hour after the login, so it is an alert, not a login decision).

## S1 - device cluster on many IPs
- **Definition.** For each device hash: attempts in the last 24 h and failures in the last hour, computed at the time of the login
  (past only). Flag when attempts >= 50 or failures >= 5.
- **Why it works here.** The campaign rotated 9,400 IPs but only 25 device hashes.
- **Measure.** `sql/14_sim_leakage.sql`: model B (existing signals: new device, risky IP class, IP failures) versus model C (B + S1),
  weights learned on 31 Aug - 11 Oct, scored on 12 Oct - 22 Nov.
- **Limits.** If the device hash is empty (SDK 4.2 on C07, 38 % of app events) the signal is silent: monitor the empty share.

## S2 - success then credential change within 1 hour
- **Definition.** A successful login followed, within 60 minutes and in the same account, by an e-mail, phone or password change.
- **Measure.** `sql/15_signal_eval.sql`. Label = takeover reported later (7 to 30 days).
- **Limits.** Needs the customer to send account-change events (Account Protect style integration).

## S3 - crawler claim not verified by published IP ranges
- **Definition.** User-agent matches a known crawler pattern (public list, 1,510 patterns) and the IP is outside the ranges that
  crawler's operator publishes (Googlebot: 317 prefixes; GPTBot: 18 prefixes; lists read on 26 Nov 2026).
- **Measure.** `out_e4_crawlers`, `out_s3_volume`: 4,529 unverified sessions from 571 IPs on 12 customers.
- **Limits.** Simulated IPs are drawn inside the real published ranges only to set their class; no IP is published.

## Interface idea 1 - "Cluster" view in the dashboard (ILLUSTRATIVE mock-up, values from the SIMULATED data)
```
+--------------------------------------------------------------------------------------+
| Clusters - customer C03 - last 14 days                         [device] [ASN] [UA]   |
|--------------------------------------------------------------------------------------|
| Device hash   IPs    Accounts   Attempts   Failures   Successes   First seen   Action |
| D7000010      7,762  15,917     16,060     98 %       388         05 Oct      [Challenge] |
| D7000013      7,748  15,854     15,990     97 %       409         05 Oct      [Challenge] |
| ... 25 devices, 9,400 IPs in total                                                    |
| [Export counts for the customer report]                                               |
+--------------------------------------------------------------------------------------+
```
The analyst sees the tie between events (one device, thousands of IPs) instead of thousands of clean-looking IPs.

## Interface idea 2 - filter "crawler claims not verified" (ILLUSTRATIVE mock-up, values from the SIMULATED data)
```
Traffic > Bots > Verified crawlers                    [x] show claims NOT verified by published ranges
Claimed bot   Verified sessions   Unverified sessions   Unverified requests   Current rule
Googlebot     2,579 (C08)         3,114 (C08)           1.22 M (C08)          allow (user-agent)  [Change to: verify IP]
```
One click shows customers whose allow-list trusts the user-agent alone.

## Hand-off to Solution Engineers (M5)
For each customer touched: the KPI before / after in monitor mode, the expected alert volume per day, and the false-positive
cases to watch (shared devices, travellers, partner crawlers). Detection performance expectations are stated as precision and
alerts per day, not as AUC.
