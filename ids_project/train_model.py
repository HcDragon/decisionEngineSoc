import joblib
from sklearn.ensemble import RandomForestClassifier
from preprocess import load_and_preprocess
from evaluate import evaluate_model

MODEL_PATH = "model.pkl"

def main():
    data = load_and_preprocess()

    print("\nTraining Random Forest...")
    model = RandomForestClassifier(
        n_estimators=100,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    model.fit(data.X_train, data.y_train)

    evaluate_model(model, data.X_test, data.y_test, data.encoder)

    joblib.dump(model, MODEL_PATH)
    print(f"\nModel saved to '{MODEL_PATH}'")

if __name__ == "__main__":
    main()
