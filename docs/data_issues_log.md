# Data issues log

Same structure as a production issue log: what was found, the evidence, the decision, and the status. PUBLIC DATA issues concern
the downloaded datasets; SIMULATED issues are part of the exercise (they were planted and then found by the checks).

| ID | Source | Field | Dimension | Severity | What we found | Evidence | Decision | Status |
|---|---|---|---|---|---|---|---|---|
| I01 | RBA (PUBLIC DATA) | whole file | completeness | info | The file has 31,269,264 rows and 4,304,857 distinct users; the dataset notice speaks of more than 33 M attempts and 3.3 M users | `out_rba_calibration` | Report what the file contains, quote the notice as stated | Accepted - documented |
| I02 | RBA (PUBLIC DATA) | Is Account Takeover | completeness | high | No takeover label at all from Dec 2020 to Feb 2021 (16, 14, 8 in Sep, Oct, Nov 2020; then 0) | `out_rba_test_labels` | Test period limited to Sep-Nov 2020 | Fixed in `03_rba_rule_eval.sql` |
| I03 | RBA (PUBLIC DATA) | IP Address | privacy / validity | high | Addresses are artificial (some private ranges) | dataset notice | Hashed at ingestion (salted SHA-256, 12 characters); never geolocated, never matched with real lists | Fixed in `ingest_rba.py` |
| I04 | RBA (PUBLIC DATA) | User ID | privacy | high | Original 64-bit IDs | dataset columns | Replaced by a dense key at ingestion; original never leaves the step | Fixed in `ingest_rba.py` |
| I05 | RBA (PUBLIC DATA) | Round-Trip Time [ms] | completeness | low | Often empty | dataset notice | Not used | Accepted |
| I06 | RBA (PUBLIC DATA) | Login Successful | validity | info | Success rate is 41.7 % even for non-attack IPs (synthesized values) | `out_rba_success_by_attack` | Reused as is for calibration, said in the assumptions | Accepted - documented |
| I07 | Web robots (PUBLIC DATA) | STANDARD_DEVIATION, SF_* | completeness | medium | 14,407 sessions (single request) have no value; 8,776 have no page-similarity value | `ingest_webrobots.py` check | Filled with 0 ("no gap / no content seen") before modelling | Accepted - documented |
| I08 | Web robots (PUBLIC DATA) | ROBOT | validity | medium | Labelling method not described in the notice | dataset notice | Called "as labelled by the dataset"; no claim of perfect truth | Accepted - documented |
| I09 | Web robots (PUBLIC DATA) | time, IP | completeness | medium | No timestamp or IP in the feature files | file columns | Cross-validation instead of a time split | Accepted - limit |
| I10 | Platform (SIMULATED) | event_id | uniqueness | high | SDK 4.2 of C07 (12 Oct) sends 23.1 % of its events twice (network retries) | `out_sdk_quality` | Deduplicate by event_id before any KPI | Fixed in `10_sim_clean.sql` |
| I11 | Platform (SIMULATED) | device_hash | completeness | high | 37.8 % of SDK 4.2 events have no device hash | `out_sdk_quality` | Flag the customer as "data quality"; device signals are silent there | Open - customer to update SDK |
| I12 | Platform (SIMULATED) | deny rate | consistency | medium | Raw deny rate of C07 fell from 8.2 % to about 7 % because of the duplicates, not because the protection weakened | `out_e5_dedup_effect` | Answer ticket T08 with the clean rate | Fixed |
| I13 | Platform (SIMULATED) | accounts snapshot | leakage | high | The account table extracted on 23 Nov marks taken-over accounts as locked: a model using it reaches AUC 0.998 | `out_e7_auc` | Excluded; only signals known at login time, time split | Fixed in `14_sim_leakage.sql` |
| I14 | Platform (SIMULATED) | reported_fraud_date | timeliness | medium | Reports arrive 7 to 30 days after the takeover; fakes flagged 10 to 40 days after sign-up | simulation rules | Recall measured only on periods whose reports have arrived | Accepted - limit |
| I15 | Platform (SIMULATED) | traffic_daily | consistency | info | Login and sign-up rows of traffic_daily equal the raw event counts; verified_bot rows equal the crawler sessions | tests Q02-Q04 | - | Checked |
