# First stage of hospital analytics pipeline. 
# Takes raw patient-flow events from Azure Event Hubs into the bronze Delta table


# Take data from stream and convert from binary into JSON string then load into bronze table
# Any data being cleaned using Kafka is converted into binary data
# Any data used again is converted into a string then stored
from pyspark.sql.functions import *
# Create a key vault in Azure to keep the connection string secured

# Azure Event Hub Configuration
event_hub_namespace = "<<Namespace_hostname>>"
event_hub_name="<<Eventhub_Name>>"  
event_hub_conn_str = dbtutils.secrets.get(scope='scope_name', key='secret_key_name')


#Configuration for EventHub
kafka_options = {
    'kafka.bootstrap.servers': f"{event_hub_namespace}:9093",
    'subscribe': event_hub_name,
    'kafka.security.protocol': 'SASL_SSL',
    'kafka.sasl.mechanism': 'PLAIN',
    'kafka.sasl.jaas.config': f'kafkashaded.org.apache.kafka.common.security.plain.PlainLoginModule required username="$ConnectionString" password="{event_hub_conn_str}";',
    'startingOffsets': 'latest',
    'failOnDataLoss': 'false'
}

# Eventhub authorization
raw_df = (
    spark.readStream
    .format("kafka")
    .options(**kafka_options)
    .load()
)

# Kafka message comes with binary data since kafka stores the payload as bytes
# Spark casts the payload into a string
json_df = raw_df.selectExpr('CAST(value AS STRING) as raw_json')

#ADLS configuration 
spark.conf.set(
  "fs.azure.account.key.<<Storageaccount_name>>.dfs.core.windows.net",
  "<<Storage_Account_access_key>>"
)

bronze_path = "abfss://<<container>>@<<Storageaccount_name>>.core.windows.net/<<path>>"

# Write the stream to bronze
(
    json_df
    .writeStream
    .format('delta')
    # Append new record to the bottom of the dataset
    .outputMode('append')
    # Create a folder named 'checkpoints'. Spark records its progress
    # Kafka saves after each batch to the folder. If the notebook fails and restarts, Spark will read the folder and continue from the last saved commit
    .option('checkpointLocation', 'dbfs:/mnt/bronze/_checkpoints/patient_flow')
    .start(bronze_path)
)