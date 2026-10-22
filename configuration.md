# Hospital Analytics Pipeline — Guide

Plain-English setup for this project. No prior Azure or Databricks experience is required. Unfamiliar words are in the [Glossary](docs/glossary.md).

A hospital sends a message every time a patient is admitted (for example: "Patient 123, age 45, went to Cardiology at 9:00 AM"). This project **catches those messages, cleans them, and organizes them into tables** so someone can build reports like "How long do patients stay in each department?"

The work happens in three stages, called the **medallion architecture**:

| Stage      | Kitchen analogy                 | What happens to the data                                                           |
| ---------- | ------------------------------- | ---------------------------------------------------------------------------------- |
| **Bronze** | Groceries dumped on the counter | Raw messages saved exactly as they arrived. Nothing is changed.                    |
| **Silver** | Washed and chopped vegetables   | Messages are opened up, bad values are fixed, and everything gets proper columns. |
| **Gold**   | The finished meal on a plate    | Data is organized into report-ready tables (patients, departments, visits).        |

**How the pieces connect.** Azure Event Hub is the mailbox. Databricks notebooks move data bronze → silver → gold, and the files live in Azure Data Lake (`bronze`, `silver`, and `gold` containers). Passwords stay in Azure Key Vault. A Databricks Job runs the notebooks when new bronze files arrive. Azure Data Factory is an optional substitute for that job. Azure Synapse is an optional SQL layer on top of the gold tables. Azure Monitor can email you when an ADF run fails.

Do the steps in order. Steps 8 and 9 are optional. Pick **one** scheduler: the Databricks Job (Step 7) or Data Factory (Step 8). Using both processes the same data twice.

---

## Table of contents

### [Overview — the big picture and the tools](docs/00-overview.md)

What each Azure and Databricks service does in this project, and the four websites you will actually open: Azure Portal, the Databricks workspace, ADF Studio, and Synapse Studio.

### [Step 0 — Create your Azure accounts and resources](docs/step-00-azure-accounts-and-resources.md)

Create the subscription, the `hospital-analytics` resource group, and every resource in order: storage account `hospitalstorage1023` (hierarchical namespace on), `bronze` / `silver` / `gold` containers, Key Vault `hospitalvault` (RBAC), Event Hubs namespace `hospital-analytics-1023` (Standard tier or higher), Event Hub `hospital-analytics-eh`, Databricks workspace `hospital-analytics-databricks` (Premium), and Access Connector `hospital-databricks-access-connector`. Data Factory and Synapse are optional and created here only if you will use them.

Also covers who needs which Azure role (you, the access connector, the AzureDatabricks app, and the optional Data Factory and Synapse identities) and the Databricks permissions for storage credentials, external locations, the secret scope, and the job's **Run as** user. Event Hub uses a shared access policy instead of a role: **Listen** for Databricks, **Send** for whoever publishes the hospital messages.

### [Step 1 — Set up the storage](docs/step-01-storage.md)

Create storage account `hospitalstorage1023` and the three private containers. The notebooks create the subfolders themselves.

### [Step 2 — Give Databricks permission to use the storage](docs/step-02-databricks-storage-access.md)

Give the Access Connector **Storage Blob Data Contributor** on the storage account. In Unity Catalog, create storage credential `hospitalstoragecredential` and three external locations: `hospital_bronze_storage`, `hospital_silver_storage`, and `hospital_gold_storage`.

Serverless compute will not accept a storage password in code. Use `abfss://` paths, and set streams to `availableNow=True` so they process what is waiting and then stop.

### [Step 3 — Set up the mailbox (Event Hub)](docs/step-03-event-hub.md)

Create the Event Hubs namespace and hub, copy the connection string, and store it in Key Vault as `eventhub-connection`. On the Databricks website, create secret scope `hospitalanalyticsvaultscope` (add `#secrets/createScope` to the workspace URL). Notebooks read the secret with `dbutils.secrets.get(...)`, so the password never appears in code.

### [Step 4 — Notebook 1: bronze](docs/step-04-bronze-notebook.md)

`01_bronze_raw_data` reads new Event Hub messages and saves them to the bronze folder unchanged. A checkpoint remembers what was already read. The notebook counts new messages in `new_rows` so later steps can skip a run when nothing arrived.

Three bugs were fixed here: a stray `%python` line, `sum()` being overwritten by a PySpark import (use `builtins.sum`), and a `None` row count (use `value or 0`). Cell 2 inserts one fake test patient every time it runs.

### [Step 5 — Notebook 2: silver](docs/step-05-silver-notebook.md)

