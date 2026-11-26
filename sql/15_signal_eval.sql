-- 15_signal_eval.sql : offline measure of the 3 proposed detection signals (SIMULATED platform).
-- S1 device cluster on many IPs (as of login, test period of 14_sim_leakage.sql: model C versus model B)
-- S2 successful login followed by an e-mail / credential change within 1 h (label = takeover reported later)
-- S3 user-agent claims a crawler but the IP is outside that crawler's published ranges
CREATE OR REPLACE TABLE out_signal_offline AS
SELECT 'S1 device cluster (added to existing signals)' AS signal, 'successful logins, 12 Oct - 22 Nov' AS scope,
       c.alerts_per_day, c.precision_at_alert AS precision, c.recall_at_alert AS recall,
       b.alerts_per_day AS baseline_alerts_per_day, b.precision_at_alert AS baseline_precision
FROM out_e7_auc c, out_e7_auc b WHERE c.model LIKE 'C%' AND b.model LIKE 'B%'
UNION ALL
SELECT 'S2 success then credential change within 1 h', 'successful logins, 31 Aug - 22 Nov',
       ROUND(SUM(account_update_within_1h::INT) / 84, 0),
       ROUND(SUM((account_update_within_1h AND reported_fraud_date IS NOT NULL)::INT) / SUM(account_update_within_1h::INT), 4),
       ROUND(SUM((account_update_within_1h AND reported_fraud_date IS NOT NULL)::INT) / SUM((reported_fraud_date IS NOT NULL)::INT), 3),
       NULL, NULL
FROM logins WHERE login_success
UNION ALL
SELECT 'S3 crawler claim not verified by published IP ranges', 'crawler sessions, all customers',
       ROUND(SUM((NOT ip_in_published_ranges)::INT) / 84, 0),
       NULL, NULL, NULL, NULL
FROM crawlers;

-- S3 volumes: what the user-agent allow-list (rule R07) let through without verification
CREATE OR REPLACE TABLE out_s3_volume AS
SELECT ip_in_published_ranges, COUNT(*) AS sessions, SUM(requests) AS requests, COUNT(DISTINCT ip_hash) AS ips,
       COUNT(DISTINCT customer_id) AS customers
FROM crawlers GROUP BY 1 ORDER BY 1;
