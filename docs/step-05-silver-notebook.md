# Step 5 — Notebook 2: `02_silver_clean_data` (wash and chop)

[← Guide](../configuration.md)

**Where:** Databricks website → left sidebar → **Workspace** → `02_silver_clean_data`

**In plain English:** "Take the raw messages from bronze, open them up into proper columns, fix obviously wrong values, and save to silver."

What it does:

1. Reads new rows from bronze.
2. Unpacks each message into columns: patient ID, gender, age, department, admission time, discharge time, bed ID, hospital ID.
3. Turns the time text into real dates and times.
4. Fixes bad data:
   - Missing admission time, or one in the future? Replace with "now."
   - Age over 100? Treat as a typo and replace with a random age between 1 and 90.
5. If a column is missing from a message, it adds it as blank so nothing breaks.
6. Saves to the silver folder.

No code changes were needed here.

> **Known issue:** Some patients have a discharge time that's _before_ their admission time (they "left before they arrived"). That makes their length of stay negative. This still needs fixing.

---

[← Step 4 — Bronze notebook](step-04-bronze-notebook.md) · [Guide](../configuration.md) · [Step 6 — Gold notebook →](step-06-gold-notebook.md)
