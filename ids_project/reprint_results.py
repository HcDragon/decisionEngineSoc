"""Reprint held-out evaluation metrics from the saved model — no retraining.

Rebuilds the exact 20% test split preprocess.load_and_preprocess uses (same
columns dropped, same seed) and scores the saved model on it, so the numbers
match train_model.py. Input/output follow the saved artifacts: 72 scaled
features in, the label encoder's 5 classes out.

Run from ids_project/:  python reprint_results.py
"""
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split

from evaluate import evaluate_model
from preprocess import DATASET_PATH, DROP_COLS

# Saved artifacts (the model's I/O contract)
model   = joblib.load('model.pkl')
encoder = joblib.load('label_encoder.pkl')
scaler  = joblib.load('scaler.pkl')
feature_names = joblib.load('feature_names.pkl')

# Reload + clean the dataset the same way preprocess does (no retraining).
df = pd.read_csv(DATASET_PATH)
df.columns = df.columns.str.strip()
df.drop(columns=[c for c in DROP_COLS if c in df.columns], inplace=True)
df.replace([float('inf'), float('-inf')], pd.NA, inplace=True)
df.dropna(inplace=True)
df.drop_duplicates(inplace=True)

y = encoder.transform(df['Attack Name'])
# Align to the model's exact ordered feature list (defends against column drift).
X = df[feature_names]
X_scaled = scaler.transform(X)

# Same split/seed as training -> the held-out test rows.
_, X_test, _, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42, stratify=y
)
evaluate_model(model, X_test, y_test, encoder)
