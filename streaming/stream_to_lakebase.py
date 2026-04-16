# Databricks notebook source
# MAGIC %md
# MAGIC # LakePulse: Stream metrics from Delta → Lakebase
# MAGIC
# MAGIC Reads the ZeroBus landing table (`lakepulse.default.metrics_raw`) with
# MAGIC Spark Structured Streaming in real-time mode, and writes to Lakebase
# MAGIC using `lakebase-foreachwriter` in upsert mode.

# COMMAND ----------

# MAGIC %pip install git+https://github.com/jtaylorisbell/lakebase-foreachwriter.git@feature/oauth-credential-provider
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

from pyspark.sql import SparkSession
from lakebase_foreachwriter import LakebaseForeachWriter, oauth_credential_provider

spark = SparkSession.builder.getOrCreate()

# COMMAND ----------

# Configuration — passed in via DABs base_parameters
dbutils.widgets.text("landing_table", "")
dbutils.widgets.text("lakebase_project", "")
LANDING_TABLE = dbutils.widgets.get("landing_table")
LAKEBASE_PROJECT = dbutils.widgets.get("lakebase_project")
CHECKPOINT_PATH = f"/tmp/lakepulse/checkpoints/stream_to_lakebase"

# COMMAND ----------

# Read from ZeroBus landing table as a stream
df = (
    spark.readStream
    .format("delta")
    .table(LANDING_TABLE)
)

# COMMAND ----------

# Write to Lakebase using foreachwriter (upsert mode, OAuth credentials)
writer = LakebaseForeachWriter(
    credential_provider=oauth_credential_provider(LAKEBASE_PROJECT, branch_id="production", endpoint_id="primary"),
    lakebase_name=LAKEBASE_PROJECT,
    table="public.metrics",
    df=df,
    mode="upsert",
    primary_keys=["ts", "hostname", "category", "metric"],
    batch_size=500,
    batch_interval_ms=200,
)

query = (
    df.writeStream
    .foreach(writer)
    .option("checkpointLocation", CHECKPOINT_PATH)
    .trigger(processingTime="0 seconds")  # real-time mode
    .start()
)

# COMMAND ----------

query.awaitTermination()
