import pandas as pd
import numpy as np
import xgboost as xgb
import os
import joblib

print("="*70)
print("RISKLOCK: THREE-TIER EXPECTED-COST DECISIONING REPORT (VALIDATION SET)")
print("="*70)

csv_path = "PS_20174392719_1491204439457_log.csv"
model_path = "models/baseline_xgboost.json"
calibrator_path = "models/calibrated_platt_scaler.joblib"
indices_path = "models/split_indices.npz"

print("\nLoading dataset, split indices, baseline model, and calibrator...")
df = pd.read_csv(csv_path)
df = df.sort_values(by='step').reset_index(drop=True)

split_data = np.load(indices_path)
val_indices = split_data['val']

val_df = df.iloc[val_indices].copy()
y_val = val_df['isFraud'].to_numpy()
amounts_val = val_df['amount'].to_numpy()

feature_cols = ['amount', 'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest']
df_encoded = pd.get_dummies(df[['type'] + feature_cols], columns=['type'], drop_first=False)
X_val = df_encoded.iloc[val_indices]

model = xgb.XGBClassifier()
model.load_model(model_path)
platt_calibrator = joblib.load(calibrator_path)

p_val_raw = model.predict_proba(X_val)[:, 1]
p_val_cal = platt_calibrator.predict_proba(p_val_raw.reshape(-1, 1))[:, 1]

# ---------------------------------------------------------
# THREE-TIER DECISION RULE DERIVATION & ASSUMPTIONS:
# 1. BLOCK   : cost = 500 (full manual review)
# 2. STEP_UP : cost = 30 + p * (1 - 0.90) * amount = 30 + 0.10 * p * amount
#    * EXPLICIT ASSUMPTION: Step-up (e.g. OTP/2FA) deters 90% of real fraud attempts,
#      leaving a 10% residual unrecovered loss if the transaction is truly fraudulent.
# 3. APPROVE : cost = p * amount (auto-approve, zero friction)
# ---------------------------------------------------------

# Compute expected costs for each transaction
exp_cost_block = np.full(len(val_df), 500.0)
exp_cost_stepup = 30.0 + 0.10 * p_val_cal * amounts_val
exp_cost_approve = p_val_cal * amounts_val

# Stack expected costs into array of shape (N, 3): columns [0: BLOCK, 1: STEP_UP, 2: APPROVE]
exp_costs = np.column_stack([exp_cost_block, exp_cost_stepup, exp_cost_approve])
tier_choices = np.argmin(exp_costs, axis=1)  # 0: BLOCK, 1: STEP_UP, 2: APPROVE

tier_names = np.array(['BLOCK', 'STEP_UP', 'APPROVE'])
val_df['chosen_tier'] = tier_names[tier_choices]

# ---------------------------------------------------------
# REALIZED COST CALCULATION (VALIDATION SET):
# - BLOCK   : INR 500 flat (regardless of true label)
# - STEP_UP : INR 30 flat + (if truly fraud y=1) 10% * amount
# - APPROVE : INR 0 flat + (if truly fraud y=1) 100% * amount
# ---------------------------------------------------------
realized_costs = np.zeros(len(val_df))

block_mask = (tier_choices == 0)
stepup_mask = (tier_choices == 1)
approve_mask = (tier_choices == 2)

realized_costs[block_mask] = 500.0
realized_costs[stepup_mask] = 30.0 + (y_val[stepup_mask] == 1) * 0.10 * amounts_val[stepup_mask]
realized_costs[approve_mask] = 0.0 + (y_val[approve_mask] == 1) * 1.00 * amounts_val[approve_mask]

total_realized_cost_3tier = np.sum(realized_costs)

# ---------------------------------------------------------
# 1 & 2. TIER BREAKDOWN STATS
# ---------------------------------------------------------
print("\n" + "="*70)
print("1 & 2. THREE-TIER ROUTING & TIER METRICS BREAKDOWN (VALIDATION SET)")
print("="*70)

