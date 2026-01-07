import json
import time
import random
from datetime import datetime
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

def generate_transaction():
    return {
        "transaction_id": random.randint(100000, 999999),
        "user_id": random.randint(1, 1000),
        "amount": round(random.uniform(5, 500), 2),
        "merchant_id": random.randint(1, 100),
        "timestamp": datetime.utcnow().isoformat(),
        "is_fraud": random.choice([0, 1])
    }

print("🚀 Sending transactions to Kafka...")

while True:
    tx = generate_transaction()
    producer.send("transactions", tx)
    print(tx)
    time.sleep(1)
