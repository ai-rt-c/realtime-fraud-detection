import json
import time
import random
import argparse
from datetime import datetime, timedelta, timezone
import pandas as pd
from faker import Faker
from kafka import KafkaProducer
import numpy as np

# Argument parser for configurable options
parser = argparse.ArgumentParser(description="Kafka Producer for Fraud Detection")
parser.add_argument("--input-file", default=None, help="Path to seed CSV file (e.g., creditcard.csv)")
parser.add_argument("--num-records", type=int, default=1000000, help="Total records to produce (>=1M)")
parser.add_argument("--rate", type=int, default=2000, help="Records per second (adjust for simulation)")
parser.add_argument("--bootstrap-server", default="localhost:9092", help="Kafka bootstrap server")
parser.add_argument("--topic", default="transactions", help="Kafka topic")
args = parser.parse_args()

# Initialize Kafka Producer
producer = KafkaProducer(
    bootstrap_servers=args.bootstrap_server,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

fake = Faker()

def generate_synthetic_transaction(amount_mean, amount_std, fraud_rate):
    """Generate synthetic tx preserving patterns"""
    return {
        "transaction_id": random.randint(100000, 999999),
        "user_id": random.randint(1, 1000),
        "amount": round(np.random.normal(amount_mean, amount_std), 2),  # Preserve distribution
        "merchant_id": random.randint(1, 100),
        "timestamp": (datetime.now(timezone.utc) - timedelta(seconds=random.randint(0, 60))).isoformat(),  # All in 1 minute for testing
        "is_fraud": 1 if random.random() < fraud_rate else 0  # Preserve fraud rate ~0.17%
    }

print("🚀 Starting producer...")

# Load seed dataset if provided
seed_records = []
if args.input_file:
    df = pd.read_csv(args.input_file)
    # Calculate patterns for synthetic
    amount_mean = df['Amount'].mean()
    amount_std = df['Amount'].std()
    fraud_rate = df['Class'].mean() if 'Class' in df.columns else 0.0017
    
    print(f"Loaded {len(df)} records from {args.input_file}")
    print(f"Mean amount: {amount_mean:.2f}, Std: {amount_std:.2f}, Fraud rate: {fraud_rate*100:.3f}%")
    
    for _, row in df.iterrows():
        seed_records.append({
            "transaction_id": random.randint(100000, 999999),  # Add if missing
            "user_id": random.randint(1, 1000),  # Synthetic if missing
            "amount": row['Amount'],
            "merchant_id": random.randint(1, 100),  # Synthetic
            "timestamp": (datetime.now(timezone.utc) - timedelta(seconds=int(row['Time']))).isoformat(),  # Convert Time to ISO
            "is_fraud": row['Class']
        })
    seed_records = seed_records[:min(len(seed_records), args.num_records)]
else:
    amount_mean, amount_std, fraud_rate = 88.0, 250.0, 0.0017  # Defaults if no seed

# Send seed records first
for tx in seed_records:
    producer.send(args.topic, tx, partition=tx['user_id'] % 3)  # Partition based on user_id for scalability
    print(f"Sent seed: {tx}")
    time.sleep(1 / args.rate)  # Control rate

# Generate synthetic to reach total
remaining = args.num_records - len(seed_records)
for _ in range(max(0, remaining)):
    tx = generate_synthetic_transaction(amount_mean, amount_std, fraud_rate)
    producer.send(args.topic, tx, partition=tx['user_id'] % 3)  # Partition based on user_id for scalability
    print(f"Sent synthetic: {tx}")
    time.sleep(1 / args.rate)

# Flush and close producer cleanly
print("Flushing remaining messages...")
producer.flush(timeout=60)  # Give 60 seconds for flush
print("Closing producer...")
producer.close(timeout=10)
print("✅ Producer finished and closed cleanly.")