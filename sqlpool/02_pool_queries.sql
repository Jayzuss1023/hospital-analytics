CREATE OR ALTER VIEW dbo.vw_bed_occupany AS
SELECT p.gender,
    COUNT(CASE WHEN f.is_currently_admitted = 1 THEN f.bed_id END) * 1.0 / COUNT(f.bed_id) * 100 AS bed_occupancy_percent
FROM dbo.fact_patient_flow f
JOIN dbo.dim_patient p ON f.patient_sk = p.surrogate_key
GROUP BY p.gender;
GO

CREATE OR ALTER VIEW dbo.vw_bed_turnover_rate AS
SELECT p.gender,
    COUNT(DISTINCT f.fact_id) * 1.0 / COUNT(DISTINCT f.bed_id) AS bed_turnover_rate
FROM dbo.fact_patient_flow f
JOIN dbo.dim_patient p ON f.patient_sk = p.surrogate_key
GROUP BY
p.gender;
GO

CREATE OR ALTER VIEW dbo.vw_patient_demographics AS
SELECT p.gender,
       COUNT(CASE WHEN f.is_currently_admitted = 1 THEN f.fact_id END) AS total_patients
FROM dbo.fact_patient_flow f
JOIN dbo.dim_patient p ON f.patient_sk = p.surrogate_key
GROUP BY p.gender;
GO

CREATE OR ALTER VIEW dbo.vw_avg_treatment_duration AS
SELECT d.department, p.gender,
    AVG(length_of_stay_hours) AS avg_treatment_duration
FROM dbo.fact_patient_flow f
JOIN dbo.dim_patient p ON f.patient_sk = p.surrogate_key
JOIN dbo.dim_department d ON f.department_sk = d.surrogate_key
GROUP BY d.department, p.gender;
GO

CREATE OR ALTER VIEW dbo.vw_patient_volume_trend AS
SELECT f.admission_date, p.gender,
    COUNT(DISTINCT f.fact_id) AS patient_count
FROM dbo.fact_patient_flow f
JOIN dbo.dim_patient p ON f.patient_sk = p.surrogate_key
GROUP BY f.admission_date, p.gender;
GO

CREATE OR ALTER VIEW dbo.vw_department_inflow AS
SELECT d.department, p.gender,
    COUNT(CASE WHEN f.is_currently_admitted = 1 THEN f.fact_id END) AS patient_count
FROM dbo.fact_patient_flow f
JOIN dbo.dim_patient p ON p.surrogate_key = f.patient_sk
JOIN dbo.dim_department d ON d.surrogate_key = f.department_sk
GROUP BY d.department, p.gender;
GO

CREATE OR ALTER VIEW dbo.vw_overstay_patients AS
SELECT d.department, p.gender,
    COUNT(f.fact_id) AS overstay_count
FROM dbo.fact_patient_flow f
JOIN dbo.dim_patient p on f.patient_sk = p.surrogate_key
jOIN dbo.dim_department d on f.department_sk = d.surrogate_key
WHERE f.length_of_stay_hours > 50
GROUP BY d.department, p.gender;
GO

SELECT * FROM dbo.vw_bed_occupany;
SELECT * FROM dbo.vw_bed_turnover_rate;
SELECT * FROM dbo.vw_patient_demographics;
SELECT * FROM dbo.vw_avg_treatment_duration ORDER BY department, gender;
SELECT * FROM dbo.vw_patient_volume_trend ORDER BY admission_date;
SELECT * FROM dbo.vw_department_inflow ORDER BY patient_count DESC;
SELECT * FROM dbo.vw_overstay_patients ORDER BY overstay_count DESC;

SELECT DB_NAME();
SELECT name FROM sys.views;