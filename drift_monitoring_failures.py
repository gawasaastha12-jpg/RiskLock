import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import precision_score, recall_score, average_precision_score
import os
import joblib

print("="*70)
print("RISKLOCK: DRIFT MONITORING, TEMPORAL STABILITY & FAILURE CASE ANALYSIS")
print("="*70)

csv_path = "PS_20174392719_1491204439457_log.csv"
model_path = "models/baseline_xgboost.json"
calibrator_path = "models/calibrated_platt_scaler.joblib"
indices_path = "models/split_indices.npz"

print("\nLoading dataset, split indices, baseline model, and calibrator...")
df = pd.read_csv(csv_path)
df = df.sort_values(by='step').reset_index(drop=True)

split_data = np.load(indices_path)
train_indices = split_data['train']
test_indices = split_data['test']

train_df = df.iloc[train_indices].copy()
test_df = df.iloc[test_indices].copy()

feature_cols = ['amount', 'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest']
df_encoded = pd.get_dummies(df[['type'] + feature_cols], columns=['type'], drop_first=False)

X_train = df_encoded.iloc[train_indices]
X_test = df_encoded.iloc[test_indices]

model = xgb.XGBClassifier()
model.load_model(model_path)
platt_calibrator = joblib.load(calibrator_path)

# Calibrated probabilities for Train and Test
p_train_raw = model.predict_proba(X_train)[:, 1]
p_train_cal = platt_calibrator.predict_proba(p_train_raw.reshape(-1, 1))[:, 1]

p_test_raw = model.predict_proba(X_test)[:, 1]
p_test_cal = platt_calibrator.predict_proba(p_test_raw.reshape(-1, 1))[:, 1]

train_df['p_cal'] = p_train_cal
test_df['p_cal'] = p_test_cal
test_df['risk_product'] = p_test_cal * test_df['amount']

# ---------------------------------------------------------
# 1. POPULATION STABILITY INDEX (PSI) DRIFT CALCULATOR
# ---------------------------------------------------------
def compute_psi(train_series, test_series, num_bins=10):
    quantiles = np.linspace(0, 100, num_bins + 1)
    bins = np.percentile(train_series, quantiles)
    bins = np.unique(bins)
    if len(bins) < 2:
        return 0.0
    
    bins[0] = -np.inf
    bins[-1] = np.inf
    
    train_counts, _ = np.histogram(train_series, bins=bins)
    test_counts, _ = np.histogram(test_series, bins=bins)
    
    expected = train_counts / len(train_series)
    actual = test_counts / len(test_series)
    
    eps = 1e-7
    expected = np.where(expected == 0, eps, expected)
    actual = np.where(actual == 0, eps, actual)
    
    psi_val = np.sum((actual - expected) * np.log(actual / expected))
    return psi_val

psi_features = ['amount', 'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest', 'p_cal']

psi_results = []
for feat in psi_features:
    psi_val = compute_psi(train_df[feat], test_df[feat])
    if psi_val < 0.10:
        flag = "Stable (No Shift)"
    elif 0.10 <= psi_val <= 0.25:
        flag = "MODERATE SHIFT (PSI > 0.1)"
    else:
        flag = "SIGNIFICANT SHIFT (PSI > 0.25)"
        
    psi_results.append({
        'Feature': feat,
        'PSI Score': f"{psi_val:.6f}",
        'Drift Status': flag
    })

psi_table = pd.DataFrame(psi_results)
print("\n" + "="*70)
print("1. POPULATION STABILITY INDEX (PSI) DRIFT REPORT (TRAIN VS. TEST)")
print("="*70)
print(psi_table.to_string(index=False))

# ---------------------------------------------------------
# 2. TEMPORAL DEGRADATION ANALYSIS WITHIN TEST SET (3 SUB-WINDOWS)
# ---------------------------------------------------------
print("\n" + "="*70)
print("2. TEMPORAL STABILITY MONITORING ACROSS TEST SUB-WINDOWS")
print("="*70)

