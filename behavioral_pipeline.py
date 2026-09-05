import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score, f1_score, average_precision_score, brier_score_loss, confusion_matrix
import os
import joblib

print("="*70)
print("RISKLOCK: LEAKAGE-SAFE BEHAVIORAL FEATURE ENGINEERING & RETRAINING")
print("="*70)

csv_path = "PS_20174392719_1491204439457_log.csv"
indices_path = "models/split_indices.npz"

print("\nLoading dataset and split indices...")
df = pd.read_csv(csv_path)
df = df.sort_values(by='step').reset_index(drop=True)

split_data = np.load(indices_path)
train_indices = split_data['train']
val_indices = split_data['val']

# ---------------------------------------------------------
# STEP 1: LEAKAGE-SAFE BEHAVIORAL FEATURE ENGINEERING
# ---------------------------------------------------------
print("\n" + "="*70)
print("STEP 1: COMPUTING LEAKAGE-SAFE BEHAVIORAL FEATURES")
print("="*70)

# Compute population median amount on TRAIN set only
train_median_amount = df.iloc[train_indices]['amount'].median()
print(f"Train Set Population Median Amount (Fallback): INR {train_median_amount:,.2f}")

# Expanding cumulative sum and count per sender account (nameOrig)
df['cumsum_amount'] = df.groupby('nameOrig')['amount'].cumsum() - df['amount']
df['cumcount_amount'] = df.groupby('nameOrig').cumcount()

df['historical_avg_amount'] = np.where(
    df['cumcount_amount'] > 0,
    df['cumsum_amount'] / df['cumcount_amount'],
    train_median_amount
)

df['amount_vs_own_history_ratio'] = df['amount'] / (df['historical_avg_amount'] + 1.0)

# Step 1 Output Summaries
train_df = df.iloc[train_indices].copy()
prior_txns_count = np.sum(train_df['cumcount_amount'] > 0)
fallback_count = np.sum(train_df['cumcount_amount'] == 0)

print(f"\nSENDER HISTORY BREAKDOWN (TRAIN SET):")
print(f"  - Transactions with >= 1 Prior Transaction : {prior_txns_count:,} ({(prior_txns_count/len(train_df))*100:.2f}%)")
print(f"  - Transactions falling back to Train Median: {fallback_count:,} ({(fallback_count/len(train_df))*100:.2f}%)")

fraud_ratios = train_df[train_df['isFraud'] == 1]['amount_vs_own_history_ratio']
non_fraud_ratios = train_df[train_df['isFraud'] == 0]['amount_vs_own_history_ratio']

ratio_summary = pd.DataFrame([
    {
        'Group': 'Fraud Rows Only',
        'Mean Ratio': f"{fraud_ratios.mean():,.2f}x",
        'Median Ratio': f"{fraud_ratios.median():,.2f}x",
        'Min Ratio': f"{fraud_ratios.min():,.2f}x",
        'Max Ratio': f"{fraud_ratios.max():,.2f}x"
    },
    {
        'Group': 'Non-Fraud Rows Only',
        'Mean Ratio': f"{non_fraud_ratios.mean():,.2f}x",
        'Median Ratio': f"{non_fraud_ratios.median():,.2f}x",
        'Min Ratio': f"{non_fraud_ratios.min():,.2f}x",
        'Max Ratio': f"{non_fraud_ratios.max():,.2f}x"
    }
])
print("\nDISTRIBUTION OF `amount_vs_own_history_ratio` (TRAIN SET):")
print(ratio_summary.to_string(index=False))

# ---------------------------------------------------------
# STEP 2: RETRAIN XGBOOST WITH NEW BEHAVIORAL FEATURES
# ---------------------------------------------------------
print("\n" + "="*70)
print("STEP 2: RETRAINING XGBOOST WITH BEHAVIORAL FEATURES")
print("="*70)

feature_cols = [
    'amount', 'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest',
    'historical_avg_amount', 'amount_vs_own_history_ratio'
]
df_encoded = pd.get_dummies(df[['type'] + feature_cols], columns=['type'], drop_first=False)
exact_features = list(df_encoded.columns)

X_train = df_encoded.iloc[train_indices]
y_train = df.loc[train_indices, 'isFraud']

X_val = df_encoded.iloc[val_indices]
val_df = df.iloc[val_indices].copy()
y_val = val_df['isFraud'].to_numpy()
amounts_val = val_df['amount'].to_numpy()

