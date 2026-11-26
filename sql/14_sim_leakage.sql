-- 14_sim_leakage.sql : E7. "Detection quality" model for account takeover on successful logins (SIMULATED).
-- Trap: the account table extracted on 23 Nov says 'locked' for accounts locked AFTER a fraud report -> near-perfect AUC,
-- but that information does not exist at login time. Fix: signals known at login time + a time split
-- (weights learned on 31 Aug - 11 Oct, scored on 12 Oct - 22 Nov). Model C adds the proposed device-cluster signal S1.
CREATE OR REPLACE TABLE e7 AS
WITH f AS (
    SELECT l.ts_utc, l.customer_id, l.account_key, l.login_success, l.ip_type,
           l.reported_fraud_date IS NOT NULL AS label,
           -- existing signals, as of the login (past only)
           row_number() OVER (PARTITION BY l.account_key, l.device_hash ORDER BY l.ts_utc) = 1          AS new_device_for_account,
           SUM((NOT l.login_success)::INT) OVER (PARTITION BY l.ip_hash ORDER BY l.ts_utc
                          RANGE BETWEEN INTERVAL 1 HOUR PRECEDING AND CURRENT ROW)                     AS ip_failures_1h,
           -- proposed signal S1: the same device hash is very busy / failing across many accounts
           COUNT(*) OVER (PARTITION BY l.device_hash ORDER BY l.ts_utc
                          RANGE BETWEEN INTERVAL 24 HOUR PRECEDING AND CURRENT ROW) - 1                AS device_attempts_24h,
           SUM((NOT l.login_success)::INT) OVER (PARTITION BY l.device_hash ORDER BY l.ts_utc
                          RANGE BETWEEN INTERVAL 1 HOUR PRECEDING AND CURRENT ROW)                     AS device_failures_1h
    FROM logins l WHERE l.device_hash IS NOT NULL
)
SELECT f.*, s.status = 'locked' AS locked_in_snapshot,
       CASE WHEN ts_utc < TIMESTAMP '2026-10-12' THEN 'train' ELSE 'test' END AS period
FROM f LEFT JOIN snapshot s USING (customer_id, account_key)
WHERE f.login_success;

CREATE OR REPLACE TABLE e7_feat AS
SELECT period, label, COALESCE(locked_in_snapshot, FALSE) AS leak,
       new_device_for_account AS s_new_device, ip_type IN ('datacenter', 'tor', 'vpn') AS s_risky_ip,
       ip_failures_1h >= 5 AS s_ip_failures,
       device_attempts_24h >= 50 OR device_failures_1h >= 5 AS s1_device_cluster
FROM e7;

-- weights learned on TRAIN only (log-likelihood ratios, +1 smoothing), like the RBA score
CREATE OR REPLACE TABLE e7_w AS
WITH s AS (
    SELECT 's_new_device' AS signal, s_new_device AS v, label FROM e7_feat WHERE period = 'train'
    UNION ALL SELECT 's_risky_ip', s_risky_ip, label FROM e7_feat WHERE period = 'train'
    UNION ALL SELECT 's_ip_failures', s_ip_failures, label FROM e7_feat WHERE period = 'train'
    UNION ALL SELECT 's1_device_cluster', s1_device_cluster, label FROM e7_feat WHERE period = 'train'
)
SELECT signal,
       ln(((SUM((v AND label)::INT) + 1.0) / (SUM(label::INT) + 2.0)) / ((SUM((v AND NOT label)::INT) + 1.0) / (SUM((NOT label)::INT) + 2.0))) AS wp,
       ln(((SUM((NOT v AND label)::INT) + 1.0) / (SUM(label::INT) + 2.0)) / ((SUM((NOT v AND NOT label)::INT) + 1.0) / (SUM((NOT label)::INT) + 2.0))) AS wa
FROM s GROUP BY 1;

CREATE OR REPLACE TABLE e7_scored AS
WITH w AS (PIVOT e7_w ON signal USING first(wp) AS p, first(wa) AS a),
b AS (
    SELECT f.period, f.label, f.leak::INT AS score_leaky,
           CASE WHEN s_new_device THEN w.s_new_device_p ELSE w.s_new_device_a END
         + CASE WHEN s_risky_ip THEN w.s_risky_ip_p ELSE w.s_risky_ip_a END
         + CASE WHEN s_ip_failures THEN w.s_ip_failures_p ELSE w.s_ip_failures_a END AS sb,
           CASE WHEN s1_device_cluster THEN w.s1_device_cluster_p ELSE w.s1_device_cluster_a END AS s1
    FROM e7_feat f, w
)
SELECT period, label, score_leaky, ROUND(sb, 6) AS score_existing, ROUND(sb + s1, 6) AS score_with_s1 FROM b;

-- AUC = P(score of a takeover > score of a normal login) + 0.5 P(tie), computed exactly on grouped scores.
-- Operating point: alert when the score is above 0 (the signals make a takeover MORE likely than not having them),
-- or, for the leaky model, when the account is locked. Precision, recall and alerts per day at that point.
CREATE OR REPLACE MACRO auc_of(col, thr, per) AS TABLE
WITH g AS (SELECT col AS s, SUM(label::INT) AS pos, SUM((NOT label)::INT) AS neg
           FROM e7_scored WHERE per = 'all' OR period = per GROUP BY 1),
     c AS (SELECT *, COALESCE(SUM(neg) OVER (ORDER BY s ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0) AS neg_below FROM g)
SELECT ROUND(SUM(pos * (neg_below + 0.5 * neg)) / (SUM(pos) * SUM(neg)), 3)              AS auc,
       ROUND(SUM(pos) FILTER (s > thr) / NULLIF(SUM(pos + neg) FILTER (s > thr), 0), 4)   AS precision_at_alert,
       ROUND(SUM(pos) FILTER (s > thr) / SUM(pos), 3)                                     AS recall_at_alert,
       ROUND(SUM(pos + neg) FILTER (s > thr) / CASE WHEN per = 'all' THEN 84 ELSE 42 END, 0) AS alerts_per_day,
       SUM(pos) AS positives, SUM(neg) AS negatives
FROM c;

CREATE OR REPLACE TABLE out_e7_auc AS
SELECT 'A leaky: account locked in the 23 Nov snapshot' AS model, 'all rows (no split)' AS evaluated_on, * FROM auc_of(score_leaky, 0.5, 'all')
UNION ALL SELECT 'B existing signals, as of login', 'test (12 Oct - 22 Nov)', * FROM auc_of(score_existing, 0, 'test')
UNION ALL SELECT 'C existing + S1 device cluster, as of login', 'test (12 Oct - 22 Nov)', * FROM auc_of(score_with_s1, 0, 'test');

CREATE OR REPLACE TABLE out_e7_weights AS SELECT signal, ROUND(wp, 3) AS w_present, ROUND(wa, 3) AS w_absent FROM e7_w ORDER BY signal;
