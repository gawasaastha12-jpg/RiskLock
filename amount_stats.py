import pandas as pd
import numpy as np

print("="*70)
print("RISKLOCK: TRANSACTION AMOUNT DISTRIBUTION STATS (TRAINING SET)")
print("="*70)

csv_path = "PS_20174392719_1491204439457_log.csv"
indices_path = "models/split_indices.npz"

df = pd.read_csv(csv_path)
df = df.sort_values(by='step').reset_index(drop=True)

split_data = np.load(indices_path)
train_indices = split_data['train']

train_df = df.iloc[train_indices]

fraud_amounts = train_df[train_df['isFraud'] == 1]['amount']
non_fraud_amounts = train_df[train_df['isFraud'] == 0]['amount']

def get_stats(series):
    return {
        'Count': f"{len(series):,}",
        'Mean ($)': f"{series.mean():,.2f}",
        'Median ($)': f"{series.median():,.2f}",
        'Min ($)': f"{series.min():,.2f}",
        'Max ($)': f"{series.max():,.2f}"
    }

# 1. Fraud vs Non-Fraud Overall
print("\n--- 1 & 2. OVERALL TRANSACTION AMOUNT STATS (TRAIN SET) ---")
overall_table = pd.DataFrame([
    {'Group': 'Fraud Rows Only', **get_stats(fraud_amounts)},
    {'Group': 'Non-Fraud Rows Only', **get_stats(non_fraud_amounts)}
])
print(overall_table.to_string(index=False))

# 3. Fraud Breakdown by Transaction Type (TRANSFER vs CASH_OUT)
print("\n--- 3. FRAUD AMOUNT STATS BY TRANSACTION TYPE (TRAIN SET) ---")
fraud_train_df = train_df[train_df['isFraud'] == 1]
fraud_types = fraud_train_df['type'].unique()

type_rows = []
for t in sorted(fraud_types):
    amounts_by_t = fraud_train_df[fraud_train_df['type'] == t]['amount']
    type_rows.append({'Fraud Transaction Type': t, **get_stats(amounts_by_t)})

type_table = pd.DataFrame(type_rows)
print(type_table.to_string(index=False))

print("="*70)
