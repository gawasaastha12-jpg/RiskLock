import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score, f1_score, average_precision_score, brier_score_loss
import os
import joblib

print("="*70)
print("RISKLOCK: RECIPIENT-BEHAVIORAL PIPELINE & THREE-WAY COMPARISON AUDIT")
print("="*70)

csv_path = "PS_20174392719_1491204439457_log.csv"
indices_path = "models/split_indices.npz"

print("\nLoading dataset and split indices...")
df = pd.read_csv(csv_path)
df = df.sort_values(by='step').reset_index(drop=True)

split_data = np.load(indices_path)
train_indices = split_data['train']
val_indices = split_data['val']

train_df = df.iloc[train_indices].copy()
val_df = df.iloc[val_indices].copy()

y_train = train_df['isFraud'].to_numpy()
y_val = val_df['isFraud'].to_numpy()
amounts_val = val_df['amount'].to_numpy()

train_median_amount = train_df['amount'].median()

# ---------------------------------------------------------
# 1. COMPUTING RECIPIENT-BEHAVIORAL FEATURES
# ---------------------------------------------------------
print("\nComputing leakage-safe recipient behavioral features (nameDest)...")
df['dest_cumsum_amount'] = df.groupby('nameDest')['amount'].cumsum() - df['amount']
df['dest_cumcount_amount'] = df.groupby('nameDest').cumcount()

df['dest_historical_avg_amount'] = np.where(
    df['dest_cumcount_amount'] > 0,
    df['dest_cumsum_amount'] / df['dest_cumcount_amount'],
    train_median_amount
)

df['amount_vs_dest_history_ratio'] = df['amount'] / (df['dest_historical_avg_amount'] + 1.0)

# Feature set for Recipient Model
feature_cols_rec = [
    'amount', 'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest',
    'dest_historical_avg_amount', 'amount_vs_dest_history_ratio'
]
df_encoded_rec = pd.get_dummies(df[['type'] + feature_cols_rec], columns=['type'], drop_first=False)

X_train_rec = df_encoded_rec.iloc[train_indices]
X_val_rec = df_encoded_rec.iloc[val_indices]

# ---------------------------------------------------------
# 2. RETRAINING RECIPIENT XGBOOST & PLATT CALIBRATION
# ---------------------------------------------------------
num_neg = (y_train == 0).sum()
num_pos = (y_train == 1).sum()
scale_pos_weight_val = num_neg / num_pos

print(f"Retraining XGBoost with Recipient Features (scale_pos_weight={scale_pos_weight_val:.4f})...")
model_rec = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=6,
    learning_rate=0.1,
    scale_pos_weight=scale_pos_weight_val,
    random_state=42,
    tree_method='hist',
    n_jobs=-1
)
model_rec.fit(X_train_rec, y_train)

# Save recipient model
model_rec.save_model("models/recipient_behavioral_xgboost.json")
print("Saved model to: models/recipient_behavioral_xgboost.json")

p_val_raw_rec = model_rec.predict_proba(X_val_rec)[:, 1]

print("Refitting Platt Scaling Calibrator on Validation set...")
calibrator_rec = LogisticRegression(C=1.0, max_iter=1000)
calibrator_rec.fit(p_val_raw_rec.reshape(-1, 1), y_val)

joblib.dump(calibrator_rec, "models/calibrated_recipient_platt.joblib")
print("Saved Platt calibrator to: models/calibrated_recipient_platt.joblib")

p_val_cal_rec = calibrator_rec.predict_proba(p_val_raw_rec.reshape(-1, 1))[:, 1]

# ---------------------------------------------------------
# LOAD ORIGINAL BASELINE & SENDER MODELS FOR 3-WAY COMPARISON
# ---------------------------------------------------------
# 1. Original Baseline Model
model_orig = xgb.XGBClassifier()
model_orig.load_model("models/baseline_xgboost.json")
calibrator_orig = joblib.load("models/calibrated_platt_scaler.joblib")

feature_cols_orig = ['amount', 'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest']
df_encoded_orig = pd.get_dummies(df[['type'] + feature_cols_orig], columns=['type'], drop_first=False)
X_val_orig = df_encoded_orig.iloc[val_indices]

