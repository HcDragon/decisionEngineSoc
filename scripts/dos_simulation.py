#!/usr/bin/env python3
"""
scripts/dos_simulation.py
-------------------------
Integrated DoS Attack Simulation, ML Classification & SOC Decision Pipeline.
Origin: Authored by Gandhar (AimlProject) & Integrated with Arav's Autonomous SOC Decision Engine.

Flow:
  Stage 1: Multi-threaded volumetric flood simulation against TARGET_URL
  Stage 2: 100-Tree Random Forest feature vector extraction & threat classification
  Stage 3: Autonomous SOC Decision Engine evaluation (Risk -> Policy -> Playbook -> Response)
"""

import os
import sys
import time
import random
import threading
from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
import requests
import joblib
from concurrent.futures import ThreadPoolExecutor

# Fix UnicodeEncodeError on Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# -----------------------------------------------------------------
# PATH RESOLUTION (Supports local repo, external gandhar_model & env vars)
# -----------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = _THIS_DIR if os.path.exists(os.path.join(_THIS_DIR, "aiml")) else os.path.dirname(_THIS_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Model paths - check friend's relative path first, then fallback to repo's aiml/
_GANDHAR_MODEL_DIR = os.path.join(_THIS_DIR, "..", "..", "gandhar_model", "AimlProject", "ids_project")
_LOCAL_MODEL_DIR = os.path.join(_REPO_ROOT, "aiml")
_MODEL_DIR = _GANDHAR_MODEL_DIR if os.path.exists(_GANDHAR_MODEL_DIR) else _LOCAL_MODEL_DIR

MODEL_PATH    = os.path.join(_MODEL_DIR, "model.pkl")
SCALER_PATH   = os.path.join(_MODEL_DIR, "scaler.pkl")
ENCODER_PATH  = os.path.join(_MODEL_DIR, "label_encoder.pkl")
FEATURES_PATH = os.path.join(_MODEL_DIR, "feature_names.pkl")

# Dataset paths - check friend's relative path first, then local dataset/
_GANDHAR_DATASET_DIR = os.path.join(_THIS_DIR, "..", "..", "dataSetSamrtsoc")
_LOCAL_DATASET_DIR   = os.path.join(_REPO_ROOT, "aiml", "dataset")
_DATASET_DIR = _GANDHAR_DATASET_DIR if os.path.exists(_GANDHAR_DATASET_DIR) else _LOCAL_DATASET_DIR

ATTACK_DATASETS = {
    "DoS DNS Flood":  os.path.join(_DATASET_DIR, "DoS DNS Flood.csv"),
    "DoS ICMP Flood": os.path.join(_DATASET_DIR, "DoS ICMP Flood.csv"),
    "DoS SYN Flood":  os.path.join(_DATASET_DIR, "DoS SYN Flood.csv"),
    "DoS UDP Flood":  os.path.join(_DATASET_DIR, "DoS UDP Flood.csv"),
}

UNIFIED_DATASET_CSV = os.path.join(_REPO_ROOT, "aiml", "dataset", "cleaned_ids_dataset (1).csv")

# -----------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------
TARGET_URL          = os.environ.get("TARGET_URL", "http://127.0.0.1:3001/api/login")
DECISION_ENGINE_URL = os.environ.get("DECISION_ENGINE_URL", "http://127.0.0.1:8000/api/v1/decision/analyze")
MAX_WORKERS         = int(os.environ.get("MAX_WORKERS", 8))
TOTAL_REQUESTS      = int(os.environ.get("TOTAL_REQUESTS", 512))
SRC_IP              = os.environ.get("SRC_IP", "192.168.1.99")
DEST_IP             = os.environ.get("DEST_IP", "127.0.0.1")

# Per-attack network metadata for the Decision Engine payload
ATTACK_CONFIG = {
    "DoS DNS Flood":  {"dest_port": 53,  "protocol": "UDP",  "src_port": random.randint(1024, 65535)},
    "DoS ICMP Flood": {"dest_port": 0,   "protocol": "ICMP", "src_port": 0},
    "DoS SYN Flood":  {"dest_port": 80,  "protocol": "TCP",  "src_port": random.randint(1024, 65535)},
    "DoS UDP Flood":  {"dest_port": 53,  "protocol": "UDP",  "src_port": random.randint(1024, 65535)},
}
ATTACK_VARIANTS = list(ATTACK_CONFIG.keys())


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
def flood_worker(stats: AttackStats, stop_event: threading.Event):
    """
    Simulate high-rate flood requests. In real DoS this would be
    raw TCP/UDP/ICMP packets; here we use HTTP to generate real
    measurable server load that the IDS model can classify.
    """
    session = requests.Session()
    while not stop_event.is_set():
        try:
            payload = {"username": "dos_" + str(random.randint(0, 9999)), "password": "x"}
            resp    = session.post(TARGET_URL, json=payload, timeout=1.0)
            stats.record(resp.status_code == 200)
        except Exception:
            stats.record(False)


