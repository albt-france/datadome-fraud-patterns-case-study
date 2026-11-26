-- 03_rba_rule_eval.sql : simple account-takeover rules evaluated with a TIME SPLIT.
-- Train = Feb-Aug 2020 (thresholds are chosen there), Test = Sep-Nov 2020 (thresholds are frozen).
-- Dec 2020 - Feb 2021 carry no ATO label at all (checked in out_rba_test_labels): they are left out of the scores.
-- Scope: successful logins (the moment where a takeover happens). Label: Is Account Takeover (very rare).
CREATE OR REPLACE TABLE rba_eval AS
SELECT CASE WHEN ts < TIMESTAMP '2020-09-01' THEN 'train'
            WHEN ts < TIMESTAMP '2020-12-01' THEN 'test'      -- the dataset has no ATO label after Nov 2020
            ELSE 'no_label' END AS period,
       ts::DATE AS day, ts, is_ato, new_country, new_browser, new_device_type, ip_fail_1h, ip_logins_1h, is_attack_ip
FROM rba_feat WHERE login_success;

-- Candidate thresholds for the two count signals, tuned on TRAIN only (best F1)
CREATE OR REPLACE TABLE rba_thr AS
WITH grid AS (SELECT unnest([1, 2, 3, 5, 10, 20]) AS k),
cand AS (
    SELECT 'ip_fail_1h' AS signal, k,
           SUM((ip_fail_1h >= k AND is_ato)::INT) AS tp, SUM((ip_fail_1h >= k AND NOT is_ato)::INT) AS fp,
           SUM((ip_fail_1h < k AND is_ato)::INT) AS fn
    FROM rba_eval, grid WHERE period = 'train' GROUP BY k
    UNION ALL
    SELECT 'ip_logins_1h', k,
           SUM((ip_logins_1h >= k AND is_ato)::INT), SUM((ip_logins_1h >= k AND NOT is_ato)::INT),
           SUM((ip_logins_1h < k AND is_ato)::INT)
    FROM rba_eval, grid WHERE period = 'train' GROUP BY k
)
SELECT signal, k FROM (
    SELECT *, row_number() OVER (PARTITION BY signal ORDER BY 2.0 * tp / NULLIF(2 * tp + fp + fn, 0) DESC NULLS LAST, k) AS r
    FROM cand) WHERE r = 1;

-- Weights for a ranking score, learned on TRAIN only: log-likelihood ratio of each signal (naive Bayes, +1 smoothing)
CREATE OR REPLACE TABLE rba_w AS
WITH s AS (
    SELECT 'new_country' AS signal, new_country AS v, is_ato FROM rba_eval WHERE period = 'train'
    UNION ALL SELECT 'new_browser', new_browser, is_ato FROM rba_eval WHERE period = 'train'
    UNION ALL SELECT 'new_device_type', new_device_type, is_ato FROM rba_eval WHERE period = 'train'
    UNION ALL SELECT 'attack_ip', is_attack_ip, is_ato FROM rba_eval WHERE period = 'train'
)
SELECT signal,
       ln(((SUM((v AND is_ato)::INT) + 1.0) / (SUM(is_ato::INT) + 2.0))
          / ((SUM((v AND NOT is_ato)::INT) + 1.0) / (SUM((NOT is_ato)::INT) + 2.0)))           AS w_present,
       ln(((SUM((NOT v AND is_ato)::INT) + 1.0) / (SUM(is_ato::INT) + 2.0))
          / ((SUM((NOT v AND NOT is_ato)::INT) + 1.0) / (SUM((NOT is_ato)::INT) + 2.0)))       AS w_absent
FROM s GROUP BY signal;

