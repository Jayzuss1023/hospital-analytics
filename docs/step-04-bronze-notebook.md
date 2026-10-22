# Step 4 — Notebook 1: `01_bronze_raw_data` (grab the groceries)

[← Guide](../README.md)

**Where:** Databricks website → left sidebar → **Workspace** → `01_bronze_raw_data`

**In plain English:** "Go check the mailbox, take every new message, and save it to the bronze folder exactly as-is."

What it does, step by step:

1. Connects to Event Hub.
2. Reads all the new messages.
3. Saves them to the bronze folder as raw text.
4. Counts how many new messages it saved and remembers that number (`new_rows`) so later steps know whether there's anything to do.

**A "checkpoint"** is like a bookmark. It remembers which messages were already read, so the next run only picks up new ones.

## Problems we hit and how we fixed them

| Problem                 | What went wrong (simple version)                                                                                                             | Fix                                                          |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| `SyntaxError`           | A stray `%python` line was sitting in the middle of the code. That command is only allowed on the very first line of a cell.                 | Deleted it.                                                  |
| `sum()` crashed         | The line `from pyspark.sql.functions import *` quietly replaced Python's normal `sum` with a different one that only works on table columns. | Used `builtins.sum(...)` to get Python's normal `sum` back. |
| `TypeError` with `None` | Sometimes the row count was blank (`None`) instead of 0. You can't add blank to a number.                                                    | Wrote `(value or 0)`, which means "if it's blank, use 0."   |

> **Heads up:** Cell 2 in this notebook adds one fake test patient. Every time you run it, it adds another copy. Don't run it over and over.

---

[← Step 3 — Event Hub](step-03-event-hub.md) · [Guide](../README.md) · [Step 5 — Silver notebook →](step-05-silver-notebook.md)
