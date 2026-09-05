import pandas as pd
import numpy as np
import xgboost as xgb
import os
import joblib

print("="*70)
print("RISKLOCK: SHAP EXPLAINABILITY, REASON CODES & FAIRNESS AUDIT REPORT")
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
exact_features = list(df_encoded.columns)
X_val = df_encoded.iloc[val_indices]

model = xgb.XGBClassifier()
model.load_model(model_path)
platt_calibrator = joblib.load(calibrator_path)

# Predict raw and calibrated probabilities
p_val_raw = model.predict_proba(X_val)[:, 1]
p_val_cal = platt_calibrator.predict_proba(p_val_raw.reshape(-1, 1))[:, 1]

# 3-Tier Decisioning on Validation Set
exp_cost_block = np.full(len(val_df), 500.0)
exp_cost_stepup = 30.0 + 0.10 * p_val_cal * amounts_val
exp_cost_approve = p_val_cal * amounts_val

exp_costs = np.column_stack([exp_cost_block, exp_cost_stepup, exp_cost_approve])
tier_choices = np.argmin(exp_costs, axis=1)  # 0: BLOCK, 1: STEP_UP, 2: APPROVE
tier_names = np.array(['BLOCK', 'STEP_UP', 'APPROVE'])
val_df['tier'] = tier_names[tier_choices]
val_df['p_cal'] = p_val_cal

# Compute native XGBoost Tree SHAP values
booster = model.get_booster()
dval = xgb.DMatrix(X_val)
shap_matrix = booster.predict(dval, pred_contribs=True)[:, :-1]  # Exclude base value

# ---------------------------------------------------------
# 1. SHAP FEATURE EXPLANATIONS FOR FLAGGED TRANSACTIONS
# ---------------------------------------------------------
print("\n" + "="*70)
print("1. SHAP FEATURE EXPLANATIONS FOR FLAGGED TRANSACTIONS (VALIDATION SET)")
print("="*70)

flagged_mask = (val_df['tier'] == 'BLOCK') | (val_df['tier'] == 'STEP_UP')
flagged_indices_in_val = np.where(flagged_mask)[0]

print(f"Total Flagged Transactions in Validation Set: {len(flagged_indices_in_val):,} (BLOCK + STEP_UP)")

# Select 5 diverse example transactions (3 BLOCK, 2 STEP_UP)
block_idx_sample = np.where(val_df['tier'] == 'BLOCK')[0][:3]
stepup_idx_sample = np.where(val_df['tier'] == 'STEP_UP')[0][:2]
sample_indices = np.concatenate([block_idx_sample, stepup_idx_sample])

print("\n--- 5 EXAMPLE FLAGGED TRANSACTIONS WITH TOP 3 SHAP BREAKDOWNS ---")

for idx_in_val in sample_indices:
    row_df = val_df.iloc[idx_in_val]
    shap_row = shap_matrix[idx_in_val]
    
    # Sort features by absolute SHAP value descending
    top_feat_idx = np.argsort(np.abs(shap_row))[::-1][:3]
    
    print(f"\nTxn Row #{val_indices[idx_in_val]:,} | Tier: {row_df['tier']} | Actual Fraud: {row_df['isFraud']} | Amount: INR {row_df['amount']:,.2f} | Prob (p): {row_df['p_cal']:.6f}")
    print("  Top 3 Contributing Features (by absolute SHAP value):")
    for rank, f_idx in enumerate(top_feat_idx, 1):
        f_name = exact_features[f_idx]
        f_val = X_val.iloc[idx_in_val, f_idx]
        s_val = shap_row[f_idx]
        impact = "Pushes Fraud (+)" if s_val > 0 else "Lowers Risk (-)"
        print(f"    {rank}. {f_name:<16} = {f_val:>12,.2f}  | SHAP: {s_val:+8.4f} ({impact})")

# ---------------------------------------------------------
# 2. PLAIN-ENGLISH REASON CODE GENERATION
# ---------------------------------------------------------
print("\n" + "="*70)
print("2. PLAIN-ENGLISH REASON CODE GENERATION (RULE-BASED TEMPLATE)")
print("="*70)

