import pandas as pd
import numpy as np
import xgboost as xgb
import os
import joblib

print("="*70)
print("RISKLOCK: OFFICIAL FINAL TEST-SET 3-TIER EVALUATION REPORT")
print("="*70)

csv_path = "PS_20174392719_1491204439457_log.csv"
model_path = "models/baseline_xgboost.json"
calibrator_path = "models/calibrated_platt_scaler.joblib"
indices_path = "models/split_indices.npz"

print("\nLoading dataset, split indices, frozen model, and Platt calibrator...")
df = pd.read_csv(csv_path)
df = df.sort_values(by='step').reset_index(drop=True)

split_data = np.load(indices_path)
test_indices = split_data['test']

test_df = df.iloc[test_indices].copy()
y_test = test_df['isFraud'].to_numpy()
amounts_test = test_df['amount'].to_numpy()

print(f"Held-out Test Set Rows: {len(test_df):,} (Steps {test_df['step'].min()} to {test_df['step'].max()})")
print(f"Test Set Fraud Count : {np.sum(y_test):,} ({np.mean(y_test)*100:.4f}%)")

feature_cols = ['amount', 'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest']
df_encoded = pd.get_dummies(df[['type'] + feature_cols], columns=['type'], drop_first=False)
X_test = df_encoded.iloc[test_indices]

model = xgb.XGBClassifier()
model.load_model(model_path)
platt_calibrator = joblib.load(calibrator_path)

# Predict calibrated probabilities on TEST set
print("\nPredicting calibrated probabilities on HELD-OUT TEST SET...")
p_test_raw = model.predict_proba(X_test)[:, 1]
p_test_cal = platt_calibrator.predict_proba(p_test_raw.reshape(-1, 1))[:, 1]

# ---------------------------------------------------------
# THREE-TIER DECISION RULE ON TEST SET:
# 1. BLOCK   : exp_cost = 500
# 2. STEP_UP : exp_cost = 30 + 0.10 * p_cal * amount
# 3. APPROVE : exp_cost = p_cal * amount
# ---------------------------------------------------------

exp_cost_block = np.full(len(test_df), 500.0)
exp_cost_stepup = 30.0 + 0.10 * p_test_cal * amounts_test
exp_cost_approve = p_test_cal * amounts_test

exp_costs_test = np.column_stack([exp_cost_block, exp_cost_stepup, exp_cost_approve])
tier_choices_test = np.argmin(exp_costs_test, axis=1)  # 0: BLOCK, 1: STEP_UP, 2: APPROVE

tier_names = np.array(['BLOCK', 'STEP_UP', 'APPROVE'])

# ---------------------------------------------------------
# REALIZED COST ON TEST SET:
# - BLOCK   : INR 500 flat
# - STEP_UP : INR 30 flat + y * 0.10 * amount
# - APPROVE : INR 0 flat + y * 1.00 * amount
# ---------------------------------------------------------
realized_costs_test = np.zeros(len(test_df))

block_mask = (tier_choices_test == 0)
stepup_mask = (tier_choices_test == 1)
approve_mask = (tier_choices_test == 2)

realized_costs_test[block_mask] = 500.0
realized_costs_test[stepup_mask] = 30.0 + (y_test[stepup_mask] == 1) * 0.10 * amounts_test[stepup_mask]
realized_costs_test[approve_mask] = 0.0 + (y_test[approve_mask] == 1) * 1.00 * amounts_test[approve_mask]

total_realized_cost_3tier_test = np.sum(realized_costs_test)

# ---------------------------------------------------------
# 1 & 2. TIER BREAKDOWN STATS ON TEST SET
# ---------------------------------------------------------
print("\n" + "="*70)
print("1 & 2. OFFICIAL THREE-TIER ROUTING & METRICS BREAKDOWN (TEST SET)")
print("="*70)

