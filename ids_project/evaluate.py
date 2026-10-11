from sklearn.metrics import accuracy_score, classification_report

def evaluate_model(model, X_test, y_test, encoder):
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)

    accuracy = accuracy_score(y_test, y_pred)

    avg_confidence = y_proba.max(axis=1).mean()
    if avg_confidence >= 0.85:
        trust = "High"
    elif avg_confidence >= 0.65:
        trust = "Medium"
    else:
        trust = "Low"

    print(f"\nAccuracy   : {accuracy:.4f} ({accuracy * 100:.2f}%)")
    print(f"Confidence : {avg_confidence:.4f} (avg max predicted probability)")
    print(f"Trust Level: {trust}")
    print("\nPer-class results (held-out test set):")
    print(classification_report(y_test, y_pred, target_names=encoder.classes_, digits=3))
