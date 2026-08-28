from __future__ import annotations

import random
from datetime import datetime

import numpy as np
import pytest

from producer.producer import ProducerSettings, load_seed_data, transaction_stream


def test_generated_events_match_the_streaming_contract() -> None:
    settings = ProducerSettings(
        bootstrap_server="localhost:9092",
        topic="transactions",
        num_records=4,
        rate=0,
        start_id=500,
        log_every=0,
        input_file=None,
    )

    events = list(
        transaction_stream(
            settings,
            rng=random.Random(7),
            np_rng=np.random.default_rng(7),
        )
    )

    assert [event["transaction_id"] for event in events] == [500, 501, 502, 503]
    assert all(event["amount"] >= 0 for event in events)
    assert all(event["is_fraud"] in {0, 1} for event in events)
    assert all(1 <= event["user_id"] <= 1_000 for event in events)
    assert all(datetime.fromisoformat(event["timestamp"]) for event in events)


def test_seed_data_requires_a_numeric_amount_column(tmp_path) -> None:
    invalid_seed = tmp_path / "invalid.csv"
    invalid_seed.write_text("Class\n1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Amount"):
        load_seed_data(invalid_seed)


def test_seed_data_normalizes_amounts_and_labels(tmp_path) -> None:
    seed = tmp_path / "seed.csv"
    seed.write_text("Amount,Class\n-4.5,0\n20,1\n", encoding="utf-8")

    normalized = load_seed_data(seed)

    assert normalized.to_dict("records") == [
        {"amount": 0.0, "is_fraud": 0},
        {"amount": 20.0, "is_fraud": 1},
    ]
