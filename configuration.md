# Hospital Analytics Pipeline — The Beginner's Guide

This is the plain-English version of the main [README.md](README.md). No prior experience with Azure or Databricks needed. If a word is unfamiliar, check the **Glossary** at the bottom.

---

## The big picture (in one paragraph)

A hospital sends out little messages every time a patient is admitted (for example: "Patient 123, age 45, went to Cardiology at 9:00 AM"). This project **catches those messages, cleans them up, and organizes them into neat tables** so someone can build reports like "How long do patients stay in each department?"

We do this in three stages, like a kitchen:

| Stage | Kitchen analogy | What happens to the data |
| --- | --- | --- |
| **Bronze** | Groceries dumped on the counter | Raw messages saved exactly as they arrived. Nothing is changed. |
| **Silver** | Washed and chopped vegetables | Messages are opened up, bad values are fixed, and everything gets proper columns. |
| **Gold** | The finished meal on a plate | Data is organized into report-ready tables (patients, departments, visits). |

This three-step pattern is called the **medallion architecture** (bronze, silver, gold — like medals).

---

## The tools involved (who does what)

| Tool | What it is | Its job in this project | Where you work with it |
| --- | --- | --- | --- |
| **Azure Event Hub** | A mailbox that receives a constant stream of messages | Receives the patient messages from the hospital | Azure Portal |
| **Azure Data Lake Storage (ADLS)** | A giant online hard drive | Stores the bronze, silver, and gold data in three folders (called "containers") | Azure Portal |
| **Azure Key Vault** | A locked safe for passwords | Holds secret passwords so they never appear in code | Azure Portal |
| **Databricks** | A place to write and run data-processing code | Runs the three notebooks that move data bronze → silver → gold | Databricks website (your workspace) |
| **Databricks Job** | An automatic scheduler | Runs the notebooks for you when new data shows up | Databricks website → Jobs & Pipelines |
| **Azure Data Factory (ADF)** | Another scheduler, from Microsoft | Optional alternative to the Databricks Job | ADF Studio (opened from the Azure Portal) |
| **Azure Synapse Analytics** | A SQL tool for reporting on data in the lake | Lets you query the gold tables with SQL and build KPI views | Synapse Studio (opened from the Azure Portal) |
| **Azure Monitor (Alerts)** | Azure's alarm system | Emails you when an ADF pipeline run fails | Azure Portal → Monitor |

### The websites you'll be using

| Name | Address | How to get there |
| --- | --- | --- |
| **Azure Portal** | `https://portal.azure.com` | Sign in with your Azure account |
| **Databricks website (workspace)** | `https://adb-<your-workspace-id>.azuredatabricks.net` | Azure Portal → search "Azure Databricks" → click your workspace → **Launch Workspace** |
| **ADF Studio** | `https://adf.azure.com` | Azure Portal → search "Data factories" → click your factory → **Launch Studio** |
| **Synapse Studio** | `https://web.azuresynapse.net` | Azure Portal → search "Azure Synapse Analytics" → click your workspace → **Open Synapse Studio** |

---

## Step 0 — Create your Azure accounts and resources (do this first)

**Where:** Azure Portal

Think of Azure like an office building:
* **Subscription** = the lease (who pays the bill).
* **Resource group** = one floor where everything for this project lives.
* **Resources** = the rooms on that floor (storage, Event Hub, Databricks, etc.).

### 0a. Accounts you need

Some of these are people. Others are "robot accounts" (Azure calls them **managed identities**) that let one service log into another without a password.

