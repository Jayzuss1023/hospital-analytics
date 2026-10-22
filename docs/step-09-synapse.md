# Step 9 (optional) — Query the gold tables with Azure Synapse

[← Guide](../README.md)

**Where:** Three places, in this order: Databricks website ([9A](#9a)) → Azure Portal ([9B](#9b)) → Synapse Studio ([9C](#9c) onward).

**In plain English:** "Let people who know SQL look at the gold tables and build reports, without touching Databricks."

Think of it like this:

- **The data lake** is a filing cabinet.
- **Databricks** puts the folders in.
- **Synapse** needs a label on each drawer before it knows what's inside.

We use the **serverless (Built-in)** SQL pool, not a dedicated pool.

|                         | Serverless (Built-in)                | Dedicated pool                  |
| ----------------------- | ------------------------------------ | ------------------------------- |
| Reads Delta tables?     | Yes                                  | **No**                          |
| Cost                    | Pay per query (pennies for our data) | Pay by the hour, even when idle |
| Start/stop needed?      | No                                   | Yes                             |
| Right for this project? | **Yes**                              | No — built for terabytes        |

> **Why not dedicated + Parquet?** Our gold folders hold files from every past Databricks run. Reading them as plain Parquet shows every old copy, so you get duplicate and out-of-date rows. Delta format reads only the current version.

<a id="9a"></a>

## 9A. Databricks side — make the gold tables readable by Synapse

**Where:** Databricks website → `03_gold_transform` → Cell 3 (or any SQL cell)

**Why:** Databricks turned on a feature called **deletion vectors** on the gold tables. It speeds up Databricks, but Synapse serverless can't read tables that use it. You'd see: `Feature 'Deletion Vectors' is not supported for table 'gold_data_source/dim_patient/'`.

This doesn't change your data. The gold notebook keeps working the same.

**1. Turn off deletion vectors:**

```sql
ALTER TABLE delta.`abfss://gold@hospitalstorage1023.dfs.core.windows.net/dim_patient` DROP FEATURE deletionVectors;
ALTER TABLE delta.`abfss://gold@hospitalstorage1023.dfs.core.windows.net/dim_department` DROP FEATURE deletionVectors;
ALTER TABLE delta.`abfss://gold@hospitalstorage1023.dfs.core.windows.net/fact_patient_flow` DROP FEATURE deletionVectors;
```

> **Watch out:** It must start with `ALTER TABLE`. Writing `DESCRIBE DETAIL ... DROP FEATURE` gives `PARSE_SYNTAX_ERROR`, because `DESCRIBE DETAIL` only reads.

**2. Check they're gone:**

```sql
DESCRIBE DETAIL delta.`abfss://gold@hospitalstorage1023.dfs.core.windows.net/dim_patient`;
```

Repeat for the other two. You want:

- `deletionVectors` **not** listed in `tableFeatures`
- `minReaderVersion` = **1**

(Seeing `checkpointProtection` in the list is normal and fine.)

**3. If `deletionVectors` is still there:** Databricks sometimes needs old history to expire. Wait **24 hours**, then re-run step 1 with `TRUNCATE HISTORY` added to the end of each line.

> `TRUNCATE HISTORY` removes old table versions (no more "time travel" to them). That's fine here because gold is rebuilt from silver on every run.

**4. Stop them from coming back:**

```sql
ALTER TABLE delta.`abfss://gold@hospitalstorage1023.dfs.core.windows.net/dim_patient` SET TBLPROPERTIES ('delta.enableDeletionVectors' = false);
ALTER TABLE delta.`abfss://gold@hospitalstorage1023.dfs.core.windows.net/dim_department` SET TBLPROPERTIES ('delta.enableDeletionVectors' = false);
ALTER TABLE delta.`abfss://gold@hospitalstorage1023.dfs.core.windows.net/fact_patient_flow` SET TBLPROPERTIES ('delta.enableDeletionVectors' = false);
```

<a id="9b"></a>

## 9B. Azure side — create the Synapse workspace and permissions

**1. Create the workspace**

**Where:** Azure Portal → search **Azure Synapse Analytics** → **+ Create**

**Basics tab:**

| Setting                                                | What to pick                                               | Why                                                      |
| ------------------------------------------------------ | ---------------------------------------------------------- | -------------------------------------------------------- |
| Resource group                                         | `hospital-analytics` (same as everything else)             | Keeps the project together                               |
| Workspace name                                         | Your choice (e.g. `hospital-synapse-ws`)                   | Becomes part of the web address                          |
| Region                                                 | **Same region as `hospitalstorage1023`**                   | Avoids slow, costly cross-region reads                   |
| Account name (Data Lake Storage Gen2)                  | **Select existing:** `hospitalstorage1023`                 | Synapse needs a "home" storage account                   |
| File system name                                       | Create new, e.g. `synapseworkspace` (lowercase, no spaces) | Synapse's own internal files. NOT where gold data lives. |
| "Assign myself the Storage Blob Data Contributor role" | Tick it                                                    | Lets you browse the lake from Synapse Studio             |

Click **Next: Security**.

**Security tab:**

| Setting                                                | What to pick                                    | Why                                                                                   |
| ------------------------------------------------------ | ----------------------------------------------- | ------------------------------------------------------------------------------------- |
| SQL Server admin login                                 | Keep the default (`sqladminuser`) or choose one | The "master login" for the workspace's SQL pools                                      |
| SQL Password                                           | A strong password                               | Save it in Key Vault (`hospitalvault`). This is NOT the master key password from [9C](#9c). |
| Allow network access to Data Lake Storage Gen2 account | Tick it if offered                              | Lets Synapse reach storage that has a firewall                                        |

Click **Review + create** → **Create**. Takes 2–3 minutes.

**Open Synapse Studio:** When it finishes, click **Go to resource group** → click your Synapse workspace → **Open Synapse Studio** (on the Overview page).

**2. Let Synapse read the gold data**

**Where:** Azure Portal → `hospitalstorage1023` → **Access control (IAM)** → **+ Add role assignment**

- Role: **Storage Blob Data Reader**
- Assign access to: **Managed identity** → **Synapse workspace** → pick yours
- Repeat with **User** → yourself, so you can query with your own login

> **Why Reader, not Contributor?** Synapse only reads gold. Databricks does the writing. Give the smallest permission needed. Roles can take 5–10 minutes to start working.

**3. (Optional) Key Vault access**

Only if Synapse will use secrets from Key Vault.

**Where:** Azure Portal → `hospitalvault` → **Access control (IAM)** → **Key Vault Secrets User** → **Managed identity** → **Synapse workspace**

**4. Storage firewall check**

**Where:** Azure Portal → `hospitalstorage1023` → **Networking**

- **"Enabled from all networks"** → you're fine.
- **"Enabled from selected networks"** → tick **"Allow Azure services on the trusted services list to access this storage account"**, or add a managed private endpoint (Synapse Studio → **Manage** → **Managed private endpoints**).

If you skip this, setup statements can hang for a very long time.

**5. (Optional, NOT needed for this project) Create a dedicated SQL pool**

A dedicated SQL pool is like renting your own data warehouse. The **Built-in** serverless pool already exists in every workspace, so you don't need one here.

**Where:** Synapse Studio → **Manage** (toolbox icon on the left) → **SQL pools** → **+ New**

- **Name:** your choice
- **Performance level:** the slider sets the size and the price. **DW100c** is the smallest.
- **Review + create** → **Create**

> **Warning:** A dedicated pool bills **every hour** it's running, even when idle. It also can't read Delta, and `CREATE DATABASE` fails on it (see [9E](#9e)). If you create one, pause it when you're done ([9F](#9f)).

<a id="9c"></a>

## 9C. Synapse side — register the gold tables

**Where:** Synapse Studio → **Develop** (code icon on the left) → **+** → **SQL script**

(Other way: refresh the page → **Data** (cylinder icon) → **Workspace** tab → **SQL database** → right-click your database → **New SQL script** → **Empty script**. `hospital_gold` only shows up here after Block 1 runs.)

**Before you run anything, check the toolbar above the script:**

- **Connect to:** **Built-in** (NOT your dedicated pool's name)
- **Use database:** `master` for Block 1 only. Then click the refresh icon and switch to `hospital_gold`.

> **Why a separate database?** `master` is the building's front desk. You can ask it a quick question, but you can't leave your filing cabinet there. Serverless won't let you create keys, credentials, data sources, formats, or external tables in `master`.

Highlight one block at a time and click **Run**.

```sql
-- BLOCK 1: Create your own database (run with "Use database" = master)
CREATE DATABASE hospital_gold;
GO

-- BLOCK 2: Switch to it (or just pick hospital_gold in the toolbar dropdown)
USE hospital_gold;
GO

-- BLOCK 3: Master key - protects saved credentials.
-- Replace <YOUR_STRONG_PASSWORD> (brackets too). Never commit the real one to GitHub.
CREATE MASTER KEY ENCRYPTION BY PASSWORD = '<YOUR_STRONG_PASSWORD>';
GO

-- BLOCK 4: Credential - Synapse logs into storage as its managed identity
-- (uses the Storage Blob Data Reader role from 9B)
CREATE DATABASE SCOPED CREDENTIAL storage_credential
WITH IDENTITY = 'Managed Identity';
GO

-- BLOCK 5: Address of the gold container (no TYPE = HADOOP - that's dedicated-only)
CREATE EXTERNAL DATA SOURCE gold_data_source
WITH (
    LOCATION = 'abfss://gold@hospitalstorage1023.dfs.core.windows.net/',
    CREDENTIAL = storage_credential
);
GO

-- BLOCK 6: The files are Delta, so read only the current version
CREATE EXTERNAL FILE FORMAT DeltaFormat
WITH (FORMAT_TYPE = DELTA);
GO

-- BLOCK 7: Three labels pointing at the three gold folders (no data copied)
CREATE EXTERNAL TABLE dbo.dim_patient (
    patient_id      VARCHAR(50),
    gender          VARCHAR(10),
    age             INT,
    effective_from  DATETIME2,
    surrogate_key   BIGINT,
    effective_to    DATETIME2,
    is_current      BIT
)
WITH (LOCATION = 'dim_patient/', DATA_SOURCE = gold_data_source, FILE_FORMAT = DeltaFormat);
GO

CREATE EXTERNAL TABLE dbo.dim_department (
    surrogate_key   BIGINT,
    department      NVARCHAR(200),
    hospital_id     INT
)
WITH (LOCATION = 'dim_department/', DATA_SOURCE = gold_data_source, FILE_FORMAT = DeltaFormat);
GO

CREATE EXTERNAL TABLE dbo.fact_patient_flow (
    fact_id                BIGINT,
    patient_sk             BIGINT,
    department_sk          BIGINT,
    admission_time         DATETIME2,
    discharge_time         DATETIME2,
    admission_date         DATE,
    length_of_stay_hours   FLOAT,
    is_currently_admitted  BIT,
    bed_id                 INT,
    event_ingestion_time   DATETIME2
)
WITH (LOCATION = 'fact_patient_flow/', DATA_SOURCE = gold_data_source, FILE_FORMAT = DeltaFormat);
GO

-- BLOCK 8: Test it
SELECT TOP 10 * FROM dbo.fact_patient_flow;
```

**What each block does:**

| Block | What it does                                    | Filing-cabinet analogy                                 |
| ----- | ----------------------------------------------- | ------------------------------------------------------ |
| 1     | Creates a database to hold your labels          | Getting your own office                                |
| 2     | Switches to that database                       | Walking into your office                               |
| 3     | Creates an encryption key                       | Putting a lock on the office door                      |
| 4     | Saves Synapse's identity                        | The ID badge Synapse shows the storage account         |
| 5     | Saves the gold container's address              | Writing the filing cabinet's address on a sticky note  |
| 6     | Says "these files are Delta"                    | Telling the office which filing system the folders use |
| 7     | Creates three labels for the three gold folders | Labeling the drawers: Patients, Departments, Visits    |
| 8     | Reads 10 rows                                   | Opening a drawer to check it works                     |

**Where does `dbo` come from?** You don't create it. Every new database comes with a built-in `dbo` schema ("database owner"). Since you created `hospital_gold`, you're its owner, so `dbo` is your default.

Only run Blocks 1–7 **once**. External tables see new Databricks data automatically. After that, just run SELECTs.

<a id="9d"></a>

## 9D. Build KPI views and look at the data

**Where:** Synapse Studio → same SQL script, **Built-in** + `hospital_gold`

A **view** is a saved query. Your KPI and chart views (bed occupancy, turnover, demographics, treatment duration, volume trend, department inflow, overstays) follow three rules in serverless:

1. Put **`GO`** after every view. `CREATE VIEW` must be alone in its batch.
2. Use **`CREATE OR ALTER VIEW dbo.vw_name AS ...`** so re-running doesn't fail.
3. **Never** put the database name in the view name (`hospital_gold.dbo.vw_name` is not allowed).

Example:

```sql
CREATE OR ALTER VIEW dbo.vw_bed_occupancy AS
SELECT p.gender,
       COUNT(CASE WHEN f.is_currently_admitted = 1 THEN f.bed_id END) * 1.0 / COUNT(f.bed_id) * 100 AS bed_occupancy_percent
FROM dbo.fact_patient_flow f
JOIN dbo.dim_patient p ON f.patient_sk = p.surrogate_key
GROUP BY p.gender;
GO
```

**Looking at the data:**

- Type it: `SELECT TOP 100 * FROM dbo.fact_patient_flow;` or `SELECT * FROM dbo.vw_bed_occupancy;`
- Or click it: Synapse Studio → **Data** (cylinder icon) → **Workspace** → **SQL database** → `hospital_gold` → **External tables** or **Views** → right-click → **New SQL script** → **Select TOP 100 rows**
- Switch the results from **Table** to **Chart** for a quick picture, or **Export** to CSV.
- List what exists: `SELECT SCHEMA_NAME(schema_id) AS schema_name, name FROM sys.views;`

<a id="9e"></a>

## 9E. Troubleshooting

| Error you see                                                                | What it really means                                                                             | Fix                                                                                                                                                             |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Incorrect syntax near 'hospital_gold'` (on CREATE DATABASE)                 | You're on the **dedicated** pool. It's already one database and doesn't know `CREATE DATABASE`.  | Toolbar → **Connect to: Built-in**                                                                                                                              |
| `Unknown file format type 'DELTA'`                                           | Same — dedicated pools can't read Delta.                                                         | Toolbar → **Connect to: Built-in**                                                                                                                              |
| `CREATE EXTERNAL DATA SOURCE` runs forever                                   | Synapse can't reach storage: firewall, or role not active yet.                                   | [9B](#9b) step 4 (firewall) and step 2 (role). Wait 5–10 min after adding roles.                                                                                |
| `Websocket connection was closed with code 1006`                             | Your browser lost its connection. Not a SQL error.                                               | Refresh Synapse Studio. Check **Monitor** → **SQL requests** to see if it finished. Use SSMS / Azure Data Studio for long queries.                              |
| `Feature 'Deletion Vectors' is not supported` / `unsupported reader version` | Gold tables still have deletion vectors.                                                         | Finish [9A](#9a). No need to recreate Synapse tables after.                                                                                                     |
| `... already exists`                                                         | That block already worked earlier.                                                               | Skip it, or check with `SELECT * FROM sys.external_tables;` (also `sys.external_data_sources`, `sys.external_file_formats`, `sys.database_scoped_credentials`)  |
| `'CREATE/ALTER VIEW' does not allow specifying the database name`            | View name has 3 parts (`hospital_gold.dbo.vw_x`).                                                | Use `dbo.vw_x`. The toolbar decides the database.                                                                                                               |
| `CREATE VIEW must be the only statement in the batch`                        | Missing `GO` between views.                                                                      | Add `GO` after each view.                                                                                                                                       |
| `Invalid object name 'dbo.vw_...'`                                           | View is in a different database or schema, or the name differs.                                  | Run `SELECT DB_NAME();` and the `sys.views` query from [9D](#9d). Re-run views with `hospital_gold` selected.                                                   |
| Query returns no rows                                                        | Gold is empty.                                                                                   | Run `03_gold_transform` in Databricks first.                                                                                                                    |
| Duplicate or old rows                                                        | You're reading Parquet instead of Delta.                                                         | Use `FORMAT_TYPE = DELTA` on **Built-in**.                                                                                                                      |
| "Potential conversion error" warnings on text columns                        | Delta text is UTF-8.                                                                             | Once: `ALTER DATABASE hospital_gold COLLATE Latin1_General_100_BIN2_UTF8;`                                                                                      |

<a id="9f"></a>

## 9F. Cleanup — the old dedicated pool

If you tried a dedicated pool first, its objects are separate and unused now.

**1. Drop the old objects** (toolbar → **Connect to:** your dedicated pool):

```sql
DROP EXTERNAL TABLE dbo.fact_patient_flow;
DROP EXTERNAL TABLE dbo.dim_department;
DROP EXTERNAL TABLE dbo.dim_patient;
DROP EXTERNAL FILE FORMAT ParquetFileFormat;
DROP EXTERNAL DATA SOURCE gold_data_source;
DROP DATABASE SCOPED CREDENTIAL storage_credential;
```

**2. Pause it to stop billing:**

**Where:** Synapse Studio → **Manage** (toolbox icon) → **SQL pools** → your pool → **Pause** (or Azure Portal → your Synapse workspace → **SQL pools** → **Pause**)

> Dedicated pools bill **every hour** they're running, used or not. Serverless bills only for data read.

<a id="9g"></a>

## 9G. Synapse permissions summary

| Who                        | Role                                                     | On what               | Where to set                                     | Why                                                                      |
| -------------------------- | -------------------------------------------------------- | --------------------- | ------------------------------------------------ | ------------------------------------------------------------------------ |
| Synapse workspace identity | **Storage Blob Data Reader**                             | `hospitalstorage1023` | Azure Portal → storage account → IAM             | Read gold data                                                           |
| You                        | **Storage Blob Data Reader**                             | `hospitalstorage1023` | Azure Portal → storage account → IAM             | Query with your own login                                                |
| Synapse workspace identity | **Key Vault Secrets User**                               | `hospitalvault`       | Azure Portal → Key Vault → IAM                   | Only if using Key Vault secrets                                          |
| You                        | **Synapse Administrator** (or Synapse SQL Administrator) | Synapse workspace     | Synapse Studio → **Manage** → **Access control** | Create databases and objects (workspace creator gets this automatically) |
| You                        | **Owner** or **Contributor**                             | Resource group        | Azure Portal → resource group → IAM              | Create the Synapse workspace                                             |

---

[← Step 8 — Azure Data Factory](step-08-azure-data-factory.md) · [Guide](../README.md) · [Quick start →](quick-start.md)
