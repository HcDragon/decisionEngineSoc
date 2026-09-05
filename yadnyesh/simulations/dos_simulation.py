import os
import sys
import time
import random
import threading
import numpy as np
import pandas as pd
import requests
import joblib
from concurrent.futures import ThreadPoolExecutor

# Fix UnicodeEncodeError on Windows terminals
if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# -----------------------------------------------------------------
# PATHS
# -----------------------------------------------------------------
_THIS_DIR     = os.path.dirname(os.path.abspath(__file__))
_MODEL_DIR    = os.path.join(_THIS_DIR, "..", "..", "gandhar_model", "AimlProject", "ids_project")
_DATASET_DIR  = os.path.join(_THIS_DIR, "..", "..", "dataSetSamrtsoc")
MODEL_PATH    = os.path.join(_MODEL_DIR, "model.pkl")
SCALER_PATH   = os.path.join(_MODEL_DIR, "scaler.pkl")
ENCODER_PATH  = os.path.join(_MODEL_DIR, "label_encoder.pkl")
FEATURES_PATH = os.path.join(_MODEL_DIR, "feature_names.pkl")

# Attack variant -> dataset CSV mapping
ATTACK_DATASETS = {
    "DoS DNS Flood":  os.path.join(_DATASET_DIR, "DoS DNS Flood.csv"),
    "DoS ICMP Flood": os.path.join(_DATASET_DIR, "DoS ICMP Flood.csv"),
    "DoS SYN Flood":  os.path.join(_DATASET_DIR, "DoS SYN Flood.csv"),
    "DoS UDP Flood":  os.path.join(_DATASET_DIR, "DoS UDP Flood.csv"),
}

# -----------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------
TARGET_URL          = "http://127.0.0.1:3001/api/login"
DECISION_ENGINE_URL = "http://127.0.0.1:8000/api/v1/decision/analyze"
MAX_WORKERS         = 8
TOTAL_REQUESTS      = 512
SRC_IP              = "192.168.1.99"
DEST_IP             = "127.0.0.1"

# Per-attack network metadata for the Decision Engine payload
ATTACK_CONFIG = {
    "DoS DNS Flood":  {"dest_port": 53,  "protocol": "UDP",  "src_port": random.randint(1024, 65535)},
    "DoS ICMP Flood": {"dest_port": 0,   "protocol": "ICMP", "src_port": 0},
    "DoS SYN Flood":  {"dest_port": 80,  "protocol": "TCP",  "src_port": random.randint(1024, 65535)},
    "DoS UDP Flood":  {"dest_port": 53,  "protocol": "UDP",  "src_port": random.randint(1024, 65535)},
}
ATTACK_VARIANTS = list(ATTACK_DATASETS.keys())


# -----------------------------------------------------------------
# THREAD-SAFE STATS TRACKER
# -----------------------------------------------------------------
class AttackStats:
    def __init__(self):
        self.attempts   = 0
        self.failures   = 0
        self.lock       = threading.Lock()
        self.start_time = time.perf_counter()

    def record(self, success=False):
        with self.lock:
            self.attempts += 1
            if not success:
                self.failures += 1

    def snapshot(self):
        with self.lock:
            elapsed = max(time.perf_counter() - self.start_time, 0.001)
            return {
                "attempts": self.attempts,
                "failures": self.failures,
                "elapsed":  elapsed,
                "rate":     round(self.attempts / elapsed, 2),
            }


# -----------------------------------------------------------------
# STAGE 1 - FLOOD SIMULATION
# -----------------------------------------------------------------
def flood_worker(stats, stop_event):
    """
    Simulate high-rate flood requests. In real DoS this would be
    raw TCP/UDP/ICMP packets; here we use HTTP to generate real
    measurable server load that the IDS model can classify.
    """
    while not stop_event.is_set():
        try:
            payload = {"username": "dos_" + str(random.randint(0, 9999)), "password": "x"}
            resp    = requests.post(TARGET_URL, json=payload, timeout=2)
            stats.record(resp.status_code == 200)
        except Exception:
            stats.record(False)


