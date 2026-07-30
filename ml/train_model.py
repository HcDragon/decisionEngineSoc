import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import joblib
import argparse
import os

def train_xgboost(dataset_path: str, model_output_path: str = "xgboost_model.pkl", label_encoder_path: str = "label_encoder.pkl"):
    import glob
    
    if os.path.isdir(dataset_path):
        print(f"Loading all CSV datasets from directory: {dataset_path}...")
        all_files = glob.glob(os.path.join(dataset_path, "*.csv"))
        df_list = []
        for file in all_files:
            try:
                # We can sample or load entirely. For now, load entire file.
                df_list.append(pd.read_csv(file))
                print(f"  -> Loaded {os.path.basename(file)}")
            except Exception as e:
                print(f"Error loading {file}: {e}")
        if not df_list:
            print("No valid CSV files found in the directory.")
            return
        df = pd.concat(df_list, ignore_index=True)
        print(f"Successfully merged {len(df_list)} datasets. Total rows: {len(df)}")
    else:
        print(f"Loading dataset from {dataset_path}...")
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

    # Expected features (based on NetworkFlow schema)
    features = ['src_port', 'dest_port', 'protocol', 'packet_count', 'flow_duration']
    target = 'attack_type'

    # Check if necessary columns exist
    missing_cols = [col for col in features + [target] if col not in df.columns]
    if missing_cols:
        print(f"Dataset is missing required columns: {missing_cols}")
        print(f"Make sure your dataset has: {features + [target]}")
        return

    # Preprocessing
    # Map protocol (TCP:6->0, UDP:17->1, ICMP:1->2)
    protocol_mapping = {6: 0, 17: 1, 1: 2, "6": 0, "17": 1, "1": 2, 'TCP': 0, 'UDP': 1, 'ICMP': 2, 'tcp': 0, 'udp': 1, 'icmp': 2}
    df['protocol'] = df['protocol'].map(protocol_mapping).fillna(3).astype(int)

    # XGBoost multi:softprob requires at least 2 classes
    if df[target].nunique() == 1:
        print(f"Warning: Only 1 class found ({df[target].iloc[0]}). Adding dummy 'Benign Traffic' classes for XGBoost to initialize.")
        dummy_rows = pd.DataFrame([{
            'src_port': 12345,
            'dest_port': 443,
            'protocol': 0,
            'packet_count': 10,
            'flow_duration': 10.0,
            target: 'Benign Traffic'
        } for _ in range(10)])
        df = pd.concat([df, dummy_rows], ignore_index=True)
    
    X = df[features]
    y_raw = df[target]
    
    print("\n--- Essential Data ---")
    print("\n1. Dataset Class Distribution:")
    print(y_raw.value_counts().to_string())
    
    # Encode Target Labels
    le = LabelEncoder()
    y = le.fit_transform(y_raw)
    
    # Split: exactly 80% train, 20% test for each class using stratify=y
    try:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    except ValueError:
        # Fallback if a class has too few instances for stratify
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training XGBoost Classifier...")
    num_classes = len(le.classes_)
    
    # Use appropriate objective
    objective = 'multi:softprob' if num_classes > 2 else 'binary:logistic'
    
    model = xgb.XGBClassifier(
        objective=objective,
        eval_metric='mlogloss' if num_classes > 2 else 'logloss',
        n_estimators=300,
        learning_rate=0.05,
        max_depth=8,
        subsample=0.8,
        colsample_bytree=0.8,
        early_stopping_rounds=20,
        random_state=42,
        n_jobs=-1
    )
    
    if num_classes > 2:
        model.set_params(num_class=num_classes)
    
    model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train), (X_test, y_test)],
        verbose=50
    )
    
    # Evaluate
    print("Evaluating Model...")
    y_pred = model.predict(X_test)
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    
    target_names = le.inverse_transform(list(range(len(le.classes_))))
    print("\n2. Classification Report:")
    print(classification_report(y_test, y_pred, target_names=target_names))
    
    print("\n3. Confusion Matrix:")
    cm_df = pd.DataFrame(confusion_matrix(y_test, y_pred), index=target_names, columns=target_names)
    print(cm_df)
    
    print("\n4. Feature Importances:")
    importances = pd.DataFrame({
        'Feature': features,
        'Importance': model.feature_importances_
    }).sort_values(by='Importance', ascending=False)
    print(importances.to_string(index=False))
    
    # Save Model and Encoder
    joblib.dump(model, model_output_path)
    joblib.dump(le, label_encoder_path)
    
    print(f"Model saved to {model_output_path}")
    print(f"Label Encoder saved to {label_encoder_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train XGBoost on Network Flow Data")
    parser.add_argument("--dataset", type=str, required=True, help="Path to the training dataset CSV")
    parser.add_argument("--model-out", type=str, default="xgboost_model.pkl", help="Output path for the model")
    parser.add_argument("--le-out", type=str, default="label_encoder.pkl", help="Output path for the label encoder")
    args = parser.parse_args()
    
    train_xgboost(args.dataset, args.model_out, args.le_out)
