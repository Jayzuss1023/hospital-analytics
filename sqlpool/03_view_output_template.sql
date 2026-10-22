-- View output template
-- Sample rows only. These are not live Synapse results.
-- Clock for "currently admitted": 2026-10-22 16:00.
-- A visit is currently admitted when discharge_time is still in the future.
--
-- Gold keeps one fact row per patient: the latest admission.
-- The fact table is overwritten on every gold run, so these views
-- describe that snapshot, not every visit the hospital has ever had.
--
-- The shapes below match the view definitions in sqlpool/text.
-- sqlpool/02_pool_queries.sql has syntax errors and will not return these grids until those are fixed.


-- ============================================================
-- Source tables
-- ============================================================

-- dbo.dim_patient
-- One row per version of a patient (SCD Type 2).
-- Views join on surrogate_key. They do not filter is_current.
-- The closed row below is history only. No fact points at it, so it does not change any view.
--
-- surrogate_key | patient_id | gender | age | effective_from      | effective_to        | is_current
-- 100           | P-1002     | Male   | 66  | 2026-09-01 00:00:00 | 2026-10-20 01:00:00 | 0
-- 101           | P-1001     | Female | 34  | 2026-10-20 01:00:00 | NULL                | 1
-- 102           | P-1002     | Male   | 67  | 2026-10-20 01:00:00 | NULL                | 1
-- 103           | P-1003     | Female | 52  | 2026-10-20 01:00:00 | NULL                | 1
-- 104           | P-1004     | Male   | 41  | 2026-10-20 01:00:00 | NULL                | 1
-- 105           | P-1005     | Female | 29  | 2026-10-20 01:00:00 | NULL                | 1
-- 106           | P-1006     | Male   | 73  | 2026-10-20 01:00:00 | NULL                | 1
-- 107           | P-1007     | Female | 31  | 2026-10-20 01:00:00 | NULL                | 1


-- dbo.dim_department
-- One row per department + hospital pair.
--
-- surrogate_key | department  | hospital_id
-- 1             | Emergency   | 1
-- 2             | ICU         | 1
-- 3             | Surgery     | 2
-- 4             | Cardiology  | 1
-- 5             | Maternity   | 3


-- dbo.fact_patient_flow
-- One row per patient visit in the current gold snapshot.
--
-- fact_id | patient_sk | department_sk | admission_time      | discharge_time      | admission_date | length_of_stay_hours | is_currently_admitted | bed_id
-- 1       | 101        | 1             | 2026-10-20 08:00:00 | 2026-10-21 02:00:00 | 2026-10-20     | 18                   | 0                     | 12
-- 2       | 102        | 2             | 2026-10-20 06:00:00 | 2026-10-23 06:00:00 | 2026-10-20     | 72                   | 1                     | 44
-- 3       | 103        | 2             | 2026-10-21 10:00:00 | 2026-10-23 22:00:00 | 2026-10-21     | 60                   | 1                     | 45
-- 4       | 104        | 3             | 2026-10-21 09:00:00 | 2026-10-22 15:00:00 | 2026-10-21     | 30                   | 0                     | 44
-- 5       | 105        | 4             | 2026-10-21 14:00:00 | 2026-10-23 06:00:00 | 2026-10-21     | 40                   | 1                     | 80
-- 6       | 106        | 1             | 2026-10-22 07:00:00 | 2026-10-24 14:00:00 | 2026-10-22     | 55                   | 1                     | 12
-- 7       | 107        | 5             | 2026-10-22 08:00:00 | 2026-10-22 12:00:00 | 2026-10-22     | 4                    | 0                     | 90
--
-- Reading the fact against the dimensions:
-- fact 1  Female  Emergency   bed 12  left already     18h
-- fact 2  Male    ICU         bed 44  still admitted   72h
-- fact 3  Female  ICU         bed 45  still admitted   60h
-- fact 4  Male    Surgery     bed 44  left already     30h   (same bed as fact 2)
-- fact 5  Female  Cardiology  bed 80  still admitted   40h
-- fact 6  Male    Emergency   bed 12  still admitted   55h   (same bed as fact 1)
-- fact 7  Female  Maternity   bed 90  left already      4h


