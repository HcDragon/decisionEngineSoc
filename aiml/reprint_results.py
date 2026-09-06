import joblib
import glob
import pandas as pd
from evaluate import evaluate_model
from preprocess import DROP_COLS

DATASET_DIR = "dataset/"

# Load saved artifacts
model   = joblib.load('model.pkl')
encoder = joblib.load('label_encoder.pkl')
scaler  = joblib.load('scaler.pkl')

# Reload and preprocess data the same way (no retraining)
files = glob.glob(f"{DATASET_DIR}/*.csv")
df = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
df.columns = df.columns.str.strip()
df.drop(columns=[c for c in DROP_COLS if c in df.columns], inplace=True)
df.replace([float('inf'), float('-inf')], pd.NA, inplace=True)
df.dropna(inplace=True)
df.drop_duplicates(inplace=True)
df = df[df['Attack Name'] != 'Recon Host Discovery']
df = df[[c for c in df.columns if df[c].nunique() > 1]]

X = df.drop(columns=['Attack Name'])
y = encoder.transform(df['Attack Name'])
X_scaled = scaler.transform(X)

feature_names = joblib.load('feature_names.pkl')

# Reprint evaluation
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42, stratify=y
)
evaluate_model(model, X_test, y_test, encoder, feature_names)