| Account | Person or robot? | What it's for | Where it comes from |
| --- | --- | --- | --- |
| **Azure account + subscription** | Person (you) | Your login and billing | `https://portal.azure.com` → sign up, then **Subscriptions** |
| **Databricks workspace user** | Person (you) | Your login to the Databricks website | Automatic. Whoever creates the workspace becomes its admin. |
| **Access connector identity** | Robot | Lets Databricks open the storage | Created automatically with the Access Connector (0b, row 8) |
| **Data Factory identity** | Robot | Lets ADF open the Key Vault | Created automatically with the data factory (0b, row 9) |
| **AzureDatabricks app** | Robot (Microsoft's) | Lets Databricks read secrets from Key Vault | Already exists in every Azure tenant. You just give it a role. |

### 0b. Resources to create (in this order)

**Where:** Azure Portal → search the resource name in the top search bar → **+ Create**

| # | Resource | Our name | Settings that matter | Where to click |
| --- | --- | --- | --- | --- |
| 1 | **Resource group** | `hospital-analytics` | Pick one region and use it for everything below | Resource groups → + Create |
| 2 | **Storage account** | `hospitalstorage1023` | **Turn on "Enable hierarchical namespace"**. This is what makes it Data Lake (ADLS Gen2) storage. | Storage accounts → + Create → **Advanced** tab |
| 3 | **Containers** | `bronze`, `silver`, `gold` | Access level: Private | Your storage account → **Containers** → + Container |
| 4 | **Key Vault** | `hospitalvault` | Permission model: **Azure role-based access control** | Key vaults → + Create → **Access configuration** tab |
| 5 | **Event Hubs namespace** | `hospital-analytics-1023` | **Standard tier or higher.** Basic tier does not support the Kafka connection the bronze notebook uses. | Event Hubs → + Create |
| 6 | **Event Hub** | `hospital-analytics-eh` | Defaults are fine | Your namespace → + Event Hub |
| 7 | **Azure Databricks workspace** | `hospital-analytics-databricks` | **Premium tier** (required for Unity Catalog) | Azure Databricks → + Create |
| 8 | **Access Connector for Azure Databricks** | `hospital-databricks-access-connector` | System-assigned identity: On (default) | Access Connector for Azure Databricks → + Create |
| 9 | **Data Factory** (optional) | `hospital-analytics-df1023` | Defaults are fine | Data factories → + Create |
| 10 | **Synapse workspace** (optional) | your choice (e.g. `hospital-synapse-ws`) | Same region as the storage account. Details in Step 9B. | Azure Synapse Analytics → + Create |

> **"Buckets" vs "containers":** AWS calls storage folders "buckets." Azure calls them "containers." Same idea.

### 0c. Azure permissions cheat sheet (who gets which role)

A **role** is a permission slip. You give one out like this:

**Where:** Azure Portal → open the resource in the "On what" column → **Access control (IAM)** → **+ Add** → **Add role assignment** → pick the role → **Members** tab → choose **User** (for people/apps) or **Managed identity** (for robots) → **Review + assign**

| Who | Role | On what | Why | Needed? |
| --- | --- | --- | --- | --- |
| You | **Owner** (or Contributor + User Access Administrator) | Resource group | Create everything and hand out roles | Always |
| You | **Key Vault Secrets Officer** | `hospitalvault` | Add and edit secrets. Being Owner does NOT include this. | Always |
| Access connector | **Storage Blob Data Contributor** | Storage account | Read and write bronze/silver/gold data | Always |
| Access connector | **Storage Queue Data Contributor** and **Storage Account Contributor** | Storage account | Lets Databricks watch for new files quickly | Only for file events (Step 7) |
| Access connector | **EventGrid EventSubscription Contributor** | Resource group | Same as above | Only for file events (Step 7) |
| AzureDatabricks app | **Key Vault Secrets User** | `hospitalvault` | Lets the Databricks secret scope read the Event Hub password | Always |
| Data Factory identity | **Key Vault Secrets User** | `hospitalvault` | Lets ADF read the Databricks token | Only if using ADF |
| Data Factory identity | **Contributor** | Databricks workspace resource | Lets ADF log into Databricks without a token | Only for the no-token option in Step 8 |
| Synapse workspace identity | **Storage Blob Data Reader** | Storage account | Lets Synapse read the gold tables | Only if using Synapse (Step 9) |
| You | **Storage Blob Data Reader** | Storage account | Lets you query gold data in Synapse with your own login | Only if using Synapse (Step 9) |

**Event Hub works differently.** It uses a "shared access policy" (a password with limits) instead of a role.

**Where:** Azure Portal → Event Hubs → `hospital-analytics-1023` → **Shared access policies** → **+ Add**
* For Databricks, tick **Listen** only. The bronze notebook just reads.
* Whatever sends the hospital messages needs **Send**.
* Copy that policy's connection string. This is what goes into Key Vault in Step 3.

### 0d. Databricks permissions cheat sheet

Azure roles get you in the building. Databricks has its own permissions for what you can do once inside.

| Who | Permission | On what | Why | Where to set |
| --- | --- | --- | --- | --- |
| You (admin) | **CREATE STORAGE CREDENTIAL**, **CREATE EXTERNAL LOCATION** | Metastore | To do Step 2 | Databricks website → **Catalog** → gear icon → **Metastore** → **Permissions** |
| Whoever runs the notebooks or job | **READ FILES**, **WRITE FILES** | All 3 external locations | To read and write data | **Catalog** → **External Locations** → pick one → **Permissions** tab → **Grant** |
| Whoever runs the notebooks or job | **READ** | Secret scope `hospitalanalyticsvaultscope` | To fetch the Event Hub password | No button for this. Use the Databricks CLI. The person who created the scope already has full access. |
| Whoever runs the notebooks or job | Serverless compute access | Workspace | Notebooks and the job run on Serverless | Usually on by default. Admins: **Settings** → **Workspace admin** |
| The job | **Run as** a user | Job | The job uses that person's permissions | **Jobs & Pipelines** → your job → **Job details** → **Run as** |

---

## Step 1 — Set up the storage (the hard drive)

**Where:** Azure Portal → search **Storage accounts**

1. In Azure, create a storage account. Ours is called `hospitalstorage1023`.
2. Inside it, create three containers (think: folders): `bronze`, `silver`, `gold`.

That's it. The notebooks will create the sub-folders automatically.

---

## Step 2 — Give Databricks permission to use the storage

**Where:** Two places — first Azure, then Databricks.
* **Azure Portal:** search **Access Connector for Azure Databricks** to create the connector. Then go to your storage account → **Access control (IAM)** → give the connector the **Storage Blob Data Contributor** role.
* **Databricks website:** left sidebar → **Catalog** → gear icon / **External data** → **Credentials** (for the key card) and **External Locations** (for the doors).

Databricks needs a "key card" to get into the storage. We set this up in **Unity Catalog** (the Databricks security desk):

1. **Storage Credential** (`hospitalstoragecredential`) — the key card itself. It's linked to an Azure identity called `hospital-databricks-access-connector`.
2. **External Locations** — one for each folder, telling Databricks "this key card opens this door":
   * `hospital_bronze_storage` → bronze container
   * `hospital_silver_storage` → silver container
   * `hospital_gold_storage` → gold container

> **Why not just paste the storage password into the code?** Our Databricks uses **Serverless** compute (Databricks manages the computers for you). Serverless doesn't allow that old method. It's also less safe. Unity Catalog is the modern, secure way.

**Three Serverless rules to remember:**
* Don't put storage passwords in the code.
* Use full addresses that start with `abfss://` (not `dbfs:/mnt/`).
* Streams must use `availableNow=True`, which means "process everything that's waiting, then stop." Serverless can't run a stream forever.

---

## Step 3 — Set up the mailbox (Event Hub)

**Where:** Mostly Azure Portal, with one setup step on the Databricks website.

1. **Azure Portal → Event Hubs:** Create an Event Hub namespace (`hospital-analytics-1023`) and an Event Hub inside it (`hospital-analytics-eh`).
2. **Azure Portal → Event Hubs → your namespace → Shared access policies:** Copy the **connection string** (basically its password).
3. **Azure Portal → Key vaults → your vault → Secrets:** Paste it in as a new secret named `eventhub-connection`.
4. **Databricks website:** Connect Databricks to the vault by creating a secret scope (`hospitalanalyticsvaultscope`). You do this by adding `#secrets/createScope` to the end of your workspace address.
5. **Databricks notebook:** The code fetches that password from the vault with `dbutils.secrets.get(...)`. The password never appears in the notebook.

---

## Step 4 — Notebook 1: `01_bronze_raw_data` (grab the groceries)

**Where:** Databricks website → left sidebar → **Workspace** → `01_bronze_raw_data`

**In plain English:** "Go check the mailbox, take every new message, and save it to the bronze folder exactly as-is."

What it does, step by step:
1. Connects to Event Hub.
2. Reads all the new messages.
3. Saves them to the bronze folder as raw text.
4. Counts how many new messages it saved and remembers that number (`new_rows`) so later steps know whether there's anything to do.

**A "checkpoint"** is like a bookmark. It remembers which messages were already read, so the next run only picks up new ones.

### Problems we hit and how we fixed them

| Problem | What went wrong (simple version) | Fix |
| --- | --- | --- |
| `SyntaxError` | A stray `%python` line was sitting in the middle of the code. That command is only allowed on the very first line of a cell. | Deleted it. |
| `sum()` crashed | The line `from pyspark.sql.functions import *` quietly replaced Python's normal `sum` with a different one that only works on table columns. | Used `builtins.sum(...)` to get Python's normal `sum` back. |
| `TypeError` with `None` | Sometimes the row count was blank (`None`) instead of 0. You can't add blank to a number. | Wrote `(value or 0)`, which means "if it's blank, use 0." |

> **Heads up:** Cell 2 in this notebook adds one fake test patient. Every time you run it, it adds another copy. Don't run it over and over.

---

## Step 5 — Notebook 2: `02_silver_clean_data` (wash and chop)

**Where:** Databricks website → left sidebar → **Workspace** → `02_silver_clean_data`

**In plain English:** "Take the raw messages from bronze, open them up into proper columns, fix obviously wrong values, and save to silver."

What it does:
1. Reads new rows from bronze.
2. Unpacks each message into columns: patient ID, gender, age, department, admission time, discharge time, bed ID, hospital ID.
3. Turns the time text into real dates and times.
4. Fixes bad data:
   * Missing admission time, or one in the future? Replace with "now."
   * Age over 100? Treat as a typo and replace with a random age between 1 and 90.
5. If a column is missing from a message, it adds it as blank so nothing breaks.
6. Saves to the silver folder.

No code changes were needed here.

> **Known issue:** Some patients have a discharge time that's *before* their admission time (they "left before they arrived"). That makes their length of stay negative. This still needs fixing.

---

## Step 6 — Notebook 3: `03_gold_transform` (plate the meal)

**Where:** Databricks website → left sidebar → **Workspace** → `03_gold_transform`

**In plain English:** "Take the clean silver data and organize it into three report-friendly tables."

| Gold table | Think of it as... | What's in it |
| --- | --- | --- |
| `dim_patient` | A patient address book that keeps history | One row per version of each patient |
| `dim_department` | A list of departments | Each department + hospital combo |
| `fact_patient_flow` | The visit log | One row per hospital visit, linked to the patient and department, with length of stay |

**"Dim" (dimension)** tables describe *things* (who, where). **"Fact"** tables record *events* (what happened). Putting them together is called a **star schema**.

### What "keeps history" means (SCD Type 2)

If a patient's info changes (say their age is updated), we **don't erase the old row**. Instead:
* The old row is marked "no longer current" with an end date.
* A new row is added and marked "current."

This lets you look back and see what the data looked like at any point in time.

### The bug we fixed: duplicate ID numbers

Every patient row gets an ID number (a **surrogate key**). The original code generated IDs that **started over from 0 every run**. Since the patient table keeps growing, new patients ended up with the same IDs as old ones. Result: visits got linked to the wrong patients.

**The fix:** Before adding new patients, look up the highest ID already used, and start counting from there. Like a deli ticket machine that continues from the last number instead of resetting.

We also had to:
* Make sure the new IDs are the same number type (`long`) as the old ones, or the save fails.
* Rebuild the patient table once from scratch to clean up the old duplicate IDs. After that: 226 patients, IDs 0–225, no duplicates.

---

## Step 7 — Make it run automatically (Databricks Job)

**Where:** Databricks website → left sidebar → **Jobs & Pipelines**

Running three notebooks by hand gets old. A **Databricks Job** does it for you.

Our job: **Hospital Patient Flow - Bronze to Gold Refresh**

**How it works:**
1. It watches the bronze folder.
2. When new files show up, it waits 60 seconds (in case more are coming).
3. It runs the silver notebook.
4. If that works, it runs the gold notebook.
5. Only one run at a time. Extra runs wait in line.

This is called a **file arrival trigger** — like a motion-sensor light that turns on when something enters the room.

**It will NOT start if:**
* The bronze notebook ran but found no new messages (nothing new got saved).
* Files were deleted or changed rather than added.

**If it never starts:**
1. Turn on **file events** for `hospital_bronze_storage` (Databricks website → **Catalog** → **External Locations** → `hospital_bronze_storage`). This makes the job notice new files much faster and more reliably.
2. Check the job page for errors (Databricks website → **Jobs & Pipelines** → your job).
3. Turn on email alerts for failures so you find out right away (same job page → **Job notifications**).
4. Make sure you have read permission on the storage location (Databricks website → **Catalog** → **External Locations** → **Permissions** tab).

---

## Step 8 (optional) — Use Azure Data Factory instead

**Where:** Three places, in this order: Databricks website (8a) → Azure Portal (8b) → ADF Studio (8c and 8d).

Some teams prefer Azure Data Factory as their scheduler. **Pick ONE: either the Databricks Job or ADF.** If you use both, the same data gets processed twice.

### 8a. Databricks side — make a token for ADF

**Where:** Databricks website

A **token** is a password that lets ADF log into Databricks as you.

1. **Check tokens are allowed** (admins only, on by default): **Settings** → **Workspace admin** → **Advanced** → **Personal Access Tokens** → On.
2. **Make the token:** your profile icon (top right) → **Settings** → **Developer** → **Access tokens** → **Manage** → **Generate new token**. Comment: `ADF`. Pick a lifetime.
3. **Copy it right away.** It's only shown once.
4. **The token acts as you.** So you must be able to open and run all three notebooks. If someone else owns the token, share each notebook with them: open the notebook → **Share** → **Can Run**.
5. **Hand back the row count:** add `dbutils.notebook.exit(str(new_rows))` to the end of the bronze notebook (explained in 8d).

### 8b. Azure side — store the token and let ADF read it

**Where:** Azure Portal

1. **Save the token:** Key vaults → `hospitalvault` → **Secrets** → **+ Generate/Import**. Name: `azure-databricks-connection`. Value: paste the token only, no spaces or quotes.
2. **Create the data factory** if you haven't (Data factories → + Create). Its robot identity is turned on automatically.
3. **Let ADF open the vault:** Key vaults → `hospitalvault` → **Access control (IAM)** → + Add role assignment → **Key Vault Secrets User** → Members: **Managed identity** → **Data factory** → pick yours.
4. **Network check:** if your Databricks workspace is locked to private networks or specific IP addresses, ADF must be allowed in. Check at your Databricks workspace → **Networking**.

### 8c. ADF side — create two linked services

A **linked service** is ADF's saved connection to another system, like a contact in your phone.

**Where:** ADF Studio → **Manage** (toolbox icon on the left) → **Linked services** → **+ New**

**First: the Key Vault connection** (ADF needs this to fetch the token)
* Search **Azure Key Vault** → Name: `hospitalvault`
* Pick your subscription and `hospitalvault`
* Authentication: **System-assigned managed identity**
* **Test connection** → **Create**

**Second: the Databricks connection**
* Search **Azure Databricks**. Fill in:
* Workspace: `hospital-analytics-databricks`
* Cluster type: **Serverless**
* Authentication: Access Token, pulled from Key Vault (`hospitalvault`, secret `azure-databricks-connection`)
* **Test connection** → **Create**

> **No-token option (recommended later):** Tokens expire. Instead, give the Data Factory identity the **Contributor** role on your Databricks workspace (Azure Portal → your Databricks workspace → **Access control (IAM)**). Then in the Databricks linked service, choose Authentication: **Managed service identity**. No token to renew.

**If "Test Connection" fails, check:**
1. **Is the token expired?** Databricks tokens die after 90 days of not being used. Make a new one on the **Databricks website** (your profile icon → **Settings** → **Developer** → **Access tokens**), then update the secret in the **Azure Portal** (Key vaults → `hospitalvault` → Secrets).
2. **Can ADF open the vault?** ADF needs the "Key Vault Secrets User" role. Set it in the **Azure Portal** → Key vaults → `hospitalvault` → **Access control (IAM)**.
3. **Any extra spaces?** The secret should be only the token, nothing else. Check it in the **Azure Portal** → Key vaults → `hospitalvault` → Secrets.
4. **Network blocks?** If Databricks is locked to private networks, ADF may not be able to reach it. Check in the **Azure Portal** → your Databricks workspace → **Networking**.

### 8d. ADF side — build the pipeline

**Where:** ADF Studio → **Author** (pencil icon on the left) → **+** → **Pipeline**. Step 2 below is done on the Databricks website, in the bronze notebook.

```
Run bronze notebook
        │
        ▼
Did it find new rows?
   ├─ Yes → Run silver notebook → Run gold notebook
   └─ No  → Do nothing
```

1. Add a **Notebook** activity for `01_bronze_raw_data`.
2. ADF can't see the `new_rows` number by default. On the **Databricks website**, add this to the end of the bronze notebook so it "hands back" the number: `dbutils.notebook.exit(str(new_rows))`
3. Add an **If Condition** with: `@greater(int(activity('BronzeNotebook').output.runOutput), 0)` (meaning "is the number bigger than 0?").
4. In the **True** box, add the silver notebook, then the gold notebook.
5. Leave the **False** box empty.

### 8e. Get an email when a pipeline run fails

**Where:** Azure Portal → search **Monitor** → left sidebar **Alerts** → **+ Create** → **Alert rule**

(Shortcut: ADF Studio → **Monitor** → **Alerts & metrics** → **+ New alert rule** opens the same form.)

**In plain English:** "If the pipeline breaks, tell the person who looks after it right away, instead of finding out days later."

The form has four tabs. Fill them in order:

**1. Scope tab — what to watch**
* Click **Select scope**.
* Expand the resource group `hospital-analytics`.
* Tick the data factory `hospital-analytics-df1023` → **Apply**.

**2. Condition tab — when to sound the alarm**

| Setting | Value | Meaning |
| --- | --- | --- |
| Signal name | **Failed pipeline runs metrics** | Count pipeline runs that failed |
| Aggregation type | **Count** (Total also works) | How the failures are added up |
| Operator | **Greater than or equal to** | |
| Threshold | **1** | Alert on the very first failure |
| Check every / Lookback period | **1 minute** / **5 minutes** | How often Azure checks, and how far back it looks |

> **Optional:** Under **Split by dimensions**, pick **Name** to watch only specific pipelines.

**3. Actions tab — who gets told, and how**

An **action group** is a contact list for alerts. Make one once, reuse it for every alert.
* Click **+ Create action group**.
* **Basics:** resource group `hospital-analytics`, region **Global**, an action group name (e.g. `pipeline-failure-ag`) and a short display name (max 12 characters).
* **Notifications:** type **Email/SMS message/Push/Voice** → tick **Email** → enter the pipeline owner's address. Give it a name.
* **Review + create**. Back on the alert, the new action group is selected.

**4. Details tab — name it**
* **Severity:** **1 – Error**
* **Alert rule name:** e.g. `adf-pipeline-failure-alert`
* Leave **Enable upon creation** ticked.
* **Review + create** → **Create**.

**Test it:** Make a pipeline fail on purpose (for example, point a Notebook activity at a wrong path) and run it. The email should arrive within a few minutes. Fix the path afterward.

> **This only covers ADF.** If you use the Databricks Job (Step 7) instead, set failure emails on the job page → **Job notifications**. Alert rules have a small monthly cost.

---

## Step 9 (optional) — Query the gold tables with Azure Synapse

**Where:** Three places, in this order: Databricks website (9A) → Azure Portal (9B) → Synapse Studio (9C onward).

**In plain English:** "Let people who know SQL look at the gold tables and build reports, without touching Databricks."

Think of it like this:
* **The data lake** is a filing cabinet.
* **Databricks** puts the folders in.
* **Synapse** needs a label on each drawer before it knows what's inside.

We use the **serverless (Built-in)** SQL pool, not a dedicated pool.

| | Serverless (Built-in) | Dedicated pool |
| --- | --- | --- |
| Reads Delta tables? | Yes | **No** |
| Cost | Pay per query (pennies for our data) | Pay by the hour, even when idle |
| Start/stop needed? | No | Yes |
| Right for this project? | **Yes** | No — built for terabytes |

> **Why not dedicated + Parquet?** Our gold folders hold files from every past Databricks run. Reading them as plain Parquet shows every old copy, so you get duplicate and out-of-date rows. Delta format reads only the current version.

### 9A. Databricks side — make the gold tables readable by Synapse

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
* `deletionVectors` **not** listed in `tableFeatures`
* `minReaderVersion` = **1**

(Seeing `checkpointProtection` in the list is normal and fine.)

**3. If `deletionVectors` is still there:** Databricks sometimes needs old history to expire. Wait **24 hours**, then re-run step 1 with `TRUNCATE HISTORY` added to the end of each line.

> `TRUNCATE HISTORY` removes old table versions (no more "time travel" to them). That's fine here because gold is rebuilt from silver on every run.

**4. Stop them from coming back:**

```sql
ALTER TABLE delta.`abfss://gold@hospitalstorage1023.dfs.core.windows.net/dim_patient` SET TBLPROPERTIES ('delta.enableDeletionVectors' = false);
ALTER TABLE delta.`abfss://gold@hospitalstorage1023.dfs.core.windows.net/dim_department` SET TBLPROPERTIES ('delta.enableDeletionVectors' = false);
ALTER TABLE delta.`abfss://gold@hospitalstorage1023.dfs.core.windows.net/fact_patient_flow` SET TBLPROPERTIES ('delta.enableDeletionVectors' = false);
```

### 9B. Azure side — create the Synapse workspace and permissions

**1. Create the workspace**

**Where:** Azure Portal → search **Azure Synapse Analytics** → **+ Create**

| Setting | What to pick | Why |
| --- | --- | --- |
**Basics tab:**

| Setting | What to pick | Why |
| --- | --- | --- |
| Resource group | `hospital-analytics` (same as everything else) | Keeps the project together |
| Workspace name | Your choice (e.g. `hospital-synapse-ws`) | Becomes part of the web address |
| Region | **Same region as `hospitalstorage1023`** | Avoids slow, costly cross-region reads |
| Account name (Data Lake Storage Gen2) | **Select existing:** `hospitalstorage1023` | Synapse needs a "home" storage account |
| File system name | Create new, e.g. `synapseworkspace` (lowercase, no spaces) | Synapse's own internal files. NOT where gold data lives. |
| "Assign myself the Storage Blob Data Contributor role" | Tick it | Lets you browse the lake from Synapse Studio |

Click **Next: Security**.

**Security tab:**

| Setting | What to pick | Why |
| --- | --- | --- |
| SQL Server admin login | Keep the default (`sqladminuser`) or choose one | The "master login" for the workspace's SQL pools |
| SQL Password | A strong password | Save it in Key Vault (`hospitalvault`). This is NOT the master key password from 9C. |
| Allow network access to Data Lake Storage Gen2 account | Tick it if offered | Lets Synapse reach storage that has a firewall |

Click **Review + create** → **Create**. Takes 2–3 minutes.

**Open Synapse Studio:** When it finishes, click **Go to resource group** → click your Synapse workspace → **Open Synapse Studio** (on the Overview page).

**2. Let Synapse read the gold data**

**Where:** Azure Portal → `hospitalstorage1023` → **Access control (IAM)** → **+ Add role assignment**

* Role: **Storage Blob Data Reader**
* Assign access to: **Managed identity** → **Synapse workspace** → pick yours
* Repeat with **User** → yourself, so you can query with your own login

> **Why Reader, not Contributor?** Synapse only reads gold. Databricks does the writing. Give the smallest permission needed. Roles can take 5–10 minutes to start working.

**3. (Optional) Key Vault access**

Only if Synapse will use secrets from Key Vault.

**Where:** Azure Portal → `hospitalvault` → **Access control (IAM)** → **Key Vault Secrets User** → **Managed identity** → **Synapse workspace**

**4. Storage firewall check**

**Where:** Azure Portal → `hospitalstorage1023` → **Networking**

* **"Enabled from all networks"** → you're fine.
* **"Enabled from selected networks"** → tick **"Allow Azure services on the trusted services list to access this storage account"**, or add a managed private endpoint (Synapse Studio → **Manage** → **Managed private endpoints**).

If you skip this, setup statements can hang for a very long time.

**5. (Optional, NOT needed for this project) Create a dedicated SQL pool**

A dedicated SQL pool is like renting your own data warehouse. The **Built-in** serverless pool already exists in every workspace, so you don't need one here.

**Where:** Synapse Studio → **Manage** (toolbox icon on the left) → **SQL pools** → **+ New**
* **Name:** your choice
* **Performance level:** the slider sets the size and the price. **DW100c** is the smallest.
* **Review + create** → **Create**

> **Warning:** A dedicated pool bills **every hour** it's running, even when idle. It also can't read Delta, and `CREATE DATABASE` fails on it (see 9E). If you create one, pause it when you're done (9F).

### 9C. Synapse side — register the gold tables

**Where:** Synapse Studio → **Develop** (code icon on the left) → **+** → **SQL script**

(Other way: refresh the page → **Data** (cylinder icon) → **Workspace** tab → **SQL database** → right-click your database → **New SQL script** → **Empty script**. `hospital_gold` only shows up here after Block 1 runs.)

**Before you run anything, check the toolbar above the script:**
* **Connect to:** **Built-in** (NOT your dedicated pool's name)
* **Use database:** `master` for Block 1 only. Then click the refresh icon and switch to `hospital_gold`.

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

| Block | What it does | Filing-cabinet analogy |
| --- | --- | --- |
| 1 | Creates a database to hold your labels | Getting your own office |
| 2 | Switches to that database | Walking into your office |
| 3 | Creates an encryption key | Putting a lock on the office door |
| 4 | Saves Synapse's identity | The ID badge Synapse shows the storage account |
| 5 | Saves the gold container's address | Writing the filing cabinet's address on a sticky note |
| 6 | Says "these files are Delta" | Telling the office which filing system the folders use |
| 7 | Creates three labels for the three gold folders | Labeling the drawers: Patients, Departments, Visits |
| 8 | Reads 10 rows | Opening a drawer to check it works |

**Where does `dbo` come from?** You don't create it. Every new database comes with a built-in `dbo` schema ("database owner"). Since you created `hospital_gold`, you're its owner, so `dbo` is your default.

Only run Blocks 1–7 **once**. External tables see new Databricks data automatically. After that, just run SELECTs.

### 9D. Build KPI views and look at the data

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
* Type it: `SELECT TOP 100 * FROM dbo.fact_patient_flow;` or `SELECT * FROM dbo.vw_bed_occupancy;`
* Or click it: Synapse Studio → **Data** (cylinder icon) → **Workspace** → **SQL database** → `hospital_gold` → **External tables** or **Views** → right-click → **New SQL script** → **Select TOP 100 rows**
* Switch the results from **Table** to **Chart** for a quick picture, or **Export** to CSV.
* List what exists: `SELECT SCHEMA_NAME(schema_id) AS schema_name, name FROM sys.views;`

### 9E. Troubleshooting

| Error you see | What it really means | Fix |
| --- | --- | --- |
| `Incorrect syntax near 'hospital_gold'` (on CREATE DATABASE) | You're on the **dedicated** pool. It's already one database and doesn't know `CREATE DATABASE`. | Toolbar → **Connect to: Built-in** |
| `Unknown file format type 'DELTA'` | Same — dedicated pools can't read Delta. | Toolbar → **Connect to: Built-in** |
| `CREATE EXTERNAL DATA SOURCE` runs forever | Synapse can't reach storage: firewall, or role not active yet. | 9B step 4 (firewall) and step 2 (role). Wait 5–10 min after adding roles. |
| `Websocket connection was closed with code 1006` | Your browser lost its connection. Not a SQL error. | Refresh Synapse Studio. Check **Monitor** → **SQL requests** to see if it finished. Use SSMS / Azure Data Studio for long queries. |
| `Feature 'Deletion Vectors' is not supported` / `unsupported reader version` | Gold tables still have deletion vectors. | Finish 9A. No need to recreate Synapse tables after. |
| `... already exists` | That block already worked earlier. | Skip it, or check with `SELECT * FROM sys.external_tables;` (also `sys.external_data_sources`, `sys.external_file_formats`, `sys.database_scoped_credentials`) |
| `'CREATE/ALTER VIEW' does not allow specifying the database name` | View name has 3 parts (`hospital_gold.dbo.vw_x`). | Use `dbo.vw_x`. The toolbar decides the database. |
| `CREATE VIEW must be the only statement in the batch` | Missing `GO` between views. | Add `GO` after each view. |
| `Invalid object name 'dbo.vw_...'` | View is in a different database or schema, or the name differs. | Run `SELECT DB_NAME();` and the `sys.views` query from 9D. Re-run views with `hospital_gold` selected. |
| Query returns no rows | Gold is empty. | Run `03_gold_transform` in Databricks first. |
| Duplicate or old rows | You're reading Parquet instead of Delta. | Use `FORMAT_TYPE = DELTA` on **Built-in**. |
| "Potential conversion error" warnings on text columns | Delta text is UTF-8. | Once: `ALTER DATABASE hospital_gold COLLATE Latin1_General_100_BIN2_UTF8;` |

### 9F. Cleanup — the old dedicated pool

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

### 9G. Synapse permissions summary

| Who | Role | On what | Where to set | Why |
| --- | --- | --- | --- | --- |
| Synapse workspace identity | **Storage Blob Data Reader** | `hospitalstorage1023` | Azure Portal → storage account → IAM | Read gold data |
| You | **Storage Blob Data Reader** | `hospitalstorage1023` | Azure Portal → storage account → IAM | Query with your own login |
| Synapse workspace identity | **Key Vault Secrets User** | `hospitalvault` | Azure Portal → Key Vault → IAM | Only if using Key Vault secrets |
| You | **Synapse Administrator** (or Synapse SQL Administrator) | Synapse workspace | Synapse Studio → **Manage** → **Access control** | Create databases and objects (workspace creator gets this automatically) |
| You | **Owner** or **Contributor** | Resource group | Azure Portal → resource group → IAM | Create the Synapse workspace |

---

## Quick start: running it by hand

**Where:** Databricks website → left sidebar → **Workspace**

If you just want to see it work, open each notebook and run the first cell, in this order:

1. `01_bronze_raw_data` — grabs new messages
2. `02_silver_clean_data` — cleans them
3. `03_gold_transform` — builds the report tables

---

## Still to do

* Fix the "left before they arrived" negative length of stay (in the silver notebook).
* Get the automatic job trigger working reliably (turn on file events, add alerts).
* Remove the duplicate test patient rows from bronze.
* Confirm all seven KPI views exist in `hospital_gold` (`sys.views`) and query them.
* Take the old master key password out of any saved Synapse scripts and change it.

---

## Glossary

| Term | Plain-English meaning |
| --- | --- |
| **Pipeline** | A series of steps data goes through, like an assembly line |
| **Notebook** | A document where you write and run code in small chunks called cells |
| **Cell** | One block of code in a notebook |
| **Delta table** | A smart file format for tables that keeps a history of changes and won't get corrupted if a write fails |
| **Stream** | Reading data that keeps arriving, instead of a one-time file |
| **Checkpoint** | A bookmark that remembers what has already been processed |
| **Serverless** | Databricks runs the computers for you; you just run code |
| **Unity Catalog** | Databricks' security and organization system for data |
| **Container** | A top-level folder in Azure storage |
| **Connection string / token / PAT** | Different kinds of passwords that let one system log into another |
| **Key Vault** | Azure's password safe |
| **Trigger** | Something that starts a job automatically |
| **Surrogate key** | An ID number we create for each row (instead of using the hospital's own ID) |
| **SCD Type 2** | A way of updating records that keeps the old versions instead of overwriting them |
| **Star schema** | Organizing data as one central "events" table connected to "descriptions" tables |
| **Medallion architecture** | The bronze → silver → gold approach to cleaning data in stages |
| **Subscription** | Your Azure billing account |
| **Resource group** | A folder in Azure that holds all the services for one project |
| **Managed identity** | A "robot account" Azure creates so one service can log into another without a password |
| **Role (RBAC)** | A permission slip in Azure that says who can do what on which resource |
| **IAM** | "Identity and Access Management" — the Azure page where you hand out roles |
| **Shared access policy** | An Event Hub password with limits (e.g. read-only) |
| **Secret scope** | Databricks' link to Key Vault, so notebooks can fetch passwords |
| **Linked service** | ADF's saved connection to another system |
| **ADLS Gen2** | Azure storage with real folders, turned on with "hierarchical namespace" |
| **Serverless (Built-in) pool** | Synapse's pay-per-query SQL engine. Reads Delta. Nothing to start or stop. |
| **Dedicated SQL pool** | Synapse's always-on SQL engine, billed hourly. Can't read Delta. |
| **External table** | A label pointing at files in the lake. No data is copied. |
| **External data source** | A saved address of a storage location |
| **Database scoped credential** | A saved login Synapse uses to reach storage |
| **Master key** | A key that protects saved credentials in a database |
| **View** | A saved query you can SELECT from like a table |
| **Schema (`dbo`)** | A folder inside a database. `dbo` comes built in. |
| **Deletion vectors** | A Databricks speed feature that marks rows deleted without rewriting files. Synapse can't read it. |
| **GO** | Tells Synapse "send everything above as one batch" |
| **Alert rule** | An Azure "if this happens, tell someone" setting |
| **Action group** | A reusable contact list (emails, texts) for alerts |
| **Synapse Studio** | The Synapse website where you write SQL and manage pools |
| **SQL admin login** | The main username/password for a Synapse workspace's SQL pools |