-- Rules as 0/1 flags (thresholds come from rba_thr) and the ranking score
CREATE OR REPLACE TABLE rba_flags AS
WITH w AS (PIVOT rba_w ON signal USING first(w_present) AS p, first(w_absent) AS a)
SELECT e.period, e.day, e.ts, e.is_ato,
       e.new_country                                                                  AS r1_new_country,
       e.new_browser                                                                  AS r2_new_browser,
       e.ip_fail_1h   >= (SELECT k FROM rba_thr WHERE signal = 'ip_fail_1h')          AS r3_ip_failures,
       e.ip_logins_1h >= (SELECT k FROM rba_thr WHERE signal = 'ip_logins_1h')        AS r4_ip_velocity,
       e.new_country AND e.new_browser                                                AS r5_country_and_browser,
       e.is_attack_ip                                                                 AS r6_ip_reputation,
       CASE WHEN e.new_country THEN w.new_country_p ELSE w.new_country_a END
     + CASE WHEN e.new_browser THEN w.new_browser_p ELSE w.new_browser_a END
     + CASE WHEN e.new_device_type THEN w.new_device_type_p ELSE w.new_device_type_a END
     + CASE WHEN e.is_attack_ip THEN w.attack_ip_p ELSE w.attack_ip_a END             AS score
FROM rba_eval e, w;

CREATE OR REPLACE TABLE out_rba_rules AS
WITH long AS (
    SELECT period, day, is_ato, 'R1 new country for the user' AS rule, r1_new_country AS hit FROM rba_flags
    UNION ALL SELECT period, day, is_ato, 'R2 new browser version for the user', r2_new_browser FROM rba_flags
    UNION ALL SELECT period, day, is_ato, 'R3 failed logins from the IP (1 h)', r3_ip_failures FROM rba_flags
    UNION ALL SELECT period, day, is_ato, 'R4 logins from the IP (1 h)', r4_ip_velocity FROM rba_flags
    UNION ALL SELECT period, day, is_ato, 'R5 new country AND new browser', r5_country_and_browser FROM rba_flags
    UNION ALL SELECT period, day, is_ato, 'R6 IP on the attack-IP list', r6_ip_reputation FROM rba_flags
)
SELECT rule, period,
       SUM((hit AND is_ato)::INT)                                         AS tp,
       SUM((hit AND NOT is_ato)::INT)                                     AS fp,
       SUM((NOT hit AND is_ato)::INT)                                     AS fn,
       ROUND(SUM((hit AND is_ato)::INT) / NULLIF(SUM(hit::INT), 0), 5)    AS precision,
       ROUND(SUM((hit AND is_ato)::INT) / NULLIF(SUM(is_ato::INT), 0), 3) AS recall,
       ROUND(SUM(hit::INT) / COUNT(DISTINCT day), 0)                      AS alerts_per_day,
       ROUND(SUM((hit AND NOT is_ato)::INT) / NULLIF(SUM((hit AND is_ato)::INT), 0), 0) AS false_alerts_per_ato
FROM long WHERE period <> 'no_label' GROUP BY rule, period ORDER BY rule, period DESC;

-- Precision at rank k on the labelled TEST months (Sep-Nov 2020: the dataset has no ATO label after Nov 2020).
-- Logins are ranked by the train-learned score; ties are broken by a hash of the timestamp (no hidden order).
CREATE OR REPLACE TABLE out_rba_topk AS
WITH ranked AS (
    SELECT is_ato, row_number() OVER (ORDER BY score DESC, hash(ts)) AS rk
    FROM rba_flags WHERE period = 'test' AND day < DATE '2020-12-01'
)
SELECT k, SUM((rk <= k AND is_ato)::INT) AS ato_in_top_k, ROUND(SUM((rk <= k AND is_ato)::INT) / k, 4) AS precision_at_k,
       (SELECT SUM(is_ato::INT) FROM ranked) AS ato_in_test,
       (SELECT COUNT(*) FROM ranked) AS logins_in_test,
       ROUND(k / (SELECT COUNT(*) FROM ranked), 6) AS share_reviewed
FROM ranked, (SELECT unnest([100, 1000, 10000, 100000]) AS k) GROUP BY k ORDER BY k;

CREATE OR REPLACE TABLE out_rba_thresholds AS SELECT * FROM rba_thr ORDER BY signal;
CREATE OR REPLACE TABLE out_rba_weights AS SELECT signal, ROUND(w_present, 3) AS w_present, ROUND(w_absent, 3) AS w_absent FROM rba_w ORDER BY signal;
-- ATO labels by month in the test period (shows where labels stop)
CREATE OR REPLACE TABLE out_rba_test_labels AS
SELECT date_trunc('month', day)::DATE AS month, COUNT(*) AS successful_logins, SUM(is_ato::INT) AS ato
FROM rba_flags WHERE period <> 'train' GROUP BY 1 ORDER BY 1;
