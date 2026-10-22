# Step 6 — Notebook 3: `03_gold_transform` (plate the meal)

[← Guide](../README.md)

**Where:** Databricks website → left sidebar → **Workspace** → `03_gold_transform`

**In plain English:** "Take the clean silver data and organize it into three report-friendly tables."

| Gold table          | Think of it as...                         | What's in it                                                                           |
| ------------------- | ----------------------------------------- | -------------------------------------------------------------------------------------- |
| `dim_patient`       | A patient address book that keeps history | One row per version of each patient                                                    |
| `dim_department`    | A list of departments                     | Each department + hospital combo                                                       |
| `fact_patient_flow` | The visit log                             | One row per hospital visit, linked to the patient and department, with length of stay |

**"Dim" (dimension)** tables describe _things_ (who, where). **"Fact"** tables record _events_ (what happened). Putting them together is called a **star schema**.

## What "keeps history" means (SCD Type 2)

If a patient's info changes (say their age is updated), we **don't erase the old row**. Instead:

- The old row is marked "no longer current" with an end date.
- A new row is added and marked "current."

This lets you look back and see what the data looked like at any point in time.

## The bug we fixed: duplicate ID numbers

Every patient row gets an ID number (a **surrogate key**). The original code generated IDs that **started over from 0 every run**. Since the patient table keeps growing, new patients ended up with the same IDs as old ones. Result: visits got linked to the wrong patients.

**The fix:** Before adding new patients, look up the highest ID already used, and start counting from there. Like a deli ticket machine that continues from the last number instead of resetting.

We also had to:

- Make sure the new IDs are the same number type (`long`) as the old ones, or the save fails.
- Rebuild the patient table once from scratch to clean up the old duplicate IDs. After that: 226 patients, IDs 0–225, no duplicates.

---

[← Step 5 — Silver notebook](step-05-silver-notebook.md) · [Guide](../README.md) · [Step 7 — Databricks Job →](step-07-databricks-job.md)