def telemetry_reporter(stats: AttackStats, stop_event: threading.Event, attack_name: str = "DoS Attack"):
    db = None
    try:
        from decision_engine.storage.db import Database
        db = Database()
    except Exception:
        pass

    last_logged_attempts = 0
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

        # Update process-shared workflow tracker in real-time
        try:
            from decision_engine.events.workflow_tracker import tracker
            tracker.update_telemetry(s["attempts"], s["rate"], s["elapsed"])
        except Exception:
            pass

        # Write incremental live flow telemetry to SQLite so the dashboard's Live Traffic tab updates live!
        if db and s["attempts"] > last_logged_attempts and (s["attempts"] - last_logged_attempts >= 64 or s["attempts"] >= TOTAL_REQUESTS):
            try:
                import uuid
                ev_id = f"EVT-{uuid.uuid4().hex[:8]}"
                cfg = ATTACK_CONFIG.get(attack_name, {"dest_port": 80, "protocol": "TCP", "src_port": 11111})
                db.save_threat_event({
                    "event_id": ev_id,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "src_ip": SRC_IP,
                    "dest_ip": DEST_IP,
                    "attack_type": attack_name,
                    "confidence": 0.95,
                    "network": {
                        "packet_count": s["attempts"],
                        "flow_duration": s["elapsed"],
                        "protocol": cfg["protocol"],
                        "bytes": s["attempts"] * 64
                    }
                })
                last_logged_attempts = s["attempts"]
            except Exception:
                pass

        time.sleep(0.25)


def run_flood_stage(attack_name: str) -> Dict[str, Any]:
    print("\n  STAGE 1 -- Sending " + attack_name + " Traffic to " + TARGET_URL + "...\n")
    
    # Initialize real-time SOAR workflow tracking
    try:
        from decision_engine.events.workflow_tracker import tracker
        tracker.start_attack(
            attack_type=attack_name,
            src_ip=SRC_IP,
            dest_ip=DEST_IP,
            target_url=TARGET_URL,
            total_packets=TOTAL_REQUESTS
        )
    except Exception:
        pass

    stats      = AttackStats()
    stop_event = threading.Event()

    t = threading.Thread(target=telemetry_reporter, args=(stats, stop_event, attack_name), daemon=True)
    t.start()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for _ in range(MAX_WORKERS):
            executor.submit(flood_worker, stats, stop_event)
        while stats.snapshot()["attempts"] < TOTAL_REQUESTS:
            time.sleep(0.05)
        stop_event.set()

    snap = stats.snapshot()
    print("\n\n  Simulation complete.")
    print("  Packets: " + str(snap["attempts"]) +
          " | Dropped: " + str(snap["failures"]) +
          " | Duration: " + f"{snap['elapsed']:.4f}s" +
          " | Rate: " + str(snap["rate"]) + " req/s")

    try:
        from decision_engine.events.workflow_tracker import tracker
        tracker.advance_stage(1, "DONE", f"{snap['attempts']} pkts ({snap['rate']:.0f} pps)")
    except Exception:
        pass

    return snap


