# AI/ML Intrusion Detection System (IDS)

A beginner-friendly IDS that trains a Random Forest classifier on the CICIDS2017 dataset to classify network traffic as benign or an attack type.

## Project Structure

```
ids_project/
├── dataset/          ← Place your CICIDS2017 CSV file here
├── preprocess.py     ← Data loading, cleaning, and splitting
├── evaluate.py       ← Model evaluation metrics
├── train_model.py    ← Main entry point: trains and saves the model
├── model.pkl         ← Saved model (generated after training)
└── requirements.txt
```

## Setup & Run

### 1. Get the Dataset
Download any CSV file from the [CICIDS2017 dataset](https://www.unb.ca/cic/datasets/ids-2017.html) and place it inside the `dataset/` folder.

### 2. Update the File Path
Open `train_model.py` and update `DATASET_PATH` to match your CSV filename:
```python
DATASET_PATH = "dataset/your-file-name.csv"
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Train the Model
```bash
cd ids_project
python train_model.py
```

### Expected Output
```
Dataset loaded: 225745 rows, 79 columns
Classes: ['BENIGN', 'DDoS']
Train size: 180596, Test size: 45149
Training Random Forest...
Training complete.

--- Model Evaluation ---
Accuracy : 0.9998
Precision: 0.9998
Recall   : 0.9998
F1 Score : 0.9998

Confusion Matrix:
...
Model saved to 'model.pkl'
```

## How It Works

| Step | File | Description |
|------|------|-------------|
| 1 | `preprocess.py` | Loads CSV, drops NaN/inf, encodes labels, splits data |
| 2 | `train_model.py` | Trains a `RandomForestClassifier` on the training set |
| 3 | `evaluate.py` | Prints accuracy, precision, recall, F1, and confusion matrix |
| 4 | `train_model.py` | Saves the trained model as `model.pkl` using joblib |