# Assign 3 Pareto thresholds per transaction in test set
conditions_test = [
    (test_df['oldbalanceOrg'] == 0),
    (test_df['oldbalanceOrg'] > 0) & (test_df['oldbalanceOrg'] <= 50000),
    (test_df['oldbalanceOrg'] > 50000) & (test_df['oldbalanceOrg'] <= 250000),
    (test_df['oldbalanceOrg'] > 250000)
]
segment_labels = [
    "1. Zero Balance (INR 0)",
    "2. Low Balance (INR 1 - 50k)",
    "3. Mid Balance (INR 50k - 250k)",
    "4. High Balance (> INR 250k)"
]
test_df['segment'] = np.select(conditions_test, segment_labels, default="Unknown")

# 3-Tier Pareto decisioning on Test Set
tiers_test = []
realized_costs_test = []

for idx, row in test_df.iterrows():
    amt = row['amount']
    r_prod = row['risk_product']
    seg = row['segment']
    is_fraud = row['isFraud']
    T_k = 13417.98 if "Mid Balance" in seg else 33.333333
    
    if r_prod > 4700.0:
        t_tier = 'BLOCK'
        cost = 500.0
    elif r_prod > T_k:
        t_tier = 'STEP_UP'
        cost = 30.0 + (0.10 * amt if is_fraud else 0.0)
    else:
        t_tier = 'APPROVE'
        cost = amt if is_fraud else 0.0
        
    tiers_test.append(t_tier)
    realized_costs_test.append(cost)

test_df['tier'] = tiers_test
test_df['cost'] = realized_costs_test

# Split test set into 3 equal sequential step windows
steps_unique = sorted(test_df['step'].unique())
step_split = np.array_split(steps_unique, 3)

w1_steps, w2_steps, w3_steps = step_split[0], step_split[1], step_split[2]

subwindows = [
    ("Window 1 (Early Test: Steps {}-{})".format(w1_steps[0], w1_steps[-1]), test_df[test_df['step'].isin(w1_steps)]),
    ("Window 2 (Mid Test: Steps {}-{})".format(w2_steps[0], w2_steps[-1]), test_df[test_df['step'].isin(w2_steps)]),
    ("Window 3 (Late Test: Steps {}-{})".format(w3_steps[0], w3_steps[-1]), test_df[test_df['step'].isin(w3_steps)])
]

temporal_rows = []
for w_name, w_df in subwindows:
    y_true_w = w_df['isFraud'].to_numpy()
    p_cal_w = w_df['p_cal'].to_numpy()
    tier_w = w_df['tier'].to_numpy()
    
    # Flagged = BLOCK or STEP_UP
    pred_flag_w = np.isin(tier_w, ['BLOCK', 'STEP_UP']).astype(int)
    
    total_txns = len(w_df)
    total_frauds = np.sum(y_true_w)
    
    prec_w = precision_score(y_true_w, pred_flag_w, pos_label=1, zero_division=0)
    rec_w = recall_score(y_true_w, pred_flag_w, pos_label=1, zero_division=0)
    prauc_w = average_precision_score(y_true_w, p_cal_w)
    tot_cost_w = w_df['cost'].sum()
    
    temporal_rows.append({
        'Test Sub-Window': w_name,
        'Txns (N)': f"{total_txns:,}",
        'Frauds (N)': f"{total_frauds:,}",
        'Precision': f"{prec_w:.4f}",
        'Recall': f"{rec_w:.4f}",
        'PR-AUC': f"{prauc_w:.4f}",
        'Total Cost (INR)': f"INR {tot_cost_w:,.2f}"
    })

temp_table = pd.DataFrame(temporal_rows)
print(temp_table.to_string(index=False))

# ---------------------------------------------------------
# 3. MISSED FRAUD FAILURE CASE ANALYSIS (FALSE NEGATIVES)
# ---------------------------------------------------------
print("\n" + "="*70)
print("3. MISSED FRAUD FAILURE CASE ANALYSIS (TEST SET FALSE NEGATIVES)")
print("="*70)

