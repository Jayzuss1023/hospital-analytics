# Step 8 (optional) — Use Azure Data Factory instead

[← Guide](../README.md)

**Where:** Three places, in this order: Databricks website ([8a](#8a)) → Azure Portal ([8b](#8b)) → ADF Studio ([8c](#8c) and [8d](#8d)).

Some teams prefer Azure Data Factory as their scheduler. **Pick ONE: either the Databricks Job or ADF.** If you use both, the same data gets processed twice.

<a id="8a"></a>

## 8a. Databricks side — make a token for ADF

**Where:** Databricks website

A **token** is a password that lets ADF log into Databricks as you.

1. **Check tokens are allowed** (admins only, on by default): **Settings** → **Workspace admin** → **Advanced** → **Personal Access Tokens** → On.
2. **Make the token:** your profile icon (top right) → **Settings** → **Developer** → **Access tokens** → **Manage** → **Generate new token**. Comment: `ADF`. Pick a lifetime.
3. **Copy it right away.** It's only shown once.
4. **The token acts as you.** So you must be able to open and run all three notebooks. If someone else owns the token, share each notebook with them: open the notebook → **Share** → **Can Run**.
5. **Hand back the row count:** add `dbutils.notebook.exit(str(new_rows))` to the end of the bronze notebook (explained in [8d](#8d)).

<a id="8b"></a>

## 8b. Azure side — store the token and let ADF read it

**Where:** Azure Portal

1. **Save the token:** Key vaults → `hospitalvault` → **Secrets** → **+ Generate/Import**. Name: `azure-databricks-connection`. Value: paste the token only, no spaces or quotes.
2. **Create the data factory** if you haven't (Data factories → + Create). Its robot identity is turned on automatically.
3. **Let ADF open the vault:** Key vaults → `hospitalvault` → **Access control (IAM)** → + Add role assignment → **Key Vault Secrets User** → Members: **Managed identity** → **Data factory** → pick yours.
4. **Network check:** if your Databricks workspace is locked to private networks or specific IP addresses, ADF must be allowed in. Check at your Databricks workspace → **Networking**.

<a id="8c"></a>

## 8c. ADF side — create two linked services

A **linked service** is ADF's saved connection to another system, like a contact in your phone.

**Where:** ADF Studio → **Manage** (toolbox icon on the left) → **Linked services** → **+ New**

**First: the Key Vault connection** (ADF needs this to fetch the token)

- Search **Azure Key Vault** → Name: `hospitalvault`
- Pick your subscription and `hospitalvault`
- Authentication: **System-assigned managed identity**
- **Test connection** → **Create**

**Second: the Databricks connection**

- Search **Azure Databricks**. Fill in:
- Workspace: `hospital-analytics-databricks`
- Cluster type: **Serverless**
- Authentication: Access Token, pulled from Key Vault (`hospitalvault`, secret `azure-databricks-connection`)
- **Test connection** → **Create**

> **No-token option (recommended later):** Tokens expire. Instead, give the Data Factory identity the **Contributor** role on your Databricks workspace (Azure Portal → your Databricks workspace → **Access control (IAM)**). Then in the Databricks linked service, choose Authentication: **Managed service identity**. No token to renew.

**If "Test Connection" fails, check:**

1. **Is the token expired?** Databricks tokens die after 90 days of not being used. Make a new one on the **Databricks website** (your profile icon → **Settings** → **Developer** → **Access tokens**), then update the secret in the **Azure Portal** (Key vaults → `hospitalvault` → Secrets).
2. **Can ADF open the vault?** ADF needs the "Key Vault Secrets User" role. Set it in the **Azure Portal** → Key vaults → `hospitalvault` → **Access control (IAM)**.
3. **Any extra spaces?** The secret should be only the token, nothing else. Check it in the **Azure Portal** → Key vaults → `hospitalvault` → Secrets.
4. **Network blocks?** If Databricks is locked to private networks, ADF may not be able to reach it. Check in the **Azure Portal** → your Databricks workspace → **Networking**.

<a id="8d"></a>

## 8d. ADF side — build the pipeline

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

<a id="8e"></a>

## 8e. Get an email when a pipeline run fails

**Where:** Azure Portal → search **Monitor** → left sidebar **Alerts** → **+ Create** → **Alert rule**

(Shortcut: ADF Studio → **Monitor** → **Alerts & metrics** → **+ New alert rule** opens the same form.)

**In plain English:** "If the pipeline breaks, tell the person who looks after it right away, instead of finding out days later."

The form has four tabs. Fill them in order:

**1. Scope tab — what to watch**

- Click **Select scope**.
- Expand the resource group `hospital-analytics`.
- Tick the data factory `hospital-analytics-df1023` → **Apply**.

**2. Condition tab — when to sound the alarm**

| Setting                       | Value                            | Meaning                                       |
| ----------------------------- | -------------------------------- | --------------------------------------------- |
| Signal name                   | **Failed pipeline runs metrics** | Count pipeline runs that failed               |
| Aggregation type              | **Count** (Total also works)     | How the failures are added up                 |
| Operator                      | **Greater than or equal to**     |                                               |
| Threshold                     | **1**                            | Alert on the very first failure               |
| Check every / Lookback period | **1 minute** / **5 minutes**     | How often Azure checks, and how far back it looks |

> **Optional:** Under **Split by dimensions**, pick **Name** to watch only specific pipelines.

**3. Actions tab — who gets told, and how**

An **action group** is a contact list for alerts. Make one once, reuse it for every alert.

- Click **+ Create action group**.
- **Basics:** resource group `hospital-analytics`, region **Global**, an action group name (e.g. `pipeline-failure-ag`) and a short display name (max 12 characters).
- **Notifications:** type **Email/SMS message/Push/Voice** → tick **Email** → enter the pipeline owner's address. Give it a name.
- **Review + create**. Back on the alert, the new action group is selected.

**4. Details tab — name it**

- **Severity:** **1 – Error**
- **Alert rule name:** e.g. `adf-pipeline-failure-alert`
- Leave **Enable upon creation** ticked.
- **Review + create** → **Create**.

**Test it:** Make a pipeline fail on purpose (for example, point a Notebook activity at a wrong path) and run it. The email should arrive within a few minutes. Fix the path afterward.

> **This only covers ADF.** If you use the Databricks Job ([Step 7](step-07-databricks-job.md)) instead, set failure emails on the job page → **Job notifications**. Alert rules have a small monthly cost.

---

[← Step 7 — Databricks Job](step-07-databricks-job.md) · [Guide](../README.md) · [Step 9 — Synapse →](step-09-synapse.md)
