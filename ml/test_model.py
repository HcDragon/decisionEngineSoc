import pandas as pd
import xgboost as xgb
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import joblib
import argparse
import os
import glob

def test_xgboost(dataset_path: str, model_path: str = "xgboost_model.pkl", label_encoder_path: str = "label_encoder.pkl"):
    if not os.path.exists(model_path) or not os.path.exists(label_encoder_path):
        print(f"Error: Model files '{model_path}' or '{label_encoder_path}' not found. Train the model first.")
        return

    print("Loading saved model and label encoder...")
    model = joblib.load(model_path)
    le = joblib.load(label_encoder_path)

    if os.path.isdir(dataset_path):
        print(f"Loading all CSV datasets from directory for testing: {dataset_path}...")
        all_files = glob.glob(os.path.join(dataset_path, "*.csv"))
        df_list = []
        for file in all_files:
            try:
                df_list.append(pd.read_csv(file))
                print(f"  -> Loaded {os.path.basename(file)}")
            except Exception as e:
                print(f"Error loading {file}: {e}")
        if not df_list:
            print("No valid CSV files found.")
            return
        df = pd.concat(df_list, ignore_index=True)
    else:
        print(f"Loading test dataset from {dataset_path}...")
        try:
            df = pd.read_csv(dataset_path)
        except Exception as e:
            print(f"Error loading CSV: {e}")
            return

    # Map dataset columns to expected features
    rename_map = {
        'Src Port': 'src_port',
        'Dst Port': 'dest_port',
        'Protocol': 'protocol',
        'Flow Duration': 'flow_duration',
        'Attack Name': 'attack_type'
    }
    df.rename(columns=rename_map, inplace=True)

    if 'packet_count' not in df.columns:
        if 'Total Fwd Packet' in df.columns and 'Total Bwd packets' in df.columns:
            df['packet_count'] = df['Total Fwd Packet'] + df['Total Bwd packets']

    features = ['src_port', 'dest_port', 'protocol', 'packet_count', 'flow_duration']
    target = 'attack_type'

    missing_cols = [col for col in features + [target] if col not in df.columns]
    if missing_cols:
        print(f"Dataset is missing required columns: {missing_cols}")
        return

    # Preprocessing
    protocol_mapping = {6: 0, 17: 1, 1: 2, "6": 0, "17": 1, "1": 2, 'TCP': 0, 'UDP': 1, 'ICMP': 2, 'tcp': 0, 'udp': 1, 'icmp': 2}
    df['protocol'] = df['protocol'].map(protocol_mapping).fillna(3).astype(int)

    X_test = df[features]
    y_raw = df[target]
    
    print("\n--- Testing Data Analysis ---")
    print("\n1. Test Dataset Class Distribution:")
    print(y_raw.value_counts().to_string())

    # Map target labels using the loaded LabelEncoder.
    # We must handle unseen classes gracefully!
    known_classes = set(le.classes_)
    unseen = set(y_raw) - known_classes
    if unseen:
        print(f"\nWarning: Test set contains classes not seen during training: {unseen}")
        # Filter out unseen classes for scoring purposes since the model cannot predict them
        valid_idx = y_raw.isin(known_classes)
        X_test = X_test[valid_idx]
        y_raw = y_raw[valid_idx]
        print(f"Filtered test set to {len(X_test)} rows of known classes.")

    if len(X_test) == 0:
        print("No valid known classes to evaluate.")
        return

    y_test = le.transform(y_raw)

    print("\nEvaluating Model on Test Data...")
    y_pred = model.predict(X_test)
    print(f"Test Accuracy: {accuracy_score(y_test, y_pred):.4f}")

    target_names = le.inverse_transform(list(range(len(le.classes_))))
    print("\n2. Classification Report:")
    print(classification_report(y_test, y_pred, target_names=target_names, labels=list(range(len(le.classes_)))))

    print("\n3. Confusion Matrix:")
    cm_df = pd.DataFrame(
        confusion_matrix(y_test, y_pred, labels=list(range(len(le.classes_)))), 
        index=target_names, 
        columns=target_names
    )
    print(cm_df)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test XGBoost on Network Flow Data")
    parser.add_argument("--dataset", type=str, required=True, help="Path to the test dataset CSV or Directory")
    parser.add_argument("--model", type=str, default="xgboost_model.pkl", help="Path to the trained model")
    parser.add_argument("--le", type=str, default="label_encoder.pkl", help="Path to the label encoder")
    args = parser.parse_args()
    
    test_xgboost(args.dataset, args.model, args.le)
