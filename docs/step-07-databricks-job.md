# Step 7 — Make it run automatically (Databricks Job)

[← Guide](../configuration.md)

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

- The bronze notebook ran but found no new messages (nothing new got saved).
- Files were deleted or changed rather than added.

**If it never starts:**

1. Turn on **file events** for `hospital_bronze_storage` (Databricks website → **Catalog** → **External Locations** → `hospital_bronze_storage`). This makes the job notice new files much faster and more reliably.
2. Check the job page for errors (Databricks website → **Jobs & Pipelines** → your job).
3. Turn on email alerts for failures so you find out right away (same job page → **Job notifications**).
4. Make sure you have read permission on the storage location (Databricks website → **Catalog** → **External Locations** → **Permissions** tab).

---

[← Step 6 — Gold notebook](step-06-gold-notebook.md) · [Guide](../configuration.md) · [Step 8 — Azure Data Factory →](step-08-azure-data-factory.md)
