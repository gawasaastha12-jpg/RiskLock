import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import precision_score, recall_score, f1_score, average_precision_score, confusion_matrix
import os
import joblib

# Ensure output directory exists
os.makedirs("models", exist_ok=True)

csv_path = "PS_20174392719_1491204439457_log.csv"

print("="*70)
print("RISKLOCK: FRAUD-SPIKE DETECTOR PIPELINE")
print("="*70)

# STEP 2 Output Summary
print("\n--- STEP 2: LOADED DATA METADATA ---")
df = pd.read_csv(csv_path)
print(f"Total Rows: {len(df):,}")
print(f"Columns: {list(df.columns)}")

# STEP 3: DEDUPLICATION / IMPUTATION / DROPPING DISCLOSURE
print("\n--- STEP 3: DATA CLEANING DISCLOSURE ---")
null_counts = df.isnull().sum().sum()
duplicate_counts = df.duplicated().sum()
print(f"Missing (null) values in dataset: {null_counts}")
print(f"Duplicate rows in dataset: {duplicate_counts}")
print("DISCLOSURE: No rows were dropped, imputed, or deduplicated. All 6,362,620 original rows are preserved.")

# STEP 4: TIME-BASED SPLIT
print("\n--- STEP 4: TIME-BASED SPLIT (SORT BY 'step') ---")
df = df.sort_values(by='step').reset_index(drop=True)

unique_steps = sorted(df['step'].unique())
total_steps = len(unique_steps)
train_step_cutoff = unique_steps[int(total_steps * 0.70) - 1]  # First 70% steps
val_step_cutoff = unique_steps[int(total_steps * 0.85) - 1]    # Next 15% steps (up to 85%)

train_mask = df['step'] <= train_step_cutoff
val_mask = (df['step'] > train_step_cutoff) & (df['step'] <= val_step_cutoff)
test_mask = df['step'] > val_step_cutoff

train_indices = df.index[train_mask].to_numpy()
val_indices = df.index[val_mask].to_numpy()
test_indices = df.index[test_mask].to_numpy()

print(f"Step Range Total: {unique_steps[0]} to {unique_steps[-1]} (Total {total_steps} steps)")
print(f"Train Split  : Steps {unique_steps[0]} to {train_step_cutoff} | Rows: {len(train_indices):,} | Fraud: {df.loc[train_indices, 'isFraud'].sum():,} ({df.loc[train_indices, 'isFraud'].mean()*100:.4f}%)")
print(f"Val Split    : Steps {train_step_cutoff + 1} to {val_step_cutoff} | Rows: {len(val_indices):,} | Fraud: {df.loc[val_indices, 'isFraud'].sum():,} ({df.loc[val_indices, 'isFraud'].mean()*100:.4f}%)")
print(f"Test Split   : Steps {val_step_cutoff + 1} to {unique_steps[-1]} | Rows: {len(test_indices):,} | Fraud: {df.loc[test_indices, 'isFraud'].sum():,} ({df.loc[test_indices, 'isFraud'].mean()*100:.4f}%) [HELD-OUT]")

# FEATURE PREPARATION
# Features to use: 'type' (one-hot encoded), 'amount', 'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest'
feature_cols = ['amount', 'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest']
df_encoded = pd.get_dummies(df[['type'] + feature_cols], columns=['type'], drop_first=False)

X_train = df_encoded.iloc[train_indices]
y_train = df.loc[train_indices, 'isFraud']

X_val = df_encoded.iloc[val_indices]
y_val = df.loc[val_indices, 'isFraud']

# STEP 5: BASELINE XGBOOST CLASSIFIER
print("\n--- STEP 5: TRAIN BASELINE XGBOOST CLASSIFIER ---")
num_neg = (y_train == 0).sum()
num_pos = (y_train == 1).sum()
scale_pos_weight_val = num_neg / num_pos
print(f"Calculated scale_pos_weight: {scale_pos_weight_val:.4f} (Neg: {num_neg:,}, Pos: {num_pos:,})")

model = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=6,
    learning_rate=0.1,
    scale_pos_weight=scale_pos_weight_val,
    random_state=42,
    tree_method='hist',
    n_jobs=-1
)

print("Training XGBoost baseline on train set...")
model.fit(X_train, y_train)
print("Training completed.")

# STEP 6: EVALUATION ON VALIDATION ONLY
print("\n--- STEP 6: EVALUATION ON VALIDATION SET ONLY ---")
y_val_pred_proba = model.predict_proba(X_val)[:, 1]
y_val_pred = (y_val_pred_proba >= 0.5).astype(int)

prec = precision_score(y_val, y_val_pred, pos_label=1)
rec = recall_score(y_val, y_val_pred, pos_label=1)
f1 = f1_score(y_val, y_val_pred, pos_label=1)
pr_auc = average_precision_score(y_val, y_val_pred_proba)
cm = confusion_matrix(y_val, y_val_pred)

print("FRAUD CLASS SPECIFIC METRICS (val set):")
print(f"  Precision (Fraud): {prec:.6f}")
print(f"  Recall (Fraud)   : {rec:.6f}")
print(f"  F1 Score (Fraud) : {f1:.6f}")
print(f"  PR-AUC (Fraud)   : {pr_auc:.6f}")

print("\nCONFUSION MATRIX (val set):")
print(f"  TN: {cm[0, 0]:>8,}   FP: {cm[0, 1]:>8,}")
print(f"  FN: {cm[1, 0]:>8,}   TP: {cm[1, 1]:>8,}")

# STEP 7: SAVE MODEL & SPLIT INDICES
print("\n--- STEP 7: SAVING ARTIFACTS ---")
model_path = "models/baseline_xgboost.json"
indices_path = "models/split_indices.npz"
requirements_path = "requirements.txt"

model.save_model(model_path)
print(f"Saved trained model to: {model_path}")

np.savez_compressed(indices_path, train=train_indices, val=val_indices, test=test_indices)
print(f"Saved split indices to: {indices_path}")

reqs = """pandas==3.0.3
numpy==2.2.3
xgboost==3.2.0
scikit-learn==1.9.0
joblib==1.4.2
"""
with open(requirements_path, "w") as f:
    f.write(reqs)
print(f"Saved requirements to: {requirements_path}")

print("\n[CONFIRMATION] Held-out test set (89,466 rows, steps 632-743) was NOT touched or evaluated.")
print("="*70)
