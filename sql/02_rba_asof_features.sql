-- 02_rba_asof_features.sql : signals KNOWN AT LOGIN TIME (windows look at the past only, never at the future).
-- One row per login. A signal that uses information from after the login would leak (see 14_sim_leakage.sql).
CREATE OR REPLACE TABLE rba_feat AS
WITH base AS (
    SELECT ts, user_key, ip_hash, country, browser, device_type, login_success, is_attack_ip, is_ato
    FROM rba
)
SELECT ts, user_key, login_success, is_attack_ip, is_ato,
       -- how many earlier logins this user had (0 = first time we see the user: "new" flags make no sense then)
       row_number() OVER (PARTITION BY user_key ORDER BY ts) - 1                                  AS user_prior_logins,
       -- first time this user logs in from this country / with this browser version / this device type
       row_number() OVER (PARTITION BY user_key, country ORDER BY ts) = 1                         AS first_country,
       row_number() OVER (PARTITION BY user_key, browser ORDER BY ts) = 1                         AS first_browser,
       row_number() OVER (PARTITION BY user_key, device_type ORDER BY ts) = 1                     AS first_device_type,
       -- failed logins from the same hashed IP in the previous hour (current row excluded)
       COALESCE(SUM((NOT login_success)::INT) OVER (PARTITION BY ip_hash ORDER BY ts
                RANGE BETWEEN INTERVAL 1 HOUR PRECEDING AND CURRENT ROW), 0) - (NOT login_success)::INT AS ip_fail_1h,
       -- logins from the same hashed IP in the previous hour (current row excluded)
       COUNT(*) OVER (PARTITION BY ip_hash ORDER BY ts
                RANGE BETWEEN INTERVAL 1 HOUR PRECEDING AND CURRENT ROW) - 1                      AS ip_logins_1h
FROM base;

-- "new" only counts for users we already know (at least one earlier login)
CREATE OR REPLACE TABLE rba_feat AS
SELECT *, user_prior_logins > 0 AND first_country     AS new_country,
          user_prior_logins > 0 AND first_browser     AS new_browser,
          user_prior_logins > 0 AND first_device_type AS new_device_type
FROM rba_feat;

-- Share of ATO logins and of normal logins that carry each signal (successful logins only)
CREATE OR REPLACE TABLE out_rba_signal_rates AS
SELECT is_ato,
       COUNT(*)                                   AS logins,
       ROUND(AVG(new_country::INT), 4)            AS new_country,
       ROUND(AVG(new_browser::INT), 4)            AS new_browser,
       ROUND(AVG(new_device_type::INT), 4)        AS new_device_type,
       ROUND(AVG((ip_fail_1h >= 1)::INT), 4)      AS ip_fail_1h_ge1,
       ROUND(AVG((ip_logins_1h >= 5)::INT), 4)    AS ip_logins_1h_ge5,
       ROUND(AVG(is_attack_ip::INT), 4)           AS attack_ip
FROM rba_feat WHERE login_success GROUP BY 1 ORDER BY 1;
