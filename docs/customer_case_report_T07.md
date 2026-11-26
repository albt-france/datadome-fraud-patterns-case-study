# Customer case report - ticket T07 (customer C03, streaming) - SIMULATED

Ticket received 2026-10-20: "Several customers report that the e-mail address of their account was changed without their action. Are we under attack?" Priority: high. Report drafted on 2026-10-21 from data up to 2026-10-20; counts updated with the 23 Nov extract.

## Summary (5 lines)

1. Yes: C03 was the target of a credential stuffing campaign from 2026-10-05 to 2026-10-18 (400,278 login attempts, 97.4% failed).
2. The attempts came from 9,400 residential and mobile IPs, never more than 1 per IP and per hour, so the per-IP limit (5 per hour) never triggered.
3. They shared only 25 device fingerprints and an old browser version (Chrome 109): that is how the campaign is recognised.
4. 9,930 accounts had a successful login from these devices; 214 of them had their e-mail address changed within the hour (account takeover).
5. Recommended now: reset passwords and restore the e-mail of the affected accounts, step-up checks on e-mail changes, and the new device-cluster signal (deployed in monitor mode first).

## Timeline

| Date | What happened |
|---|---|
| 2026-10-05 | First attempts from the device cluster (low and slow per IP). |
| 2026-10-12 | Weekly monitoring (run after the week closes) flags C03 (failure rate, logins, devices per login): alert for the week of 2026-10-05. Not escalated to the customer at that time (gap: see recommendations). |
| 2026-10-17 | Peak day: 28,861 attempts, 772 successful logins. |
| 2026-10-18 | Last attempts. |
| 2026-10-20 | Ticket T07: end users report e-mail changes (27 takeovers already reported by then). |
| 2026-10-21 | Analysis: device cluster found, affected accounts counted, this report drafted. |

## Affected accounts (counts only)

| Group | Accounts |
|---|---|
| Successful login from the cluster (credentials known to the attacker) | 9,930 |
| ... of which e-mail changed within 1 hour (taken over) | 214 |
| ... of which reported as fraud by 23 Nov | 214 |

## What the detection saw, and what it missed

- Missed: 86% of the cluster's attempts received an 'allow' recommendation. The IPs were clean residential addresses and each one stayed under the per-IP rate rule.
- Missed: all 214 takeover logins were recommended 'allow'; the e-mail change that followed was not a signal.
- Seen: the weekly monitoring flagged C03 from the first week (failure rate +46 %, devices per login -83 %), but no rule turned that into a customer alert.
- Seen in the analysis: 25 device fingerprints on 9,400 IPs with 97 % failures is not human behaviour.

## Recommended actions

| Owner | Action | When |
|---|---|---|
| Customer | Force a password reset on the 9,930 accounts; restore the e-mail of the 214 taken-over accounts and notify their owners. | Now |
| Customer | Ask for a confirmation (old e-mail or second factor) before an e-mail or password change. | This week |
| Threat Research | Ship signal S1 'device cluster on many IPs' (monitor mode, then deny) and S2 'success then credential change within 1 h' (alert). | 2 weeks |
| Solution Engineer | Review the per-IP limit with the customer: it cannot stop a low-and-slow campaign. | Next call |

## What remains uncertain

- Whether the attacker used the other validated accounts later (no e-mail change seen yet): treat them as exposed.
- Where the leaked credentials come from (C03 or a third-party breach): the data cannot tell.
- Fraud reports arrive 7 to 30 days after the takeover: the count of reported takeovers can still grow.
- Simulated case: every number comes from the fictional platform of this study.

Independent case study based on public data · not affiliated with or endorsed by DataDome
