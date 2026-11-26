-- 12_sim_patterns.sql : find the fraud patterns behind the alerts (defender's view, SIMULATED data).

-- E1 credential stuffing: one device hash seen on MANY IPs with a high failure rate (a per-IP rule cannot see it)
CREATE OR REPLACE TABLE e1_dev AS
SELECT customer_id, device_hash,
       COUNT(*) AS attempts, COUNT(DISTINCT ip_hash) AS ips, COUNT(DISTINCT account_key) AS accounts,
       AVG((NOT login_success)::INT) AS failure_rate, mode(ua_family) AS ua_family,
       MIN(ts_utc)::DATE AS first_day, MAX(ts_utc)::DATE AS last_day
FROM logins WHERE device_hash IS NOT NULL GROUP BY ALL;

-- signal S1 "device cluster": a device hash with >= 200 IPs and >= 90 % failures over the 12 weeks
CREATE OR REPLACE TABLE e1_cluster AS SELECT * FROM e1_dev WHERE ips >= 200 AND failure_rate >= 0.9;

CREATE OR REPLACE TABLE out_e1_summary AS
SELECT customer_id, COUNT(*) AS cluster_devices, SUM(attempts) AS attempts, SUM(ips) AS ip_device_pairs,
       ROUND(SUM(attempts * failure_rate) / SUM(attempts), 4) AS failure_rate, MIN(first_day) AS first_day,
       MAX(last_day) AS last_day, mode(ua_family) AS ua_family
FROM e1_cluster GROUP BY ALL;

-- how many distinct IPs, and the busiest IP-hour: shows why the per-IP rule R10 (> 5 per hour) never fired
CREATE OR REPLACE TABLE out_e1_ip_rate AS
WITH c AS (SELECT l.* FROM logins l JOIN e1_cluster USING (customer_id, device_hash)),
     ih AS (SELECT ip_hash, date_trunc('hour', ts_utc) AS hr, COUNT(*) AS n FROM c GROUP BY ALL)
SELECT (SELECT COUNT(DISTINCT ip_hash) FROM c) AS distinct_ips, MAX(n) AS max_attempts_per_ip_hour,
       ROUND(AVG(n), 2) AS avg_attempts_per_active_ip_hour,
       (SELECT ROUND(AVG((recommendation = 'allow')::INT), 4) FROM c) AS share_recommended_allow
FROM ih;

-- daily C03 logins: cluster versus everything else
CREATE OR REPLACE TABLE out_e1_daily AS
SELECT ts_utc::DATE AS day,
       SUM((c.device_hash IS NOT NULL)::INT) AS cluster_attempts,
       SUM((c.device_hash IS NULL)::INT)     AS other_attempts,
       SUM((c.device_hash IS NOT NULL AND l.login_success)::INT) AS cluster_successes
FROM logins l LEFT JOIN e1_cluster c USING (customer_id, device_hash)
WHERE l.customer_id = 'C03' GROUP BY 1 ORDER BY 1;

-- E2 account takeover: successful login from the cluster, then the account e-mail changes within the hour (signal S2)
CREATE OR REPLACE TABLE e2_acc AS
SELECT l.account_key, MIN(l.ts_utc) AS first_success, bool_or(l.account_update_within_1h) AS changed_within_1h,
       MIN(l.reported_fraud_date) AS reported, mode(l.recommendation) AS recommendation
FROM logins l JOIN e1_cluster c USING (customer_id, device_hash)
WHERE l.login_success GROUP BY 1;

CREATE OR REPLACE TABLE out_e2_summary AS
SELECT COUNT(*)                                              AS accounts_with_success_from_cluster,
       SUM(changed_within_1h::INT)                           AS accounts_taken_over,
       SUM((changed_within_1h AND reported IS NOT NULL)::INT) AS taken_over_and_reported,
       MIN(first_success) FILTER (changed_within_1h)::DATE   AS first_takeover,
       MAX(first_success) FILTER (changed_within_1h)::DATE   AS last_takeover,
       SUM((changed_within_1h AND reported <= DATE '2026-10-20')::INT) AS reported_before_ticket,
       ROUND(AVG((recommendation = 'allow')::INT) FILTER (changed_within_1h), 4) AS share_recommended_allow
FROM e2_acc;

CREATE OR REPLACE TABLE out_e2_timeline AS
SELECT first_success::DATE AS day, COUNT(*) AS accounts_with_success, SUM(changed_within_1h::INT) AS taken_over
FROM e2_acc GROUP BY 1 HAVING COUNT(*) >= 5 ORDER BY 1;   -- privacy: no published group under 5 accounts

-- E3 fake trial sign-ups: many sign-ups per device, disposable e-mail, prepaid cards, no conversion (signal on devices)
CREATE OR REPLACE TABLE e3_dev AS
SELECT customer_id, device_hash, COUNT(*) AS signups FROM signups GROUP BY ALL HAVING COUNT(*) >= 20;

CREATE OR REPLACE TABLE out_e3_summary AS
SELECT s.customer_id, COUNT(DISTINCT s.device_hash) AS devices, COUNT(*) AS signups,
       ROUND(AVG((email_domain_type = 'disposable')::INT), 4) AS disposable_share,
       ROUND(AVG((payment_type = 'prepaid')::INT), 4)          AS prepaid_share,
       ROUND(AVG(username_entropy), 2)                         AS avg_username_entropy,
       ROUND(AVG(trial_converted::INT), 4)                     AS trial_conversion,
       ROUND(AVG((recommendation = 'allow')::INT), 4)          AS share_recommended_allow,
       MIN(ts_utc)::DATE AS first_day, MAX(ts_utc)::DATE AS last_day
FROM signups s JOIN e3_dev USING (customer_id, device_hash) GROUP BY 1;

CREATE OR REPLACE TABLE out_e3_weekly AS
SELECT date_trunc('week', s.ts_utc)::DATE AS week,
       SUM((d.device_hash IS NOT NULL)::INT) AS cluster_signups, SUM((d.device_hash IS NULL)::INT) AS other_signups,
       ROUND(AVG(CASE WHEN d.device_hash IS NULL AND trial_started THEN trial_converted::INT END), 4) AS other_conversion
FROM signups s LEFT JOIN e3_dev d USING (customer_id, device_hash)
WHERE s.customer_id = 'C05' GROUP BY 1 ORDER BY 1;

-- E4 fake Googlebot: the user-agent claims a crawler, the IP is outside the crawler's PUBLISHED ranges (signal S3)
CREATE OR REPLACE TABLE out_e4_crawlers AS
SELECT customer_id, claimed_bot, ip_in_published_ranges, ip_type,
       COUNT(*) AS sessions, SUM(requests) AS requests, COUNT(DISTINCT ip_hash) AS ips,
       ROUND(AVG((decision = 'allow')::INT), 4) AS allowed_share
FROM crawlers GROUP BY ALL ORDER BY requests DESC;

CREATE OR REPLACE TABLE out_e4_daily AS
SELECT date AS day,
       SUM(requests) FILTER (ip_in_published_ranges)     AS verified_requests,
       SUM(requests) FILTER (NOT ip_in_published_ranges) AS unverified_requests
FROM crawlers WHERE customer_id = 'C08' AND claimed_bot = 'Googlebot' GROUP BY 1 ORDER BY 1;

-- unverified crawler claims by customer and week (the dashboard view "crawler claims not verified")
CREATE OR REPLACE TABLE out_e4_weekly AS
SELECT customer_id, date_trunc('week', date)::DATE AS week, SUM(requests) AS unverified_requests
FROM crawlers WHERE NOT ip_in_published_ranges GROUP BY ALL ORDER BY customer_id, week;

-- traffic mix over time (all customers), as the platform labelled it
CREATE OR REPLACE TABLE out_traffic_weekly AS
SELECT date_trunc('week', date)::DATE AS week, traffic_class, SUM(requests) AS requests
FROM traffic GROUP BY ALL ORDER BY week, traffic_class;
