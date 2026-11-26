-- 13_sim_simpson.sql : E6. After rule R12 (C04, 2 Nov 2026) the TOTAL challenge pass rate goes up,
-- yet it goes DOWN in each channel: the mix of challenges moved to the app, where users pass more often.
CREATE OR REPLACE TABLE out_e6_simpson AS
WITH c AS (
    SELECT CASE WHEN ts_utc < TIMESTAMP '2026-11-02' THEN '1 before R12 (5-25 Oct)' ELSE '2 after R12 (2-22 Nov)' END AS period,
           channel, challenge_passed
    FROM logins
    WHERE customer_id = 'C04' AND challenge_shown
      AND (ts_utc >= TIMESTAMP '2026-11-02' OR ts_utc BETWEEN TIMESTAMP '2026-10-05' AND TIMESTAMP '2026-10-26')
)
SELECT period, channel, COUNT(*) AS challenges, ROUND(AVG(challenge_passed::INT), 4) AS pass_rate,
       ROUND(COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY period), 4) AS share_of_challenges
FROM c GROUP BY GROUPING SETS ((period, channel), (period))
ORDER BY period, channel NULLS FIRST;

UPDATE out_e6_simpson SET channel = 'total' WHERE channel IS NULL;
