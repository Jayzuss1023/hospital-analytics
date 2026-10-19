from pyspark.sql import functions as F
from pyspark.sql.functions import lit, col, expr, current_timestamp, to_timestamp,sha2, concat_ws, coalesce, monotonically_increasing_id
from delta.tables import DeltaTable
from pyspark.sql import Window

# Paths - 1 silver, 3 gold paths: dimension for patient, dimension for department, fact table
silver_path = "abfss://<<container>>@<<Storageaccount_name>>.core.windows.net/<<path>>"
gold_dim_patient = "abfss://<<container>>@<<Storageaccount_name>>.core.windows.net/<<path>>"
gold_dim_department = "abfss://<<container>>@<<Storageaccount_name>>.core.windows.net/<<path>>"
gold_fact = "abfss://<<container>>@<<Storageaccount_name>>.core.windows.net/<<path>>"

# Read Silver Data
silver_df = spark.read.format('delta').load(silver_path)

# Define window for latest admission per patient
# partitionBy('patient_id') splits the rows into groups, one group per patient. One group may have many rows of the same patient
# then sort each group by admission_time, newest first.
w = Window.partitionBy('patient_id').orderBy(F.col('admission_time').desc())

# withColumn: add a new column, 'row_num' to the modified window above. 
# row_number(): increment starting at '1' to the extent of how many rows there are
# filter: Drop old admissions and keep only the most recent admission for one patient
# drop: remove helper column to keep from being added the original Data Frame
silver_df = (
    silver_df
    .withColumn('row_num', F.row_number().over(w))
    .filter(F.col('row_num') == 1)
    .drop('row_num')
)

# Patient Dimension Table Creation ['patient_id', 'gender', 'age', 'effective_from']
# Prepare incoming dimension record (deduplicated per patient, latest record)
incoming_patient = (
    silver_df
    .select('patient_id', 'gender', 'age')
    .withColumn('effective_from', current_timestamp())
)

# Initialize DeltaTable if not exists. First write.
# 3 SCD columns: [timestamp, isCurrent, surrogate_key]
# surrogate_key with monotonically_increasing_id(). Each row in this job gets a unique 64-bit id
# effect_to casted as type timestamp set to NULL && set isCurrent to True every row
# Overwrite replaces whatever is in that path already
if not DeltaTable.isDeltaTable(spark, gold_dim_patient):
    incoming_patient.withColumn('surrogate_key', F.monotonically_increasing_id()) \
        .withColumn('effective_to', lit(None).cast('timestamp')) \
        .withColumn('is_current', lit(True)) \
        .write.format('delta').mode('overwrite').save(gold_dim_patient)


# Open the Gold Delta table object to be able to write data into it
target_patient = DeltaTable.forPath(spark, gold_dim_patient)

# Hash implemented to detect a change. Incoming rows get joined to the current gold rown on patient_id.
# Hash is then compated. The old row closes and new row is inserted if there is a change.
incoming_patient = incoming_patient.withColumn(
    '_hash',
    F.sha2(F.concat_ws('||', F.coalesce(col('gender'), lit('NA')), F.coalesce(col('age').cast('string'), lit('NA'))), 256)
)

# Read the two columns: col('gender'), col('age') - F 67
# Turn age into text: col('age').cast('string') - 67
# Replace nulls with NA: coalesce(..., lit('NA'))
# Join with a separator: concat_ws('||', gender, age) - F||67
# Hash the joined string: sha2(..., 256) - ff6ea6dd4261…cafab792
target_patient_df = spark.read.format('delta').load(gold_dim_patient).withColumn(
    '_target_hash',
    F.sha2(F.concat_ws('||', F.coalesce(col('gender'), lit('NA')), F.coalesce(col('age').cast('string'), lit('NA'))), 256)
).select('surrogate_key', 'patient_id', 'gender', 'age', 'is_current', '_target_hash', 'effective_from', 'effective_to')

# Create temp views for merge: 
# incoming_patient = new or changed records VS target_patient = existing records
incoming_patient.createOrReplaceTempView('incoming_patient_temp')
target_patient_df.createOrReplaceTempView('target_patient_temp')

# 2 steps using Delta Merge(sage & explicit)

# 1. Mark old current rows as not current where changed

