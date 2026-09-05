import pandas as pd
import numpy as np
import xgboost as xgb
import os
import joblib

print("="*70)
print("RISKLOCK: TEST SET DISAGREEMENT & BOOTSTRAP SIGNIFICANCE REPORT")
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

bmr_flag = (p_test_cal * amounts_test > 500).astype(int)
naive05_flag = (p_test_cal >= 0.5).astype(int)

# ---------------------------------------------------------
# 1. DIAGNOSTIC: DISAGREEMENT BREAKDOWN
# ---------------------------------------------------------
print("\n" + "="*70)
print("1. DISAGREEMENT BREAKDOWN BETWEEN BMR AND NAIVE-0.5 (TEST SET)")
print("="*70)

group_a_mask = (bmr_flag == 1) & (naive05_flag == 0)
group_b_mask = (naive05_flag == 1) & (bmr_flag == 0)

def summarize_group(mask, group_name):
    count = np.sum(mask)
    if count == 0:
        return {
            'Group': group_name,
            'Count': 0,
            'Actual Fraud Count': 0,
            'Fraud Rate (%)': "0.00%",
            'Mean Amount (INR)': "INR 0.00",
            'Median Amount (INR)': "INR 0.00",
            'Min Amount (INR)': "INR 0.00",
            'Max Amount (INR)': "INR 0.00"
        }
    frauds = y_test[mask]
    amounts = amounts_test[mask]
    return {
        'Group': group_name,
        'Count': f"{count:,}",
        'Actual Fraud Count': f"{np.sum(frauds):,}",
        'Fraud Rate (%)': f"{(np.mean(frauds)*100):.2f}%",
        'Mean Amount (INR)': f"INR {amounts.mean():,.2f}",
        'Median Amount (INR)': f"INR {np.median(amounts):,.2f}",
        'Min Amount (INR)': f"INR {amounts.min():,.2f}",
        'Max Amount (INR)': f"INR {amounts.max():,.2f}"
    }

disagreement_df = pd.DataFrame([
    summarize_group(group_a_mask, "(a) BMR Flagged=1, Naive-0.5=0"),
    summarize_group(group_b_mask, "(b) Naive-0.5 Flagged=1, BMR=0")
])

print(disagreement_df.to_string(index=False))

# Detailed analysis of Group A (BMR=1, Naive05=0)
if np.sum(group_a_mask) > 0:
    frauds_in_a = np.sum(y_test[group_a_mask])
    non_frauds_in_a = np.sum(group_a_mask) - frauds_in_a
    p_in_a = p_test_cal[group_a_mask]
    amt_in_a = amounts_test[group_a_mask]
    print(f"\nGroup (a) Detail:")
    print(f"  - Total Transactions: {np.sum(group_a_mask):,}")
    print(f"  - Actual Fraud Cases: {frauds_in_a:,} (TP gained by BMR)")
    print(f"  - Actual Non-Fraud  : {non_frauds_in_a:,} (FP added by BMR)")
    print(f"  - Probability Range : [{p_in_a.min():.6f}, {p_in_a.max():.6f}]")
    print(f"  - Amount Range      : [INR {amt_in_a.min():,.2f}, INR {amt_in_a.max():,.2f}]")

# Detailed analysis of Group B (Naive05=1, BMR=0)
if np.sum(group_b_mask) > 0:
    frauds_in_b = np.sum(y_test[group_b_mask])
    non_frauds_in_b = np.sum(group_b_mask) - frauds_in_b
    p_in_b = p_test_cal[group_b_mask]
    amt_in_b = amounts_test[group_b_mask]
    print(f"\nGroup (b) Detail:")
    print(f"  - Total Transactions: {np.sum(group_b_mask):,}")
    print(f"  - Actual Fraud Cases: {frauds_in_b:,} (FN caused by BMR)")
    print(f"  - Actual Non-Fraud  : {non_frauds_in_b:,} (FP saved by BMR)")
    print(f"  - Probability Range : [{p_in_b.min():.6f}, {p_in_b.max():.6f}]")
    print(f"  - Amount Range      : [INR {amt_in_b.min():,.2f}, INR {amt_in_b.max():,.2f}]")

