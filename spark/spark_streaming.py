"""Kafka-to-Parquet streaming job for the local fraud-detection prototype."""

from __future__ import annotations

import os
from typing import Any

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col,
    count,
    current_timestamp,
    from_json,
    sum,
    to_timestamp,
    when,
    window,
)
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
)

TRANSACTION_SCHEMA = StructType(
    [
        StructField("transaction_id", LongType(), nullable=False),
        StructField("user_id", IntegerType(), nullable=False),
        StructField("amount", DoubleType(), nullable=False),
        StructField("merchant_id", IntegerType(), nullable=False),
        StructField("timestamp", StringType(), nullable=False),
        StructField("is_fraud", IntegerType(), nullable=False),
    ]
)


def get_config(name: str, default: str) -> str:
    return os.getenv(name, default)


def get_float_config(name: str, default: float) -> float:
    value = float(get_config(name, str(default)))
    if value < 0:
        raise ValueError(f"{name} cannot be negative.")
    return value


def create_spark_session() -> SparkSession:
    spark = SparkSession.builder.appName("KafkaFraudStreaming").getOrCreate()
    spark.sparkContext.setLogLevel(get_config("SPARK_LOG_LEVEL", "WARN"))
    return spark


def read_transactions(spark: SparkSession) -> DataFrame:
    """Read, parse, validate, and deduplicate the Kafka event stream."""

    raw_stream = (
        spark.readStream.format("kafka")
        .option(
            "kafka.bootstrap.servers",
            get_config("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092"),
        )
        .option("subscribe", get_config("KAFKA_TOPIC", "transactions"))
        .option("startingOffsets", get_config("KAFKA_STARTING_OFFSETS", "earliest"))
        .option("failOnDataLoss", "false")
        .load()
    )

    parsed = (
        raw_stream.selectExpr("CAST(value AS STRING) AS value")
        .select(from_json(col("value"), TRANSACTION_SCHEMA).alias("transaction"))
        .where(col("transaction").isNotNull())
        .select("transaction.*")
        .withColumn("event_time", to_timestamp(col("timestamp")))
    )

    valid = parsed.where(
        col("transaction_id").isNotNull()
        & col("user_id").isNotNull()
        & col("merchant_id").isNotNull()
        & col("event_time").isNotNull()
        & col("amount").isNotNull()
        & (col("amount") >= 0)
        & col("is_fraud").isin(0, 1)
    )

    return valid.withWatermark(
        "event_time", get_config("SPARK_WATERMARK_DELAY", "30 seconds")
    ).dropDuplicates(["transaction_id"])


def aggregate_transactions(transactions: DataFrame) -> DataFrame:
    """Aggregate one-minute user windows and flag rule-based risk indicators."""

    amount_threshold = get_float_config("FRAUD_AMOUNT_THRESHOLD", 1_000.0)
    transaction_threshold = get_float_config("FRAUD_TRANSACTION_THRESHOLD", 5.0)

    aggregates = transactions.groupBy(
        window("event_time", "1 minute"), col("user_id")
    ).agg(
        count("*").alias("tx_count"),
        sum("amount").alias("total_amount"),
        sum("is_fraud").alias("labeled_fraud_count"),
    )

    return aggregates.withColumn(
        "is_suspicious",
        when(
            (col("total_amount") > amount_threshold)
            | (col("tx_count") > transaction_threshold),
            1,
        ).otherwise(0),
    ).withColumn("processed_at", current_timestamp())


def start_queries(aggregates: DataFrame) -> list[Any]:
    """Write closed windows to Parquet and optionally show them in container logs."""

    output_path = get_config("SPARK_OUTPUT_PATH", "/output")
    checkpoint_root = get_config("SPARK_CHECKPOINT_PATH", "/checkpoint")
    trigger_interval = get_config("SPARK_TRIGGER_INTERVAL", "5 seconds")

    parquet_query = (
        aggregates.writeStream.outputMode("append")
        .format("parquet")
        .option("path", output_path)
        .option("checkpointLocation", f"{checkpoint_root}/parquet")
        .trigger(processingTime=trigger_interval)
        .start()
    )
    queries: list[Any] = [parquet_query]

    if get_config("SPARK_CONSOLE_OUTPUT", "true").lower() == "true":
        console_query = (
            aggregates.writeStream.outputMode("append")
            .format("console")
            .option("truncate", "false")
            .option("numRows", 20)
            .option("checkpointLocation", f"{checkpoint_root}/console")
            .trigger(processingTime=trigger_interval)
            .start()
        )
        queries.append(console_query)

    return queries


def main() -> None:
    spark = create_spark_session()
    try:
        aggregates = aggregate_transactions(read_transactions(spark))
        start_queries(aggregates)
        spark.streams.awaitAnyTermination()
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
