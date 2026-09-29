import glob
import time
import joblib
import pandas as pd

DATASET_DIR    = "dataset/"
ROWS_PER_FILE  = 20
DELAY_SECONDS  = 0.5
EXCLUDE_LABELS = ['Recon Host Discovery']

def load_simulation_data(dataset_dir):
    """Sample ROWS_PER_FILE rows from each CSV and shuffle."""
    files = glob.glob(f"{dataset_dir}/*.csv")
    if not files:
        raise FileNotFoundError(f"No CSV files found in '{dataset_dir}'")

    samples = []
    for f in files:
        df = pd.read_csv(f)
        df.columns = df.columns.str.strip()
        df = df[~df['Attack Name'].isin(EXCLUDE_LABELS)]
        samples.append(df.sample(n=min(ROWS_PER_FILE, len(df)), random_state=None))

    return pd.concat(samples, ignore_index=True).sample(frac=1).reset_index(drop=True)

def main():
    model         = joblib.load('model.pkl')
    encoder       = joblib.load('label_encoder.pkl')
    scaler        = joblib.load('scaler.pkl')
    feature_names = joblib.load('feature_names.pkl')

    df            = load_simulation_data(DATASET_DIR)
    actual_labels = df['Attack Name'].tolist()

    df = df[feature_names]
    df.replace([float('inf'), float('-inf')], pd.NA, inplace=True)
    df.dropna(inplace=True)

    # Batch predict all rows at once — much faster than one call per row
    predictions = encoder.inverse_transform(model.predict(scaler.transform(df)))

    total   = len(predictions)
    correct = 0

    print(f"\n{'='*60}")
    print(f"  IDS Live Feed Simulation — {total} packets")
    print(f"{'='*60}\n")

    for i, (pred, actual) in enumerate(zip(predictions, actual_labels)):
        match    = pred == actual
        correct += match
        print(f"[{i+1:>3}/{total}] Predicted: {pred:<25} Actual: {actual:<25} {'✓' if match else '✗'}")
        time.sleep(DELAY_SECONDS)

    print(f"\n{'='*60}")
    print(f"  Simulation Complete")
    print(f"  Correct: {correct}/{total} | Accuracy: {correct/total*100:.1f}%")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
