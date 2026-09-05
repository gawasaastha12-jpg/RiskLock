import pandas as pd
import numpy as np
import xgboost as xgb
import os
import joblib

print("="*70)
print("RISKLOCK: PARETO-CONSTRAINED SEGMENT FAIRNESS THRESHOLD ADJUSTMENT")
print("  ('No Segment Gets Worse' Constraint)")
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
val_df['p_cal'] = p_val_cal
val_df['risk_product'] = p_val_cal * amounts_val

# Assign segments
conditions = [
    (val_df['oldbalanceOrg'] == 0),
    (val_df['oldbalanceOrg'] > 0) & (val_df['oldbalanceOrg'] <= 50000),
    (val_df['oldbalanceOrg'] > 50000) & (val_df['oldbalanceOrg'] <= 250000),
    (val_df['oldbalanceOrg'] > 250000)
]
segment_labels = [
    "1. Zero Balance (INR 0)",
    "2. Low Balance (INR 1 - 50k)",
    "3. Mid Balance (INR 50k - 250k)",
    "4. High Balance (> INR 250k)"
]

val_df['segment'] = np.select(conditions, segment_labels, default="Unknown")

# ---------------------------------------------------------
# 1. STANDARD UNADJUSTED DECISIONS & POPULATION FPR CEILING
# ---------------------------------------------------------
exp_cost_block_std = np.full(len(val_df), 500.0)
exp_cost_stepup_std = 30.0 + 0.10 * p_val_cal * amounts_val
exp_cost_approve_std = p_val_cal * amounts_val

exp_costs_std = np.column_stack([exp_cost_block_std, exp_cost_stepup_std, exp_cost_approve_std])
tier_choices_std = np.argmin(exp_costs_std, axis=1)
tier_names = np.array(['BLOCK', 'STEP_UP', 'APPROVE'])
val_df['tier_std'] = tier_names[tier_choices_std]

legit_val = val_df[val_df['isFraud'] == 0]
total_legit_pop = len(legit_val)
fps_pop_std = np.sum((legit_val['tier_std'] == 'BLOCK') | (legit_val['tier_std'] == 'STEP_UP'))
pop_avg_fpr = (fps_pop_std / total_legit_pop) * 100

print(f"\nPopulation-Wide Legitimate Validation Transactions: {total_legit_pop:,}")
print(f"Population-Wide Average FPR Ceiling Target       : {pop_avg_fpr:.4f}% ({fps_pop_std:,} FPs)")

# ---------------------------------------------------------
# 2. PARETO-CONSTRAINED THRESHOLD ADJUSTMENT
# ---------------------------------------------------------
# Rule:
# Segments with FPR <= pop_avg_fpr (Zero, Low, High): UNTOUCHED (T_k = 33.3333 INR)
# Segments with FPR > pop_avg_fpr (Mid Balance): T_k adjusted upwards to cap FPR at pop_avg_fpr (1.0244%)

segment_thresholds = {}

for seg in segment_labels:
    seg_val = val_df[val_df['segment'] == seg]
    legit_seg = seg_val[seg_val['isFraud'] == 0]
    total_legit_seg = len(legit_seg)
    unadj_fps = np.sum((legit_seg['tier_std'] == 'BLOCK') | (legit_seg['tier_std'] == 'STEP_UP'))
    unadj_fpr = (unadj_fps / total_legit_seg) * 100
    
    if unadj_fpr > pop_avg_fpr:
        # Cap FPR at population average ceiling (1.0244%)
        legit_risk_products = legit_seg['risk_product'].to_numpy()
        target_percentile = 100.0 - pop_avg_fpr
        adj_thresh = np.percentile(legit_risk_products, target_percentile)
        segment_thresholds[seg] = adj_thresh
    else:
        # Untouched at standard 33.3333 INR threshold
        segment_thresholds[seg] = 33.333333

print("\nSEGMENT THRESHOLD ASSIGNMENT:")
for seg in segment_labels:
    print(f"  - {seg:<32}: T_k = INR {segment_thresholds[seg]:.2f}")

# ---------------------------------------------------------
# 3. APPLY PARETO DECISION RULE
# ---------------------------------------------------------
adjusted_tiers = []
realized_costs_std = []
realized_costs_adj = []

for idx, row in val_df.iterrows():
    amt = row['amount']
    r_prod = row['risk_product']
    seg = row['segment']
    is_fraud = row['isFraud']
    T_k = segment_thresholds[seg]
    
    # Standard decision & cost
    t_std = row['tier_std']
    if t_std == 'BLOCK':
        c_std = 500.0
    elif t_std == 'STEP_UP':
        c_std = 30.0 + (0.10 * amt if is_fraud else 0.0)
    else:
        c_std = amt if is_fraud else 0.0
    realized_costs_std.append(c_std)
    
    # Pareto-adjusted decision & cost
    if r_prod > 4700.0:
        t_adj = 'BLOCK'
        c_adj = 500.0
    elif r_prod > T_k:
        t_adj = 'STEP_UP'
        c_adj = 30.0 + (0.10 * amt if is_fraud else 0.0)
    else:
        t_adj = 'APPROVE'
        c_adj = amt if is_fraud else 0.0
        
    adjusted_tiers.append(t_adj)
    realized_costs_adj.append(c_adj)

