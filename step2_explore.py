import pandas as pd
import os

csv_path = "PS_20174392719_1491204439457_log.csv"

print("--- STEP 2: LOADING DATA & INITIAL EXPLORATION ---")
print(f"Loading dataset from: {os.path.abspath(csv_path)}")

df = pd.read_csv(csv_path)

print("\n1. DATASET SHAPE:")
print(f"Rows: {df.shape[0]:,}, Columns: {df.shape[1]}")

print("\n2. DATA TYPES (dtypes):")
print(df.dtypes)

print("\n3. CLASS BALANCE (isFraud value counts):")
fraud_counts = df['isFraud'].value_counts()
fraud_pct = df['isFraud'].value_counts(normalize=True) * 100
balance_df = pd.DataFrame({'Count': fraud_counts, 'Percentage (%)': fraud_pct.round(4)})
print(balance_df)

print("\n4. TRANSACTION 'type' VALUES & COUNTS:")
type_counts = df['type'].value_counts()
type_pct = df['type'].value_counts(normalize=True) * 100
types_df = pd.DataFrame({'Count': type_counts, 'Percentage (%)': type_pct.round(4)})
print(types_df)

print("\n5. FIRST 5 ROWS:")
print(df.head())
