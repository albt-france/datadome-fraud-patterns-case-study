-- 10_sim_clean.sql : load the SIMULATED platform tables and clean them (E5: SDK 4.2 duplicates and empty device hashes).
CREATE OR REPLACE VIEW login_raw AS
SELECT * FROM read_parquet('data/sim/login_events/*/*.parquet', hive_partitioning = true);
CREATE OR REPLACE VIEW signups AS SELECT * FROM 'data/sim/signup_events.parquet';
CREATE OR REPLACE VIEW crawlers AS SELECT * FROM 'data/sim/crawler_sessions.parquet';
CREATE OR REPLACE VIEW traffic AS SELECT * FROM 'data/sim/traffic_daily.parquet';
CREATE OR REPLACE VIEW snapshot AS SELECT * FROM 'data/sim/accounts_snapshot.parquet';
CREATE OR REPLACE VIEW calendar AS SELECT * FROM 'data/sim/customer_calendar.parquet';

-- Deduplicate: a network retry re-sends the same event_id; keep the first copy
CREATE OR REPLACE TABLE logins AS
SELECT * EXCLUDE (rn) FROM (
    SELECT *, row_number() OVER (PARTITION BY event_id ORDER BY ts_utc) AS rn FROM login_raw) WHERE rn = 1;

-- Data quality by SDK version: duplicate share and empty device hash share
CREATE OR REPLACE TABLE out_sdk_quality AS
SELECT customer_id, channel, sdk_version,
       COUNT(*)                                                    AS events_raw,
       COUNT(DISTINCT event_id)                                    AS events_unique,
       ROUND(1 - COUNT(DISTINCT event_id) / COUNT(*), 4)           AS duplicate_share,
       ROUND(AVG((device_hash IS NULL)::INT), 4)                   AS empty_device_share
FROM login_raw GROUP BY ALL HAVING COUNT(*) >= 1000 ORDER BY customer_id, channel, sdk_version;

-- E5 effect on C07: weekly deny rate and volume, raw (as received) versus deduplicated
CREATE OR REPLACE TABLE out_e5_dedup_effect AS
WITH r AS (SELECT date_trunc('week', ts_utc)::DATE AS week, COUNT(*) AS logins_raw,
                  ROUND(AVG((recommendation = 'deny')::INT), 4) AS deny_rate_raw,
                  ROUND(AVG((device_hash IS NULL)::INT), 4) AS empty_device_share
           FROM login_raw WHERE customer_id = 'C07' GROUP BY 1),
     d AS (SELECT date_trunc('week', ts_utc)::DATE AS week, COUNT(*) AS logins_clean,
                  ROUND(AVG((recommendation = 'deny')::INT), 4) AS deny_rate_clean
           FROM logins WHERE customer_id = 'C07' GROUP BY 1)
SELECT * FROM r JOIN d USING (week) ORDER BY week;
