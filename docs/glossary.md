# Glossary

| Term | Meaning in this study |
|---|---|
| Account takeover (ATO) | A successful login by someone other than the owner, usually followed by a change that locks the owner out |
| Credential stuffing | Automated login attempts with username / password pairs leaked elsewhere |
| Low and slow | An attack spread over many IPs so that each one stays under per-IP limits |
| Fake account / trial abuse | Accounts created in bulk to take free trials, promotions or credits (the posting's "fake subscriptions") |
| Device hash | A fingerprint of the browser or app sent by the protection SDK; ties events that come from the same device |
| Device cluster | A small set of device hashes behind many IPs and many accounts (signal S1) |
| Verified crawler | A crawler whose IP is inside the ranges its operator publishes; a user-agent alone proves nothing |
| Recommendation / customer action | What the platform advises (allow, challenge, deny) / what the customer's application finally did |
| Challenge pass rate | Share of challenges passed; a proxy of friction for real users |
| Precision / recall | Share of alerts that are fraud / share of fraud that raised an alert |
| Alert budget | Number of alerts per day the team can review; precision is read at that budget |
| AUC | Probability that a random fraud case scores higher than a random normal case (0.5 = coin flip) |
| As-of signal | A signal computed only with information available at the moment of the event |
| Leakage | Using information from after the event (e.g. an account locked after the fraud report): looks perfect, cannot run live |
| Time split | Learn on an earlier period, measure on a later one, as in production |
| Robust z-score | Distance from the median of the previous weeks, in units of the median absolute deviation |
| Simpson's paradox | A total moves one way while every segment moves the other way, because the mix of segments changed |
| Label maturity | Fraud reports arrive days or weeks later: recent periods look cleaner than they are |
| KQL / ES\|QL | Kibana Query Language (filters in Discover) / Elasticsearch piped query language (aggregations) |
