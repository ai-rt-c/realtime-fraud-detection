import matplotlib.pyplot as plt
import pandas as pd
import glob

# Read all Parquet files from output_local
files = glob.glob('output_local/part-*.parquet')
data = pd.concat([pd.read_parquet(f) for f in files])

# Convert window to string for plot
data['window_str'] = data['window'].apply(lambda w: w['start'].strftime('%Y-%m-%d %H:%M:%S'))

# Group by window for plot
grouped = data.groupby('window_str').agg({'tx_count': 'sum', 'total_amount': 'sum', 'is_suspicious': 'sum'})

fig, ax1 = plt.subplots()
ax1.bar(grouped.index, grouped['tx_count'], color='blue', label='Transaction Count (Scaled)')
ax1.set_xlabel('Time Window')
ax1.set_ylabel('Transaction Count', color='blue')
ax1.tick_params(axis='y', labelcolor='blue')

ax2 = ax1.twinx()
ax2.plot(grouped.index, grouped['total_amount'], color='green', label='Total Amount')
ax2.set_ylabel('Total Amount', color='green')
ax2.tick_params(axis='y', labelcolor='green')

ax3 = ax1.twinx()
ax3.spines['right'].set_position(('axes', 1.1))
ax3.scatter(grouped.index, grouped['is_suspicious'], color='red', marker='*', label='Suspicious Users (Scaled Count)')
ax3.set_ylabel('Suspicious Users Count', color='red')
ax3.tick_params(axis='y', labelcolor='red')

fig.suptitle('Real-Time Transaction Monitoring & Fraud Detection')
plt.xticks(rotation=45)
fig.tight_layout()
plt.legend()
plt.show()