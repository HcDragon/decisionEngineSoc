import numpy as np
import pandas as pd
import joblib
from collections import namedtuple
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from imblearn.over_sampling import SMOTE

DATASET_PATH = "dataset/relabeled_ids_dataset.csv"  # built by relabel_dataset.py

# Features NFStream's live capture cannot produce (TCP initial window size, TCP
# header length, bulk-transfer averages, active/idle split). The SOC runs live
# detection on NFStream flows (soc/backend/app/monitor/features.py), so training
# on columns that are always 0 at inference would just mislead the model — drop
# them here so the trained feature set == what NFStream can actually observe.
NFSTREAM_UNAVAILABLE = [
    'Fwd Header Length', 'Bwd Header Length',
    'Bwd Bytes/Bulk Avg', 'Bwd Packet/Bulk Avg', 'Bwd Bulk Rate Avg',
    'FWD Init Win Bytes', 'Bwd Init Win Bytes',
    'Active Mean', 'Active Std', 'Active Max', 'Active Min',
    'Idle Mean', 'Idle Std', 'Idle Max', 'Idle Min',
]
# Src Port is ephemeral: the model memorised the one port each nmap run used.
DROP_COLS = ['Label', 'Multi_Label', 'Src Port'] + NFSTREAM_UNAVAILABLE

PreprocessResult = namedtuple(
    'PreprocessResult',
    ['X_train', 'X_test', 'y_train', 'y_test', 'encoder', 'feature_names']
)

def load_and_preprocess():
    df = pd.read_csv(DATASET_PATH)
    df.columns = df.columns.str.strip()

    print(f"Loaded {len(df):,} rows | {df.shape[1]} columns")
    print(f"\nClass distribution:\n{df['Attack Name'].value_counts()}")

    df.drop(columns=[c for c in DROP_COLS if c in df.columns], inplace=True)
    df.replace([float('inf'), float('-inf')], pd.NA, inplace=True)
    df.dropna(inplace=True)
    df.drop_duplicates(inplace=True)

    constant_cols = [c for c in df.columns if df[c].nunique() <= 1]
    if constant_cols:
        df.drop(columns=constant_cols, inplace=True)

    X = df.drop(columns=['Attack Name'])
    y = df['Attack Name']
    feature_names = list(X.columns)

    encoder = LabelEncoder()
    y_encoded = encoder.fit_transform(y)
    joblib.dump(encoder, 'label_encoder.pkl')
    joblib.dump(feature_names, 'feature_names.pkl')

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)
    joblib.dump(scaler, 'scaler.pkl')

    unique, counts = np.unique(y_train, return_counts=True)
    min_samples = 1000
    sampling_strategy = {
        cls: min_samples for cls, count in zip(unique, counts)
        if count < min_samples
    }
    if sampling_strategy:
        targeted = [encoder.classes_[c] for c in sampling_strategy]
        print(f"\nApplying SMOTE to: {targeted}")
        smote = SMOTE(sampling_strategy=sampling_strategy, random_state=42, k_neighbors=5)
        X_train, y_train = smote.fit_resample(X_train, y_train)

    print(f"\nClasses : {list(encoder.classes_)}")
    print(f"Train   : {len(X_train):,} | Test: {len(X_test):,} | Features: {len(feature_names)}")

    return PreprocessResult(X_train, X_test, y_train, y_test, encoder, feature_names)
