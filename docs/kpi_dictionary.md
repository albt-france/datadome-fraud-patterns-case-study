# KPI dictionary

Grain: customer x week unless stated. Computed in `sql/11_sim_monitoring.sql` (SIMULATED platform) after deduplication
(`sql/10_sim_clean.sql`). "Risky direction" is the direction that raises a flag; a flag needs a robust z-score of 4 or more against
the customer's own previous 6 weeks (median and MAD) and a minimum relative move.

| KPI | Definition | Formula | Risky direction · minimum move | Watch-out |
|---|---|---|---|---|
| Deny rate | Share of login attempts the platform recommended to deny | deny recommendations / attempts | up · 30 % | Falls when good traffic rises (campaign) or when events are duplicated (E5): read with volume and data checks |
| Challenge rate | Share of attempts sent to a challenge | challenges / attempts | up · 30 % | Moves with rule changes (R12): triaged as "expected after rule" |
| Challenge pass rate | Share of challenges passed: a proxy of friction for humans | passed / challenges | down · 20 % | Mix effect: compare web and app separately (E6) |
| Failure rate | Share of login attempts that fail | failed / attempts | up · 20 % | Credential stuffing raises it; forgotten-password waves too |
| Devices per login | Distinct device hashes / attempts | distinct devices / attempts | down · 20 % | Collapses when few devices make many attempts (E1) |
| Account takeover rate | Takeovers reported later / successful logins | reported takeovers / successes | - | **Lagging**: reports arrive 7 to 30 days later; the last 4 weeks are incomplete |
| Update after login rate | Successful logins followed by a credential change within 1 h | changes / successes | up · 50 % | Rare event: needs a large move to be meaningful |
| Fake account rate | Sign-ups flagged as fake later / sign-ups | flagged / sign-ups | - | **Lagging** (10 to 40 days) |
| Disposable e-mail share | Sign-ups with a disposable e-mail domain | disposable / sign-ups | up · 50 % | Privacy relays are not disposable domains |
| Prepaid share | Sign-ups paying with a prepaid card | prepaid / sign-ups | up · 50 % | Some markets use prepaid cards widely |
| Devices per sign-up | Distinct device hashes / sign-ups | distinct / sign-ups | down · 20 % | Shared devices in shops and schools |
| Trial conversion | Trials converted / trials started | converted / started | down · 30 % | Known only 14 days after the sign-up |
| Empty device share | Events without a device hash | empty / events | up · +2 points | Data-quality metric: when it moves, fix the data before reading the others |
| Precision (rule) | Share of alerts that are fraud | true alerts / alerts | - | Depends on label maturity; read at the alert budget |
| Recall (rule) | Share of fraud the rule alerts on | true alerts / fraud | - | Needs a complete label: use a period whose reports have arrived |
| Alerts per day | Workload created by a rule | alerts / days | - | The constraint that decides the threshold |
| Report delay | Days between the fraud and its report | report date - event date | - | Sets how long to wait before measuring recall |

Triage of a flagged customer-week: **data quality** (empty device share moved) > **explained by the customer's campaign** (only
volume moved, quality metrics normal, campaign declared) > **expected after rule** (challenge metrics moved within 3 weeks of a
rule change) > **alert**.
