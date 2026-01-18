import pandas as pd
import matplotlib.pyplot as plt

#
data = {
    "timestamp": [
        "2026-01-12 12:00",
        "2026-01-12 12:01",
        "2026-01-12 12:02",
        "2026-01-12 12:03",
        "2026-01-12 12:04",
    ],
    "amount": [120, 3500, 420, 5100, 1800]
}

df = pd.DataFrame(data)
df["timestamp"] = pd.to_datetime(df["timestamp"])

# Rule-based fraud indicator
df["fraud"] = df["amount"].apply(lambda x: 1 if x > 2000 else 0)

# Aggregate fraud count over time
fraud_over_time = df.groupby("timestamp")["fraud"].sum()

# Plot
plt.figure()
fraud_over_time.plot()
plt.xlabel("Time")
plt.ylabel("Number of Fraudulent Transactions")
plt.title("Fraudulent Transactions Over Time")

#  save
plt.savefig("fraud_over_time.png", dpi=300)
plt.close()

print("Fraud visualization saved as fraud_over_time.png")
