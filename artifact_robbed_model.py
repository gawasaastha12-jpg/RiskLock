import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import precision_score, recall_score, f1_score, average_precision_score, confusion_matrix
import os

print("="*70)
print("RISKLOCK: ARTIFACT-ROBBED MODEL ROBUSTNESS CHECK")
print("="*70)

csv_path = "PS_20174392719_1491204439457_log.csv"
model_path_base = "models/baseline_xgboost.json"
indices_path = "models/split_indices.npz"

print("\nLoading dataset and saved split indices...")
df = pd.read_csv(csv_path)
df = df.sort_values(by='step').reset_index(drop=True)

split_data = np.load(indices_path)
train_indices = split_data['train']
val_indices = split_data['val']

y_train = df.loc[train_indices, 'isFraud']
y_val = df.loc[val_indices, 'isFraud']

# ---------------------------------------------------------
# 1. EVALUATE BASELINE MODEL ON VAL SET
# ---------------------------------------------------------
feature_cols_base = ['amount', 'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest']
df_encoded_base = pd.get_dummies(df[['type'] + feature_cols_base], columns=['type'], drop_first=False)

X_val_base = df_encoded_base.iloc[val_indices]

model_base = xgb.XGBClassifier()
model_base.load_model(model_path_base)

y_val_prob_base = model_base.predict_proba(X_val_base)[:, 1]
y_val_pred_base = (y_val_prob_base >= 0.5).astype(int)

prec_base = precision_score(y_val, y_val_pred_base, pos_label=1)
rec_base = recall_score(y_val, y_val_pred_base, pos_label=1)
f1_base = f1_score(y_val, y_val_pred_base, pos_label=1)
prauc_base = average_precision_score(y_val, y_val_prob_base)
cm_base = confusion_matrix(y_val, y_val_pred_base)

# ---------------------------------------------------------
# 2. TRAIN & EVALUATE ARTIFACT-ROBBED MODEL
# ---------------------------------------------------------
print("\nPreparing Artifact-Robbed Feature Set...")
print("Dropped Features: ['oldbalanceOrg', 'newbalanceOrig']")
print("Retained Features: ['amount', 'oldbalanceDest', 'newbalanceDest', 'type']")

feature_cols_robbed = ['amount', 'oldbalanceDest', 'newbalanceDest']
df_encoded_robbed = pd.get_dummies(df[['type'] + feature_cols_robbed], columns=['type'], drop_first=False)

X_train_robbed = df_encoded_robbed.iloc[train_indices]
X_val_robbed = df_encoded_robbed.iloc[val_indices]

num_neg = (y_train == 0).sum()
num_pos = (y_train == 1).sum()
scale_pos_weight_val = num_neg / num_pos

model_robbed = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=6,
    learning_rate=0.1,
    scale_pos_weight=scale_pos_weight_val,
    random_state=42,
    tree_method='hist',
    n_jobs=-1
)

print(f"Training Artifact-Robbed XGBoost Classifier (scale_pos_weight={scale_pos_weight_val:.4f})...")
model_robbed.fit(X_train_robbed, y_train)

# Save artifact-robbed model
model_path_robbed = "models/artifact_robbed_xgboost.json"
model_robbed.save_model(model_path_robbed)
print(f"Saved artifact-robbed model to: {model_path_robbed}")

y_val_prob_robbed = model_robbed.predict_proba(X_val_robbed)[:, 1]
y_val_pred_robbed = (y_val_prob_robbed >= 0.5).astype(int)

prec_robbed = precision_score(y_val, y_val_pred_robbed, pos_label=1)
rec_robbed = recall_score(y_val, y_val_pred_robbed, pos_label=1)
f1_robbed = f1_score(y_val, y_val_pred_robbed, pos_label=1)
prauc_robbed = average_precision_score(y_val, y_val_prob_robbed)
cm_robbed = confusion_matrix(y_val, y_val_pred_robbed)

# ---------------------------------------------------------
# 3. SIDE-BY-SIDE COMPARISON TABLE
# ---------------------------------------------------------
print("\n" + "="*70)
print("SIDE-BY-SIDE VALIDATION METRICS COMPARISON (FRAUD CLASS)")
print("="*70)

metrics_table = pd.DataFrame([
    {
        'Metric': 'Precision (Fraud)',
        'Baseline Model (All Features)': f"{prec_base:.6f}",
        'Artifact-Robbed Model (-Org Balances)': f"{prec_robbed:.6f}",
        'Difference': f"{prec_robbed - prec_base:+.6f}"
    },
    {
        'Metric': 'Recall (Fraud)',
        'Baseline Model (All Features)': f"{rec_base:.6f}",
        'Artifact-Robbed Model (-Org Balances)': f"{rec_robbed:.6f}",
        'Difference': f"{rec_robbed - rec_base:+.6f}"
    },
    {
        'Metric': 'F1-Score (Fraud)',
        'Baseline Model (All Features)': f"{f1_base:.6f}",
        'Artifact-Robbed Model (-Org Balances)': f"{f1_robbed:.6f}",
        'Difference': f"{f1_robbed - f1_base:+.6f}"
    },
    {
        'Metric': 'PR-AUC (Fraud)',
        'Baseline Model (All Features)': f"{prauc_base:.6f}",
        'Artifact-Robbed Model (-Org Balances)': f"{prauc_robbed:.6f}",
        'Difference': f"{prauc_robbed - prauc_base:+.6f}"
    }
])

print(metrics_table.to_string(index=False))

print("\nCONFUSION MATRIX COMPARISON:")
print("\n  Baseline Model:")
print(f"    TN: {cm_base[0, 0]:>8,}   FP: {cm_base[0, 1]:>8,}")
print(f"    FN: {cm_base[1, 0]:>8,}   TP: {cm_base[1, 1]:>8,}")

print("\n  Artifact-Robbed Model:")
print(f"    TN: {cm_robbed[0, 0]:>8,}   FP: {cm_robbed[0, 1]:>8,}")
print(f"    FN: {cm_robbed[1, 0]:>8,}   TP: {cm_robbed[1, 1]:>8,}")

# Feature importance of artifact-robbed model
booster_robbed = model_robbed.get_booster()
score_robbed = booster_robbed.get_score(importance_type='gain')
total_robbed_gain = sum(score_robbed.values())

gain_df_robbed = pd.DataFrame([
    {'Feature': feature, 'Gain': score_robbed.get(feature, 0.0), 'Gain (%)': (score_robbed.get(feature, 0.0)/total_robbed_gain)*100}
    for feature in list(df_encoded_robbed.columns)
]).sort_values(by='Gain', ascending=False).reset_index(drop=True)

print("\nARTIFACT-ROBBED MODEL FEATURE IMPORTANCE (GAIN-BASED):")
print(gain_df_robbed.to_string(index=False, formatters={'Gain': '{:,.2f}'.format, 'Gain (%)': '{:.2f}%'.format}))

print("="*70)
