# Step 0 — Create your Azure accounts and resources (do this first)

[← Guide](../README.md)

**Where:** Azure Portal

Think of Azure like an office building:

- **Subscription** = the lease (who pays the bill).
- **Resource group** = one floor where everything for this project lives.
- **Resources** = the rooms on that floor (storage, Event Hub, Databricks, etc.).

## 0a. Accounts you need

Some of these are people. Others are "robot accounts" (Azure calls them **managed identities**) that let one service log into another without a password.

| Account                          | Person or robot?    | What it's for                               | Where it comes from                                            |
| -------------------------------- | ------------------- | ------------------------------------------- | -------------------------------------------------------------- |
| **Azure account + subscription** | Person (you)        | Your login and billing                      | `https://portal.azure.com` → sign up, then **Subscriptions**   |
| **Databricks workspace user**    | Person (you)        | Your login to the Databricks website        | Automatic. Whoever creates the workspace becomes its admin.    |
| **Access connector identity**    | Robot               | Lets Databricks open the storage            | Created automatically with the Access Connector (0b, row 8)    |
| **Data Factory identity**        | Robot               | Lets ADF open the Key Vault                 | Created automatically with the data factory (0b, row 9)        |
| **AzureDatabricks app**          | Robot (Microsoft's) | Lets Databricks read secrets from Key Vault | Already exists in every Azure tenant. You just give it a role. |

## 0b. Resources to create (in this order)

**Where:** Azure Portal → search the resource name in the top search bar → **+ Create**

| #   | Resource                                  | Our name                                 | Settings that matter                                                                                    | Where to click                                       |
| --- | ----------------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| 1   | **Resource group**                        | `hospital-analytics`                     | Pick one region and use it for everything below                                                         | Resource groups → + Create                           |
| 2   | **Storage account**                       | `hospitalstorage1023`                    | **Turn on "Enable hierarchical namespace"**. This is what makes it Data Lake (ADLS Gen2) storage.       | Storage accounts → + Create → **Advanced** tab       |
| 3   | **Containers**                            | `bronze`, `silver`, `gold`               | Access level: Private                                                                                   | Your storage account → **Containers** → + Container  |
| 4   | **Key Vault**                             | `hospitalvault`                          | Permission model: **Azure role-based access control**                                                   | Key vaults → + Create → **Access configuration** tab |
| 5   | **Event Hubs namespace**                  | `hospital-analytics-1023`                | **Standard tier or higher.** Basic tier does not support the Kafka connection the bronze notebook uses. | Event Hubs → + Create                                |
| 6   | **Event Hub**                             | `hospital-analytics-eh`                  | Defaults are fine                                                                                       | Your namespace → + Event Hub                         |
| 7   | **Azure Databricks workspace**            | `hospital-analytics-databricks`          | **Premium tier** (required for Unity Catalog)                                                           | Azure Databricks → + Create                          |
| 8   | **Access Connector for Azure Databricks** | `hospital-databricks-access-connector`   | System-assigned identity: On (default)                                                                  | Access Connector for Azure Databricks → + Create     |
| 9   | **Data Factory** (optional)               | `hospital-analytics-df1023`              | Defaults are fine                                                                                       | Data factories → + Create                            |
| 10  | **Synapse workspace** (optional)          | your choice (e.g. `hospital-synapse-ws`) | Same region as the storage account. Details in [Step 9B](step-09-synapse.md#9b).                        | Azure Synapse Analytics → + Create                   |

> **"Buckets" vs "containers":** AWS calls storage folders "buckets." Azure calls them "containers." Same idea.

## 0c. Azure permissions cheat sheet (who gets which role)

A **role** is a permission slip. You give one out like this:

**Where:** Azure Portal → open the resource in the "On what" column → **Access control (IAM)** → **+ Add** → **Add role assignment** → pick the role → **Members** tab → choose **User** (for people/apps) or **Managed identity** (for robots) → **Review + assign**

| Who                        | Role                                                                   | On what                       | Why                                                          | Needed?                                                      |
| -------------------------- | ---------------------------------------------------------------------- | ----------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| You                        | **Owner** (or Contributor + User Access Administrator)                 | Resource group                | Create everything and hand out roles                         | Always                                                       |
| You                        | **Key Vault Secrets Officer**                                          | `hospitalvault`               | Add and edit secrets. Being Owner does NOT include this.     | Always                                                       |
| Access connector           | **Storage Blob Data Contributor**                                      | Storage account               | Read and write bronze/silver/gold data                       | Always                                                       |
| Access connector           | **Storage Queue Data Contributor** and **Storage Account Contributor** | Storage account               | Lets Databricks watch for new files quickly                  | Only for file events ([Step 7](step-07-databricks-job.md))   |
| Access connector           | **EventGrid EventSubscription Contributor**                            | Resource group                | Same as above                                                | Only for file events ([Step 7](step-07-databricks-job.md))   |
| AzureDatabricks app        | **Key Vault Secrets User**                                             | `hospitalvault`               | Lets the Databricks secret scope read the Event Hub password | Always                                                       |
| Data Factory identity      | **Key Vault Secrets User**                                             | `hospitalvault`               | Lets ADF read the Databricks token                           | Only if using ADF                                            |
| Data Factory identity      | **Contributor**                                                        | Databricks workspace resource | Lets ADF log into Databricks without a token                 | Only for the no-token option in [Step 8](step-08-azure-data-factory.md) |
| Synapse workspace identity | **Storage Blob Data Reader**                                           | Storage account               | Lets Synapse read the gold tables                            | Only if using Synapse ([Step 9](step-09-synapse.md))         |
| You                        | **Storage Blob Data Reader**                                           | Storage account               | Lets you query gold data in Synapse with your own login      | Only if using Synapse ([Step 9](step-09-synapse.md))         |

**Event Hub works differently.** It uses a "shared access policy" (a password with limits) instead of a role.

**Where:** Azure Portal → Event Hubs → `hospital-analytics-1023` → **Shared access policies** → **+ Add**

- For Databricks, tick **Listen** only. The bronze notebook just reads.
- Whatever sends the hospital messages needs **Send**.
- Copy that policy's connection string. This is what goes into Key Vault in [Step 3](step-03-event-hub.md).

## 0d. Databricks permissions cheat sheet

Azure roles get you in the building. Databricks has its own permissions for what you can do once inside.

| Who                               | Permission                                                  | On what                                    | Why                                     | Where to set                                                                                          |
| --------------------------------- | ----------------------------------------------------------- | ------------------------------------------ | --------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| You (admin)                       | **CREATE STORAGE CREDENTIAL**, **CREATE EXTERNAL LOCATION** | Metastore                                  | To do [Step 2](step-02-databricks-storage-access.md) | Databricks website → **Catalog** → gear icon → **Metastore** → **Permissions**                        |
| Whoever runs the notebooks or job | **READ FILES**, **WRITE FILES**                             | All 3 external locations                   | To read and write data                  | **Catalog** → **External Locations** → pick one → **Permissions** tab → **Grant**                     |
| Whoever runs the notebooks or job | **READ**                                                    | Secret scope `hospitalanalyticsvaultscope` | To fetch the Event Hub password         | No button for this. Use the Databricks CLI. The person who created the scope already has full access. |
| Whoever runs the notebooks or job | Serverless compute access                                   | Workspace                                  | Notebooks and the job run on Serverless | Usually on by default. Admins: **Settings** → **Workspace admin**                                     |
| The job                           | **Run as** a user                                           | Job                                        | The job uses that person's permissions  | **Jobs & Pipelines** → your job → **Job details** → **Run as**                                        |

---

[← Overview](00-overview.md) · [Guide](../README.md) · [Step 1 — Storage →](step-01-storage.md)