# patient records to close: t._target_hash <> i._hash pulls the rows that no longer match the new gender or age. 
changes_df = spark.sql("""
SELECT t.surrogate_key, t.patient_id
FROM target_patient_temp t
INNER JOIN incoming_patient_temp i
ON t.patient_id = i.patient_id
WHERE t.is_current = true and t._target_hash <> i._hash
""")

changed_keys = [row['surrogate_key'] for row in changes_df.collect()]

# Update existing records no longer current: Set is_current = false and effective_to=current_timestamp()
if changed_keys:
    target_patient.update(
        # Condition tells what rows to update. must meet is_current = true AND only the keys found
        condition = expr('is_current = true AND surrogate_key IN ({})'.format(','.join(str(k) for k in changed_keys))),
        set = {
            'is_current': expr('false'),
            'effective_to': expr('current_timestamp()')
        }
    )


# 2.) Insert the newly active || changed record
# t.patient_id IS NULL: no record located. new patient
# t._target_hash <> i._hash: record has a change. age/gender hashes don't match
inserts_df = spark.sql("""
SELECT i.patient_id, i.gender, i.age, i.effective_from, i._hash
FROM incoming_patient_temp i
LEFT JOIN target_patient_temp t
    ON i.patient_id = t.patient_id AND t.is_current = true
WHERE t.patient_id IS NULL OR t._target_hash <> i._hash
""").withColumn('surrogate_key', F.monotonically_increasing_id()) \
    .withColumn('effective_to', lit(None).cast('timestamp')) \
    .withColumn('is_current', lit(True)) \
    .select('surrogate_key', 'patient_id', 'gender','age', 'effective_from', 'effective_to', 'is_current')

# Append new rows
if inserts_df.count() > 0:
    inserts_df.write.format('delta').mode('append').save(gold_dim_patient)

# Department Dimension Table Creation

# Prepare incoming (latest per patient feed snapshot) and overwrite dim_department
(silver_df.select('department', 'hospital_id')
    .distinct()
    .withColumn('surrogate_key', monotonically_increasing_id())
    .write.format('delta').mode('overwrite').save(gold_dim_department))

# Create Fact table

# Read current dims (filter is_current=true)
dim_patient_df = (spark.read.format('delta').load(gold_dim_patient)
                .filter(col('is_current') == True)
                .select(col('surrogate_key').alias('surrogate_key_patient'), 'patient_id', 'gender', 'age'))

dim_dept_df = (spark.read.format('delta').load(gold_dim_department)
                .select(col('surrogate_key').alias('surrogate_key_dept'), 'department', 'hospital_id'))

# Build base fact from silver events
fact_base = (silver_df
            .select('patient_id', 'department', 'hospital_id', 'admission_time', 'discharge_time', 'bed_id')
            .withColumn('admission_date', F.to_date('admission_time'))
            )

# Join to get surrogate keys
fact_enriched = (fact_base
                .join(dim_patient_df, on='patient_id', how="left")
                .join(dim_dept_df, on=['department', 'hospital_id'], how='left')
                )

# Compute metrics
# Time is computed into seconds. Dividing by 3600 converts from seconds to hours
# Patient is admitted if discharge time is in the future
# Stamp to show when gold job wrote it
fact_enriched = fact_enriched.withColumn('length_of_stay_hours',
                                         (F.unix_timestamp(col("discharge_time")) - F.unix_timestamp(col("admission_time"))) / 3600.0) \
                            .withColumn('is_currently_admitted', F.when(col('discharge_time') > current_timestamp(), lit(True)).otherwise(False)) \
                            .withColumn('event_ingestion_time', current_timestamp())


# Cast alias'
fact_final = fact_enriched.select(
    F.monotonically_increasing_id().alias('fact_id'),
    col('surrogate_key_patient').alias('patient_sk'),
    col('surrogate_key_dept').alias('department_sk'),
    'admission_time',
    'discharge_time',
    'admission_date',
    'length_of_stay_hours',
    'is_currently_admitted',
    'bed_id',
    'event_ingestion_time'
)

# Persist fact table partitioned by admission_date (helps Synapse / queries)
fact_final.write.format('delta').mode('overwrite').save(gold_fact)

# Quick sanity checks
print("Gold Dim Patient")
display(spark.read.format('delta').load(gold_dim_patient))
print("Gold Dim Department")
display(spark.read.format('delta').load(gold_dim_department))
print('Gold Fact')
display(spark.read.format('delta').load(gold_fact))