tier_stats_test = []
for t_idx, t_name in enumerate(['APPROVE', 'STEP_UP', 'BLOCK']):
    mask = (tier_names[tier_choices_test] == t_name)
    count = np.sum(mask)
    if count > 0:
        frauds = y_test[mask]
        amts = amounts_test[mask]
        f_count = np.sum(frauds)
        f_rate = (f_count / count) * 100
        mean_amt = amts.mean()
        med_amt = np.median(amts)
    else:
        f_count = 0
        f_rate = 0.0
        mean_amt = 0.0
        med_amt = 0.0

    tier_stats_test.append({
        'Decision Tier': t_name,
        'Txn Count': f"{count:,}",
        '% of Test Set': f"{(count/len(test_df))*100:.2f}%",
        'Actual Fraud Count': f"{f_count:,}",
        'Fraud Rate (%)': f"{f_rate:.4f}%",
        'Mean Amount (INR)': f"INR {mean_amt:,.2f}",
        'Median Amount (INR)': f"INR {med_amt:,.2f}"
    })

tier_test_df = pd.DataFrame(tier_stats_test)
print(tier_test_df.to_string(index=False))

# ---------------------------------------------------------
# 3. OFFICIAL FINANCIAL COST COMPARISON (TEST SET)
# ---------------------------------------------------------
print("\n" + "="*70)
print("3. OFFICIAL FINANCIAL COST COMPARISON ACROSS STRATEGIES (TEST SET)")
print("="*70)

# Test set costs for previous strategies:
cost_never_t = np.sum((y_test == 1) * amounts_test)

naive05_mask_t = (p_test_cal >= 0.5)
cost_05_t = np.sum(naive05_mask_t * 500.0) + np.sum((~naive05_mask_t & (y_test == 1)) * amounts_test)

bmr_mask_t = (p_test_cal * amounts_test > 500.0)
cost_bmr_t = np.sum(bmr_mask_t * 500.0) + np.sum((~bmr_mask_t & (y_test == 1)) * amounts_test)

cost_comp_test_df = pd.DataFrame([
    {
        'Strategy': 'Naive Never Flag Anything',
        'Total Realized Cost (INR)': f"INR {cost_never_t:,.2f}",
        'Savings vs Never Flag': "INR 0.00 (Baseline)"
    },
    {
        'Strategy': 'Calibrated BMR Rule (2-Tier)',
        'Total Realized Cost (INR)': f"INR {cost_bmr_t:,.2f}",
        'Savings vs Never Flag': f"INR {cost_never_t - cost_bmr_t:,.2f} ({((cost_never_t - cost_bmr_t)/cost_never_t)*100:.2f}%)"
    },
    {
        'Strategy': 'Naive 0.5 Threshold (Calibrated)',
        'Total Realized Cost (INR)': f"INR {cost_05_t:,.2f}",
        'Savings vs Never Flag': f"INR {cost_never_t - cost_05_t:,.2f} ({((cost_never_t - cost_05_t)/cost_never_t)*100:.2f}%)"
    },
    {
        'Strategy': 'Three-Tier Expected-Cost Rule',
        'Total Realized Cost (INR)': f"INR {total_realized_cost_3tier_test:,.2f}",
        'Savings vs Never Flag': f"INR {cost_never_t - total_realized_cost_3tier_test:,.2f} ({((cost_never_t - total_realized_cost_3tier_test)/cost_never_t)*100:.2f}%)"
    }
])

print(cost_comp_test_df.to_string(index=False))

print(f"\nNet Additional Savings of 3-Tier Rule vs Naive 0.5  : INR {cost_05_t - total_realized_cost_3tier_test:,.2f}")
print(f"Net Additional Savings of 3-Tier Rule vs 2-Tier BMR  : INR {cost_bmr_t - total_realized_cost_3tier_test:,.2f}")

# Save final 3-tier evaluation results to text file artifact
with open("models/final_3tier_test_evaluation.txt", "w") as f:
    f.write("RISKLOCK OFFICIAL 3-TIER TEST SET EVALUATION\n")
    f.write(f"Total Test Rows: {len(test_df):,}\n")
    f.write(f"3-Tier Total Cost: INR {total_realized_cost_3tier_test:,.2f}\n")
    f.write(f"2-Tier BMR Cost  : INR {cost_bmr_t:,.2f}\n")
    f.write(f"Naive 0.5 Cost   : INR {cost_05_t:,.2f}\n")
    f.write(f"Never Flag Cost  : INR {cost_never_t:,.2f}\n")

print("\nSaved official 3-tier test evaluation to: models/final_3tier_test_evaluation.txt")
print("="*70)
