-- 11_sim_monitoring.sql : weekly KPIs per customer, deviation from each customer's own recent baseline (robust z-score),
-- and a triage status: alert / data quality / explained by the customer's campaign.
CREATE OR REPLACE TABLE kpi_login AS
SELECT customer_id, date_trunc('week', ts_utc)::DATE AS week,
       COUNT(*)                                                        AS logins,
       AVG((NOT login_success)::INT)                                   AS failure_rate,
       AVG((recommendation = 'deny')::INT)                             AS deny_rate,
       AVG(challenge_shown::INT)                                       AS challenge_rate,
       AVG(CASE WHEN challenge_shown THEN challenge_passed::INT END)   AS challenge_pass_rate,
       AVG((device_hash IS NULL)::INT)                                 AS empty_device_share,
       COUNT(DISTINCT device_hash) / COUNT(*)                          AS devices_per_login,
       AVG(CASE WHEN login_success THEN account_update_within_1h::INT END) AS update_after_login_rate
FROM logins GROUP BY ALL;

CREATE OR REPLACE TABLE kpi_signup AS
SELECT customer_id, date_trunc('week', ts_utc)::DATE AS week,
       COUNT(*)                                                        AS signups,
       AVG((email_domain_type = 'disposable')::INT)                    AS disposable_share,
       AVG((payment_type = 'prepaid')::INT)                            AS prepaid_share,
       COUNT(DISTINCT device_hash) / COUNT(*)                          AS devices_per_signup,
       AVG(CASE WHEN trial_started THEN trial_converted::INT END)      AS trial_conversion
FROM signups GROUP BY ALL;

-- long format: one row per customer x week x metric
CREATE OR REPLACE TABLE kpi_long AS
SELECT customer_id, week, metric, value FROM (UNPIVOT kpi_login ON COLUMNS(* EXCLUDE (customer_id, week)) INTO NAME metric VALUE value)
UNION ALL
SELECT customer_id, week, metric, value FROM (UNPIVOT kpi_signup ON COLUMNS(* EXCLUDE (customer_id, week)) INTO NAME metric VALUE value);

-- baseline = median of the 6 previous weeks; spread = MAD (floored so tiny spreads do not create alerts)
CREATE OR REPLACE TABLE out_monitoring AS
WITH b AS (
    SELECT *, median(value) OVER w AS baseline, mad(value) OVER w AS spread, COUNT(value) OVER w AS n_prev
    FROM kpi_long WINDOW w AS (PARTITION BY customer_id, metric ORDER BY week ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING)
)
SELECT customer_id, week, metric, ROUND(value, 5) AS value, ROUND(baseline, 5) AS baseline,
       ROUND((value - baseline) / greatest(1.4826 * spread, 0.02 * abs(baseline), 1e-4), 2) AS robust_z,
       ROUND(value / NULLIF(baseline, 0) - 1, 3) AS rel_change
FROM b WHERE n_prev >= 3;

-- flags: only moves in the RISKY direction count, with a minimum size per metric (rare-event rates need a bigger move)
CREATE OR REPLACE TABLE metric_rules AS SELECT * FROM (VALUES
    ('logins', 1, 0.25), ('signups', 1, 0.25), ('failure_rate', 1, 0.20), ('deny_rate', 1, 0.30),
    ('challenge_rate', 1, 0.30), ('challenge_pass_rate', -1, 0.20), ('devices_per_login', -1, 0.20),
    ('update_after_login_rate', 1, 0.50), ('disposable_share', 1, 0.50), ('prepaid_share', 1, 0.50),
    ('devices_per_signup', -1, 0.20), ('trial_conversion', -1, 0.30), ('empty_device_share', 1, NULL))
    t(metric, direction, min_rel);

CREATE OR REPLACE TABLE flags AS
SELECT m.* FROM out_monitoring m JOIN metric_rules r USING (metric)
WHERE r.direction * m.robust_z >= 4
  AND (CASE WHEN r.min_rel IS NULL THEN m.value - m.baseline >= 0.02          -- collection metric: +2 points absolute
            ELSE r.direction * m.rel_change >= r.min_rel END);

-- triage, one row per customer x week:
--   data quality  -> a collection metric moved (empty device hash): fix the data before reading the KPIs;
--   explained     -> only volume moved, quality metrics are normal, and the customer declared a campaign that week;
--   alert         -> anything else.
CREATE OR REPLACE TABLE out_alerts AS
WITH f AS (
    SELECT customer_id, week,
           string_agg(metric || ' ' || CASE WHEN rel_change IS NULL
                                              THEN '+' || CAST(ROUND(100 * (value - baseline)) AS INT) || ' pts'
                                              ELSE CASE WHEN rel_change > 0 THEN '+' ELSE '' END || CAST(ROUND(100 * rel_change) AS INT) || '%' END, ', '
                      ORDER BY abs(robust_z) DESC) AS moved,
           bool_and(metric IN ('logins', 'signups')) AS volume_only,
           bool_or(metric = 'empty_device_share') AS data_metric
    FROM flags GROUP BY ALL
)
SELECT f.customer_id, f.week, f.moved,
       CASE WHEN f.data_metric THEN 'data quality'
            WHEN f.volume_only AND c.campaign IS NOT NULL THEN 'explained by the customer''s campaign'
            WHEN r.rule_id IS NOT NULL AND f.moved LIKE 'challenge%' THEN 'expected after rule ' || r.rule_id || ' (review its effect)'
            ELSE 'alert' END AS status,
       c.campaign
FROM f LEFT JOIN calendar c
  ON c.customer_id = f.customer_id AND c.start_date::DATE <= f.week + 6 AND c.end_date::DATE >= f.week
LEFT JOIN 'data/sim/rule_changes.parquet' r
  ON r.scope = f.customer_id AND r.date::DATE <= f.week + 6 AND r.date::DATE >= f.week - 21
ORDER BY f.week, f.customer_id;

-- weekly KPI table for the dashboard (simulated)
CREATE OR REPLACE TABLE out_kpi_weekly AS
SELECT l.*, s.signups, s.disposable_share, s.prepaid_share, s.devices_per_signup, s.trial_conversion
FROM kpi_login l FULL JOIN kpi_signup s USING (customer_id, week) ORDER BY customer_id, week;