p_val_raw_orig = model_orig.predict_proba(X_val_orig)[:, 1]
p_val_cal_orig = calibrator_orig.predict_proba(p_val_raw_orig.reshape(-1, 1))[:, 1]

# 2. Failed Sender Model
model_send = xgb.XGBClassifier()
model_send.load_model("models/behavioral_xgboost.json")
calibrator_send = joblib.load("models/calibrated_behavioral_platt.joblib")

df['cumsum_amount'] = df.groupby('nameOrig')['amount'].cumsum() - df['amount']
df['cumcount_amount'] = df.groupby('nameOrig').cumcount()
df['historical_avg_amount'] = np.where(df['cumcount_amount'] > 0, df['cumsum_amount'] / df['cumcount_amount'], train_median_amount)
df['amount_vs_own_history_ratio'] = df['amount'] / (df['historical_avg_amount'] + 1.0)

feature_cols_send = [
    'amount', 'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest',
    'historical_avg_amount', 'amount_vs_own_history_ratio'
]
df_encoded_send = pd.get_dummies(df[['type'] + feature_cols_send], columns=['type'], drop_first=False)
X_val_send = df_encoded_send.iloc[val_indices]

p_val_raw_send = model_send.predict_proba(X_val_send)[:, 1]
p_val_cal_send = calibrator_send.predict_proba(p_val_raw_send.reshape(-1, 1))[:, 1]

# ---------------------------------------------------------
# THREE-WAY MODEL METRIC COMPARISON (VALIDATION SET)
# ---------------------------------------------------------
def calc_metrics(p_cal, y_true):
    pred = (p_cal >= 0.5).astype(int)
    return {
        'prec': precision_score(y_true, pred, pos_label=1),
        'rec': recall_score(y_true, pred, pos_label=1),
        'f1': f1_score(y_true, pred, pos_label=1),
        'prauc': average_precision_score(y_true, p_cal),
        'brier': brier_score_loss(y_true, p_cal)
    }

m_orig = calc_metrics(p_val_cal_orig, y_val)
m_send = calc_metrics(p_val_cal_send, y_val)
m_rec = calc_metrics(p_val_cal_rec, y_val)

comp_metrics_table = pd.DataFrame([
    {
        'Metric': 'Precision (Fraud)',
        'Original Baseline': f"{m_orig['prec']:.6f}",
        'Failed Sender Model': f"{m_send['prec']:.6f}",
        'New Recipient Model': f"{m_rec['prec']:.6f}",
        'Diff (Recipient vs Orig)': f"{m_rec['prec'] - m_orig['prec']:+.6f}"
    },
    {
        'Metric': 'Recall (Fraud)',
        'Original Baseline': f"{m_orig['rec']:.6f}",
        'Failed Sender Model': f"{m_send['rec']:.6f}",
        'New Recipient Model': f"{m_rec['rec']:.6f}",
        'Diff (Recipient vs Orig)': f"{m_rec['rec'] - m_orig['rec']:+.6f}"
    },
    {
        'Metric': 'F1-Score (Fraud)',
        'Original Baseline': f"{m_orig['f1']:.6f}",
        'Failed Sender Model': f"{m_send['f1']:.6f}",
        'New Recipient Model': f"{m_rec['f1']:.6f}",
        'Diff (Recipient vs Orig)': f"{m_rec['f1'] - m_orig['f1']:+.6f}"
    },
    {
        'Metric': 'PR-AUC (Fraud)',
        'Original Baseline': f"{m_orig['prauc']:.6f}",
        'Failed Sender Model': f"{m_send['prauc']:.6f}",
        'New Recipient Model': f"{m_rec['prauc']:.6f}",
        'Diff (Recipient vs Orig)': f"{m_rec['prauc'] - m_orig['prauc']:+.6f}"
    },
    {
        'Metric': 'Brier Score',
        'Original Baseline': f"{m_orig['brier']:.6f}",
        'Failed Sender Model': f"{m_send['brier']:.6f}",
        'New Recipient Model': f"{m_rec['brier']:.6f}",
        'Diff (Recipient vs Orig)': f"{m_rec['brier'] - m_orig['brier']:+.6f}"
    }
])

print("\n" + "="*70)
print("1. THREE-WAY MODEL PERFORMANCE METRICS COMPARISON (VALIDATION SET)")
print("="*70)
print(comp_metrics_table.to_string(index=False))

