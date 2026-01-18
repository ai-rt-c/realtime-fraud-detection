from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, count, sum, when, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, TimestampType

spark = SparkSession.builder \
    .appName("KafkaFraudStreaming") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

schema = StructType([
    StructField("transaction_id", IntegerType(), True),
    StructField("user_id", IntegerType(), True),
    StructField("amount", DoubleType(), True),
    StructField("merchant_id", IntegerType(), True),
    StructField("timestamp", StringType(), True),
    StructField("is_fraud", IntegerType(), True)
])

df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:29092") \
    .option("subscribe", "transactions") \
    .option("startingOffsets", "latest") \
    .option("failOnDataLoss", "false") \
    .load()

parsed_df = df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.*") \
    .withColumn("timestamp", col("timestamp").cast(TimestampType()))

dedup_df = parsed_df.dropDuplicates(["transaction_id"])

# Watermark increased to 10 minutes for testing (helps with late-arriving data)
agg_df = dedup_df.withWatermark("timestamp", "10 minutes") \
                 .groupBy(window("timestamp", "1 minute"), "user_id") \
                 .agg(count("*").alias("tx_count"),
                      sum("amount").alias("total_amount"))

fraud_df = agg_df.withColumn("is_suspicious", 
                             when((col("total_amount") > 1000) | (col("tx_count") > 5), 1)
                             .otherwise(0)) \
                 .withColumn("processed_at", current_timestamp())

# Query 1: Console 
query_console = fraud_df.writeStream \
    .outputMode("append") \
    .format("console") \
    .option("numRows", 20) \
    .option("truncate", False) \
    .start()

# Query 2: Parquet 
query_parquet = fraud_df.writeStream \
    .outputMode("append") \
    .format("parquet") \
    .option("path", "/output") \
    .option("checkpointLocation", "/checkpoint") \
    .start()

# query 
spark.streams.awaitAnyTermination()