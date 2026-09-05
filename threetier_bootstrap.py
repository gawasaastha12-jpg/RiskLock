import pandas as pd
import numpy as np
import xgboost as xgb
import os
import joblib

print("="*70)
print("RISKLOCK: THREE-TIER BOOTSTRAP SIGNIFICANCE REPORT (TEST SET)")
print("="*70)

csv_path = "PS_20174392719_1491204439457_log.csv"
model_path = "models/baseline_xgboost.json"
calibrator_path = "models/calibrated_platt_scaler.joblib"
indices_path = "models/split_indices.npz"

df = pd.read_csv(csv_path)
df = df.sort_values(by='step').reset_index(drop=True)

split_data = np.load(indices_path)
test_indices = split_data['test']

test_df = df.iloc[test_indices].copy()
y_test = test_df['isFraud'].to_numpy()
amounts_test = test_df['amount'].to_numpy()

feature_cols = ['amount', 'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest']
df_encoded = pd.get_dummies(df[['type'] + feature_cols], columns=['type'], drop_first=False)
X_test = df_encoded.iloc[test_indices]

model = xgb.XGBClassifier()
model.load_model(model_path)
platt_calibrator = joblib.load(calibrator_path)

p_test_raw = model.predict_proba(X_test)[:, 1]
p_test_cal = platt_calibrator.predict_proba(p_test_raw.reshape(-1, 1))[:, 1]

# ---------------------------------------------------------
# PRECOMPUTE DECISIONS ON TEST SET
# ---------------------------------------------------------
exp_cost_block = np.full(len(test_df), 500.0)
exp_cost_stepup = 30.0 + 0.10 * p_test_cal * amounts_test
exp_cost_approve = p_test_cal * amounts_test

exp_costs_test = np.column_stack([exp_cost_block, exp_cost_stepup, exp_cost_approve])
tier_choices = np.argmin(exp_costs_test, axis=1)  # 0: BLOCK, 1: STEP_UP, 2: APPROVE

naive05_mask = (p_test_cal >= 0.5)
bmr_mask = (p_test_cal * amounts_test > 500.0)

# Precompute per-row realized costs
cost_rows_3tier = np.zeros(len(test_df))
cost_rows_3tier[tier_choices == 0] = 500.0
cost_rows_3tier[tier_choices == 1] = 30.0 + (y_test[tier_choices == 1] == 1) * 0.10 * amounts_test[tier_choices == 1]
cost_rows_3tier[tier_choices == 2] = 0.0 + (y_test[tier_choices == 2] == 1) * 1.00 * amounts_test[tier_choices == 2]

cost_rows_naive05 = np.zeros(len(test_df))
cost_rows_naive05[naive05_mask] = 500.0
cost_rows_naive05[~naive05_mask] = (y_test[~naive05_mask] == 1) * 1.00 * amounts_test[~naive05_mask]

cost_rows_bmr = np.zeros(len(test_df))
cost_rows_bmr[bmr_mask] = 500.0
cost_rows_bmr[~bmr_mask] = (y_test[~bmr_mask] == 1) * 1.00 * amounts_test[~bmr_mask]

# ---------------------------------------------------------
# STRATIFIED BOOTSTRAP (1,000 RESAMPLES)
# ---------------------------------------------------------
print("\nRunning 1,000 stratified bootstrap iterations on Test set...")
np.random.seed(42)
n_iterations = 1000

fraud_idx = np.where(y_test == 1)[0]
non_fraud_idx = np.where(y_test == 0)[0]

n_fraud = len(fraud_idx)
n_non_fraud = len(non_fraud_idx)

diff_a_list = np.zeros(n_iterations)  # 3-Tier minus Naive 0.5
diff_b_list = np.zeros(n_iterations)  # 3-Tier minus 2-Tier BMR