# Missed fraud = isFraud == 1 and tier == 'APPROVE'
missed_frauds = test_df[(test_df['isFraud'] == 1) & (test_df['tier'] == 'APPROVE')].copy()

print(f"Total Missed Fraud Transactions on Test Set: {len(missed_frauds)} (out of {np.sum(test_df['isFraud']==1):,} total test fraud cases)")

if len(missed_frauds) > 0:
    print("\nSUMMARY OF MISSED FRAUD TRANSACTIONS:")
    summary_fn = []
    for idx, row in missed_frauds.iterrows():
        summary_fn.append({
            'Txn Row #': f"{idx:,}",
            'Step': row['step'],
            'Type': row['type'],
            'Amount (INR)': f"INR {row['amount']:,.2f}",
            'Prob p_cal': f"{row['p_cal']:.6f}",
            'Risk Product': f"INR {row['risk_product']:,.2f}",
            'Segment': row['segment']
        })
    fn_df = pd.DataFrame(summary_fn)
    print(fn_df.to_string(index=False))
    
    # Find SINGLE LARGEST missed fraud by amount
    largest_missed = missed_frauds.loc[missed_frauds['amount'].idxmax()]
    largest_idx = largest_missed.name
    
    print("\n" + "-"*70)
    print("SINGLE LARGEST MISSED FRAUD TRANSACTION (WORST-CASE FAILURE MODE):")
    print(f"  - Dataset Row Index   : #{largest_idx:,}")
    print(f"  - Step / Time        : Step {largest_missed['step']}")
    print(f"  - Transaction Type   : {largest_missed['type']}")
    print(f"  - Amount (INR)       : INR {largest_missed['amount']:,.2f}")
    print(f"  - Origin Balance     : INR {largest_missed['oldbalanceOrg']:,.2f} -> INR {largest_missed['newbalanceOrig']:,.2f}")
    print(f"  - Destination Balance: INR {largest_missed['oldbalanceDest']:,.2f} -> INR {largest_missed['newbalanceDest']:,.2f}")
    print(f"  - Calibrated Prob    : {largest_missed['p_cal']:.8f}")
    print(f"  - Risk Product       : INR {largest_missed['risk_product']:,.4f}")
    print(f"  - Decision Tier      : {largest_missed['tier']} (Failed to flag!)")
    
    # SHAP breakdown for the largest missed fraud
    X_single = X_test.loc[[largest_idx]]
    dmat_single = xgb.DMatrix(X_single)
    shap_single = model.get_booster().predict(dmat_single, pred_contribs=True)[0, :-1]
    
    top_shap_idx = np.argsort(np.abs(shap_single))[::-1][:3]
    
    print("\n  Top 3 SHAP Feature Contributions for Largest Missed Fraud:")
    exact_cols = list(X_test.columns)
    for rank, f_idx in enumerate(top_shap_idx, 1):
        f_name = exact_cols[f_idx]
        f_val = X_single.iloc[0, f_idx]
        s_val = shap_single[f_idx]
        impact = "Lowered Risk (-)" if s_val < 0 else "Pushed Fraud (+)"
        print(f"    {rank}. {f_name:<16} = {f_val:>12,.2f} | SHAP: {s_val:+8.4f} ({impact})")
        
    print("\n  ROOT CAUSE DIAGNOSTIC:")
    print("  Why the model missed this transaction:")
    print(f"  1. Probability Suppressed: Model output a very low calibrated probability (p_cal = {largest_missed['p_cal']:.8f}).")
    print(f"  2. Expected Risk Product (INR {largest_missed['risk_product']:,.2f}) stayed well below the decision threshold (INR 33.33).")
    print(f"  3. Key Feature Driver: Feature '{exact_cols[top_shap_idx[0]]}' (SHAP = {shap_single[top_shap_idx[0]]:+.4f}) strongly lowered predicted risk, masking the fraud signal.")

print("="*70)
