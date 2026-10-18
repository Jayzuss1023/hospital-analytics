from pyspark.sql.types import *
from pyspark.sql.functions import *

# Configuration for ADLS
spark.conf.set(
    "fs.azure.account.key.<<Storageaccount_name>>.dfs.core.windows.net",
    "<<Databricks_Scope_Storage_Account_access_key>>"
)

bronze_path = "abfss://<<container>>@<<Storageaccount_name>>.core.windows.net/<<path>>"
silver_path = "abfss://<<container>>@<<Storageaccount_name>>.core.windows.net/<<path>>"


# Reading from Bronze Path
bronze_df = (
    spark.readStream
    .format('delta')
    .load(bronze_path)
)

# Schema
schema = StructType([
    StructField('patient_id', StringType()),
    StructField('gender', StringType()),
    StructField('age', IntegerType()),
    StructField('department', StringType()),
    StructField('admission_time', StringType()),
    StructField('discharge_time', StringType()),
    StructField('bed_id', IntegerType()),
    StructField('hospital_id', IntegerType())
])

# Parse schema to Data Frame
# col('raw_json') picks that string column from bronze_df.
# from_json(..., schema) parses the string using the StructType defined just above 
# .withColumn('data', ...) attaches that struct as a new column named data
parsed_df = bronze_df.withColumn('data',from_json(col('raw_json'),schema)).select('data.*')

# Convert admission and discharge times to Timestamp
clean_df = parsed_df.withColumn('admission_time', to_timestamp('admission_time'))
clean_df = clean_df.withColumn('discharge_time', to_timestamp('discharge_time'))

# Fix invalid admission_times to current_timestamp - 'right now'
# Fix if admission time is Null or if timestamp is later than now's time
clean_df = clean_df.withColumn('admission_time', 
                                when(
                                    col('admission_time').isNull() | (col('admission_time') > current_timestamp()),
                                    current_timestamp())
                                .otherwise(col('admission_time')))

# Handle invalid ages greater than 100. Randomly select a number [1 - 90]
# rand() returns a random decimal between 0 and 1, multiply by 90
# adding 1 shifts that range to 1 through just under 91 (90.999). Floor then rounds down to 90
clean_df = clean_df.withColumn('age',
                                when(col('age')>100,floor(rand()*90+1).cast('int'))
                                .otherwise(col('age')))

# Schema Evolution
expected_cols = ['patient_id', 'gender', 'age', 'department', 'admission_time', 'discharge_time', 'bed_id', 'hospital_id']

# Handle non existing columns.
# If column doesn't exist, create the columns, fill it as Null
for col_name in expected_cols:
    if col_name not in clean_df.columns:
        clean_df = clean_df.withColumn(col_name, lit(None))

# Write to Silver Table
(
    clean_df.writeStream
    .format('delta')
    .outputMode('append')
    .option('mergeSchema', 'true')
    .option('checkpointLocation', silver_path + '_checkpoint')
    .start(silver_path)
)