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