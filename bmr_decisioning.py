import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
import os

print("="*70)
print("RISKLOCK: BAYES MINIMUM RISK (BMR) DECISIONING REPORT")
print("="*70)

csv_path = "PS_20174392719_1491204439457_log.csv"
model_path = "models/baseline_xgboost.json"
indices_path = "models/split_indices.npz"

print("\nLoading dataset and baseline XGBoost model...")
df = pd.read_csv(csv_path)
df = df.sort_values(by='step').reset_index(drop=True)

split_data = np.load(indices_path)
val_indices = split_data['val']

val_df = df.iloc[val_indices].copy()
y_val = val_df['isFraud'].to_numpy()
amounts_val = val_df['amount'].to_numpy()

# Load full-feature baseline XGBoost
feature_cols = ['amount', 'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest']
df_encoded = pd.get_dummies(df[['type'] + feature_cols], columns=['type'], drop_first=False)
X_val = df_encoded.iloc[val_indices]

model = xgb.XGBClassifier()
model.load_model(model_path)

# Predict probabilities on Validation Set
print("Predicting fraud probabilities (p) on Validation set...")
p_val = model.predict_proba(X_val)[:, 1]

# ---------------------------------------------------------
# BMR DECISION RULE DERIVATION:
# Expected Cost Flagging = p * C_TP + (1-p) * C_FP = p * 500 + (1-p) * 500 = 500
# Expected Cost Passing  = p * C_FN + (1-p) * C_TN = p * amount + (1-p) * 0 = p * amount
# Flag if Expected Cost Flagging < Expected Cost Passing:
#   500 < p * amount  <===>  p * amount > 500  <===>  p > 500 / amount
# ---------------------------------------------------------

# Compute decisions for the 3 strategies
# 1. BMR Decisioning Strategy
bmr_decision = (p_val * amounts_val > 500).astype(int)

# 2. Naive 0.5 Threshold Strategy
naive_05_decision = (p_val >= 0.5).astype(int)

# 3. Naive Never Flag Strategy
never_flag_decision = np.zeros(len(val_df), dtype=int)

# Cost calculation function per row:
# TP: 500, FP: 500, FN: amount, TN: 0
def calculate_total_cost(y_true, y_pred, amounts):
    tp_mask = (y_true == 1) & (y_pred == 1)
    fp_mask = (y_true == 0) & (y_pred == 1)
    fn_mask = (y_true == 1) & (y_pred == 0)
    tn_mask = (y_true == 0) & (y_pred == 0)

    cost_tp = np.sum(tp_mask) * 500
    cost_fp = np.sum(fp_mask) * 500
    cost_fn = np.sum(amounts[fn_mask])
    cost_tn = 0.0

    total_cost = cost_tp + cost_fp + cost_fn + cost_tn
    return total_cost, np.sum(tp_mask), np.sum(fp_mask), np.sum(fn_mask), np.sum(tn_mask)

cost_bmr, tp_bmr, fp_bmr, fn_bmr, tn_bmr = calculate_total_cost(y_val, bmr_decision, amounts_val)
cost_05, tp_05, fp_05, fn_05, tn_05 = calculate_total_cost(y_val, naive_05_decision, amounts_val)
cost_never, tp_never, fp_never, fn_never, tn_never = calculate_total_cost(y_val, never_flag_decision, amounts_val)

# Metrics for BMR
prec_bmr = precision_score(y_val, bmr_decision, pos_label=1)
rec_bmr = recall_score(y_val, bmr_decision, pos_label=1)
f1_bmr = f1_score(y_val, bmr_decision, pos_label=1)

# Metrics for Naive 0.5
prec_05 = precision_score(y_val, naive_05_decision, pos_label=1)
rec_05 = recall_score(y_val, naive_05_decision, pos_label=1)
f1_05 = f1_score(y_val, naive_05_decision, pos_label=1)

print("\n" + "="*70)
print("1, 2, 3. TOTAL FINANCIAL COST COMPARISON (VALIDATION SET)")
print("="*70)

cost_summary_df = pd.DataFrame([
    {
        'Strategy': 'Naive Never Flag Anything',
        'Total Cost (INR)': f"INR {cost_never:,.2f}",
        'Cost Savings vs Never Flag': "INR 0.00 (Baseline)",
        'Flagged Count': f"{np.sum(never_flag_decision):,}"
    },
    {
        'Strategy': 'Naive 0.5 Threshold',
        'Total Cost (INR)': f"INR {cost_05:,.2f}",
        'Cost Savings vs Never Flag': f"INR {cost_never - cost_05:,.2f} ({((cost_never - cost_05)/cost_never)*100:.2f}%)",
        'Flagged Count': f"{np.sum(naive_05_decision):,}"
    },
    {
        'Strategy': 'Bayes Minimum Risk (BMR)',
        'Total Cost (INR)': f"INR {cost_bmr:,.2f}",
        'Cost Savings vs Never Flag': f"INR {cost_never - cost_bmr:,.2f} ({((cost_never - cost_bmr)/cost_never)*100:.2f}%)",
        'Flagged Count': f"{np.sum(bmr_decision):,}"
    }
])
print(cost_summary_df.to_string(index=False))

print("\n" + "="*70)
print("4. BMR DECISION RULE PERFORMANCE METRICS (FRAUD CLASS)")
print("="*70)
print(f"  Precision (BMR) : {prec_bmr:.6f}")
print(f"  Recall (BMR)    : {rec_bmr:.6f}")
print(f"  F1 Score (BMR)  : {f1_bmr:.6f}")

print("\nBMR CONFUSION MATRIX:")
print(f"  TN: {tn_bmr:>8,}   FP: {fp_bmr:>8,}")
print(f"  FN: {fn_bmr:>8,}   TP: {tp_bmr:>8,}")

print("\n" + "="*70)
print("5. FLAGGED TRANSACTION COUNT COMPARISON")
print("="*70)
print(f"  Transactions Flagged by Naive 0.5 Threshold : {np.sum(naive_05_decision):,}")
print(f"  Transactions Flagged by BMR Decision Rule  : {np.sum(bmr_decision):,}")
print(f"  Difference (BMR - Naive 0.5)               : {np.sum(bmr_decision) - np.sum(naive_05_decision):+,}")

print("\n" + "="*70)
print("CONFIRMATION: Held-out test set (89,466 rows) was NOT touched or evaluated.")
print("="*70)
