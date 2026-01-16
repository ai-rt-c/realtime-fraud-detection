from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, count, sum, when, current_timestamp, sha2
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
    .load()

parsed_df = df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.*") \
    .withColumn("timestamp", col("timestamp").cast(TimestampType())) \
    .withColumn("user_id", sha2(col("user_id").cast("string"), 256))  # Anonymize for security

# Deduplication based on transaction_id
dedup_df = parsed_df.dropDuplicates(["transaction_id"])

# Windowed aggregation: 1-min tumbling window per user_id
agg_df = dedup_df.withWatermark("timestamp", "1 minute") \
    .groupBy(window("timestamp", "1 minute"), "user_id") \
    .agg(count("*").alias("tx_count"), sum("amount").alias("total_amount"))

# Rule-based fraud detection: flag if total_amount > 1000 or tx_count > 5
fraud_df = agg_df.withColumn("is_suspicious", 
                             when((col("total_amount") > 1000) | (col("tx_count") > 5), 1)
                             .otherwise(0)) \
                 .withColumn("processed_at", current_timestamp())

# Output to console for testing/debugging
query = fraud_df.writeStream \
    .outputMode("append") \
    .format("console") \
    .start()

query.awaitTermination()