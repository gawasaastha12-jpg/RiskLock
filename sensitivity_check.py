import pandas as pd
import numpy as np
import xgboost as xgb
import os
import joblib

print("="*70)
print("RISKLOCK: SENSITIVITY CHECK REPORT FOR 3-TIER RULE (TEST SET)")
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

# Base reference costs on TEST set:
cost_never_t = np.sum((y_test == 1) * amounts_test)

naive05_mask_t = (p_test_cal >= 0.5)
cost_05_t = np.sum(naive05_mask_t * 500.0) + np.sum((~naive05_mask_t & (y_test == 1)) * amounts_test)

bmr_mask_t = (p_test_cal * amounts_test > 500.0)
cost_bmr_t = np.sum(bmr_mask_t * 500.0) + np.sum((~bmr_mask_t & (y_test == 1)) * amounts_test)

print(f"Reference Test Set Costs:")
print(f"  - Naive Never Flag      : INR {cost_never_t:,.2f}")
print(f"  - 2-Tier Calibrated BMR : INR {cost_bmr_t:,.2f}")
print(f"  - Naive 0.5 Calibrated  : INR {cost_05_t:,.2f}")

def evaluate_3tier_scenario(stepup_fee, catch_rate, scenario_name):
    uncovered_rate = 1.0 - catch_rate
    
    exp_cost_block = np.full(len(test_df), 500.0)
    exp_cost_stepup = stepup_fee + uncovered_rate * p_test_cal * amounts_test
    exp_cost_approve = p_test_cal * amounts_test
    
    exp_costs = np.column_stack([exp_cost_block, exp_cost_stepup, exp_cost_approve])
    tier_choices = np.argmin(exp_costs, axis=1)  # 0: BLOCK, 1: STEP_UP, 2: APPROVE
    
    realized_costs = np.zeros(len(test_df))
    
    b_mask = (tier_choices == 0)
    s_mask = (tier_choices == 1)
    a_mask = (tier_choices == 2)
    
    realized_costs[b_mask] = 500.0
    realized_costs[s_mask] = stepup_fee + (y_test[s_mask] == 1) * uncovered_rate * amounts_test[s_mask]
    realized_costs[a_mask] = 0.0 + (y_test[a_mask] == 1) * 1.00 * amounts_test[a_mask]
    
    tot_cost = np.sum(realized_costs)
    
    n_approve = np.sum(a_mask)
    n_stepup = np.sum(s_mask)
    n_block = np.sum(b_mask)
    
    beats_bmr = tot_cost < cost_bmr_t
    beats_05 = tot_cost < cost_05_t
    
    return {
        'Scenario': scenario_name,
        'Step-Up Fee': f"INR {stepup_fee}",
        'Catch Rate': f"{catch_rate*100:.0f}%",
        'Approve Count': f"{n_approve:,}",
        'Step-Up Count': f"{n_stepup:,}",
        'Block Count': f"{n_block:,}",
        'Total Realized Cost (INR)': f"INR {tot_cost:,.2f}",
        'Beats 2-Tier BMR?': "YES" if beats_bmr else "NO",
        'Beats Naive 0.5?': "YES" if beats_05 else "NO",
        'Savings vs Naive 0.5': f"INR {cost_05_t - tot_cost:+,.2f}"
    }

scenarios = [
    evaluate_3tier_scenario(30, 0.90, "Original Baseline (Fee=30, Catch=90%)"),
    evaluate_3tier_scenario(30, 0.75, "(a) Pessimistic Catch Rate (Fee=30, Catch=75%)"),
    evaluate_3tier_scenario(100, 0.90, "(b) Expensive Verification (Fee=100, Catch=90%)"),
    evaluate_3tier_scenario(100, 0.75, "(c) Harshest Combination (Fee=100, Catch=75%)")
]

sens_df = pd.DataFrame(scenarios)

print("\n" + "="*70)
print("SENSITIVITY ANALYSIS SUMMARY TABLE (TEST SET)")
print("="*70)
print(sens_df[['Scenario', 'Step-Up Count', 'Block Count', 'Total Realized Cost (INR)', 'Beats 2-Tier BMR?', 'Beats Naive 0.5?']].to_string(index=False))

print("\n" + "="*70)
print("DETAILED SCENARIO BREAKDOWN")
print("="*70)
for s in scenarios:
    print(f"\n[{s['Scenario']}]")
    print(f"  - Routing Counts    : Approve={s['Approve Count']} | Step-Up={s['Step-Up Count']} | Block={s['Block Count']}")
    print(f"  - Total Realized Cost: {s['Total Realized Cost (INR)']}")
    print(f"  - Savings vs Naive 0.5: {s['Savings vs Naive 0.5']}")
    print(f"  - Status vs 2-Tier BMR: {'Outperforms 2-Tier BMR' if s['Beats 2-Tier BMR?'] == 'YES' else 'Lags 2-Tier BMR'}")
    print(f"  - Status vs Naive 0.5 : {'Outperforms Naive 0.5' if s['Beats Naive 0.5?'] == 'YES' else 'Lags Naive 0.5'}")

print("="*70)
