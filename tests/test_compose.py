from __future__ import annotations

from pathlib import Path

import yaml


def test_compose_declares_reproducible_pipeline_services() -> None:
    compose = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]

    assert {"zookeeper", "kafka", "spark", "producer"} <= set(services)
    assert (
        services["kafka"]["environment"]["KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR"] == 1
    )
    assert services["producer"]["profiles"] == ["producer"]
    assert services["spark"]["depends_on"]["kafka"]["condition"] == "service_healthy"
