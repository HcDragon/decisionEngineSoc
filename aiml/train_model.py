import time
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
        max_depth=20,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    start = time.time()
    model.fit(data.X_train, data.y_train)
    print(f"Training time: {time.time() - start:.1f}s")

    evaluate_model(model, data.X_test, data.y_test, data.encoder)

    joblib.dump(model, MODEL_PATH)
    print(f"\nModel saved to '{MODEL_PATH}'")

if __name__ == "__main__":
    main()