# ---------------------------------------------------------
# THREE-WAY SEGMENT-LEVEL FAIRNESS AUDIT (ABSOLUTE RATES & RATIOS)
# ---------------------------------------------------------
def get_3tier_decisions(p_cal, amounts):
    exp_block = np.full(len(amounts), 500.0)
    exp_stepup = 30.0 + 0.10 * p_cal * amounts
    exp_approve = p_cal * amounts
    exp_matrix = np.column_stack([exp_block, exp_stepup, exp_approve])
    tier_choices = np.argmin(exp_matrix, axis=1)
    tier_names = np.array(['BLOCK', 'STEP_UP', 'APPROVE'])
    return tier_names[tier_choices]

val_df['tier_orig'] = get_3tier_decisions(p_val_cal_orig, amounts_val)
val_df['tier_send'] = get_3tier_decisions(p_val_cal_send, amounts_val)
val_df['tier_rec'] = get_3tier_decisions(p_val_cal_rec, amounts_val)

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

fairness_3way_rows = []
fpr_orig_list, fpr_send_list, fpr_rec_list = [], [], []

for seg in segment_labels:
    seg_df = val_df[val_df['segment'] == seg]
    legit_df = seg_df[seg_df['isFraud'] == 0]
    total_legit = len(legit_df)
    
    if total_legit > 0:
        fp_orig = np.sum((legit_df['tier_orig'] == 'BLOCK') | (legit_df['tier_orig'] == 'STEP_UP'))
        fpr_orig = (fp_orig / total_legit) * 100
        
        fp_send = np.sum((legit_df['tier_send'] == 'BLOCK') | (legit_df['tier_send'] == 'STEP_UP'))
        fpr_send = (fp_send / total_legit) * 100
        
        fp_rec = np.sum((legit_df['tier_rec'] == 'BLOCK') | (legit_df['tier_rec'] == 'STEP_UP'))
        fpr_rec = (fp_rec / total_legit) * 100
    else:
        fpr_orig, fpr_send, fpr_rec = 0.0, 0.0, 0.0
        
    fpr_orig_list.append(fpr_orig)
    fpr_send_list.append(fpr_send)
    fpr_rec_list.append(fpr_rec)
    
    fairness_3way_rows.append({
        'User Segment': seg,
        'Total Legit Txns': f"{total_legit:,}",
        'Original FPR (%)': f"{fpr_orig:.4f}%",
        'Sender-Model FPR (%)': f"{fpr_send:.4f}%",
        'Recipient-Model FPR (%)': f"{fpr_rec:.4f}%",
        'Absolute FPR Change (Rec vs Orig)': f"{fpr_rec - fpr_orig:+.4f}%"
    })

fairness_3way_df = pd.DataFrame(fairness_3way_rows)

print("\n" + "="*70)
print("2. THREE-WAY SEGMENT-LEVEL FAIRNESS AUDIT (ABSOLUTE RATES)")
print("="*70)
print(fairness_3way_df.to_string(index=False))

# Disparate Impact Ratios
ratio_orig = max(fpr_orig_list) / min([f for f in fpr_orig_list if f > 0])
ratio_send = max(fpr_send_list) / min([f for f in fpr_send_list if f > 0])
ratio_rec = max(fpr_rec_list) / min([f for f in fpr_rec_list if f > 0])

print("\n" + "-"*70)
print("DISPARATE BURDEN RATIO SUMMARY:")
print(f"  - Original Baseline Disparate Ratio : {ratio_orig:.2f}x")
print(f"  - Failed Sender Model Disparate Ratio: {ratio_send:.2f}x")
print(f"  - New Recipient Model Disparate Ratio: {ratio_rec:.2f}x")

all_decreased = all((r_rec <= r_orig) for r_rec, r_orig in zip(fpr_rec_list, fpr_orig_list))

print("\nABSOLUTE FPR EVALUATION VERDICT:")
if all_decreased:
    print("  [SUCCESS] Absolute False Positive Rates went DOWN across ALL balance segments with Recipient-Behavioral features!")
else:
    print(f"  [MIXED/EVALUATED] Absolute FPRs changed: Mid-Balance FPR changed from {fpr_orig_list[2]:.4f}% to {fpr_rec_list[2]:.4f}%.")

print("="*70)