num_neg = (y_train == 0).sum()
num_pos = (y_train == 1).sum()
scale_pos_weight_val = num_neg / num_pos

model_beh = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=6,
    learning_rate=0.1,
    scale_pos_weight=scale_pos_weight_val,
    random_state=42,
    tree_method='hist',
    n_jobs=-1
)

print(f"Training Behavioral XGBoost Classifier (scale_pos_weight={scale_pos_weight_val:.4f})...")
model_beh.fit(X_train, y_train)

# Save behavioral model
model_beh.save_model("models/behavioral_xgboost.json")
print("Saved model to: models/behavioral_xgboost.json")

# Predict raw & refit Platt Calibrator on Validation Set
p_val_raw_beh = model_beh.predict_proba(X_val)[:, 1]

print("Refitting Platt Scaling Calibrator on Validation set...")
calibrator_beh = LogisticRegression(C=1.0, max_iter=1000)
calibrator_beh.fit(p_val_raw_beh.reshape(-1, 1), y_val)

joblib.dump(calibrator_beh, "models/calibrated_behavioral_platt.joblib")
print("Saved Platt calibrator to: models/calibrated_behavioral_platt.joblib")

p_val_cal_beh = calibrator_beh.predict_proba(p_val_raw_beh.reshape(-1, 1))[:, 1]

# Original Baseline Model for Comparison
model_orig = xgb.XGBClassifier()
model_orig.load_model("models/baseline_xgboost.json")
calibrator_orig = joblib.load("models/calibrated_platt_scaler.joblib")

feature_cols_orig = ['amount', 'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest']
df_encoded_orig = pd.get_dummies(df[['type'] + feature_cols_orig], columns=['type'], drop_first=False)
X_val_orig = df_encoded_orig.iloc[val_indices]

p_val_raw_orig = model_orig.predict_proba(X_val_orig)[:, 1]
p_val_cal_orig = calibrator_orig.predict_proba(p_val_raw_orig.reshape(-1, 1))[:, 1]

# Validation Metrics Comparison (at 0.5 threshold)
pred_orig = (p_val_cal_orig >= 0.5).astype(int)
pred_beh = (p_val_cal_beh >= 0.5).astype(int)

prec_orig = precision_score(y_val, pred_orig, pos_label=1)
rec_orig = recall_score(y_val, pred_orig, pos_label=1)
f1_orig = f1_score(y_val, pred_orig, pos_label=1)
prauc_orig = average_precision_score(y_val, p_val_cal_orig)
brier_orig = brier_score_loss(y_val, p_val_cal_orig)

prec_beh = precision_score(y_val, pred_beh, pos_label=1)
rec_beh = recall_score(y_val, pred_beh, pos_label=1)
f1_beh = f1_score(y_val, pred_beh, pos_label=1)
prauc_beh = average_precision_score(y_val, p_val_cal_beh)
brier_beh = brier_score_loss(y_val, p_val_cal_beh)

print("\n" + "="*70)
print("SIDE-BY-SIDE MODEL PERFORMANCE METRICS (VALIDATION SET)")
print("="*70)
model_comp_table = pd.DataFrame([
    {
        'Metric': 'Precision (Fraud)',
        'Original Baseline Model': f"{prec_orig:.6f}",
        'New Behavioral Model': f"{prec_beh:.6f}",
        'Difference': f"{prec_beh - prec_orig:+.6f}"
    },
    {
        'Metric': 'Recall (Fraud)',
        'Original Baseline Model': f"{rec_orig:.6f}",
        'New Behavioral Model': f"{rec_beh:.6f}",
        'Difference': f"{rec_beh - rec_orig:+.6f}"
    },
    {
        'Metric': 'F1-Score (Fraud)',
        'Original Baseline Model': f"{f1_orig:.6f}",
        'New Behavioral Model': f"{f1_beh:.6f}",
        'Difference': f"{f1_beh - f1_orig:+.6f}"
    },
    {
        'Metric': 'PR-AUC (Fraud)',
        'Original Baseline Model': f"{prauc_orig:.6f}",
        'New Behavioral Model': f"{prauc_beh:.6f}",
        'Difference': f"{prauc_beh - prauc_orig:+.6f}"
    },
    {
        'Metric': 'Brier Score (Calibrated)',
        'Original Baseline Model': f"{brier_orig:.6f}",
        'New Behavioral Model': f"{brier_beh:.6f}",
        'Difference': f"{brier_beh - brier_orig:+.6f}"
    }
])
print(model_comp_table.to_string(index=False))

