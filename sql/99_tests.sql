-- 99_tests.sql : automated checks. src/run_sql.py fails if any test returns passed = false.
-- K = keys, Q = data quality and consistency, P = privacy, R = RBA evaluation, E1..E8 = the 8 simulated events (each
-- must be FOUND by the analysis: a rule that names the customer and the date), F1 = the false signal is NOT escalated.
CREATE OR REPLACE TABLE tests AS
SELECT 'K01 login event_id unique after deduplication' AS test, COUNT(*) = COUNT(DISTINCT event_id) AS passed,
       COUNT(*) || ' rows' AS detail FROM logins
UNION ALL SELECT 'K02 sign-up event_id unique', COUNT(*) = COUNT(DISTINCT event_id), COUNT(*) || ' rows' FROM signups
UNION ALL SELECT 'K03 crawler session_id unique', COUNT(*) = COUNT(DISTINCT session_id), COUNT(*) || ' rows' FROM crawlers
UNION ALL SELECT 'Q01 duplicates exist only in SDK 4.2 events',
       SUM(events_raw - events_unique) FILTER (sdk_version <> '4.2') = 0 AND SUM(events_raw - events_unique) > 0,
       SUM(events_raw - events_unique) || ' duplicates' FROM out_sdk_quality
UNION ALL SELECT 'Q02 traffic_daily login requests = raw login events (customer x day)', COUNT(*) = 0, COUNT(*) || ' mismatches'
FROM (SELECT customer_id, ts_utc::DATE AS date, COUNT(*) AS n FROM login_raw GROUP BY ALL) e
FULL JOIN (SELECT customer_id, date, SUM(requests) AS n FROM traffic WHERE endpoint = 'login' GROUP BY ALL) t USING (customer_id, date)
WHERE e.n IS DISTINCT FROM t.n
UNION ALL SELECT 'Q03 traffic_daily sign-up requests = sign-up events (customer x day)', COUNT(*) = 0, COUNT(*) || ' mismatches'
FROM (SELECT customer_id, ts_utc::DATE AS date, COUNT(*) AS n FROM signups GROUP BY ALL) e
FULL JOIN (SELECT customer_id, date, SUM(requests) AS n FROM traffic WHERE endpoint = 'signup' GROUP BY ALL) t USING (customer_id, date)
WHERE e.n IS DISTINCT FROM t.n
UNION ALL SELECT 'Q04 traffic_daily verified_bot requests = crawler sessions',
       (SELECT SUM(requests) FROM traffic WHERE traffic_class = 'verified_bot') = (SELECT SUM(requests) FROM crawlers),
       (SELECT SUM(requests) FROM crawlers) || ' requests'
UNION ALL SELECT 'P01 no IP address in published tables (hash of 10 hex characters only)',
       (SELECT COUNT(*) FROM login_raw WHERE NOT regexp_full_match(ip_hash, '[0-9a-f]{10}')) = 0
   AND (SELECT COUNT(*) FROM signups WHERE NOT regexp_full_match(ip_hash, '[0-9a-f]{10}')) = 0
   AND (SELECT COUNT(*) FROM crawlers WHERE NOT regexp_full_match(ip_hash, '[0-9a-f]{10}')) = 0
   AND (SELECT COUNT(*) FROM login_raw WHERE regexp_matches(ua_family || ' ' || COALESCE(device_hash, ''), '\d+\.\d+\.\d+\.\d+')) = 0,
       'ip_hash, ua_family, device_hash checked'
UNION ALL SELECT 'P02 no original RBA User ID in outputs (no user column in out_rba_*)', COUNT(*) = 0, COUNT(*) || ' columns'
FROM information_schema.columns WHERE table_name LIKE 'out_rba%' AND column_name IN ('uid', 'user_id', 'user_key', 'User ID')
UNION ALL SELECT 'P03 no published group under 5 accounts', MIN(accounts_with_success) >= 5, 'min ' || MIN(accounts_with_success)
FROM out_e2_timeline
UNION ALL SELECT 'R01 RBA rules: thresholds learned on train, scored on labelled test months',
       (SELECT COUNT(*) FROM out_rba_thresholds) = 2 AND (SELECT SUM(ato) FROM out_rba_test_labels WHERE month >= DATE '2020-12-01') = 0
   AND (SELECT COUNT(DISTINCT period) FROM out_rba_rules) = 2,
       'test ATO = ' || (SELECT MAX(ato_in_test) FROM out_rba_topk)
UNION ALL SELECT 'E1 credential stuffing on C03 flagged the week of 5 Oct: device cluster, per-IP rule blind',
       EXISTS (SELECT 1 FROM out_alerts WHERE customer_id = 'C03' AND week = DATE '2026-10-05' AND status = 'alert')
   AND (SELECT cluster_devices = 25 AND first_day = DATE '2026-10-05' FROM out_e1_summary WHERE customer_id = 'C03')
   AND (SELECT distinct_ips >= 9000 AND max_attempts_per_ip_hour <= 3 FROM out_e1_ip_rate),
       (SELECT distinct_ips || ' IPs, max ' || max_attempts_per_ip_hour || ' per IP-hour' FROM out_e1_ip_rate)