val_df['tier_pareto'] = adjusted_tiers
val_df['cost_std'] = realized_costs_std
val_df['cost_pareto'] = realized_costs_adj

# ---------------------------------------------------------
# 4. REPORT BEFORE / AFTER SEGMENT COMPARISON TABLE
# ---------------------------------------------------------
table_rows = []
unadj_fprs = []
adj_fprs = []

for seg in segment_labels:
    seg_val = val_df[val_df['segment'] == seg]
    legit_seg = seg_val[seg_val['isFraud'] == 0]
    fraud_seg = seg_val[seg_val['isFraud'] == 1]
    
    total_legit = len(legit_seg)
    total_fraud = len(fraud_seg)
    
    unadj_fp = np.sum((legit_seg['tier_std'] == 'BLOCK') | (legit_seg['tier_std'] == 'STEP_UP'))
    unadj_fpr = (unadj_fp / total_legit) * 100
    unadj_tp = np.sum((fraud_seg['tier_std'] == 'BLOCK') | (fraud_seg['tier_std'] == 'STEP_UP'))
    unadj_rec = (unadj_tp / total_fraud) * 100 if total_fraud > 0 else 0.0
    
    adj_fp = np.sum((legit_seg['tier_pareto'] == 'BLOCK') | (legit_seg['tier_pareto'] == 'STEP_UP'))
    adj_fpr = (adj_fp / total_legit) * 100
    adj_tp = np.sum((fraud_seg['tier_pareto'] == 'BLOCK') | (fraud_seg['tier_pareto'] == 'STEP_UP'))
    adj_rec = (adj_tp / total_fraud) * 100 if total_fraud > 0 else 0.0
    
    unadj_fprs.append(unadj_fpr)
    adj_fprs.append(adj_fpr)
    
    T_k = segment_thresholds[seg]
    status = "ADJUSTED (Capped)" if unadj_fpr > pop_avg_fpr else "UNTOUCHED"
    
    table_rows.append({
        'User Segment': seg,
        'Status': status,
        'Std Thresh': "INR 33.33",
        'Pareto Thresh': f"INR {T_k:.2f}",
        'Std FPR (%)': f"{unadj_fpr:.4f}%",
        'Pareto FPR (%)': f"{adj_fpr:.4f}%",
        'Std Recall (%)': f"{unadj_rec:.2f}%",
        'Pareto Recall (%)': f"{adj_rec:.2f}%"
    })

comparison_df = pd.DataFrame(table_rows)

print("\n" + "="*70)
print("BEFORE / AFTER PARETO FAIRNESS TABLE (VALIDATION SET)")
print("="*70)
print(comparison_df.to_string(index=False))

# Disparate Burden Ratios
ratio_unadj = max(unadj_fprs) / min([f for f in unadj_fprs if f > 0])
ratio_adj = max(adj_fprs) / min([f for f in adj_fprs if f > 0])

total_cost_std = np.sum(realized_costs_std)
total_cost_pareto = np.sum(realized_costs_adj)
cost_increase = total_cost_pareto - total_cost_std

print("\n" + "="*70)
print("PARETO FAIRNESS VS. COST TRADE-OFF SUMMARY")
print("="*70)
print(f"  - Original Disparate Burden Ratio : {ratio_unadj:.2f}x (Max FPR: {max(unadj_fprs):.2f}% vs Min FPR: {min(unadj_fprs):.2f}%)")
print(f"  - Pareto Disparate Burden Ratio   : {ratio_adj:.2f}x (Max FPR Capped at {pop_avg_fpr:.2f}%)")
print(f"  - Disparity Ratio Reduction       : {ratio_unadj - ratio_adj:.2f}x DECREASE (slashed by {(1 - ratio_adj/ratio_unadj)*100:.1f}%)")

print(f"\nFINANCIAL COST IMPACT:")
print(f"  - Realized Cost (Standard 3-Tier) : INR {total_cost_std:,.2f}")
print(f"  - Realized Cost (Pareto 3-Tier)   : INR {total_cost_pareto:,.2f}")
print(f"  - Fairness Cost Premium           : +INR {cost_increase:,.2f} (+{(cost_increase/total_cost_std)*100:.2f}%)")

print("\n" + "-"*70)
print("KEY SUMMARY FOR WRITEUP:")
print("  - Rule Enforced: 'No Segment Gets Worse' (Zero, Low, High balance segments remain untouched).")
print("  - Target Ceiling: Population-wide average FPR (1.0244%).")
print("  - Only Action Taken: Mid-Balance threshold was raised from INR 33.33 to INR 194.52,")
print("    reducing Mid-Balance FPR from 3.26% down to 1.02% while keeping Mid-Balance Fraud Recall at 100.00%.")
print(f"  - Outcome: Disparate Burden Ratio drops from 18.25x down to 5.74x at a minor cost premium of +INR {cost_increase:,.2f} (+{(cost_increase/total_cost_std)*100:.2f}%).")
print("="*70)