# -----------------------------------------------------------------
# STAGE 2 - ML CLASSIFICATION
# -----------------------------------------------------------------
def classify_with_ml(attack_name: str, snap: Dict[str, Any]) -> Tuple[str, float]:
    sep = "=" * 60
    print("\n" + sep)
    print("  STAGE 2 -- ML Classification (Gandhar's Model)")
    print(sep)
    print("  [~] Loading model files from: " + _MODEL_DIR)

    try:
        from decision_engine.events.workflow_tracker import tracker
        tracker.advance_stage(2, "ACTIVE", "Extracting 73 flow features...")
    except Exception:
        pass

    model         = joblib.load(MODEL_PATH)
    scaler        = joblib.load(SCALER_PATH)
    encoder       = joblib.load(ENCODER_PATH)
    feature_names = joblib.load(FEATURES_PATH)

    print("  [v] Model loaded (" + str(len(feature_names)) + " features, " + str(getattr(model, "n_estimators", 100)) + " trees)")

    csv_path = ATTACK_DATASETS.get(attack_name, "")
    row_found = False
    feature_df = None

    # 1. Try individual variant CSV first
    if csv_path and os.path.exists(csv_path):
        print("  [~] Sampling feature row from: " + os.path.basename(csv_path))
        df = pd.read_csv(csv_path)
        for col in ["Attack Name", "Label", "Multi_Label"]:
            if col in df.columns:
                df.drop(columns=[col], inplace=True)
        df.replace([float("inf"), float("-inf")], pd.NA, inplace=True)
        df.dropna(inplace=True)
        available  = [f for f in feature_names if f in df.columns]
        df         = df[available]
        if not df.empty:
            row        = df.sample(n=1, random_state=random.randint(0, 9999))
            feature_df = row[feature_names] if all(f in row.columns for f in feature_names) else row
            row_found  = True
            print("  [v] Feature vector: authentic " + attack_name + " signature from dataset")

    # 2. Try unified dataset if individual CSV not found
    if not row_found and os.path.exists(UNIFIED_DATASET_CSV):
        print("  [~] Sampling signature from unified dataset: " + os.path.basename(UNIFIED_DATASET_CSV))
        df = pd.read_csv(UNIFIED_DATASET_CSV)
        matched_rows = df[df["Attack Name"] == attack_name] if "Attack Name" in df.columns else pd.DataFrame()
        if not matched_rows.empty:
            row = matched_rows.sample(n=1, random_state=random.randint(0, 9999))
            feature_df = row[feature_names]
            row_found = True
            print("  [v] Feature vector: authentic " + attack_name + " signature extracted")

    # 3. Fallback zero-vector if neither is accessible
    if not row_found:
        print("  [!] Dataset CSV not found. Using zero-vector fallback...")
        vals       = {f: 0.0 for f in feature_names}
        feature_df = pd.DataFrame([vals])[feature_names]

    # Map measured flow telemetry into the 73-feature vector for the Random Forest model
    cfg = ATTACK_CONFIG.get(attack_name, {"dest_port": 80, "protocol": "TCP", "src_port": 11111})
    feature_df = feature_df.copy()
    if "Src Port" in feature_df.columns:
        feature_df["Src Port"] = float(cfg.get("src_port", 1024))
    if "Dst Port" in feature_df.columns:
        feature_df["Dst Port"] = float(cfg.get("dest_port", 80))
    if "Flow Duration" in feature_df.columns and snap.get("elapsed"):
        feature_df["Flow Duration"] = float(snap["elapsed"] * 1e6)
    if "Total Fwd Packet" in feature_df.columns and snap.get("attempts"):
        feature_df["Total Fwd Packet"] = float(snap["attempts"])
    if "Flow Packets/s" in feature_df.columns and snap.get("rate"):
        feature_df["Flow Packets/s"] = float(snap["rate"])

    print(f"  [v] Telemetry mapped to RF feature vector (Pkts: {snap['attempts']}, Rate: {snap['rate']:.1f} pps)")

    try:
        from decision_engine.events.workflow_tracker import tracker
        tracker.advance_stage(2, "ACTIVE", "Running 100-tree RF inference...")
    except Exception:
        pass

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

    try:
        from decision_engine.events.workflow_tracker import tracker
        tracker.advance_stage(2, "DONE", f"{confidence:.1f}% {pred_label}")
    except Exception:
        pass

    return pred_label, confidence


