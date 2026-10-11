"""Live-feed simulation: replay real dataset rows through the saved model.

Samples rows per class from the relabeled dataset so every one of the model's
output classes shows up, aligns them to the model's 72-feature input, scales,
predicts, and prints predicted-vs-actual with a running accuracy — the "real AI
classifying real attack flows" demo (Track A).

Run from ids_project/:  python simulate.py
"""
import time
from pathlib import Path

import joblib
import pandas as pd

PROJECT_DIR     = Path(__file__).resolve().parent
DATASET_DIR     = PROJECT_DIR / "dataset"
DEFAULT_DATASET = DATASET_DIR / "relabeled_ids_dataset.csv"
ROWS_PER_CLASS  = 30
DELAY_SECONDS   = 0.3


def load_dataset() -> pd.DataFrame:
    """Prefer the relabeled dataset; else concatenate any CSVs in dataset/."""
    if DEFAULT_DATASET.exists():
        df = pd.read_csv(DEFAULT_DATASET)
    else:
        files = sorted(DATASET_DIR.glob("*.csv"))
        if not files:
            raise FileNotFoundError(
                f"No dataset found. Expected {DEFAULT_DATASET.name} (build it with "
                f"relabel_dataset.py) or any CSV in '{DATASET_DIR}'."
            )
        df = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
    df.columns = df.columns.str.strip()
    return df


def sample_per_class(df: pd.DataFrame) -> pd.DataFrame:
    """Up to ROWS_PER_CLASS rows from each Attack Name, then shuffle."""
    parts = [
        g.sample(n=min(ROWS_PER_CLASS, len(g)), random_state=None)
        for _, g in df.groupby("Attack Name")
    ]
    return pd.concat(parts, ignore_index=True).sample(frac=1).reset_index(drop=True)


def main():
    model         = joblib.load(PROJECT_DIR / "model.pkl")
    encoder       = joblib.load(PROJECT_DIR / "label_encoder.pkl")
    scaler        = joblib.load(PROJECT_DIR / "scaler.pkl")
    feature_names = joblib.load(PROJECT_DIR / "feature_names.pkl")

    df = sample_per_class(load_dataset())
    df.replace([float("inf"), float("-inf")], pd.NA, inplace=True)
    df.dropna(subset=feature_names, inplace=True)

    actual_labels = df["Attack Name"].tolist()
    X = df[feature_names]                       # model input: 72 ordered features
    predictions = encoder.inverse_transform(    # model output: 5 class labels
        model.predict(scaler.transform(X))
    )

    total, correct = len(predictions), 0
    print(f"\n{'='*60}")
    print(f"  IDS Live Feed Simulation — {total} packets")
    print(f"{'='*60}\n")
    for i, (pred, actual) in enumerate(zip(predictions, actual_labels)):
        match = pred == actual
        correct += match
        print(f"[{i+1:>3}/{total}] Predicted: {pred:<25} Actual: {actual:<25} {'✓' if match else '✗'}")
        time.sleep(DELAY_SECONDS)

    print(f"\n{'='*60}")
    print(f"  Simulation Complete")
    print(f"  Correct: {correct}/{total} | Accuracy: {correct/total*100:.1f}%")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