UNION ALL SELECT 'E2 account takeover: 214 accounts with success from the cluster then e-mail change within 1 h',
       accounts_taken_over = 214 AND first_takeover >= DATE '2026-10-05' AND last_takeover <= DATE '2026-10-18',
       accounts_taken_over || ' of ' || accounts_with_success_from_cluster FROM out_e2_summary
UNION ALL SELECT 'E3 fake trial sign-ups on C05: 40 devices, no conversion, flagged week of 21 Sep',
       devices = 40 AND trial_conversion = 0 AND signups BETWEEN 3500 AND 4100
   AND EXISTS (SELECT 1 FROM out_alerts WHERE customer_id = 'C05' AND week = DATE '2026-09-21' AND status = 'alert'),
       signups || ' sign-ups on ' || devices || ' devices' FROM out_e3_summary WHERE customer_id = 'C05'
UNION ALL SELECT 'E4 fake Googlebot on C08 from 26 Oct: > 1 M requests outside the published ranges',
       (SELECT SUM(unverified_requests) FROM out_e4_daily) > 1e6
   AND (SELECT MIN(day) FROM out_e4_daily WHERE unverified_requests > 10000) = DATE '2026-10-26',
       (SELECT SUM(unverified_requests) FROM out_e4_daily) || ' requests'
UNION ALL SELECT 'E5 SDK 4.2 on C07: data-quality status from 12 Oct, raw deny rate falsely lower than clean',
       EXISTS (SELECT 1 FROM out_alerts WHERE customer_id = 'C07' AND week = DATE '2026-10-12' AND status = 'data quality')
   AND (SELECT AVG(deny_rate_clean - deny_rate_raw) FROM out_e5_dedup_effect WHERE week >= DATE '2026-10-19') > 0.005,
       (SELECT 'empty device ' || empty_device_share || ', duplicates ' || duplicate_share FROM out_sdk_quality WHERE sdk_version = '4.2')
UNION ALL SELECT 'E6 Simpson after R12 on C04: total pass rate up, web AND app down',
       MAX(pass_rate) FILTER (period LIKE '2%' AND channel = 'total') > MAX(pass_rate) FILTER (period LIKE '1%' AND channel = 'total')
   AND MAX(pass_rate) FILTER (period LIKE '2%' AND channel = 'web') < MAX(pass_rate) FILTER (period LIKE '1%' AND channel = 'web')
   AND MAX(pass_rate) FILTER (period LIKE '2%' AND channel = 'app') < MAX(pass_rate) FILTER (period LIKE '1%' AND channel = 'app'),
       'total ' || MAX(pass_rate) FILTER (period LIKE '1%' AND channel = 'total') || ' -> ' || MAX(pass_rate) FILTER (period LIKE '2%' AND channel = 'total')
FROM out_e6_simpson
UNION ALL SELECT 'E7 leakage: leaky AUC >= 0.97, honest as-of AUC on the test period clearly lower',
       MAX(auc) FILTER (model LIKE 'A%') >= 0.97 AND MAX(auc) FILTER (model LIKE 'B%') < 0.92,
       'A ' || MAX(auc) FILTER (model LIKE 'A%') || ' / B ' || MAX(auc) FILTER (model LIKE 'B%') || ' / C ' || MAX(auc) FILTER (model LIKE 'C%')
FROM out_e7_auc
UNION ALL SELECT 'E8 C01 pre-sale 19-22 Nov: volume moved, classified as explained by the campaign',
       EXISTS (SELECT 1 FROM out_alerts WHERE customer_id = 'C01' AND week = DATE '2026-11-16' AND status LIKE 'explained%'),
       (SELECT moved FROM out_alerts WHERE customer_id = 'C01' AND week = DATE '2026-11-16')
UNION ALL SELECT 'F1 no alert raised for C01 between 19 and 22 Nov', COUNT(*) = 0, COUNT(*) || ' alerts'
FROM out_alerts WHERE customer_id = 'C01' AND week = DATE '2026-11-16' AND status = 'alert'
UNION ALL SELECT 'F2 no alert at all outside the 8 events (no false positive in 12 weeks x 12 customers)', COUNT(*) = 0,
       COUNT(*) || ' unexpected alerts'
FROM out_alerts WHERE status = 'alert' AND NOT (customer_id = 'C03' AND week IN (DATE '2026-10-05', DATE '2026-10-12'))
                  AND NOT (customer_id = 'C05' AND week = DATE '2026-09-21');
