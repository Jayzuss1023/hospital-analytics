# Step 2 — Give Databricks permission to use the storage

[← Guide](../README.md)

**Where:** Two places — first Azure, then Databricks.

- **Azure Portal:** search **Access Connector for Azure Databricks** to create the connector. Then go to your storage account → **Access control (IAM)** → give the connector the **Storage Blob Data Contributor** role.
- **Databricks website:** left sidebar → **Catalog** → gear icon / **External data** → **Credentials** (for the key card) and **External Locations** (for the doors).

Databricks needs a "key card" to get into the storage. We set this up in **Unity Catalog** (the Databricks security desk):

1. **Storage Credential** (`hospitalstoragecredential`) — the key card itself. It's linked to an Azure identity called `hospital-databricks-access-connector`.
2. **External Locations** — one for each folder, telling Databricks "this key card opens this door":
   - `hospital_bronze_storage` → bronze container
   - `hospital_silver_storage` → silver container
   - `hospital_gold_storage` → gold container

> **Why not just paste the storage password into the code?** Our Databricks uses **Serverless** compute (Databricks manages the computers for you). Serverless doesn't allow that old method. It's also less safe. Unity Catalog is the modern, secure way.

**Three Serverless rules to remember:**

- Don't put storage passwords in the code.
- Use full addresses that start with `abfss://` (not `dbfs:/mnt/`).
- Streams must use `availableNow=True`, which means "process everything that's waiting, then stop." Serverless can't run a stream forever.

---

[← Step 1 — Storage](step-01-storage.md) · [Guide](../README.md) · [Step 3 — Event Hub →](step-03-event-hub.md)
