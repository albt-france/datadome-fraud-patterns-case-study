-- 01_rba_profile.sql : profile of the RBA login dataset (PUBLIC DATA, synthesized from real logins, Feb 2020 - Feb 2021).
-- Input: data/raw/rba.parquet (built by src/ingest_rba.py: no IP address, no original User ID).
CREATE OR REPLACE VIEW rba AS SELECT * FROM 'data/raw/rba.parquet';

-- Volumes by month: logins, users, share of logins from attack IPs, account takeovers, success rate
CREATE OR REPLACE TABLE out_rba_monthly AS
SELECT date_trunc('month', ts)::DATE                     AS month,
       COUNT(*)                                          AS logins,
       COUNT(DISTINCT user_key)                          AS users,
       ROUND(AVG(is_attack_ip::INT), 4)                  AS attack_ip_share,
       SUM(is_ato::INT)                                  AS ato_logins,
       ROUND(AVG(login_success::INT), 4)                 AS success_rate
FROM rba GROUP BY 1 ORDER BY 1;

-- Success rate of a login depending on whether it comes from a known attack IP
CREATE OR REPLACE TABLE out_rba_success_by_attack AS
SELECT is_attack_ip, COUNT(*) AS logins, ROUND(AVG(login_success::INT), 4) AS success_rate,
       SUM(is_ato::INT) AS ato_logins
FROM rba GROUP BY 1 ORDER BY 1;

-- Concentration of attack logins by ASN (top 10): ASNs are public network numbers, not people
CREATE OR REPLACE TABLE out_rba_asn_top AS
WITH a AS (SELECT asn, COUNT(*) AS attack_logins FROM rba WHERE is_attack_ip GROUP BY 1)
SELECT asn, attack_logins,
       ROUND(attack_logins / SUM(attack_logins) OVER (), 4)                                   AS share,
       ROUND(SUM(attack_logins) OVER (ORDER BY attack_logins DESC) / SUM(attack_logins) OVER (), 4) AS cum_share
FROM a ORDER BY attack_logins DESC LIMIT 10;

-- Device mix, overall and for attack IPs
CREATE OR REPLACE TABLE out_rba_devices AS
SELECT device_type, COUNT(*) AS logins, ROUND(COUNT(*) / SUM(COUNT(*)) OVER (), 4) AS share,
       ROUND(AVG(is_attack_ip::INT), 4) AS attack_ip_share
FROM rba GROUP BY 1 ORDER BY logins DESC;

-- Account takeover logins: how many, how many users, and what their first features look like
CREATE OR REPLACE TABLE out_rba_ato_profile AS
SELECT COUNT(*) AS ato_logins, COUNT(DISTINCT user_key) AS ato_users,
       ROUND(AVG(is_attack_ip::INT), 4) AS from_attack_ip_share,
       ROUND(AVG(login_success::INT), 4) AS success_rate
FROM rba WHERE is_ato;

-- One-row calibration table, re-used by src/simulate_platform.py
CREATE OR REPLACE TABLE out_rba_calibration AS
SELECT (SELECT COUNT(*) FROM rba)                                                   AS logins,
       (SELECT COUNT(DISTINCT user_key) FROM rba)                                   AS users,
       (SELECT MIN(ts)::DATE FROM rba)                                              AS first_day,
       (SELECT MAX(ts)::DATE FROM rba)                                              AS last_day,
       (SELECT ROUND(AVG(login_success::INT), 4) FROM rba WHERE NOT is_attack_ip)   AS human_success_rate,
       (SELECT ROUND(AVG(login_success::INT), 4) FROM rba WHERE is_attack_ip)       AS attack_success_rate,
       (SELECT ROUND(AVG(is_attack_ip::INT), 4) FROM rba)                           AS attack_ip_share,
       (SELECT MAX(cum_share) FROM out_rba_asn_top)                                 AS top10_asn_share_of_attacks,
       (SELECT SUM(is_ato::INT) FROM rba)                                           AS ato_logins,
       (SELECT ROUND(1e6 * AVG(is_ato::INT), 2) FROM rba)                           AS ato_per_million;
