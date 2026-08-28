"""Generate deterministic-schema transaction events for the Kafka demo.

The module keeps generation independent of Kafka so its data contract can be
tested without running the full streaming stack. Kafka is imported only when
``main`` sends the generated events.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

DEFAULT_AMOUNT_MEAN = 88.0
DEFAULT_AMOUNT_STD = 250.0
DEFAULT_FRAUD_RATE = 0.0017


@dataclass(frozen=True)
class ProducerSettings:
    """Validated runtime settings for one producer run."""

    bootstrap_server: str
    topic: str
    num_records: int
    rate: float
    start_id: int
    log_every: int
    input_file: Path | None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Publish simulated transaction events to Kafka."
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        default=None,
        help="Optional local CSV with Amount and optional Class columns.",
    )
    parser.add_argument(
        "--num-records",
        type=int,
        default=10_000,
        help="Total records to publish (default: 10,000).",
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=1_000.0,
        help="Maximum records per second; use 0 to send without throttling.",
    )
    parser.add_argument(
        "--bootstrap-server",
        default="localhost:9092",
        help="Kafka bootstrap server.",
    )
    parser.add_argument("--topic", default="transactions", help="Kafka topic name.")
    parser.add_argument(
        "--start-id",
        type=int,
        default=None,
        help="First transaction ID; defaults to the current epoch in nanoseconds.",
    )
    parser.add_argument(
        "--log-every",
        type=int,
        default=1_000,
        help="Confirm Kafka delivery every N records; use 0 to suppress progress logs.",
    )
    return parser


def settings_from_args(args: argparse.Namespace) -> ProducerSettings:
    if args.num_records < 1:
        raise ValueError("--num-records must be at least 1.")
    if args.rate < 0:
        raise ValueError("--rate cannot be negative.")
    if args.log_every < 0:
        raise ValueError("--log-every cannot be negative.")
    if args.start_id is not None and args.start_id < 0:
        raise ValueError("--start-id cannot be negative.")

    start_id = args.start_id
    if start_id is None:
        start_id = time.time_ns()

    return ProducerSettings(
        bootstrap_server=args.bootstrap_server,
        topic=args.topic,
        num_records=args.num_records,
        rate=args.rate,
        start_id=start_id,
        log_every=args.log_every,
        input_file=args.input_file,
    )


def load_seed_data(path: Path) -> pd.DataFrame:
    """Load the optional seed CSV and normalize only fields used by the demo."""

    if not path.is_file():
        raise FileNotFoundError(f"Seed CSV was not found: {path}")

    frame = pd.read_csv(path)
    if "Amount" not in frame.columns:
        raise ValueError("Seed CSV must contain an Amount column.")

    amounts = pd.to_numeric(frame["Amount"], errors="coerce")
    if amounts.isna().any() or not np.isfinite(amounts).all():
        raise ValueError("Seed CSV Amount values must be finite numbers.")

    if "Class" in frame.columns:
        labels = pd.to_numeric(frame["Class"], errors="coerce")
        if labels.isna().any():
            raise ValueError("Seed CSV Class values must be numeric when provided.")
    else:
        labels = pd.Series(0, index=frame.index, dtype="int64")

    return pd.DataFrame(
        {
            "amount": amounts.clip(lower=0).astype(float),
            "is_fraud": (labels > 0).astype(int),
        }
    )


def make_transaction(
    *,
    transaction_id: int,
    amount: float,
    is_fraud: int,
    rng: random.Random,
    event_time: datetime | None = None,
) -> dict[str, Any]:
    """Create one event matching the schema consumed by Spark."""

    timestamp = event_time or datetime.now(timezone.utc)
    return {
        "transaction_id": transaction_id,
        "user_id": rng.randint(1, 1_000),
        "amount": round(max(0.0, float(amount)), 2),
        "merchant_id": rng.randint(1, 100),
        "timestamp": timestamp.isoformat(),
        "is_fraud": int(bool(is_fraud)),
    }


def transaction_stream(
    settings: ProducerSettings,
    *,
    rng: random.Random | None = None,
    np_rng: np.random.Generator | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield a finite, uniquely identified mix of seed and synthetic events."""

    rng = rng or random.Random()
    np_rng = np_rng or np.random.default_rng()
    seed_data: pd.DataFrame | None = None

    if settings.input_file is not None:
        seed_data = load_seed_data(settings.input_file)
        amount_mean = float(seed_data["amount"].mean())
        amount_std = float(seed_data["amount"].std(ddof=0))
        fraud_rate = float(seed_data["is_fraud"].mean())
    else:
        amount_mean = DEFAULT_AMOUNT_MEAN
        amount_std = DEFAULT_AMOUNT_STD
        fraud_rate = DEFAULT_FRAUD_RATE

    sent = 0
    if seed_data is not None:
        for row in seed_data.head(settings.num_records).itertuples(index=False):
            yield make_transaction(
                transaction_id=settings.start_id + sent,
                amount=row.amount,
                is_fraud=row.is_fraud,
                rng=rng,
            )
            sent += 1

    while sent < settings.num_records:
        amount = np_rng.normal(amount_mean, amount_std)
        is_fraud = int(rng.random() < fraud_rate)
        yield make_transaction(
            transaction_id=settings.start_id + sent,
            amount=amount,
            is_fraud=is_fraud,
            rng=rng,
        )
        sent += 1


def create_kafka_producer(settings: ProducerSettings) -> Any:
    """Create a Kafka producer only for the actual send step."""

    try:
        from kafka import KafkaProducer
    except ImportError as exc:  # pragma: no cover - exercised at runtime
        raise RuntimeError(
            "Kafka dependencies are missing. Install producer/requirements.txt."
        ) from exc

    return KafkaProducer(
        bootstrap_servers=settings.bootstrap_server,
        acks="all",
        retries=5,
        linger_ms=5,
        key_serializer=lambda value: value.encode("utf-8"),
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )


def run_producer(settings: ProducerSettings) -> int:
    """Send events to Kafka and return the number accepted for delivery."""

    producer = create_kafka_producer(settings)
    sent = 0
    try:
        for event in transaction_stream(settings):
            future = producer.send(
                settings.topic,
                key=str(event["user_id"]),
                value=event,
            )
            sent += 1

            if settings.log_every and sent % settings.log_every == 0:
                future.get(timeout=10)
                print(f"Confirmed delivery of {sent:,} records.")
            if settings.rate:
                time.sleep(1 / settings.rate)

        producer.flush(timeout=60)
        return sent
    finally:
        producer.close(timeout=10)


def main() -> None:
    settings = settings_from_args(build_parser().parse_args())
    print(
        f"Publishing {settings.num_records:,} events to {settings.topic!r} "
        f"via {settings.bootstrap_server}."
    )
    sent = run_producer(settings)
    print(f"Finished publishing {sent:,} events.")


if __name__ == "__main__":
    main()