# ---------------------------------------------------------
# 2. STATISTICAL CHECK: BOOTSTRAP SIGNIFICANCE (1,000 RESAMPLES)
# ---------------------------------------------------------
print("\n" + "="*70)
print("2. BOOTSTRAP SIGNIFICANCE CHECK (1,000 STRATIFIED RESAMPLES)")
print("="*70)

np.random.seed(42)
n_iterations = 1000

fraud_idx = np.where(y_test == 1)[0]
non_fraud_idx = np.where(y_test == 0)[0]

n_fraud = len(fraud_idx)
n_non_fraud = len(non_fraud_idx)

def compute_cost_fast(y_sub, bmr_sub, naive_sub, amt_sub):
    # Cost BMR
    tp_bmr = np.sum((y_sub == 1) & (bmr_sub == 1))
    fp_bmr = np.sum((y_sub == 0) & (bmr_sub == 1))
    fn_bmr_mask = (y_sub == 1) & (bmr_sub == 0)
    cost_bmr = (tp_bmr + fp_bmr) * 500 + np.sum(amt_sub[fn_bmr_mask])
    
    # Cost Naive 0.5
    tp_n05 = np.sum((y_sub == 1) & (naive_sub == 1))
    fp_n05 = np.sum((y_sub == 0) & (naive_sub == 1))
    fn_n05_mask = (y_sub == 1) & (naive_sub == 0)
    cost_n05 = (tp_n05 + fp_n05) * 500 + np.sum(amt_sub[fn_n05_mask])
    
    return cost_bmr, cost_n05

cost_diffs = np.zeros(n_iterations)
bmr_costs = np.zeros(n_iterations)
naive_costs = np.zeros(n_iterations)

print(f"Running {n_iterations:,} bootstrap iterations (resampling test set with replacement)...")

for i in range(n_iterations):
    boot_fraud_idx = np.random.choice(fraud_idx, size=n_fraud, replace=True)
    boot_non_fraud_idx = np.random.choice(non_fraud_idx, size=n_non_fraud, replace=True)
    
    boot_idx = np.concatenate([boot_fraud_idx, boot_non_fraud_idx])
    
    y_boot = y_test[boot_idx]
    bmr_boot = bmr_flag[boot_idx]
    naive_boot = naive05_flag[boot_idx]
    amt_boot = amounts_test[boot_idx]
    
    c_bmr, c_n05 = compute_cost_fast(y_boot, bmr_boot, naive_boot, amt_boot)
    bmr_costs[i] = c_bmr
    naive_costs[i] = c_n05
    cost_diffs[i] = c_bmr - c_n05  # BMR cost minus Naive 0.5 cost

ci_lower = np.percentile(cost_diffs, 2.5)
ci_median = np.percentile(cost_diffs, 50.0)
ci_upper = np.percentile(cost_diffs, 97.5)

print("\nBOOTSTRAP RESULTS FOR COST DIFFERENCE (BMR Cost - Naive 0.5 Cost):")
print(f"  - Mean Difference   : INR {np.mean(cost_diffs):+,.2f}")
print(f"  - Median Difference : INR {ci_median:+,.2f}")
print(f"  - Std Deviation     : INR {np.std(cost_diffs):,.2f}")
print(f"  - 95% Conf. Interval: [INR {ci_lower:+,.2f}, INR {ci_upper:+,.2f}]")

is_zero_in_ci = (ci_lower <= 0) and (ci_upper >= 0)
print(f"\nSTATISTICAL SIGNIFICANCE CONCLUSION:")
if is_zero_in_ci:
    print("  RESULT: The 95% Confidence Interval CONTAINS INR 0.")
    print("  CONCLUSION: The ~INR 18,000 cost gap between BMR and Naive 0.5 is NOT statistically significant.")
    print("  It represents random sample variation / noise within the held-out test set.")
else:
    print("  RESULT: The 95% Confidence Interval DOES NOT contain INR 0.")
    print("  CONCLUSION: The cost difference is statistically significant at the 95% level.")

print("="*70)