tier_stats = []
for t_idx, t_name in enumerate(['APPROVE', 'STEP_UP', 'BLOCK']):
    mask = (tier_names[tier_choices] == t_name)
    count = np.sum(mask)
    if count > 0:
        frauds = y_val[mask]
        amts = amounts_val[mask]
        f_count = np.sum(frauds)
        f_rate = (f_count / count) * 100
        mean_amt = amts.mean()
        med_amt = np.median(amts)
    else:
        f_count = 0
        f_rate = 0.0
        mean_amt = 0.0
        med_amt = 0.0

    tier_stats.append({
        'Decision Tier': t_name,
        'Txn Count': f"{count:,}",
        '% of Val Set': f"{(count/len(val_df))*100:.2f}%",
        'Actual Fraud Count': f"{f_count:,}",
        'Fraud Rate (%)': f"{f_rate:.4f}%",
        'Mean Amount (INR)': f"INR {mean_amt:,.2f}",
        'Median Amount (INR)': f"INR {med_amt:,.2f}"
    })

tier_df = pd.DataFrame(tier_stats)
print(tier_df.to_string(index=False))

# ---------------------------------------------------------
# 3 & 4. FINANCIAL COST COMPARISON AGAINST PREVIOUS STRATEGIES
# ---------------------------------------------------------
print("\n" + "="*70)
print("3 & 4. FINANCIAL COST COMPARISON ACROSS STRATEGIES (VALIDATION SET)")
print("="*70)

# Previous strategy costs on validation set:
# 1. Never Flag
cost_never = np.sum((y_val == 1) * amounts_val)

# 2. Naive 0.5 Threshold Calibrated
naive05_mask = (p_val_cal >= 0.5)
cost_05 = np.sum(naive05_mask * 500.0) + np.sum((~naive05_mask & (y_val == 1)) * amounts_val)

# 3. Calibrated BMR
bmr_mask = (p_val_cal * amounts_val > 500.0)
cost_bmr = np.sum(bmr_mask * 500.0) + np.sum((~bmr_mask & (y_val == 1)) * amounts_val)

cost_comp_df = pd.DataFrame([
    {
        'Strategy': 'Naive Never Flag Anything',
        'Total Realized Cost (INR)': f"INR {cost_never:,.2f}",
        'Savings vs Never Flag': "INR 0.00 (Baseline)"
    },
    {
        'Strategy': 'Naive 0.5 Threshold (Calibrated)',
        'Total Realized Cost (INR)': f"INR {cost_05:,.2f}",
        'Savings vs Never Flag': f"INR {cost_never - cost_05:,.2f} ({((cost_never - cost_05)/cost_never)*100:.2f}%)"
    },
    {
        'Strategy': 'Calibrated BMR Rule (2-Tier)',
        'Total Realized Cost (INR)': f"INR {cost_bmr:,.2f}",
        'Savings vs Never Flag': f"INR {cost_never - cost_bmr:,.2f} ({((cost_never - cost_bmr)/cost_never)*100:.2f}%)"
    },
    {
        'Strategy': 'Three-Tier Expected-Cost Rule',
        'Total Realized Cost (INR)': f"INR {total_realized_cost_3tier:,.2f}",
        'Savings vs Never Flag': f"INR {cost_never - total_realized_cost_3tier:,.2f} ({((cost_never - total_realized_cost_3tier)/cost_never)*100:.2f}%)"
    }
])

print(cost_comp_df.to_string(index=False))

print(f"\nNet Savings of 3-Tier Rule vs 2-Tier BMR  : INR {cost_bmr - total_realized_cost_3tier:,.2f}")
print(f"Net Savings of 3-Tier Rule vs Naive 0.5  : INR {cost_05 - total_realized_cost_3tier:,.2f}")

print("\n" + "="*70)
print("CONFIRMATION: Held-out test set (89,466 rows) remains UNTOUCHED.")
print("="*70)
