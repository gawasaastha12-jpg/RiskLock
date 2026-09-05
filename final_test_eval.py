import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, average_precision_score, brier_score_loss
import os
import joblib

print("="*70)
print("RISKLOCK: FINAL OFFICIAL TEST-SET EVALUATION (HELD-OUT TEST SET)")
print("="*70)

csv_path = "PS_20174392719_1491204439457_log.csv"
model_path = "models/baseline_xgboost.json"
calibrator_path = "models/calibrated_platt_scaler.joblib"
indices_path = "models/split_indices.npz"

print("\nLoading dataset, split indices, trained model, and Platt calibrator...")
df = pd.read_csv(csv_path)
df = df.sort_values(by='step').reset_index(drop=True)

split_data = np.load(indices_path)
test_indices = split_data['test']

test_df = df.iloc[test_indices].copy()
y_test = test_df['isFraud'].to_numpy()
amounts_test = test_df['amount'].to_numpy()

print(f"Held-out Test Set Rows: {len(test_df):,} (Steps {test_df['step'].min()} to {test_df['step'].max()})")
print(f"Test Set Fraud Count : {np.sum(y_test):,} ({np.mean(y_test)*100:.4f}%)")

# Prepare test features
feature_cols = ['amount', 'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest']
df_encoded = pd.get_dummies(df[['type'] + feature_cols], columns=['type'], drop_first=False)
X_test = df_encoded.iloc[test_indices]

# Load frozen baseline model & calibrator
model = xgb.XGBClassifier()
model.load_model(model_path)

platt_calibrator = joblib.load(calibrator_path)

# Predict raw & calibrated probabilities on TEST set
print("\nPredicting on HELD-OUT TEST SET (No model or calibrator refitting)...")
p_test_raw = model.predict_proba(X_test)[:, 1]
p_test_cal = platt_calibrator.predict_proba(p_test_raw.reshape(-1, 1))[:, 1]

brier_test_raw = brier_score_loss(y_test, p_test_raw)
brier_test_cal = brier_score_loss(y_test, p_test_cal)
pr_auc_test = average_precision_score(y_test, p_test_cal)

print(f"\nTEST SET CALIBRATION & RANKING METRICS:")
print(f"  Test Brier Score (Raw)        : {brier_test_raw:.6f}")
print(f"  Test Brier Score (Calibrated) : {brier_test_cal:.6f}")
print(f"  Test PR-AUC (Fraud)           : {pr_auc_test:.6f}")
print(f"  Test Raw Mean Prob            : {p_test_raw.mean():.6f}")
print(f"  Test Calibrated Mean Prob     : {p_test_cal.mean():.6f}")
print(f"  Test Actual Fraud Rate        : {y_test.mean():.6f}")

# ---------------------------------------------------------
# BMR DECISION RULE & BASELINES ON TEST SET
# ---------------------------------------------------------
bmr_decision_test = (p_test_cal * amounts_test > 500).astype(int)
naive_05_decision_test = (p_test_cal >= 0.5).astype(int)
never_flag_decision_test = np.zeros(len(test_df), dtype=int)

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

cost_bmr_t, tp_bmr_t, fp_bmr_t, fn_bmr_t, tn_bmr_t = calculate_total_cost(y_test, bmr_decision_test, amounts_test)
cost_05_t, tp_05_t, fp_05_t, fn_05_t, tn_05_t = calculate_total_cost(y_test, naive_05_decision_test, amounts_test)
cost_never_t, tp_never_t, fp_never_t, fn_never_t, tn_never_t = calculate_total_cost(y_test, never_flag_decision_test, amounts_test)

prec_bmr_t = precision_score(y_test, bmr_decision_test, pos_label=1, zero_division=0)
rec_bmr_t = recall_score(y_test, bmr_decision_test, pos_label=1, zero_division=0)
f1_bmr_t = f1_score(y_test, bmr_decision_test, pos_label=1, zero_division=0)

prec_05_t = precision_score(y_test, naive_05_decision_test, pos_label=1, zero_division=0)
rec_05_t = recall_score(y_test, naive_05_decision_test, pos_label=1, zero_division=0)
f1_05_t = f1_score(y_test, naive_05_decision_test, pos_label=1, zero_division=0)

