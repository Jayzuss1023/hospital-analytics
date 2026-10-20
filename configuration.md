# Azure to Databricks Configuration

This guide sets up the Azure resources for the hospital analytics pipeline. A local simulator publishes patient events to Event Hubs. Databricks reads those events into a medallion lake on Azure Data Lake Storage, and Azure Data Factory runs the gold notebook when the silver layer has new files.

Finish the steps in order. Later resources depend on names, keys, and identities created earlier.

## Contents

1. [What you are building](#what-you-are-building)
2. [Before you begin](#before-you-begin)
3. [Create a resource group](#create-a-resource-group)
4. [Create Event Hubs](#create-event-hubs)
5. [Create the storage account](#create-the-storage-account)
6. [Create a Key Vault](#create-a-key-vault)
7. [Grant yourself access to Key Vault](#grant-yourself-access-to-key-vault)
8. [Store the first secrets](#store-the-first-secrets)
9. [Create Azure Databricks](#create-azure-databricks)
10. [Let Databricks read Key Vault](#let-databricks-read-key-vault)
11. [Create a Databricks secret scope](#create-a-databricks-secret-scope)
12. [Create Azure Data Factory](#create-azure-data-factory)
13. [Configure the notebooks](#configure-the-notebooks)
14. [Run the patient-flow simulator](#run-the-patient-flow-simulator)
15. [Suggested run order](#suggested-run-order)

## What you are building

| Layer | Container | What it holds |
| --- | --- | --- |
| Bronze | `bronze` | Raw event JSON from Event Hubs, preserved as it arrived |
| Silver | `silver` | Cleaned, validated records with parsed timestamps and a stable schema |
| Gold | `gold` | Patient and department dimensions, plus a fact table for reporting |
| Analytics | `synapse` | Reserved for downstream analytics such as Synapse. This guide does not create a Synapse workspace |

The notebooks that implement those layers are:

- [Bronze ingestion](databricks-notebooks/01_bronze_rawdata.py)
- [Silver cleaning](databricks-notebooks/02_silver_cleandata.py)
- [Gold transform](databricks-notebooks/03_gold_transform.py)

Each patient event has `patient_id`, `gender`, `age`, `department`, `admission_time`, `discharge_time`, `bed_id`, and `hospital_id`. The simulator occasionally sends an age over 100 or an admission time in the future. The silver notebook corrects those values.

## Before you begin

You need:

- An Azure subscription where you can create resource groups, Event Hubs, storage, Key Vault, Databricks, and Data Factory
- Permission to assign Azure roles on those resources
- Python 3.12 or newer and [uv](https://docs.astral.sh/uv/) if you will run the local simulator
- A Databricks Runtime that includes Apache Spark and Delta Lake

> [!IMPORTANT]
> Put every resource in the same resource group and region. Store connection strings, access keys, and tokens only in Key Vault or a local `.env` file. This repository ignores `.env`. Do not commit those values.

Pick names before you start and reuse them in every form and notebook. These placeholders match the notebooks:

| Placeholder | Used for |
| --- | --- |
| `<resource-group>` | Resource group that owns every resource below |
| `<region>` | Azure region shared by every resource |
| `<event-hub-namespace>` | Event Hubs namespace |
| `<event-hub-name>` | Event Hub inside that namespace. This is the Kafka topic name |
| `<storage-account>` | Storage account name. Lowercase letters and numbers only |
| `<key-vault>` | Key Vault name |
| `<scope-name>` | Databricks secret scope backed by that Key Vault |

## Create a resource group

The later steps all say to use the resource group you already created. Create it first.

1. Open the [Azure portal](https://portal.azure.com).
2. Search for **Resource groups**.
3. Select **Create**.
4. Choose your subscription, then enter `<resource-group>` and `<region>`.
5. Select **Review + create**, then **Create**.

## Create Event Hubs

Event Hubs is the streaming source. The simulator and the bronze notebook both connect with the Kafka protocol on port `9093`, which requires the **Standard** pricing tier or higher.

1. In the portal search bar, search for **Event Hubs**.
2. Select **Create** to create a namespace.
3. Use `<resource-group>`, `<region>`, and `<event-hub-namespace>`.
4. Set the pricing tier to **Standard** or higher.
5. Select **Review + create**, then **Create**.
6. When deployment finishes, select **Go to resource**.
7. On the namespace **Overview** page, select **+ Event Hub**.
8. Name it `<event-hub-name>` and create it.
9. Open that Event Hub, then go to **Settings** > **Shared access policies**.
10. Add a policy that includes **Send** and **Listen**. The simulator sends events. Databricks listens to them.
11. Copy the policy **Primary connection string**. You will store it in Key Vault in a later step.

The Kafka host name is `<event-hub-namespace>.servicebus.windows.net`. Use that full host anywhere a notebook or `.env` value asks for the namespace.

## Create the storage account

The notebooks write Delta tables with `abfss://` paths, and Data Factory connects with an Azure Data Lake Storage Gen2 linked service. The account must be Data Lake Storage Gen2.

1. Search for **Storage accounts**.
2. Select **Create** and use `<resource-group>` and `<region>`.
3. Name the account `<storage-account>`.
4. On the **Advanced** tab, enable **Hierarchical namespace**. This setting cannot be changed after the account is created.
5. Select **Review + create**, then **Create**.
6. Open the new account from **Overview** > **Go to resource**, or from the deployment details.
7. On the left, go to **Data storage** > **Containers**.
8. Select **+ Container** and create these four containers:

| Container | Purpose |
| --- | --- |
| `bronze` | Raw streaming landing zone |
| `silver` | Cleaned Delta data. Data Factory watches this container |
| `gold` | Dimension and fact tables |
| `synapse` | Extra container for a later analytics tool |

9. Go to **Security + networking** > **Access keys**.
10. Copy **key1**. You will store it in Key Vault. Leave the key in place. The silver notebook uses it to authenticate to the lake.

Delta paths in the notebooks look like this:

```text
abfss://<container>@<storage-account>.dfs.core.windows.net/<path>
```

Use the `dfs.core.windows.net` host. That is the Data Lake endpoint.

## Create a Key Vault

1. Search for **Key vaults**.
2. Select **Create** and use `<resource-group>` and `<region>`.
3. Name it `<key-vault>`.
4. On the access configuration step, set the permission model to **Azure role-based access control**. The steps below assign roles from **Access control (IAM)**.
5. Select **Review + create**, then **Create**.
6. When deployment finishes, select **Go to resource**.

## Grant yourself access to Key Vault

Assign this role before you create secrets. With role-based access control, secret creation fails until the assignment exists. Role changes can take a minute to apply.

1. On the Key Vault, select **Access control (IAM)**.
2. Select **Add** > **Add role assignment**.
3. Search for and select **Key Vault Administrator**.
4. Open the **Members** tab.
5. Select **Select members**, choose your own user account, then confirm.
6. Select **Review + assign**.

## Store the first secrets

On the Key Vault, expand **Objects** > **Secrets** > **Generate/Import**. Create these two secrets now. The Databricks token is added after the workspace exists. The names below are suggestions. Use the same names later in `dbutils.secrets.get`.

| Suggested secret name | Where to copy the value |
| --- | --- |
| `event-hub-connection-string` | Event Hub shared access policy, **Primary connection string** |
| `storage-account-key` | Storage account **Access keys**, **key1** |

For each secret, paste the value into **Secret value**, then select **Create**.

## Create Azure Databricks

1. Search for **Azure Databricks**.
2. Select **Create** and use `<resource-group>` and `<region>`.
3. Complete the workspace form, then create it.
4. Open the resource and select **Launch Workspace**.
5. In the workspace, select **Compute** on the left.
6. Create a cluster with a Databricks Runtime that includes Delta Lake.
7. Start the cluster before you run a notebook or a Data Factory notebook activity.

While you are in the workspace, import the three notebooks under `databricks-notebooks/` or recreate them there. Data Factory will call the gold notebook by its workspace path, so note that path. It is usually similar to:

```text
/Users/<your-email>/<gold-notebook-name>
```

## Let Databricks read Key Vault

1. Return to the Key Vault in the Azure portal.
2. Select **Access control (IAM)** > **Add** > **Add role assignment**.
3. Choose the **Key Vault Secrets User** role.
4. On the **Members** tab, select **Select members**.
5. Search for and select **AzureDatabricks**.
6. Select **Review + assign**.

## Create a Databricks secret scope

The bronze notebook reads the Event Hubs connection string with `dbutils.secrets.get`. A Key Vault-backed scope is what makes that call work.

1. In the browser address bar for your Databricks workspace, delete everything after `.net`, then add `#secrets/createScope`.

   ```text
   https://<databricks-instance>#secrets/createScope
   ```

2. On the scope page, enter `<scope-name>` and keep it. The notebooks need this exact name.
3. On the Key Vault, go to **Settings** > **Properties** and copy the values into the scope form:

   | Key Vault property | Databricks scope field |
   | --- | --- |
   | Vault URI | DNS Name |
   | Resource ID | Resource ID |

4. Create the scope.

Secret names inside the scope are the Key Vault secret names from the table above, such as `event-hub-connection-string`.

## Create Azure Data Factory

Data Factory watches the silver folder. When that folder contains at least five child items, the pipeline runs the gold notebook.

Create the factory before you assign its role. The managed identity does not exist until the factory does.

### Create a Databricks access token

1. In the Databricks workspace, open your profile menu, then **Settings** > **Developer** > **Access tokens**.
2. Select **Manage**, then **Generate new token**.
3. Copy the token immediately. Databricks shows it only once.

### Create the factory

1. In the Azure portal, search for **Data factories**.
2. Select **Create**, choose `<resource-group>`, and finish the form.
3. Open the factory. Its managed identity is now available for role assignment.

### Store the token and grant the factory access

1. In Key Vault, create another secret:

   | Secret name | Value |
   | --- | --- |
   | `databricks-access-token` | Token generated above |

2. On the same Key Vault, select **Access control (IAM)** > **Add** > **Add role assignment**.
3. Choose **Key Vault Secrets User**.
4. On the **Members** tab, choose **Managed identity**, then **Select members**.
5. Select your Data Factory, then **Review + assign**.

### Create linked services

1. On the Data Factory **Overview** page, select **Launch Studio**.
2. On the left, select **Manage** > **Linked services** > **Create**.
3. Create the Key Vault linked service and point it at `<key-vault>`.
4. Select **Publish all**. Linked services are not available to the other connections until you publish.

> [!WARNING]
> Publish after each linked service, dataset, pipeline, and trigger. Studio keeps those objects as drafts until you select **Publish all**.

5. Create the second linked service. Select **New**, switch from **Data store** to **Compute**, and choose **Azure Databricks**.
6. Select your workspace. For **Authentication type**, choose **Azure Key Vault**, then select the Key Vault linked service and the `databricks-access-token` secret.
7. Create the third linked service. Select **New**, stay on **Data store**, and choose **Azure Data Lake Storage Gen2**. Point it at `<storage-account>`.
8. Select **Publish all** again.

### Create the silver dataset

1. Select **Author**.
2. Next to the factory tab, select **+** > **Dataset** > **Azure Data Lake Storage Gen2** > **Parquet**.
3. Select the storage linked service.
4. Set the path to the silver folder. **Get Metadata** lists child items from a folder path.

### Create the pipeline

1. Select **+** > **Pipeline**.
2. Search for **Get Metadata**, then drag it onto the canvas.
3. On **General**, name the activity. The name you type here is the name used in the expression below. This guide uses `GetSilverMetadata`.
4. On **Settings**, set **Dataset** to the Parquet dataset and **Field list** to **Child items**.
5. Search for **If Condition**, drag it onto the canvas, and connect **Get Metadata** to it.
6. Select the If Condition. On **General**, name it. On **Activities**, set **Expression** to:

   ```text
   @greaterOrEquals(length(activity('GetSilverMetadata').output.childItems), 5)
   ```

   Replace `GetSilverMetadata` if you chose another activity name. The pipeline runs the gold notebook when silver has at least five child items.

7. With the If Condition selected, open the **True** branch and add a **Notebook** activity.
8. On **General**, name the activity.
9. On **Azure Databricks**, select the Databricks linked service.
10. On **Settings**, set the notebook path to the gold notebook in your workspace, for example `/Users/<your-email>/<gold-notebook-name>`.
11. On the pipeline canvas, select **Add trigger** > **New/Edit**.
12. Name the trigger and set a schedule so the pipeline keeps checking the If Condition.
13. Select **Publish all**.

## Configure the notebooks

Replace every `<<...>>` placeholder before running a notebook. Read secrets from `<scope-name>` instead of pasting them into notebook cells.

The bronze notebook needs:

- `event_hub_namespace` set to `<event-hub-namespace>.servicebus.windows.net`
- `event_hub_name` set to `<event-hub-name>`
- The connection string from `dbutils.secrets.get(scope="<scope-name>", key="event-hub-connection-string")`
- A bronze Delta path and a separate checkpoint path, both under the `bronze` container

The silver notebook should take the storage key from the scope:

```python
spark.conf.set(
    "fs.azure.account.key.<storage-account>.dfs.core.windows.net",
    dbutils.secrets.get(scope="<scope-name>", key="storage-account-key"),
)
```

Point its bronze path at the bronze Delta location and its silver path at the `silver` container.

The gold notebook reads silver and writes three paths under `gold`:

| Path | Table |
| --- | --- |
| Patient dimension | Latest patient attributes, with history when gender or age changes |
| Department dimension | Distinct department and hospital pairs |
| Fact | One row per latest admission, including length of stay and whether the patient is still admitted |

## Run the patient-flow simulator

The simulator lives at [simulator/patient_flow_generator.py](simulator/patient_flow_generator.py). From the repository root, install the project and create a `.env` file with the Event Hubs values:

```bash
uv sync
```

```text
AZURE_EVENTHUBS_NAMESPACE=<event-hub-namespace>.servicebus.windows.net
AZURE_EVENT_HUB_NAME=<event-hub-name>
AZURE_CONNECTION_STRING=<primary-connection-string>
```

Then start the producer:

```bash
uv run python simulator/patient_flow_generator.py
```

The script sends one patient event each second. Leave it running while the bronze stream is active.

## Suggested run order

- [ ] Resource group, Event Hubs, storage account, and Key Vault exist in one region.
- [ ] Your user is **Key Vault Administrator**, and the three secrets exist.
- [ ] The Databricks cluster is running, and `<scope-name>` can read Key Vault.
- [ ] The bronze notebook is written with placeholders replaced, then the simulator is sending events.
- [ ] The silver notebook has cleaned those events into the silver folder.
- [ ] Data Factory linked services, the silver dataset, the pipeline, and the schedule trigger are published.
- [ ] After silver has at least five child items, the trigger runs the gold notebook.
- [ ] The gold notebook shows the patient dimension, department dimension, and fact table.

## Further reading

- [Azure Event Hubs for Apache Kafka](https://learn.microsoft.com/en-us/azure/event-hubs/azure-event-hubs-kafka-overview)
- [Create a storage account with hierarchical namespace](https://learn.microsoft.com/en-us/azure/storage/blobs/create-data-lake-storage-account)
- [Key Vault role-based access control](https://learn.microsoft.com/en-us/azure/key-vault/general/rbac-guide)
- [Create an Azure Key Vault-backed Databricks secret scope](https://learn.microsoft.com/en-us/azure/databricks/security/secrets/secret-scopes)
- [Data Factory linked services](https://learn.microsoft.com/en-us/azure/data-factory/concepts-linked-services)
