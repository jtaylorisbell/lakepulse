# Databricks notebook source
# MAGIC %md
# MAGIC # LakePulse: Stream metrics from Delta → Lakebase
# MAGIC
# MAGIC Reads the ZeroBus landing table (`lakepulse.default.metrics_raw`) with
# MAGIC Spark Structured Streaming in real-time mode, and writes to Lakebase
# MAGIC using `lakebase-foreachwriter` in upsert mode.

# COMMAND ----------

# MAGIC %pip install lakebase-foreachwriter
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

from pyspark.sql import SparkSession
from lakebase_foreachwriter import LakebaseForeachWriter

spark = SparkSession.builder.getOrCreate()

# COMMAND ----------

# Configuration — override via notebook widgets or job parameters
CATALOG = spark.conf.get("spark.databricks.lakepulse.catalog", "lakepulse")
SCHEMA = spark.conf.get("spark.databricks.lakepulse.schema", "default")
LANDING_TABLE = f"{CATALOG}.{SCHEMA}.metrics_raw"
LAKEBASE_PROJECT = "lakepulse"
CHECKPOINT_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/checkpoints/stream_to_lakebase"

# Resolve Lakebase endpoint + credentials via Databricks SDK
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
endpoint = w.api_client.do("GET", f"/api/2.0/lakebase/projects/{LAKEBASE_PROJECT}/branches/main/endpoints/default")
LAKEBASE_HOST = endpoint.get("host")
LAKEBASE_USER = dbutils.secrets.get(scope="lakepulse", key="lakebase-user")
LAKEBASE_PASS = dbutils.secrets.get(scope="lakepulse", key="lakebase-pass")

# COMMAND ----------

# Read from ZeroBus landing table as a stream
df = (
    spark.readStream
    .format("delta")
    .table(LANDING_TABLE)
)

# COMMAND ----------

# Write to Lakebase using foreachwriter (upsert mode)
writer = LakebaseForeachWriter(
    username=LAKEBASE_USER,
    password=LAKEBASE_PASS,
    host=LAKEBASE_HOST,
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
