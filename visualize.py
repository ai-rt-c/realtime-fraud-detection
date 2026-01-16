import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.dates as mdates

data = [
    {'window_start': '2026-01-16 14:35:00', 'tx_count': 6, 'total_amount': 210.66, 'is_suspicious': 1},
    {'window_start': '2026-01-16 14:35:00', 'tx_count': 2, 'total_amount': 1006.39, 'is_suspicious': 1},
    {'window_start': '2026-01-16 14:35:00', 'tx_count': 7, 'total_amount': 1362.85, 'is_suspicious': 1},
    {'window_start': '2026-01-16 14:35:00', 'tx_count': 3, 'total_amount': -273.43, 'is_suspicious': 0},
    {'window_start': '2026-01-16 14:35:00', 'tx_count': 5, 'total_amount': 14.40, 'is_suspicious': 0},
    {'window_start': '2026-01-16 14:35:00', 'tx_count': 2, 'total_amount': -162.79, 'is_suspicious': 0},
    {'window_start': '2026-01-16 14:35:00', 'tx_count': 8, 'total_amount': 1653.06, 'is_suspicious': 1},
    {'window_start': '2026-01-16 14:35:00', 'tx_count': 7, 'total_amount': 1437.41, 'is_suspicious': 1},
    {'window_start': '2026-01-16 14:35:00', 'tx_count': 3, 'total_amount': 587.07, 'is_suspicious': 0},
    {'window_start': '2026-01-16 14:35:00', 'tx_count': 7, 'total_amount': 328.58, 'is_suspicious': 1},
    {'window_start': '2026-01-16 14:34:00', 'tx_count': 2, 'total_amount': 229.07, 'is_suspicious': 0},
    {'window_start': '2026-01-16 14:34:00', 'tx_count': 5, 'total_amount': -86.72, 'is_suspicious': 0},
    {'window_start': '2026-01-16 14:34:00', 'tx_count': 10, 'total_amount': 345.31, 'is_suspicious': 1},
    {'window_start': '2026-01-16 14:34:00', 'tx_count': 5, 'total_amount': 705.80, 'is_suspicious': 0},
    {'window_start': '2026-01-16 14:34:00', 'tx_count': 6, 'total_amount': 1109.39, 'is_suspicious': 1},
    {'window_start': '2026-01-16 14:34:00', 'tx_count': 6, 'total_amount': 771.78, 'is_suspicious': 1},
    {'window_start': '2026-01-16 14:34:00', 'tx_count': 8, 'total_amount': 298.51, 'is_suspicious': 1},
    {'window_start': '2026-01-16 14:34:00', 'tx_count': 5, 'total_amount': 257.33, 'is_suspicious': 0},
    {'window_start': '2026-01-16 14:33:00', 'tx_count': 1, 'total_amount': -185.5, 'is_suspicious': 0},
    {'window_start': '2026-01-16 14:33:00', 'tx_count': 6, 'total_amount': -2.69, 'is_suspicious': 1},
    {'window_start': '2026-01-16 14:33:00', 'tx_count': 7, 'total_amount': 941.47, 'is_suspicious': 1},
    {'window_start': '2026-01-16 14:33:00', 'tx_count': 7, 'total_amount': 645.23, 'is_suspicious': 1},
    {'window_start': '2026-01-16 14:33:00', 'tx_count': 5, 'total_amount': -75.61, 'is_suspicious': 0},
    {'window_start': '2026-01-16 14:33:00', 'tx_count': 6, 'total_amount': 373.28, 'is_suspicious': 1},
    {'window_start': '2026-01-16 14:33:00', 'tx_count': 8, 'total_amount': 651.08, 'is_suspicious': 1},
    {'window_start': '2026-01-16 14:33:00', 'tx_count': 4, 'total_amount': 250.34, 'is_suspicious': 0},
]

df = pd.DataFrame(data)
df['window_start'] = pd.to_datetime(df['window_start'])

grouped = df.groupby('window_start').agg({
    'tx_count': 'sum',
    'total_amount': 'sum',
}).reset_index()

suspicious_grouped = df[df['is_suspicious'] == 1].groupby('window_start').size().reset_index(name='suspicious_count')

fig, ax1 = plt.subplots(figsize=(14, 7))

ax1.bar(grouped['window_start'], grouped['tx_count'], 
        color='skyblue', alpha=0.8, label='Total Transaction Count')
ax1.set_xlabel('Time Window')
ax1.set_ylabel('Transaction Count', color='navy')
ax1.tick_params(axis='y', labelcolor='navy')

ax2 = ax1.twinx()
ax2.plot(grouped['window_start'], grouped['total_amount'], 
         color='darkgreen', marker='o', linewidth=2.5, markersize=8, label='Total Amount')
ax2.set_ylabel('Total Amount', color='darkgreen')
ax2.tick_params(axis='y', labelcolor='darkgreen')

if not suspicious_grouped.empty:
    ax1.scatter(suspicious_grouped['window_start'], 
                suspicious_grouped['suspicious_count'] * 4,  
                color='darkred', marker='*', s=250, 
                label='Suspicious Users (scaled count)', zorder=10)

   
    for i, row in suspicious_grouped.iterrows():
        ax1.text(row['window_start'], row['suspicious_count'] * 4 + 3, 
                 str(row['suspicious_count']), 
                 ha='center', va='bottom', fontsize=10, 
                 color='darkred', fontweight='bold')

plt.title('Real-Time Transaction Monitoring & Fraud Detection', fontsize=14, pad=15)
fig.autofmt_xdate(rotation=45)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

ax1.legend(loc='upper left', bbox_to_anchor=(0, 1.02))
ax2.legend(loc='upper right', bbox_to_anchor=(1, 1.02))

plt.tight_layout()
plt.show()