-- ============================================================
-- vw_bed_occupancy
-- Responsible for: of the visits for each gender, what percent are still admitted.
-- Formula: admitted visit rows / all visit rows * 100, grouped by gender.
-- This is a visit rate, not a census of physical beds. COUNT(bed_id) counts rows.
-- A bed used twice is counted twice.
--
-- SELECT * FROM dbo.vw_bed_occupancy;
--
-- gender | bed_occupancy_percent
-- Female | 50.000000          -- 2 admitted (facts 3, 5) / 4 female visits
-- Male   | 66.666667          -- 2 admitted (facts 2, 6) / 3 male visits


-- ============================================================
-- vw_bed_turnover_rate
-- Responsible for: how many visits each gender put through each distinct bed.
-- Formula: COUNT(DISTINCT fact_id) / COUNT(DISTINCT bed_id), grouped by gender.
-- A rate above 1 means that gender reused at least one bed.
-- A bed used by both genders is counted in each gender's denominator.
--
-- SELECT * FROM dbo.vw_bed_turnover_rate;
--
-- gender | bed_turnover_rate
-- Female | 1.000000           -- 4 visits / beds 12, 45, 80, 90
-- Male   | 1.500000           -- 3 visits / beds 44 and 12


-- ============================================================
-- vw_patient_demographics
-- Responsible for: how many patients of each gender are in a bed right now.
-- It counts fact rows where is_currently_admitted = 1. Age is not used.
-- Discharged visits add nothing, so this is a current census by gender,
-- not a count of every patient on the fact table.
--
-- SELECT * FROM dbo.vw_patient_demographics;
--
-- gender | total_patients
-- Female | 2                  -- facts 3 and 5
-- Male   | 2                  -- facts 2 and 6


-- ============================================================
-- vw_avg_treatment_duration
-- Responsible for: average length of stay, in hours, for each department and gender.
-- Formula: AVG(length_of_stay_hours).
-- Includes stays that are still open. Gold computes hours from discharge_time
-- even when that discharge is in the future, so an in-progress stay still has a duration.
--
-- SELECT * FROM dbo.vw_avg_treatment_duration;
--
-- department  | gender | avg_treatment_duration
-- Cardiology  | Female | 40
-- Emergency   | Female | 18
-- Emergency   | Male   | 55
-- ICU         | Female | 60
-- ICU         | Male   | 72
-- Maternity   | Female | 4
-- Surgery     | Male   | 30


-- ============================================================
-- vw_patient_volume_trend
-- Responsible for: how many patients were admitted on each date, split by gender.
-- One row per admission_date + gender. patient_count is the number of fact rows.
-- Because gold keeps only each patient's latest admission, a patient who was
-- admitted on an earlier date and came back later appears only on the later date.
--
-- SELECT * FROM dbo.vw_patient_volume_trend;
--
-- admission_date | gender | patient_count
-- 2026-10-20     | Female | 1              -- fact 1
-- 2026-10-20     | Male   | 1              -- fact 2
-- 2026-10-21     | Female | 2              -- facts 3 and 5
-- 2026-10-21     | Male   | 1              -- fact 4
-- 2026-10-22     | Female | 1              -- fact 7
-- 2026-10-22     | Male   | 1              -- fact 6


-- ============================================================
-- vw_department_inflow
-- Responsible for: how many patients are in each department right now, split by gender.
-- Same admitted-only count as demographics, with department added.
-- A department + gender that has only discharged visits still appears, with patient_count = 0.
--
-- SELECT * FROM dbo.vw_department_inflow;
--
-- department  | gender | patient_count
-- Cardiology  | Female | 1              -- fact 5
-- Emergency   | Female | 0              -- fact 1 already left
-- Emergency   | Male   | 1              -- fact 6
-- ICU         | Female | 1              -- fact 3
-- ICU         | Male   | 1              -- fact 2
-- Maternity   | Female | 0              -- fact 7 already left
-- Surgery     | Male   | 0              -- fact 4 already left


-- ============================================================
-- vw_overstay_patients
-- Responsible for: how many visits ran longer than 50 hours, by department and gender.
-- The WHERE clause drops shorter stays, so a department with no overstay
-- does not appear at all (unlike department inflow, which keeps a 0).
--
-- SELECT * FROM dbo.vw_overstay_patients;
--
-- department | gender | overstay_count
-- Emergency  | Male   | 1               -- fact 6, 55 hours
-- ICU        | Female | 1               -- fact 3, 60 hours
-- ICU        | Male   | 1               -- fact 2, 72 hours
