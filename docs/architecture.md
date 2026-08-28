# Architecture notes

## Data contract

The producer publishes JSON records with the following fields:

| Field | Type | Purpose |
| --- | --- | --- |
| `transaction_id` | integer | Unique ID for one producer run; used for deduplication. |
| `user_id` | integer | Synthetic partitioning key and aggregation dimension. |
| `merchant_id` | integer | Synthetic event attribute. |
| `amount` | number | Non-negative transaction amount. |
| `timestamp` | ISO 8601 UTC string | Event time used for the one-minute window. |
| `is_fraud` | 0 or 1 | Optional source label retained as an aggregate count. |

Spark rejects malformed records, negative amounts, invalid labels, and invalid timestamps before stateful processing. It applies the watermark before deduplicating by `transaction_id`, which bounds the state held for deduplication.

## Operational model

- **Kafka** receives keyed JSON events on the `transactions` topic. The local broker has three partitions but a replication factor of one.
- **Spark** starts from the earliest available offset for a fresh checkpoint, validates records, deduplicates them, and computes one-minute per-user aggregates.
- **Parquet** is the local delivery interface for closed aggregate windows. `visualization/visualize.py` reads that output on demand.
- **Docker Compose** runs the broker and Spark by default. The producer uses an explicit Compose profile so a reviewer can start it only after the pipeline is ready.

The earlier course concept included planned delivery components that are not part of the implemented local stack, so it is intentionally not included in the public portfolio view. This document and the root README describe the current implementation.
