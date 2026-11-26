# Kibana / Elasticsearch queries (specification, NOT executed)

The investigation queries of `sql/12_sim_patterns.sql`, rewritten for an Elasticsearch index as a Fraud Analyst would type them in
Kibana Discover (KQL) or in ES|QL. **They were not run**: this study has no Elasticsearch cluster. Field names assume one index
`logins-*` with the columns of `data/sim/login_events`, `signups-*` and `crawlers-*` likewise. Syntax follows the public
Elastic documentation; thresholds come from the SQL version.

## Q1 - Device clusters behind a credential stuffing campaign (E1)
KQL (Discover filter, then a "Top values of device_hash" visualisation):
```
customer_id : "C03" and login_success : false and @timestamp >= "2026-10-05" and @timestamp < "2026-10-19"
```
ES|QL:
```
FROM logins-*
| WHERE customer_id == "C03" AND @timestamp >= "2026-10-05" AND @timestamp < "2026-10-19"
| STATS attempts = COUNT(*), ips = COUNT_DISTINCT(ip_hash), accounts = COUNT_DISTINCT(account_key),
        failures = SUM(CASE(login_success == false, 1, 0)) BY device_hash
| EVAL failure_rate = failures / attempts
| WHERE ips >= 200 AND failure_rate >= 0.9
| SORT ips DESC
```
Per-IP check (why the rate limit stayed silent):
```
FROM logins-*
| WHERE customer_id == "C03" AND device_hash IN ("D7000010", "D7000013")
| EVAL hour = DATE_TRUNC(1 hour, @timestamp)
| STATS n = COUNT(*) BY ip_hash, hour
| STATS max_per_ip_hour = MAX(n)
```

## Q2 - Success from the cluster, then a credential change within 1 hour (E2)
KQL:
```
customer_id : "C03" and login_success : true and account_update_within_1h : true
```
ES|QL:
```
FROM logins-*
| WHERE customer_id == "C03" AND login_success == true
| STATS successes = COUNT(*), changed = SUM(CASE(account_update_within_1h == true, 1, 0)) BY device_hash
| WHERE successes >= 5
| SORT changed DESC
```
(Report counts only; never export the account keys to the customer report.)

## Q3 - Sign-ups per device on a trial product (E3)
```
FROM signups-*
| WHERE customer_id == "C05"
| STATS signups = COUNT(*), disposable = SUM(CASE(email_domain_type == "disposable", 1, 0)),
        prepaid = SUM(CASE(payment_type == "prepaid", 1, 0)) BY device_hash
| WHERE signups >= 20
| SORT signups DESC
```

## Q4 - Crawler claims not verified by published ranges (E4)
The verification flag is computed at ingestion (ingest pipeline or enrichment against the published lists).
KQL:
```
claimed_bot : "Googlebot" and ip_in_published_ranges : false
```
ES|QL:
```
FROM crawlers-*
| WHERE ip_in_published_ranges == false
| STATS sessions = COUNT(*), requests = SUM(requests), ips = COUNT_DISTINCT(ip_hash) BY customer_id, claimed_bot
| SORT requests DESC
```

## Q5 - Data quality by SDK version (E5)
```
FROM logins-*
| STATS events = COUNT(*), unique_events = COUNT_DISTINCT(event_id),
        empty_device = SUM(CASE(device_hash IS NULL, 1, 0)) BY customer_id, channel, sdk_version
| EVAL duplicate_share = 1 - unique_events / events, empty_share = empty_device / events
| SORT empty_share DESC
```
Note: `COUNT_DISTINCT` is approximate in Elasticsearch; for an exact deduplication use the SQL version.

## Q6 - Challenge pass rate by channel before and after a rule (E6)
```
FROM logins-*
| WHERE customer_id == "C04" AND challenge_shown == true
| EVAL period = CASE(@timestamp >= "2026-11-02", "after R12", "before R12")
| STATS challenges = COUNT(*), passed = SUM(CASE(challenge_passed == true, 1, 0)) BY period, channel
| EVAL pass_rate = passed / challenges
```
Always read the per-channel rows next to the total.