def telemetry_reporter(stats, stop_event):
    while not stop_event.is_set():
        s   = stats.snapshot()
        msg = (
            "\r  [~] Packets: " + str(s["attempts"]).rjust(5) +
            " | Dropped: "      + str(s["failures"]).rjust(5) +
            " | Speed: "        + f"{s['rate']:>7.1f}" + " req/s" +
            " | Elapsed: "      + f"{s['elapsed']:>5.1f}" + "s"
        )
        sys.stdout.write(msg)
        sys.stdout.flush()
        time.sleep(0.4)


def run_flood_stage(attack_name):
    print("\n  STAGE 1 -- Sending " + attack_name + " Traffic...\n")
    stats      = AttackStats()
    stop_event = threading.Event()

    t = threading.Thread(target=telemetry_reporter, args=(stats, stop_event), daemon=True)
    t.start()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for _ in range(MAX_WORKERS):
            executor.submit(flood_worker, stats, stop_event)
        while stats.snapshot()["attempts"] < TOTAL_REQUESTS:
            time.sleep(0.1)
        stop_event.set()

    snap = stats.snapshot()
    print("\n\n  Simulation complete.")
    print("  Packets: " + str(snap["attempts"]) +
          " | Dropped: " + str(snap["failures"]) +
          " | Duration: " + f"{snap['elapsed']:.4f}s" +
          " | Rate: " + str(snap["rate"]) + " req/s")
    return snap


# -----------------------------------------------------------------
# STAGE 2 - ML CLASSIFICATION
# -----------------------------------------------------------------
def classify_with_ml(attack_name, snap):
    sep = "=" * 60
    print("\n" + sep)
    print("  STAGE 2 -- ML Classification (Gandhar's Model)")
    print(sep)
    print("  [~] Loading model files...")

    model         = joblib.load(MODEL_PATH)
    scaler        = joblib.load(SCALER_PATH)
    encoder       = joblib.load(ENCODER_PATH)
    feature_names = joblib.load(FEATURES_PATH)

    print("  [v] Model loaded (" + str(len(feature_names)) + " features)")

    csv_path = ATTACK_DATASETS.get(attack_name, "")
    print("  [~] Sampling feature row from: " + os.path.basename(csv_path))

    if csv_path and os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        for col in ["Attack Name", "Label", "Multi_Label"]:
            if col in df.columns:
                df.drop(columns=[col], inplace=True)
        df.replace([float("inf"), float("-inf")], pd.NA, inplace=True)
        df.dropna(inplace=True)
        available  = [f for f in feature_names if f in df.columns]
        df         = df[available]
        row        = df.sample(n=1, random_state=random.randint(0, 9999))
        feature_df = row[feature_names] if all(f in row.columns for f in feature_names) else row
        print("  [v] Feature vector: authentic " + attack_name + " signature from dataset")
    else:
        print("  [!] Dataset CSV not found. Using zero-vector fallback...")
        vals       = {f: 0.0 for f in feature_names}
        feature_df = pd.DataFrame([vals])[feature_names]

    # Scale and predict
    scaled_vec   = scaler.transform(feature_df)
    pred_encoded = model.predict(scaled_vec)
    pred_label   = encoder.inverse_transform(pred_encoded)[0]

    confidence = 95.0
    if hasattr(model, "predict_proba"):
        proba      = model.predict_proba(scaled_vec)[0]
        confidence = round(float(proba.max()) * 100, 2)

    print("  [v] Prediction   : " + pred_label)
    print("  [v] Confidence   : " + str(confidence) + "%")
    return pred_label, confidence