def generate_reason_code(row_series, x_row, shap_row):
    top_indices = np.argsort(np.abs(shap_row))[::-1][:3]
    top_feats = [exact_features[i] for i in top_indices]
    
    reasons = []
    
    amount = row_series['amount']
    old_org = row_series['oldbalanceOrg']
    new_org = row_series['newbalanceOrig']
    txn_type = row_series['type']
    
    # Rule templates based on feature combination
    if abs(amount - old_org) < 0.01 and old_org > 0 and new_org == 0:
        reasons.append("Full account balance transferred out (100% drain pattern)")
    elif 'newbalanceOrig' in top_feats and new_org == 0 and old_org > 0:
        reasons.append("Sender origin account balance drained to 0")
    elif 'amount' in top_feats and amount > 500000:
        reasons.append(f"High-value transfer amount (INR {amount:,.0f})")
    elif 'amount' in top_feats:
        reasons.append(f"Transaction amount INR {amount:,.0f} relative to expected profile")
        
    if txn_type in ['TRANSFER', 'CASH_OUT'] and any(f in top_feats for f in ['type_TRANSFER', 'type_CASH_OUT']):
        reasons.append(f"High-risk transaction channel ({txn_type})")
        
    if 'oldbalanceOrg' in top_feats and old_org > 0:
        reasons.append(f"Origin balance (INR {old_org:,.0f}) matches transfer pattern")
        
    if 'newbalanceDest' in top_feats or 'oldbalanceDest' in top_feats:
        reasons.append("Recipient destination balance anomaly")
        
    if not reasons:
        reasons.append(f"Elevated fraud risk in {txn_type} channel for INR {amount:,.0f}")
        
    return " | ".join(reasons[:2])

sample_10_idx = np.concatenate([
    np.where(val_df['tier'] == 'BLOCK')[0][:5],
    np.where(val_df['tier'] == 'STEP_UP')[0][:5]
])

reason_rows = []
for idx_in_val in sample_10_idx:
    row_series = val_df.iloc[idx_in_val]
    x_row = X_val.iloc[idx_in_val]
    shap_row = shap_matrix[idx_in_val]
    
    reason = generate_reason_code(row_series, x_row, shap_row)
    reason_rows.append({
        'Row #': f"{val_indices[idx_in_val]:,}",
        'Tier': row_series['tier'],
        'Fraud?': row_series['isFraud'],
        'Amount (INR)': f"INR {row_series['amount']:,.2f}",
        'Prob (p)': f"{row_series['p_cal']:.4f}",
        'Plain-English Reason Code': reason
    })

reason_df = pd.DataFrame(reason_rows)
print(reason_df.to_string(index=False))

# ---------------------------------------------------------
# 3. SEGMENT-LEVEL FAIRNESS AUDIT
# ---------------------------------------------------------
print("\n" + "="*70)
print("3. SEGMENT-LEVEL FAIRNESS AUDIT (VALIDATION SET)")
print("="*70)
print("Proxy User Segments defined by Sender Origin Balance (`oldbalanceOrg`):")
print("  - Segment 1: Zero Balance (INR 0)")
print("  - Segment 2: Low Balance (INR 1 - INR 50k)")
print("  - Segment 3: Mid Balance (INR 50k - INR 250k)")
print("  - Segment 4: High Balance (> INR 250k)")

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

fairness_rows = []
fpr_values = []

for seg in segment_labels:
    seg_df = val_df[val_df['segment'] == seg]
    legit_df = seg_df[seg_df['isFraud'] == 0]
    total_legit = len(legit_df)
    
    if total_legit > 0:
        fps = np.sum((legit_df['tier'] == 'BLOCK') | (legit_df['tier'] == 'STEP_UP'))
        fpr = (fps / total_legit) * 100
        fpr_values.append(fpr)
    else:
        fps = 0
        fpr = 0.0
        fpr_values.append(0.0)
        
    fairness_rows.append({
        'User Segment (Origin Balance)': seg,
        'Total Legitimate Txns': f"{total_legit:,}",
        'False Positives (FP)': f"{fps:,}",
        'False Positive Rate (FPR)': f"{fpr:.4f}%"
    })

fairness_table = pd.DataFrame(fairness_rows)
print("\n" + fairness_table.to_string(index=False))

# Disparate Impact Assessment
non_zero_fprs = [f for f in fpr_values if f > 0]
max_fpr = max(fpr_values)
min_fpr = min(non_zero_fprs) if non_zero_fprs else 0.0
disparate_ratio = max_fpr / min_fpr if min_fpr > 0 else 0.0

print("\n" + "-"*70)
print("DISPARATE IMPACT & FAIRNESS EVALUATION:")
print(f"  - Maximum FPR across segments: {max_fpr:.4f}% ({segment_labels[np.argmax(fpr_values)]})")
print(f"  - Minimum FPR across segments: {min_fpr:.4f}% ({segment_labels[np.argmin(fpr_values)]})")
print(f"  - Disparate Burden Ratio     : {disparate_ratio:.2f}x")

if disparate_ratio > 2.0:
    print("\n  [WARNING - DISPARATE BURDEN DETECTED]")
    print(f"  The False Positive Rate for '{segment_labels[np.argmax(fpr_values)]}' is {disparate_ratio:.2f}x higher (> 2.0x threshold)")
    print("  than lower-burden segments. High-balance / active senders bear a disproportionate burden of OTP/manual verification friction.")
else:
    print("\n  [FAIRNESS CONFIRMED]")
    print("  No segment experiences an FPR greater than 2.0x another segment.")

print("="*70)
