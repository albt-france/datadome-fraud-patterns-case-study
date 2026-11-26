# Assumptions of the simulation (`src/simulate_platform.py`, seed 42)

The platform, its 12 customers (C01-C12) and every event are **fictional**. They are not DataDome, not DataDome customers, and
not DataDome data. The simulation follows the public Account Protect logic only in its shape: the platform sends a
recommendation (allow / challenge / deny) and the customer's application keeps the final decision (`customer_action`).

## Period and volumes
- 12 weeks, 31 Aug - 22 Nov 2026, UTC. Data extract ("snapshot") on 23 Nov 2026: later fraud reports are not known.
- Login events for 6 customers (C01, C02, C03, C04, C07, C10): 2,500 to 5,000 human logins per day each, plus background attacks;
  2,635,873 raw events (21,620 duplicates). Sign-ups for 6 customers: 450,874 events. Crawler sessions: 42,878.
- `traffic_daily` (12 customers): requests by endpoint, traffic class and decision; login and sign-up rows are the event counts.

## Calibration
| Parameter | Value | Source |
|---|---|---|
| Human login success rate | 41.66 % | RBA dataset, logins from non-attack IPs (PUBLIC DATA, synthesized values) |
| Attack-IP login success rate | 25.98 % | RBA dataset, logins from attack IPs |
| Share of logins from attack IPs | 9.9 % | RBA dataset |
| Account takeovers per million logins (background) | 4.51 | RBA dataset |
| Concentration of attack traffic | few heavy-hitter IPs (Zipf weights) | RBA: the top 10 ASNs carry 87 % of attack logins |
| Bad-bot share of sessions at the start | 20 % (30 % in classifieds) | web robot dataset: 20.0 % of sessions labelled robots (March 2018) |
| Bad-bot growth | +1.6 % per week = 2.24^(1/52) - 1 | +124 % in 12 months, as stated by DataDome (report 2026, read 26 Nov 2026) |
| Day / hour profile | evening peak, weekend +12-15 % | assumption |
| Device churn of real users | 10 % of logins on a device new for the account | assumption |
| Legitimate credential changes | 0.4 % of successful human logins | assumption |
| Report delay | takeovers 7-30 days, fake sign-ups 10-40 days | assumption |
| Trial length | 14 days (conversion known at the end) | assumption |

## IP addresses
- Residential and mobile addresses are synthetic identifiers, never real IPs.
- Hosting addresses are drawn inside real AWS published prefixes, Tor addresses from the public exit list, and verified crawler
  addresses inside Google's and OpenAI's published ranges, **only to derive a class and the verification flag**. Every address is
  hashed (salted SHA-256, 10 characters) before writing; no address and no prefix is published.

## The 8 hidden events
| # | Customer | Dates | What | Found by |
|---|---|---|---|---|
| E1 | C03 | 5-18 Oct | 400,278 login attempts, 9,400 residential IPs, at most 1 per IP-hour, 25 device hashes, Chrome 109, 97 % failures | weekly alert + device cluster query |
| E2 | C03 | 5-18 Oct | 214 accounts: success from the cluster, e-mail changed within 1 h; ticket T07 on 20 Oct | success-then-change query |
| E3 | C05 | 14 Sep-11 Oct | 3,800 trial sign-ups, 40 devices, disposable e-mail, prepaid cards, no conversion; ticket T03 | weekly alert + sign-ups per device |
| E4 | C08 | from 26 Oct | about 1.2 M requests with a Googlebot user-agent from hosting IPs outside Google's ranges; ticket T11 | crawler verification |
| E5 | C07 | from 12 Oct | SDK 4.2 (app): 38 % empty device hash, 30 % of events sent twice; ticket T08 | SDK quality table, "data quality" status |
| E6 | C04 | from 2 Nov | rule R12: total challenge pass rate up, web and app both down (mix moved to the app); ticket T12 | per-channel table |
| E7 | all | - | account snapshot leaks the label (locked after the report) | AUC with and without the snapshot, time split |
| E8 | C01 | 19-22 Nov | declared pre-sale: logins +180 %, sign-ups +240 %, quality normal; tickets T14, T15 | "explained by the customer's campaign" status, test F1 |

The hidden truth file (`data/_hidden_truth.csv`) is kept locally to compare with what the analysis finds, and is not published.