# -----------------------------------------------------------------
# STAGE 3 - DECISION ENGINE
# -----------------------------------------------------------------
def report_to_decision_engine(attack_name, pred_label, confidence, snap):
    sep = "=" * 60
    print("\n" + sep)
    print("  STAGE 3 -- Decision Engine (Arav's API)")
    print(sep)

    cfg = ATTACK_CONFIG.get(attack_name, {"dest_port": 80, "protocol": "TCP", "src_port": 11111})

    # Dynamic severity derived from model confidence
    if confidence > 95:
        severity = "CRITICAL"
    elif confidence > 80:
        severity = "HIGH"
    elif confidence > 50:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    payload = {
        "timestamp":     time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "src_ip":        SRC_IP,
        "dest_ip":       DEST_IP,
        "src_port":      cfg["src_port"],
        "dest_port":     cfg["dest_port"],
        "protocol":      cfg["protocol"],
        "attack_type":   pred_label,
        "confidence":    confidence,
        "severity":      severity,
        "packet_count":  snap["attempts"],
        "flow_duration": snap["elapsed"],
    }

    print("  [~] Sending prediction to Decision Engine...")
    try:
        resp = requests.post(DECISION_ENGINE_URL, json=payload, timeout=5)
        if resp.status_code == 200:
            data    = resp.json()
            analyst = data.get("analyst_required", False)
            w = 20
            print("\n  [v] Decision Engine responded!")
            print("  +--------------------------------------+")
            print("  |  Attack Type    : " + data.get("attack_type", "N/A").ljust(w) + "|")
            print("  |  Risk Score     : " + str(data.get("risk_score", "N/A")).ljust(w) + "|")
            print("  |  Severity       : " + data.get("severity", "N/A").ljust(w) + "|")
            print("  |  Priority       : " + data.get("priority", "N/A").ljust(w) + "|")
            print("  |  Automation Lvl : " + str(data.get("automation_level", "N/A")).ljust(w) + "|")
            print("  |  Playbook       : " + data.get("playbook", "N/A").ljust(w) + "|")
            print("  |  Status         : " + data.get("incident_status", "N/A").ljust(w) + "|")
            print("  +--------------------------------------+")
            if analyst:
                print("\n  [!] HUMAN ANALYST REQUIRED!")
                print("  Incident ID : " + data.get("incident_id", "N/A"))
                print("  Dashboard   : http://localhost:8501")
            else:
                print("\n  Action applied automatically -- no human intervention needed.")
        else:
            print("  [!] Decision Engine error: HTTP " + str(resp.status_code))
            print("      Response: " + resp.text)
    except requests.exceptions.ConnectionError:
        print("  [!] Decision Engine unreachable.")
        print("      -> Start it: python main.py --api-only  (in arav/decisionEngineSoc/)")


# -----------------------------------------------------------------
# FULL PIPELINE
# -----------------------------------------------------------------
def run_simulation(attack_name):
    sep = "=" * 60
    print("\n" + sep)
    print("  Smart SOC -- DoS Simulation (Full Pipeline)")
    print(sep)
    print("  Attack Variant  : " + attack_name)
    print("  Target URL      : " + TARGET_URL)
    print("  Attacker IP     : " + SRC_IP)
    print("  Worker Threads  : " + str(MAX_WORKERS))
    print("  Model Path      : " + MODEL_PATH)
    print(sep)

    snap                   = run_flood_stage(attack_name)
    pred_label, confidence = classify_with_ml(attack_name, snap)
    report_to_decision_engine(attack_name, pred_label, confidence, snap)
    print("\n")


def select_attack():
    print("\n  Select DoS Attack Variant:")
    for i, name in enumerate(ATTACK_VARIANTS, 1):
        print("    [" + str(i) + "] " + name)
    print("    [0] Run ALL variants sequentially\n")
    choice = input("  Enter choice (default=0): ").strip()
    if choice == "" or choice == "0":
        return "ALL"
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(ATTACK_VARIANTS):
            return ATTACK_VARIANTS[idx]
    except ValueError:
        pass
    print("  Invalid choice -- running ALL variants.")
    return "ALL"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = " ".join(sys.argv[1:])
        if arg in ATTACK_DATASETS:
            run_simulation(arg)
        elif arg.upper() == "ALL":
            for v in ATTACK_VARIANTS:
                run_simulation(v)
                time.sleep(2)
        else:
            print("  [!] Unknown attack: " + arg)
            print("      Valid: " + ", ".join(ATTACK_VARIANTS) + ", ALL")
    else:
        choice = select_attack()
        if choice == "ALL":
            for v in ATTACK_VARIANTS:
                run_simulation(v)
                time.sleep(2)
        else:
            run_simulation(choice)