for i in range(n_iterations):
    boot_fraud_idx = np.random.choice(fraud_idx, size=n_fraud, replace=True)
    boot_non_fraud_idx = np.random.choice(non_fraud_idx, size=n_non_fraud, replace=True)
    boot_idx = np.concatenate([boot_fraud_idx, boot_non_fraud_idx])
    
    tot_3tier = np.sum(cost_rows_3tier[boot_idx])
    tot_naive05 = np.sum(cost_rows_naive05[boot_idx])
    tot_bmr = np.sum(cost_rows_bmr[boot_idx])
    
    diff_a_list[i] = tot_3tier - tot_naive05
    diff_b_list[i] = tot_3tier - tot_bmr

# Statistics for (a) 3-Tier minus Naive 0.5
mean_a = np.mean(diff_a_list)
std_a = np.std(diff_a_list)
ci_a_lower = np.percentile(diff_a_list, 2.5)
ci_a_median = np.percentile(diff_a_list, 50.0)
ci_a_upper = np.percentile(diff_a_list, 97.5)
excludes_zero_a = (ci_a_upper < 0) or (ci_a_lower > 0)

# Statistics for (b) 3-Tier minus 2-Tier BMR
mean_b = np.mean(diff_b_list)
std_b = np.std(diff_b_list)
ci_b_lower = np.percentile(diff_b_list, 2.5)
ci_b_median = np.percentile(diff_b_list, 50.0)
ci_b_upper = np.percentile(diff_b_list, 97.5)
excludes_zero_b = (ci_b_upper < 0) or (ci_b_lower > 0)

print("\n" + "="*70)
print("1. (a) THREE-TIER COST MINUS NAIVE-0.5 COST")
print("="*70)
print(f"  - Point Estimate Savings : INR {np.sum(cost_rows_naive05) - np.sum(cost_rows_3tier):+,.2f}")
print(f"  - Mean Difference (3T - N05): INR {mean_a:+,.2f}")
print(f"  - Median Difference      : INR {ci_a_median:+,.2f}")
print(f"  - Std Deviation          : INR {std_a:,.2f}")
print(f"  - 95% Confidence Interval: [INR {ci_a_lower:+,.2f}, INR {ci_a_upper:+,.2f}]")
print(f"  - Excludes Zero (INR 0)?  : {'YES (Statistically Significant)' if excludes_zero_a else 'NO (Contains Zero)'}")

print("\n" + "="*70)
print("2. (b) THREE-TIER COST MINUS 2-TIER BMR COST")
print("="*70)
print(f"  - Point Estimate Savings : INR {np.sum(cost_rows_bmr) - np.sum(cost_rows_3tier):+,.2f}")
print(f"  - Mean Difference (3T - BMR): INR {mean_b:+,.2f}")
print(f"  - Median Difference      : INR {ci_b_median:+,.2f}")
print(f"  - Std Deviation          : INR {std_b:,.2f}")
print(f"  - 95% Confidence Interval: [INR {ci_b_lower:+,.2f}, INR {ci_b_upper:+,.2f}]")
print(f"  - Excludes Zero (INR 0)?  : {'YES (Statistically Significant)' if excludes_zero_b else 'NO (Contains Zero)'}")

print("\n" + "="*70)
print("SUMMARY TABLE OF BOOTSTRAP CONFIDENCE INTERVALS")
print("="*70)
bootstrap_summary = pd.DataFrame([
    {
        'Comparison Difference': '(a) 3-Tier - Naive 0.5',
        'Mean Diff (INR)': f"INR {mean_a:+,.2f}",
        'Std Dev (INR)': f"INR {std_a:,.2f}",
        '95% Confidence Interval': f"[INR {ci_a_lower:+,.2f}, INR {ci_a_upper:+,.2f}]",
        'Excludes Zero?': 'YES' if excludes_zero_a else 'NO'
    },
    {
        'Comparison Difference': '(b) 3-Tier - 2-Tier BMR',
        'Mean Diff (INR)': f"INR {mean_b:+,.2f}",
        'Std Dev (INR)': f"INR {std_b:,.2f}",
        '95% Confidence Interval': f"[INR {ci_b_lower:+,.2f}, INR {ci_b_upper:+,.2f}]",
        'Excludes Zero?': 'YES' if excludes_zero_b else 'NO'
    }
])
print(bootstrap_summary.to_string(index=False))
print("="*70)
