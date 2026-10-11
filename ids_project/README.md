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

## Live Demo (detect → block → dashboard)

Two laptops on the same network. The **victim** runs Juice Shop + the IDS; the
**attacker** SSHes in and launches network attacks.

> Scope: the model detects four **network-layer** attacks from TCP flow
> statistics: port/OS scans, SYN floods, SSH brute force and ARP-spoofing MITM.
> It does **not** inspect HTTP payloads, so web-app exploits (SQLi/XSS) against
> Juice Shop are out of scope, and it has no UDP/ICMP flood classes.

### Victim laptop (Ubuntu)
```bash
# 1. target app
docker run -d -p 3000:3000 bkimminich/juice-shop

# 2. dashboard  (http://localhost:8080)
python dashboard.py

# 3. live flow extraction -> CSV
cicflowmeter -i <iface> -c live_flows.csv      # e.g. -i eth0

# 4. detection + decision engine (arm blocking with --block, needs sudo)
sudo python engine.py --live live_flows.csv --block
```

### Attacker laptop
```bash
nmap -sS -O <victim-ip>                                # -> Recon Scan
sudo hping3 --flood --rand-source -S -p 3000 <victim-ip>   # -> DoS SYN Flood
hydra -l <user> -P words.txt ssh://<victim-ip>         # -> Dictionary Brute Force
```
The brute-force class was learned from SSH (port 22), so the victim needs
`openssh-server` running; `--rand-source` matches the spoofed flood in the
training captures.

Detections appear live on the dashboard; armed with `--block`, the source IP is
dropped via `iptables`.

### No second laptop? Replay mode (same engine, real data)
```bash
python dashboard.py                 # terminal 1
python engine.py --replay           # terminal 2  (dry-run, logs "would-block")
```

**Tuning (`engine.py`):** `--min-confidence` (default 0.5) trades sensitivity vs
false positives; if live mode under-detects, compare your `live_flows.csv` header
against the model's features and extend the `ALIAS` map in `engine.py`.

## Dataset and accuracy

`dataset/relabeled_ids_dataset.csv` is built by `relabel_dataset.py` from the raw
per-attack capture files. The raw files label every flow recorded during an
attack window as that attack, including other devices' normal traffic; the
script keeps the attack label only on flows that involve the attacking machine
and marks the rest benign. Classes with no TCP attack flows (DNS/ICMP/UDP flood,
host discovery) are removed, the two nmap recon classes are merged, and
`Src Port` is not used as a feature.

Held-out test accuracy (20% split): **99.86%**, macro F1 0.992. Before these
changes the same split scored 84.9%.

Classes: Benign Traffic, Dictionary Brute Force, DoS SYN Flood,
MITM ARP Spoofing, Recon Scan.

## How It Works

| Step | File | Description |
|------|------|-------------|
| 1 | `preprocess.py` | Loads CSV, drops NaN/inf, encodes labels, splits data |
| 2 | `train_model.py` | Trains a `RandomForestClassifier` on the training set |
| 3 | `evaluate.py` | Prints accuracy, precision, recall, F1, and confusion matrix |
| 4 | `train_model.py` | Saves the trained model as `model.pkl` using joblib |
