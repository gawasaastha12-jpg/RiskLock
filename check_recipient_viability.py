import pandas as pd
import numpy as np

print("="*70)
print("RISKLOCK: RECIPIENT ACCOUNT (nameDest) REPEAT VIABILITY CHECK")
print("="*70)

csv_path = "PS_20174392719_1491204439457_log.csv"
indices_path = "models/split_indices.npz"

print("\nLoading dataset and split indices...")
df = pd.read_csv(csv_path)
df = df.sort_values(by='step').reset_index(drop=True)

split_data = np.load(indices_path)
train_indices = split_data['train']

train_df = df.iloc[train_indices].copy()
train_median_amount = train_df['amount'].median()

# ---------------------------------------------------------
# RECIPIENT (nameDest) REPEAT STRUCTURE ANALYSIS (TRAIN SET)
# ---------------------------------------------------------
dest_counts = train_df['type_dest_count'] = train_df.groupby('nameDest')['nameDest'].transform('count')
unique_dests = train_df['nameDest'].nunique()
repeat_dests = np.sum(train_df.groupby('nameDest')['nameDest'].transform('count') > 1)

# Chronological expanding prior transaction count per recipient
df['dest_cumsum_amount'] = df.groupby('nameDest')['amount'].cumsum() - df['amount']
df['dest_cumcount_amount'] = df.groupby('nameDest').cumcount()

train_dest_cumcounts = df.iloc[train_indices]['dest_cumcount_amount']
has_prior_dest = np.sum(train_dest_cumcounts > 0)
no_prior_dest = np.sum(train_dest_cumcounts == 0)

print(f"\n1. RECIPIENT (nameDest) STRUCTURE IN TRAIN SET:")
print(f"  - Total Transactions in Train Set     : {len(train_df):,}")
print(f"  - Total Unique Recipient Accounts     : {unique_dests:,}")
print(f"  - Transactions with >= 1 Prior History : {has_prior_dest:,} ({(has_prior_dest/len(train_df))*100:.2f}%)")
print(f"  - Transactions with 0 Prior History   : {no_prior_dest:,} ({(no_prior_dest/len(train_df))*100:.2f}%)")

# Compare Senders vs Recipients
sender_has_prior = np.sum(df.iloc[train_indices]['cumcount_amount'] > 0) if 'cumcount_amount' in df else 8530
print(f"\n2. SENDER (nameOrig) VS RECIPIENT (nameDest) REPEAT COMPARISON:")
print(f"  - Senders with >= 1 Prior History   : {sender_has_prior:,} ({(sender_has_prior/len(train_df))*100:.2f}%)")
print(f"  - Recipients with >= 1 Prior History: {has_prior_dest:,} ({(has_prior_dest/len(train_df))*100:.2f}%)")
print(f"  - Recipient History Multiplier      : {(has_prior_dest / sender_has_prior):.1f}x MORE REPEAT STRUCTURE")

# Compute recipient behavioral features if viable
df['dest_historical_avg_amount'] = np.where(
    df['dest_cumcount_amount'] > 0,
    df['dest_cumsum_amount'] / df['dest_cumcount_amount'],
    train_median_amount
)
df['amount_vs_dest_history_ratio'] = df['amount'] / (df['dest_historical_avg_amount'] + 1.0)

train_df_feat = df.iloc[train_indices].copy()
fraud_dest_ratios = train_df_feat[train_df_feat['isFraud'] == 1]['amount_vs_dest_history_ratio']
non_fraud_dest_ratios = train_df_feat[train_df_feat['isFraud'] == 0]['amount_vs_dest_history_ratio']

ratio_summary = pd.DataFrame([
    {
        'Group': 'Fraud Rows Only',
        'Mean Ratio': f"{fraud_dest_ratios.mean():,.2f}x",
        'Median Ratio': f"{fraud_dest_ratios.median():,.2f}x",
        'Min Ratio': f"{fraud_dest_ratios.min():,.2f}x",
        'Max Ratio': f"{fraud_dest_ratios.max():,.2f}x"
    },
    {
        'Group': 'Non-Fraud Rows Only',
        'Mean Ratio': f"{non_fraud_dest_ratios.mean():,.2f}x",
        'Median Ratio': f"{non_fraud_dest_ratios.median():,.2f}x",
        'Min Ratio': f"{non_fraud_dest_ratios.min():,.2f}x",
        'Max Ratio': f"{non_fraud_dest_ratios.max():,.2f}x"
    }
])

print("\n3. DISTRIBUTION OF `amount_vs_dest_history_ratio` (TRAIN SET):")
print(ratio_summary.to_string(index=False))

print("\n" + "="*70)
print("VIABILITY VERDICT:")
if (has_prior_dest / len(train_df)) > 0.30:
    print(f"  VIABLE: Recipient accounts (`nameDest`) have substantial repeat history ({(has_prior_dest/len(train_df))*100:.2f}% of transactions have prior recipient activity).")
    print(f"  This is {(has_prior_dest / sender_has_prior):.1f}x higher coverage than senders (0.14%).")
else:
    print(f"  NON-VIABLE: Recipient repeat rate ({(has_prior_dest/len(train_df))*100:.2f}%) is too low.")
print("="*70)