# ---------------------------------------------------------
# REPORTING 5 OFFICIAL METRICS
# ---------------------------------------------------------
print("\n" + "="*70)
print("1, 2, 3. OFFICIAL TOTAL FINANCIAL COST COMPARISON (TEST SET)")
print("="*70)

cost_table_test = pd.DataFrame([
    {
        'Strategy': 'Naive Never Flag Anything',
        'Total Cost (INR)': f"INR {cost_never_t:,.2f}",
        'Savings vs Never Flag': "INR 0.00 (Baseline)",
        'Flagged Count': f"{np.sum(never_flag_decision_test):,}"
    },
    {
        'Strategy': 'Naive 0.5 Threshold (Calibrated)',
        'Total Cost (INR)': f"INR {cost_05_t:,.2f}",
        'Savings vs Never Flag': f"INR {cost_never_t - cost_05_t:,.2f} ({((cost_never_t - cost_05_t)/cost_never_t)*100:.2f}%)",
        'Flagged Count': f"{np.sum(naive_05_decision_test):,}"
    },
    {
        'Strategy': 'Calibrated BMR (p_cal * amount > 500)',
        'Total Cost (INR)': f"INR {cost_bmr_t:,.2f}",
        'Savings vs Never Flag': f"INR {cost_never_t - cost_bmr_t:,.2f} ({((cost_never_t - cost_bmr_t)/cost_never_t)*100:.2f}%)",
        'Flagged Count': f"{np.sum(bmr_decision_test):,}"
    }
])
print(cost_table_test.to_string(index=False))

print("\n" + "="*70)
print("4. OFFICIAL CALIBRATED BMR METRICS ON TEST SET (FRAUD CLASS)")
print("="*70)
print(f"  Precision (BMR Test) : {prec_bmr_t:.6f}")
print(f"  Recall (BMR Test)    : {rec_bmr_t:.6f}")
print(f"  F1 Score (BMR Test)  : {f1_bmr_t:.6f}")
print(f"  PR-AUC (Test)        : {pr_auc_test:.6f}")

print("\nOFFICIAL TEST SET BMR CONFUSION MATRIX:")
print(f"  TN: {tn_bmr_t:>8,}   FP: {fp_bmr_t:>8,}")
print(f"  FN: {fn_bmr_t:>8,}   TP: {tp_bmr_t:>8,}")

print("\nOFFICIAL TEST SET NAIVE 0.5 CONFUSION MATRIX:")
print(f"  TN: {tn_05_t:>8,}   FP: {fp_05_t:>8,}")
print(f"  FN: {fn_05_t:>8,}   TP: {tp_05_t:>8,}")

print("\n" + "="*70)
print("5. OFFICIAL FLAGGED TRANSACTION COUNT COMPARISON (TEST SET)")
print("="*70)
print(f"  Transactions Flagged by Naive 0.5 Threshold : {np.sum(naive_05_decision_test):,}")
print(f"  Transactions Flagged by BMR Decision Rule  : {np.sum(bmr_decision_test):,}")
print(f"  Difference (BMR - Naive 0.5)               : {np.sum(bmr_decision_test) - np.sum(naive_05_decision_test):+,}")

# Save final evaluation results to text file artifact
with open("models/final_test_evaluation_report.txt", "w") as f:
    f.write(f"RISKLOCK OFFICIAL TEST SET EVALUATION\n")
    f.write(f"Total Test Rows: {len(test_df):,}\n")
    f.write(f"BMR Total Cost: INR {cost_bmr_t:,.2f}\n")
    f.write(f"Naive 0.5 Cost: INR {cost_05_t:,.2f}\n")
    f.write(f"Never Flag Cost: INR {cost_never_t:,.2f}\n")
    f.write(f"Precision: {prec_bmr_t:.6f}, Recall: {rec_bmr_t:.6f}, F1: {f1_bmr_t:.6f}, PR-AUC: {pr_auc_test:.6f}\n")
    f.write(f"Confusion Matrix (BMR): TN={tn_bmr_t}, FP={fp_bmr_t}, FN={fn_bmr_t}, TP={tp_bmr_t}\n")

print("\nSaved official test evaluation summary to: models/final_test_evaluation_report.txt")
print("="*70)