# ---------------------------------------------------------
# STEP 3: RE-CHECK FAIRNESS WITH IMPROVED MODEL
# ---------------------------------------------------------
print("\n" + "="*70)
print("STEP 3: RE-CHECK SEGMENT FAIRNESS AUDIT WITH NEW BEHAVIORAL MODEL")
print("="*70)

# Run 3-Tier decisioning using new calibrated probabilities
exp_cost_block = np.full(len(val_df), 500.0)
exp_cost_stepup = 30.0 + 0.10 * p_val_cal_beh * amounts_val
exp_cost_approve = p_val_cal_beh * amounts_val

exp_costs_beh = np.column_stack([exp_cost_block, exp_cost_stepup, exp_cost_approve])
tier_choices_beh = np.argmin(exp_costs_beh, axis=1)
tier_names = np.array(['BLOCK', 'STEP_UP', 'APPROVE'])

val_df['tier_orig'] = np.array(['BLOCK', 'STEP_UP', 'APPROVE'])[np.argmin(np.column_stack([np.full(len(val_df), 500.0), 30.0 + 0.10 * p_val_cal_orig * amounts_val, p_val_cal_orig * amounts_val]), axis=1)]
val_df['tier_beh'] = tier_names[tier_choices_beh]

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

fairness_comp_rows = []
fpr_orig_list = []
fpr_beh_list = []

for seg in segment_labels:
    seg_df = val_df[val_df['segment'] == seg]
    legit_df = seg_df[seg_df['isFraud'] == 0]
    total_legit = len(legit_df)
    
    if total_legit > 0:
        fps_orig = np.sum((legit_df['tier_orig'] == 'BLOCK') | (legit_df['tier_orig'] == 'STEP_UP'))
        fpr_orig = (fps_orig / total_legit) * 100
        
        fps_beh = np.sum((legit_df['tier_beh'] == 'BLOCK') | (legit_df['tier_beh'] == 'STEP_UP'))
        fpr_beh = (fps_beh / total_legit) * 100
    else:
        fps_orig, fpr_orig = 0, 0.0
        fps_beh, fpr_beh = 0, 0.0
        
    fpr_orig_list.append(fpr_orig)
    fpr_beh_list.append(fpr_beh)
    
    fairness_comp_rows.append({
        'User Segment (Origin Balance)': seg,
        'Total Legit Txns': f"{total_legit:,}",
        'OLD FP Count': f"{fps_orig:,}",
        'OLD FPR (%)': f"{fpr_orig:.4f}%",
        'NEW FP Count': f"{fps_beh:,}",
        'NEW FPR (%)': f"{fpr_beh:.4f}%",
        'FPR Change': f"{fpr_beh - fpr_orig:+.4f}%"
    })

fairness_comp_df = pd.DataFrame(fairness_comp_rows)
print("\n" + fairness_comp_df.to_string(index=False))

# Disparate Ratio Comparison
non_zero_orig = [f for f in fpr_orig_list if f > 0]
ratio_orig = max(fpr_orig_list) / min(non_zero_orig) if non_zero_orig else 0.0

non_zero_beh = [f for f in fpr_beh_list if f > 0]
ratio_beh = max(fpr_beh_list) / min(non_zero_beh) if non_zero_beh else 0.0

print("\n" + "-"*70)
print("FAIRNESS & DISPARATE BURDEN COMPARISON SUMMARY:")
print(f"  - OLD Disparate Burden Ratio (Original Model): {ratio_orig:.2f}x")
print(f"  - NEW Disparate Burden Ratio (Behavioral Model): {ratio_beh:.2f}x")
print(f"  - Reduction in Disparate Impact Ratio        : {ratio_orig - ratio_beh:-.2f}x decrease")

if ratio_beh < ratio_orig:
    print(f"\n  [IMPROVEMENT CONFIRMED]")
    print(f"  Adding leakage-safe behavioral features successfully reduced the disparity ratio from {ratio_orig:.2f}x down to {ratio_beh:.2f}x!")
else:
    print("\n  [NO IMPROVEMENT]")

print("="*70)
