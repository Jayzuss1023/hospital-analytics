-- Allow Azure Synapse SQL pool to query the gold tables that Databricks wrote into the data Lake
-- Databricks builds the data. This file makes them show as SQL tables inside Synapse
-- Files live in the storage account. Synapse can not see the filter until it's registered

-- ============================================================
-- BLOCK 1: Create a database
-- ============================================================
CREATE DATABASE hospital_gold;
GO

-- ============================================================
-- Switch to the new database
-- ============================================================
USE hospital_gold;
GO


-- CREATE MASTER KEY lets the SQL pool encrypt credentials it stores.
CREATE MASTER KEY ENCRYPTION BY PASSWORD = <<SECRETPASSWORD>'
GO

-- CREATINIG A SCOPE
-- storage_credential uses the Synapse workspace managed identity 
-- The workspace identity needs Storage Blob Data Reader (or Contributor) from the Storage Account
CREATE DATABASE SCOPED CREDENTIAL storage_credential
WITH IDENTITY = 'Managed Identity';
GO

-- -- BLOCK 5: Point at the gold container
CREATE EXTERNAL DATA SOURCE gold_data_source
WITH (
    LOCATION = 'abfss://<<CONTAINER>>@<<STORAGE_ACCOUNT>>.dfs.core.windows.net/',
    CREDENTIAL = storage_credential
);

-- DEFINE FORMAT
CREATE EXTERNAL FILE FORMAT DeltaFormat
WITH (
    FORMAT_TYPE = DELTA
)
GO

-- CREATE TABLES
-- PATIENT DIMENSION
CREATE EXTERNAL TABLE dbo.dim_patient (
    patient_id VARCHAR(50),
    gender VARCHAR(10),
    age INT,
    effective_from DATETIME2,
    surrogate_key BIGINT,
    effective_to DATETIME2,
    is_current BIT
)
WITH (
    LOCATION = 'dim_patient/',
    DATA_SOURCE = gold_data_source,
    FILE_FORMAT = ParquetFileFormat
);
GO

-- DEPARTMENT DIMENSION
CREATE EXTERNAL TABLE dbo.dim_department (
    surrogate_key BIGINT,
    department NVARCHAR(200),
    hospital_id INT
)
WITH (
    LOCATION = 'dim_department/',
    DATA_SOURCE = gold_data_source,
    FILE_FORMAT = ParquetFileFormat
);
GO

-- FACT TABLE
CREATE EXTERNAL TABLE dbo.fact_patient_flow (
    fact_id BIGINT,
    patient_sk BIGINT,
    department_sk BIGINT,
    admission_time DATETIME2,
    discharge_time DATETIME2,
    admission_date DATE,
    length_of_stay_hours FLOAT,
    is_currently_admitted BIT,
    bed_id INT,
    event_ingestion_time DATETIME2
)
WITH (
    LOCATION = 'fact_patient_flow',
    DATA_SOURCE = gold_data_source,
    FILE_FORMAT = ParquetFileFormat
);
GO

SELECT * FROM dbo.fact_patient_flow;