# The big picture and the tools

[← Guide](../configuration.md)

This is the plain-English version of the main [README.md](../README.md). No prior experience with Azure or Databricks is needed. If a word is unfamiliar, check the [Glossary](glossary.md).

---

## The big picture (in one paragraph)

A hospital sends out little messages every time a patient is admitted (for example: "Patient 123, age 45, went to Cardiology at 9:00 AM"). This project **catches those messages, cleans them up, and organizes them into neat tables** so someone can build reports like "How long do patients stay in each department?"

We do this in three stages, like a kitchen:

| Stage      | Kitchen analogy                 | What happens to the data                                                           |
| ---------- | ------------------------------- | ---------------------------------------------------------------------------------- |
| **Bronze** | Groceries dumped on the counter | Raw messages saved exactly as they arrived. Nothing is changed.                    |
| **Silver** | Washed and chopped vegetables   | Messages are opened up, bad values are fixed, and everything gets proper columns. |
| **Gold**   | The finished meal on a plate    | Data is organized into report-ready tables (patients, departments, visits).        |

This three-step pattern is called the **medallion architecture** (bronze, silver, gold — like medals).

---

## The tools involved (who does what)

| Tool                               | What it is                                            | Its job in this project                                                          | Where you work with it                        |
| ---------------------------------- | ----------------------------------------------------- | -------------------------------------------------------------------------------- | --------------------------------------------- |
| **Azure Event Hub**                | A mailbox that receives a constant stream of messages | Receives the patient messages from the hospital                                 | Azure Portal                                  |
| **Azure Data Lake Storage (ADLS)** | A giant online hard drive                             | Stores the bronze, silver, and gold data in three folders (called "containers") | Azure Portal                                  |
| **Azure Key Vault**                | A locked safe for passwords                           | Holds secret passwords so they never appear in code                             | Azure Portal                                  |
| **Databricks**                     | A place to write and run data-processing code         | Runs the three notebooks that move data bronze → silver → gold                  | Databricks website (your workspace)           |
| **Databricks Job**                 | An automatic scheduler                                | Runs the notebooks for you when new data shows up                               | Databricks website → Jobs & Pipelines         |
| **Azure Data Factory (ADF)**       | Another scheduler, from Microsoft                     | Optional alternative to the Databricks Job                                      | ADF Studio (opened from the Azure Portal)     |
| **Azure Synapse Analytics**        | A SQL tool for reporting on data in the lake          | Lets you query the gold tables with SQL and build KPI views                     | Synapse Studio (opened from the Azure Portal) |
| **Azure Monitor (Alerts)**         | Azure's alarm system                                  | Emails you when an ADF pipeline run fails                                       | Azure Portal → Monitor                        |

### The websites you'll be using

| Name                               | Address                                               | How to get there                                                                                 |
| ---------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| **Azure Portal**                   | `https://portal.azure.com`                            | Sign in with your Azure account                                                                  |
| **Databricks website (workspace)** | `https://adb-<your-workspace-id>.azuredatabricks.net` | Azure Portal → search "Azure Databricks" → click your workspace → **Launch Workspace**           |
| **ADF Studio**                     | `https://adf.azure.com`                               | Azure Portal → search "Data factories" → click your factory → **Launch Studio**                  |
| **Synapse Studio**                 | `https://web.azuresynapse.net`                        | Azure Portal → search "Azure Synapse Analytics" → click your workspace → **Open Synapse Studio** |

---

[Guide](../configuration.md) · [Step 0 — Azure accounts and resources →](step-00-azure-accounts-and-resources.md)
