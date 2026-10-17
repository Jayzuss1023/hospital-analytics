# Microsoft Azure to Databricks Configuration

This guide connects a local patient-flow simulator to Azure Event Hubs, then lands the raw stream in a bronze Delta table on Azure Data Lake Storage (ADLS) Gen2. Databricks reads secrets from Azure Key Vault. Later layers clean that data (silver) and publish analytics tables (gold).

Keep every resource in the **same resource group and region**.

The repo currently implements the producer and the bronze notebook only:

- `simulator/patient_flow_generator.py` publishes events to Event Hubs.
- `databricks-notebooks/01_bronze_rawdata.py` reads that stream into bronze.

Silver, gold, and Synapse are storage containers reserved for later stages.

## Prerequisites

- An Azure subscription, and Contributor or Owner on the resource group.
- Azure Databricks workspace access (you can launch the workspace and create compute).
- Python 3.12 or newer and [uv](https://docs.astral.sh/uv/) for the local simulator.

## 1. Create a resource group

1. Sign in to the [Azure portal](https://portal.azure.com).
2. Search for **Resource groups** and create one.
3. Use this resource group for Event Hubs, Databricks, the storage account, Key Vault, and the Access Connector.

## 2. Create an Event Hubs namespace

1. In the portal search bar, search for **Event Hubs**.
2. Select **Create**.
3. Choose the resource group from step 1.
4. Set the pricing tier to **Standard** or higher. The Kafka endpoint on port `9093` is not available on the Basic tier, and both the simulator and the Spark notebook depend on it.
5. Leave public network access enabled unless you have a private endpoint plan for both your laptop and Databricks.
6. Create the namespace. When the deployment finishes, open **Overview** and select **Go to resource**.

## 3. Create an Event Hub

1. On the namespace **Overview** page, select **+ Event Hub**.
2. Name the hub. This value is `EVENT_HUB_NAME` in `.env` and `event_hub_name` in the notebook.
3. Start with 2 or more partitions if you expect parallel consumers. One partition is enough for this simulator.
4. Create the hub.

### Shared access policies

The simulator sends. Databricks listens. You can use one policy with both rights, or split them.

1. Open the Event Hub (or the namespace) and go to **Settings** → **Shared access policies**.
2. Create a policy, or open the existing root policy.
3. Enable **Send** for the local producer and **Listen** for the notebook. **Manage** includes both.
4. Copy the **Primary connection string**.

Use a namespace-level connection string when you can. A string that already contains `EntityPath=` is bound to one hub. The notebook also sets the hub name in `subscribe`, so prefer the namespace string and let `subscribe` choose the hub.

Do not paste this string into the notebook or commit it. Store it in Key Vault in step 7.

## 4. Create Azure Databricks

1. Search for **Azure Databricks**.
2. Create the workspace in the same resource group.
3. After deployment, open the resource and select **Launch Workspace**.
4. In the workspace, open **Compute**, create a cluster, and start it when you are ready to run the classic-cluster notebook.

Serverless compute does not use this cluster. If you use serverless, skip starting a classic cluster and follow [Serverless compute](#serverless-compute) before running the notebook.

## 5. Create a storage account

1. Search for **Storage accounts** and create one in the same resource group.
2. On the **Advanced** tab, enable **Hierarchical namespace**. `abfss://` paths require ADLS Gen2. This setting is chosen at creation time.
3. After deployment, open **Overview** → **Deployment details** and select the new storage account.

### Containers

The medallion layout uses three layers. This project also reserves a fourth container for Synapse.

| Container | Purpose |
| --- | --- |
| `bronze` | Raw events, preserved as landed |
| `silver` | Cleaned, validated, and de-duplicated data |
| `gold` | Refined tables for analytics and reporting |
| `synapse` | Staging area for a later Synapse workspace |

1. On the left, open **Data storage** → **Containers**.
2. Select **+ Container** and create `bronze`, `silver`, `gold`, and `synapse`.
3. Use lowercase names. Container names are case-sensitive in the `abfss` path.

### Account key

1. Open **Security + networking** → **Access keys**.
2. Copy **key1**. You will store it as a Key Vault secret. The classic notebook reads it from the secret scope.

If the storage account firewall is restricted later, allow the Databricks Access Connector (serverless) or trusted Azure services (classic) before expecting `abfss` reads and writes to succeed.

## 6. Create a Key Vault

1. Search for **Key Vault** and create one in the same resource group.
2. On the access configuration step, choose **Azure role-based access control**. The IAM steps below do nothing useful if the vault is left on vault access policies.
3. After deployment, select **Go to resource**.

## 7. Store secrets

Suggested secret names, matching the notebook samples below:

| Secret name | Value |
| --- | --- |
| `eventhub-connection` | Event Hubs primary connection string from step 3 |
| `storage-connection` | Storage account key1 from step 5 |

For each secret:

1. On the Key Vault, expand **Objects** → **Secrets**.
2. Select **Generate/Import**.
3. Enter the name and paste the value into **Secret value**.
4. Create the secret.

Role assignment can take a few minutes to propagate. If **Generate/Import** is disabled, finish step 8 first.

## 8. Grant yourself Key Vault Administrator

1. On the Key Vault, open **Access control (IAM)**.
2. Select **Add** → **Add role assignment**.
3. Choose **Key Vault Administrator**.
4. Open the **Members** tab, select **Select members**, and choose your user.
5. Select **Review + assign**.

This role lets you create and read secrets in the portal. It is separate from the Databricks role in the next step.

## 9. Grant Databricks access to Key Vault

1. Still under **Access control (IAM)**, select **Add** → **Add role assignment**.
2. Choose **Key Vault Secrets User**.
3. Open the **Members** tab, select **Select members**, and search for **AzureDatabricks**.
4. Select **Review + assign**.

**Key Vault Secrets User** allows Databricks to read secret values. It does not allow Databricks to change them.

## 10. Create a Databricks secret scope

A Key Vault-backed scope maps a scope name to this vault. The notebook then calls `dbutils.secrets.get`. The method name is `dbutils`, not `dbtutils`.

1. Copy the workspace URL and delete everything after `.net`.
2. Append `#secrets/createScope`.

```text
https://<databricks-instance>.azuredatabricks.net#secrets/createScope
```

Example: `https://adb-1234567890123456.7.azuredatabricks.net#secrets/createScope`

3. On the Key Vault, open **Settings** → **Properties**.
4. Fill in the scope page:

| Scope field | Key Vault property |
| --- | --- |
| Scope Name | A name you choose, such as `hospitalanalyticsvaultscope` |
| DNS Name | Vault URI |
| Resource ID | Resource ID |

5. Save the scope name. It is the `scope` argument in the notebook.

Manage Principal **Creator** limits who can use the scope. Choose **All Users** in the workspace if other people run the notebook.

## Placeholder reference

Replace every `<<...>>` token before running a cell. Do not commit real connection strings or account keys.

| Placeholder | Source |
| --- | --- |
| `<<databricks_scope>>` | Scope name from step 10 |
| `<<eventhub_connection_name>>` | Key Vault secret name for the Event Hubs connection string |
| `<<storage_connection_name>>` | Key Vault secret name for the storage account key |
| `<<event_hub_namespace>>` | Host name only, such as `mynamespace.servicebus.windows.net` |
| `<<event_hub_name>>` | Event Hub name from step 3 |
| `<<storage_account_name>>` | Storage account name from step 5 |
| `<<container>>` | `bronze` for this notebook |
| `<<path>>` | Folder inside the container, such as `patient_flow` |

`abfss` paths use the DFS endpoint:

```text
abfss://<<container>>@<<storage_account_name>>.dfs.core.windows.net/<<path>>
```

The host is `dfs.core.windows.net`. A path that stops at `.core.windows.net` does not resolve for ADLS Gen2.

## Classic cluster notebook

Use this pattern when the notebook runs on the cluster from step 4. The cluster must be running.

`startingOffsets` of `latest` reads only events that arrive after the stream starts. Start the notebook, then start the simulator, or switch to `earliest` when you need events already sitting in the hub.

The Kafka client on Databricks is shaded, so the JAAS login module must be `kafkashaded.org.apache.kafka.common.security.plain.PlainLoginModule`.

Spark writes a checkpoint so a restarted query continues from the last committed batch. Point that checkpoint at ADLS. A `dbfs:/mnt/...` path works only after you create a mount, and these steps never create one.

```python
from pyspark.sql.functions import *

# Azure Event Hub configuration
event_hub_namespace = "<<event_hub_namespace>>"
event_hub_name = "<<event_hub_name>>"
event_hub_conn_str = dbutils.secrets.get(
    scope="<<databricks_scope>>",
    key="<<eventhub_connection_name>>",
)

kafka_options = {
    "kafka.bootstrap.servers": f"{event_hub_namespace}:9093",
    "subscribe": event_hub_name,
    "kafka.security.protocol": "SASL_SSL",
    "kafka.sasl.mechanism": "PLAIN",
    "kafka.sasl.jaas.config": (
        "kafkashaded.org.apache.kafka.common.security.plain.PlainLoginModule required "
        f'username="$ConnectionString" password="{event_hub_conn_str}";'
    ),
    "startingOffsets": "latest",
    "failOnDataLoss": "false",
}

# Read from Event Hubs through the Kafka API
raw_df = (
    spark.readStream
    .format("kafka")
    .options(**kafka_options)
    .load()
)

# Kafka stores the payload as bytes. Cast it back to a JSON string.
json_df = raw_df.selectExpr("CAST(value AS STRING) as raw_json")

# ADLS configuration (classic cluster, account key from Key Vault)
spark.conf.set(
    "fs.azure.account.key.<<storage_account_name>>.dfs.core.windows.net",
    dbutils.secrets.get(
        scope="<<databricks_scope>>",
        key="<<storage_connection_name>>",
    ),
)

bronze_path = "abfss://<<container>>@<<storage_account_name>>.dfs.core.windows.net/<<path>>"
checkpoint_path = "abfss://<<container>>@<<storage_account_name>>.dfs.core.windows.net/_checkpoints/<<path>>"

# Append each micro-batch. The checkpoint is a different folder from the table path.
(
    json_df
    .writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", checkpoint_path)
    .start(bronze_path)
)
```

## Serverless compute

Serverless Spark does not accept the account-key setting above. ADLS access goes through an Azure Access Connector and a managed identity.

### In the Azure portal

1. Sign in as a Contributor or Owner on the resource group.
2. Select **Create a resource**.
3. Search for **Access Connector for Azure Databricks** and select **Create**.
4. On **Basics**, select the same resource group and region, then name the connector.
5. Select **Next**. Add tags if you want them, then select **Next**.
6. On **Managed Identity**, set the system-assigned identity **Status** to **On**.
7. Select **Review + create**, then **Create**.
8. Open the new connector's **Overview** page and copy the **Resource ID**.

### Grant the connector access to storage

1. Open the storage account from step 5.
2. Go to **Access control (IAM)** → **Add** → **Add role assignment**.
3. Choose **Storage Blob Data Contributor**.
4. On **Members**, select the Access Connector's managed identity (the connector resource name).
5. Select **Review + assign**.

### In Databricks

1. Open **Catalog** → **External Data** → **Credentials**.
2. Create a storage credential of type **Azure Managed Identity** and paste the Access Connector resource ID.
3. Create or update an external location for `abfss://bronze@<<storage_account_name>>.dfs.core.windows.net/` that uses this credential.

Wait a few minutes after the role assignment before the first serverless write.

Serverless queries should checkpoint on `abfss` as well. `trigger(availableNow=True)` processes the data available now and then stops, which fits a serverless notebook session that is not meant to stay up. Omit that trigger on a classic cluster when you want a continuous stream.

Keep using `dbutils.secrets.get` for the Event Hubs connection string. Serverless changes how ADLS is authorized. It does not require the connection string to be hardcoded.

```python
from pyspark.sql.functions import *

event_hub_namespace = "<<event_hub_namespace>>"
event_hub_name = "<<event_hub_name>>"
event_hub_conn_str = dbutils.secrets.get(
    scope="<<databricks_scope>>",
    key="<<eventhub_connection_name>>",
)

kafka_options = {
    "kafka.bootstrap.servers": f"{event_hub_namespace}:9093",
    "subscribe": event_hub_name,
    "kafka.security.protocol": "SASL_SSL",
    "kafka.sasl.mechanism": "PLAIN",
    "kafka.sasl.jaas.config": (
        "kafkashaded.org.apache.kafka.common.security.plain.PlainLoginModule required "
        f'username="$ConnectionString" password="{event_hub_conn_str}";'
    ),
    "startingOffsets": "latest",
    "failOnDataLoss": "false",
}

raw_df = (
    spark.readStream
    .format("kafka")
    .options(**kafka_options)
    .load()
)

json_df = raw_df.selectExpr("CAST(value AS STRING) as raw_json")

bronze_path = "abfss://<<container>>@<<storage_account_name>>.dfs.core.windows.net/<<path>>"
checkpoint_path = "abfss://<<container>>@<<storage_account_name>>.dfs.core.windows.net/_checkpoints/<<path>>"

(
    json_df
    .writeStream
    .format("delta")
    .outputMode("append")
    .trigger(availableNow=True)
    .option("checkpointLocation", checkpoint_path)
    .start(bronze_path)
)
```

## Local simulator

`simulator/patient_flow_generator.py` reads credentials from a `.env` file in the project root. That file is gitignored. Never commit it.

```dotenv
EVENTHUBS_NAMESPACE=<<event_hub_namespace>>
EVENT_HUB_NAME=<<event_hub_name>>
CONNECTION_STRING=<<event_hubs_primary_connection_string>>
```

`EVENTHUBS_NAMESPACE` is the host name only (`your-namespace.servicebus.windows.net`), with no `https://` and no port. The producer appends `:9093`.

From the repository root:

```bash
uv sync
uv run python simulator/patient_flow_generator.py
```

The producer sends one event per second. Each event includes `patient_id`, `gender`, `age`, `department`, `admission_time`, `discharge_time`, `bed_id`, and `hospital_id`. About 5% of events are intentionally dirty (an admission time in the future, or an age above 100) so later silver cleaning has something to catch.

With `startingOffsets` set to `latest`, events sent before the Databricks stream starts are skipped. Start the notebook stream first, then run the simulator.

## Notes that are easy to miss

- **Resource group first.** Databricks, storage, and Key Vault all say "use the created resource group," so create that group before those resources.
- **Event Hubs Standard or higher.** Basic namespaces have no Kafka endpoint, so the producer and the notebook cannot connect.
- **Four containers, three medallion layers.** `bronze`, `silver`, and `gold` are the medallion layout. `synapse` is extra and unused by the current notebook.
- **Hierarchical namespace.** Turn it on when the storage account is created, or `abfss` will not work.
- **Key Vault must use Azure RBAC.** **Key Vault Administrator** is for you. **Key Vault Secrets User** is for the **AzureDatabricks** enterprise application. A new RBAC assignment can take a few minutes.
- **Secret scope URL.** Only the host through `.net` stays. The fragment is `#secrets/createScope`.
- **`dbutils.secrets.get`.** Do not print secret values. Databricks redacts them, and the notebook should read both the Event Hubs string and, on a classic cluster, the storage key from the scope.
- **Classic versus serverless storage auth.** Classic uses `spark.conf.set` with the account key. Serverless uses the Access Connector, a storage credential, and an external location. Do not mix the account-key config into a serverless notebook.
- **Checkpoints.** Keep `checkpointLocation` on a different path from the Delta table. Use `abfss://.../_checkpoints/...` unless you have already mounted DBFS. The checked-in notebook still points the checkpoint at `dbfs:/mnt/bronze/_checkpoints/patient_flow`, which needs a mount these steps do not create.
- **`latest` drops history.** Events produced before the query starts are ignored until you change `startingOffsets` to `earliest` or restart with a new checkpoint.
- **Permissions on the connection string.** The simulator needs **Send**. The notebook needs **Listen**.
