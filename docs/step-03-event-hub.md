# Step 3 — Set up the mailbox (Event Hub)

[← Guide](../README.md)

**Where:** Mostly Azure Portal, with one setup step on the Databricks website.

1. **Azure Portal → Event Hubs:** Create an Event Hub namespace (`hospital-analytics-1023`) and an Event Hub inside it (`hospital-analytics-eh`).
2. **Azure Portal → Event Hubs → your namespace → Shared access policies:** Copy the **connection string** (basically its password).
3. **Azure Portal → Key vaults → your vault → Secrets:** Paste it in as a new secret named `eventhub-connection`.
4. **Databricks website:** Connect Databricks to the vault by creating a secret scope (`hospitalanalyticsvaultscope`). You do this by adding `#secrets/createScope` to the end of your workspace address.
5. **Databricks notebook:** The code fetches that password from the vault with `dbutils.secrets.get(...)`. The password never appears in the notebook.

---

[← Step 2 — Databricks storage access](step-02-databricks-storage-access.md) · [Guide](../README.md) · [Step 4 — Bronze notebook →](step-04-bronze-notebook.md)