# -----------------------------------------------------------------
# STAGE 3 - DECISION ENGINE
# -----------------------------------------------------------------
def report_to_decision_engine(attack_name: str, pred_label: str, confidence: float, snap: Dict[str, Any]):
    sep = "=" * 60
    print("\n" + sep)
    print("  STAGE 3 -- Decision Engine (Arav's API)")
    print(sep)

    cfg = ATTACK_CONFIG.get(attack_name, {"dest_port": 80, "protocol": "TCP", "src_port": 11111})

    # Stage 3 in workflow tracker: Context & Asset Enrichment
    try:
        from decision_engine.events.workflow_tracker import tracker
        tracker.advance_stage(3, "ACTIVE", f"Enriching Asset {DEST_IP}...")
        time.sleep(0.3)
        tracker.advance_stage(3, "DONE", f"Asset {DEST_IP} (Crit: HIGH)")
        
        # Stage 4 in workflow tracker: Risk Assessment
        tracker.advance_stage(4, "ACTIVE", "Calculating Multi-Factor Risk...")
        time.sleep(0.2)
    except Exception:
        pass

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

    print("  [~] Sending prediction to Decision Engine (" + DECISION_ENGINE_URL + ")...")
    
    data = None
    try:
        resp = requests.post(DECISION_ENGINE_URL, json=payload, timeout=2.0)
        if resp.status_code == 200:
            data = resp.json()
        else:
            print("  [!] Decision Engine error: HTTP " + str(resp.status_code))
            print("      Response: " + resp.text)
    except requests.exceptions.RequestException:
        print("  [*] Note: Live HTTP API not reachable at " + DECISION_ENGINE_URL)
        print("      Evaluating in-process via DecisionManager...")
        try:
            from decision_engine.decision.decision_manager import DecisionManager
            dm = DecisionManager()
            decision = dm.process(payload)
            data = decision.model_dump() if hasattr(decision, "model_dump") else decision.dict()
        except Exception as err:
            print(f"  [!] Direct pipeline execution error: {err}")

    if data:
        analyst = data.get("analyst_required", False)
        w = 20
        print("\n  [v] Decision Engine responded!")
        print("  +--------------------------------------+")
        print("  |  Attack Type    : " + str(data.get("attack_type", "N/A")).ljust(w) + "|")
        print("  |  Risk Score     : " + str(data.get("risk_score", "N/A")).ljust(w) + "|")
        print("  |  Severity       : " + str(data.get("severity", "N/A")).ljust(w) + "|")
        print("  |  Priority       : " + str(data.get("priority", "N/A")).ljust(w) + "|")
        print("  |  Automation Lvl : " + str(data.get("automation_level", "N/A")).ljust(w) + "|")
        playbook_val = data.get("playbook") or data.get("playbook_id", "N/A")
        print("  |  Playbook       : " + str(playbook_val).ljust(w) + "|")
        print("  |  Status         : " + str(data.get("incident_status", "N/A")).ljust(w) + "|")
        print("  +--------------------------------------+")

        risk_val = float(data.get("risk_score", 85.0))
        sev_val = data.get("severity", "HIGH")
        pol_val = data.get("policy_id") or data.get("policy", "DOS-SYN-001")
        pb_val = data.get("playbook") or data.get("playbook_id", "PB-CONTAIN")
        dec_val = data.get("decision", "CONTAIN")
        acts = data.get("actions", ["BLOCK_IP", "RATE_LIMIT"])
        inc_id = data.get("incident_id", "INC-LIVE")

        try:
            from decision_engine.events.workflow_tracker import tracker
            tracker.advance_stage(4, "DONE", f"Risk: {risk_val:.1f} ({sev_val})")
            
            tracker.advance_stage(5, "ACTIVE", f"Matching Policy {pol_val}...")
            time.sleep(0.3)
            tracker.advance_stage(5, "DONE", f"{pol_val} (Priority: 10)")
            
            tracker.advance_stage(6, "ACTIVE", f"Executing Playbook {pb_val}...")
            time.sleep(0.3)
            tracker.advance_stage(6, "DONE", f"{pb_val}")
            
            tracker.advance_stage(7, "ACTIVE", "Deploying Firewall Mitigation...")
            time.sleep(0.3)
            
            tracker.complete_pipeline(
                incident_id=inc_id,
                risk_score=risk_val,
                severity=sev_val,
                decision=dec_val,
                policy_id=pol_val,
                playbook_id=pb_val,
                actions=acts,
                confidence=confidence,
                pred_label=pred_label
            )
        except Exception:
            pass

        if analyst:
            print("\n  [!] HUMAN ANALYST REQUIRED!")
            print("  Incident ID : " + str(data.get("incident_id", "N/A")))
            print("  Dashboard   : http://localhost:8501 (Tab 1: Incident Queue & Response)")
        else:
            print("\n  [✓] Action applied automatically (" + str(data.get("decision", "CONTAIN")) + ") -- no human intervention needed.")
            print("  Incident ID : " + str(data.get("incident_id", "N/A")))
            print("  Dashboard   : http://localhost:8501 (Visible in Live Incident Queue)")


# -----------------------------------------------------------------
# FULL PIPELINE
# -----------------------------------------------------------------
def run_simulation(attack_name: str):
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


def select_attack() -> str:
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
        if arg in ATTACK_CONFIG:
            run_simulation(arg)
        elif arg.upper() == "ALL":
            for v in ATTACK_VARIANTS:
                run_simulation(v)
                time.sleep(1.5)
        else:
            print("  [!] Unknown attack: " + arg)
            print("      Valid: " + ", ".join(ATTACK_VARIANTS) + ", ALL")
    else:
        choice = select_attack()
        if choice == "ALL":
            for v in ATTACK_VARIANTS:
                run_simulation(v)
                time.sleep(1.5)
        else:
            run_simulation(choice)
