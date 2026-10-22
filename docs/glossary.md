# Glossary

[← Guide](../README.md)

| Term                                | Plain-English meaning                                                                                   |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------- |
| **Pipeline**                        | A series of steps data goes through, like an assembly line                                              |
| **Notebook**                        | A document where you write and run code in small chunks called cells                                    |
| **Cell**                            | One block of code in a notebook                                                                         |
| **Delta table**                     | A smart file format for tables that keeps a history of changes and won't get corrupted if a write fails |
| **Stream**                          | Reading data that keeps arriving, instead of a one-time file                                            |
| **Checkpoint**                      | A bookmark that remembers what has already been processed                                               |
| **Serverless**                      | Databricks runs the computers for you; you just run code                                                |
| **Unity Catalog**                   | Databricks' security and organization system for data                                                   |
| **Container**                       | A top-level folder in Azure storage                                                                     |
| **Connection string / token / PAT** | Different kinds of passwords that let one system log into another                                       |
| **Key Vault**                       | Azure's password safe                                                                                   |
| **Trigger**                         | Something that starts a job automatically                                                               |
| **Surrogate key**                   | An ID number we create for each row (instead of using the hospital's own ID)                            |
| **SCD Type 2**                      | A way of updating records that keeps the old versions instead of overwriting them                       |
| **Star schema**                     | Organizing data as one central "events" table connected to "descriptions" tables                        |
| **Medallion architecture**          | The bronze → silver → gold approach to cleaning data in stages                                          |
| **Subscription**                    | Your Azure billing account                                                                              |
| **Resource group**                  | A folder in Azure that holds all the services for one project                                           |
| **Managed identity**                | A "robot account" Azure creates so one service can log into another without a password                  |
| **Role (RBAC)**                     | A permission slip in Azure that says who can do what on which resource                                  |
| **IAM**                             | "Identity and Access Management" — the Azure page where you hand out roles                              |
| **Shared access policy**            | An Event Hub password with limits (e.g. read-only)                                                      |
| **Secret scope**                    | Databricks' link to Key Vault, so notebooks can fetch passwords                                         |
| **Linked service**                  | ADF's saved connection to another system                                                                |
| **ADLS Gen2**                       | Azure storage with real folders, turned on with "hierarchical namespace"                                |
| **Serverless (Built-in) pool**      | Synapse's pay-per-query SQL engine. Reads Delta. Nothing to start or stop.                              |
| **Dedicated SQL pool**              | Synapse's always-on SQL engine, billed hourly. Can't read Delta.                                        |
| **External table**                  | A label pointing at files in the lake. No data is copied.                                               |
| **External data source**            | A saved address of a storage location                                                                   |
| **Database scoped credential**      | A saved login Synapse uses to reach storage                                                             |
| **Master key**                      | A key that protects saved credentials in a database                                                     |
| **View**                            | A saved query you can SELECT from like a table                                                          |
| **Schema (`dbo`)**                  | A folder inside a database. `dbo` comes built in.                                                       |
| **Deletion vectors**                | A Databricks speed feature that marks rows deleted without rewriting files. Synapse can't read it.      |
| **GO**                              | Tells Synapse "send everything above as one batch"                                                      |
| **Alert rule**                      | An Azure "if this happens, tell someone" setting                                                        |
| **Action group**                    | A reusable contact list (emails, texts) for alerts                                                      |
| **Synapse Studio**                  | The Synapse website where you write SQL and manage pools                                                |
| **SQL admin login**                 | The main username/password for a Synapse workspace's SQL pools                                          |

---

[← Still to do](still-to-do.md) · [Guide](../README.md)