`02_silver_clean_data` unpacks each bronze message into patient ID, gender, age, department, admission and discharge times, bed ID, and hospital ID. Missing or future admission times become "now." Ages over 100 are replaced with a random age from 1 to 90. Missing columns are added as blank so the write does not fail.

**Still open:** some discharge times are earlier than admission, which makes length of stay negative.

### [Step 6 — Notebook 3: gold](docs/step-06-gold-notebook.md)

`03_gold_transform` builds a star schema:

- `dim_patient` — one row per version of a patient (SCD Type 2: old rows are closed with an end date, new rows are marked current)
- `dim_department` — each department and hospital combination
- `fact_patient_flow` — one row per visit, with length of stay, linked to the patient and department

Surrogate keys used to restart at 0 on every run, so new patients collided with old IDs and visits linked to the wrong people. The fix continues from the highest ID already in the table, and the ID type must stay `long`. The patient table was rebuilt once: 226 patients, IDs 0–225, no duplicates.

### [Step 7 — Make it run automatically (Databricks Job)](docs/step-07-databricks-job.md)

Job **Hospital Patient Flow - Bronze to Gold Refresh** watches the bronze folder. When new files arrive it waits 60 seconds, runs silver, then gold, and allows only one run at a time.

It does not start when bronze saved nothing, or when files were only deleted or changed. If it never starts, turn on file events for `hospital_bronze_storage`, check the job page, add failure emails under **Job notifications**, and confirm read permission on the external location.

### [Step 8 (optional) — Use Azure Data Factory instead](docs/step-08-azure-data-factory.md)

An ADF pipeline can replace the Databricks Job. Do not run both.

The path is: create a Databricks personal access token, store it in Key Vault as `azure-databricks-connection`, grant the Data Factory identity **Key Vault Secrets User**, then create two linked services (Key Vault and Databricks Serverless). The pipeline runs the bronze notebook, and runs silver then gold only when bronze hands back a row count greater than 0 (`dbutils.notebook.exit(str(new_rows))` plus an If Condition). A later improvement is to drop the token and use the Data Factory managed identity with **Contributor** on the Databricks workspace.

[Section 8e](docs/step-08-azure-data-factory.md#8e) builds an Azure Monitor alert on **Failed pipeline runs metrics** (threshold 1, check every 1 minute, look back 5 minutes) and emails the pipeline owner through an action group. That alert covers ADF only. The Databricks Job uses **Job notifications** instead.

### [Step 9 (optional) — Query the gold tables with Azure Synapse](docs/step-09-synapse.md)

Synapse serverless (the Built-in pool) reads the gold Delta tables with SQL. A dedicated SQL pool cannot read Delta and bills every hour it is running, so this project does not use one.

- [9A](docs/step-09-synapse.md#9a) — Turn off deletion vectors on the three gold tables, or Synapse errors with `Feature 'Deletion Vectors' is not supported`. Then set `delta.enableDeletionVectors` to false so they do not come back.
- [9B](docs/step-09-synapse.md#9b) — Create the Synapse workspace in the same region as the storage account, and grant **Storage Blob Data Reader** to the workspace identity and to yourself.
- [9C](docs/step-09-synapse.md#9c) — In database `hospital_gold` on the Built-in pool, create a master key, a managed-identity credential, data source `gold_data_source`, file format `DeltaFormat`, and external tables for the three gold folders. Run blocks 1–7 once. Later Databricks writes show up automatically.
- [9D](docs/step-09-synapse.md#9d) — Build KPI views (bed occupancy, turnover, demographics, treatment duration, volume trend, department inflow, overstays). Each view needs its own `GO`, uses `CREATE OR ALTER VIEW dbo.vw_name`, and must not include the database name.
- [9E](docs/step-09-synapse.md#9e) — Troubleshooting: wrong pool, hanging data-source creation, deletion vectors, duplicate rows from Parquet, and view-batch errors.
- [9F](docs/step-09-synapse.md#9f) — If a dedicated pool was created earlier, drop its unused objects and pause it so billing stops.
- [9G](docs/step-09-synapse.md#9g) — Permission summary for the workspace identity and your user.

### [Quick start — running it by hand](docs/quick-start.md)

Open each notebook in the Databricks workspace and run the first cell, in order: `01_bronze_raw_data`, then `02_silver_clean_data`, then `03_gold_transform`.

### [Still to do](docs/still-to-do.md)

Negative length of stay in silver, reliable file-arrival triggering, duplicate test patients in bronze, confirming the seven KPI views, and rotating the Synapse master key password out of saved scripts.

### [Glossary](docs/glossary.md)

Plain-English definitions for the terms used in this guide: medallion architecture, checkpoint, Unity Catalog, surrogate key, SCD Type 2, deletion vectors, external tables, and the rest.
