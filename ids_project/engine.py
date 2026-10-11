"""Live IDS detection + decision engine.

Reads flows (either real cicflowmeter output, or replayed dataset rows),
classifies each with the trained model, logs attacks, and optionally blocks
the source IP with iptables.

  Demo (safe, works anywhere):   python engine.py --replay
  Live on the Ubuntu victim:     cicflowmeter -i <iface> -c live_flows.csv
                                 sudo python engine.py --live live_flows.csv --block

Events are appended as JSON lines to events.log, which dashboard.py serves.
"""
import argparse
import csv
import json
import os
import subprocess
import time
from datetime import datetime

import joblib
import pandas as pd

BENIGN = "Benign Traffic"
LOG_FILE = "events.log"

MODEL = joblib.load("model.pkl")
SCALER = joblib.load("scaler.pkl")
ENCODER = joblib.load("label_encoder.pkl")
FEATURES = joblib.load("feature_names.pkl")


def normkey(s):
    return "".join(ch for ch in str(s).lower() if ch.isalnum())


# cicflowmeter emits snake_case column names; the model was trained on the
# canonical CIC names. Map the ones that differ after normalisation; anything
# unmatched is filled with 0 and reported once so you can tune this.
# ponytail: version-dependent alias table — if live mode under-detects, diff
#           your cicflowmeter CSV header against FEATURES and extend this map.
ALIAS = {
    "totfwdpkts": "Total Fwd Packet",
    "totbwdpkts": "Total Bwd packets",
    "totlenfwdpkts": "Total Length of Fwd Packet",
    "totlenbwdpkts": "Total Length of Bwd Packet",
    "fwdpktlenmax": "Fwd Packet Length Max",
    "fwdpktlenmin": "Fwd Packet Length Min",
    "fwdpktlenmean": "Fwd Packet Length Mean",
    "fwdpktlenstd": "Fwd Packet Length Std",
    "bwdpktlenmax": "Bwd Packet Length Max",
    "bwdpktlenmin": "Bwd Packet Length Min",
    "bwdpktlenmean": "Bwd Packet Length Mean",
    "bwdpktlenstd": "Bwd Packet Length Std",
    "flowbytss": "Flow Bytes/s",
    "flowpktss": "Flow Packets/s",
    "fwdpktss": "Fwd Packets/s",
    "bwdpktss": "Bwd Packets/s",
    "fwdiattot": "Fwd IAT Total",
    "bwdiattot": "Bwd IAT Total",
    "fwdheaderlen": "Fwd Header Length",
    "bwdheaderlen": "Bwd Header Length",
    "pktlenmin": "Packet Length Min",
    "pktlenmax": "Packet Length Max",
    "pktlenmean": "Packet Length Mean",
    "pktlenstd": "Packet Length Std",
    "pktlenvar": "Packet Length Variance",
    "finflagcnt": "FIN Flag Count",
    "synflagcnt": "SYN Flag Count",
    "rstflagcnt": "RST Flag Count",
    "pshflagcnt": "PSH Flag Count",
    "ackflagcnt": "ACK Flag Count",
    "urgflagcnt": "URG Flag Count",
    "cweflagcount": "CWR Flag Count",
    "cwrflagcount": "CWR Flag Count",
    "eceflagcnt": "ECE Flag Count",
    "downupratio": "Down/Up Ratio",
    "pktsizeavg": "Average Packet Size",
    "fwdsegsizeavg": "Fwd Segment Size Avg",
    "bwdsegsizeavg": "Bwd Segment Size Avg",
    "bwdbytsbavg": "Bwd Bytes/Bulk Avg",
    "bwdpktsbavg": "Bwd Packet/Bulk Avg",
    "bwdblkrateavg": "Bwd Bulk Rate Avg",
    "subflowfwdpkts": "Subflow Fwd Packets",
    "subflowfwdbyts": "Subflow Fwd Bytes",
    "subflowbwdpkts": "Subflow Bwd Packets",
    "subflowbwdbyts": "Subflow Bwd Bytes",
    "initfwdwinbyts": "FWD Init Win Bytes",
    "initbwdwinbyts": "Bwd Init Win Bytes",
    "fwdactdatapkts": "Fwd Act Data Pkts",
    "fwdsegsizemin": "Fwd Seg Size Min",
    "fwdpshflags": "Fwd PSH Flags",
    "fwdurgflags": "Fwd URG Flags",
}

# normalised-source-name -> model feature
LOOKUP = {normkey(f): f for f in FEATURES}
LOOKUP.update({normkey(k): v for k, v in ALIAS.items()})

_reported_missing = False


def align(row):
    """Map an arbitrary flow dict onto the model's 73 features (missing -> 0)."""
    global _reported_missing
    out = {f: 0.0 for f in FEATURES}
    for col, val in row.items():
        feat = LOOKUP.get(normkey(col))
        if feat is None:
            continue
        try:
            out[feat] = float(val)
        except (TypeError, ValueError):
            out[feat] = 0.0
    if not _reported_missing:
        missing = [f for f in FEATURES if f not in {LOOKUP.get(normkey(c)) for c in row}]
        if missing:
            print(f"[align] {len(missing)}/{len(FEATURES)} features not in feed, "
                  f"filled with 0: {missing}")
        _reported_missing = True
    return out


def classify(row):
    aligned = align(row)
    X = pd.DataFrame([[aligned[f] for f in FEATURES]], columns=FEATURES)
    proba = MODEL.predict_proba(SCALER.transform(X))[0]
    i = int(proba.argmax())
    return ENCODER.classes_[i], float(proba[i])


def source_ip(row):
    for col, val in row.items():
        if normkey(col) in ("srcip", "sourceip"):
            return val
    return None


_blocked = set()


def block_ip(ip):
    if ip in _blocked:
        return True
    try:
        subprocess.run(["iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"],
                       check=True, capture_output=True)
        _blocked.add(ip)
        return True
    except Exception as e:  # not root / not linux / iptables missing
        print(f"[block] failed for {ip}: {e}")
        return False


def handle(row, block, min_conf):
    label, conf = classify(row)
    if label == BENIGN or conf < min_conf:
        return
    ip = source_ip(row)
    if block and ip:
        action = "blocked" if block_ip(ip) else "block-failed"
    else:
        action = "would-block"
    event = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "attack": label,
        "confidence": round(conf, 3),
        "src_ip": ip or "n/a",
        "action": action,
    }
    with open(LOG_FILE, "a") as fh:
        fh.write(json.dumps(event) + "\n")
    print(f"[ALERT] {event['time']}  {label:<22} conf={conf:.2f}  "
          f"src={event['src_ip']:<15} -> {action}")


def replay_rows(path, limit, delay):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    if limit:
        df = df.sample(n=min(limit, len(df)))
    else:
        df = df.sample(frac=1)
    for _, r in df.iterrows():
        yield r.to_dict()
        time.sleep(delay)


def tail_rows(path, poll=0.5):
    while not os.path.exists(path):
        print(f"[live] waiting for {path} ...")
        time.sleep(1)
    header = None
    with open(path) as fh:
        while True:
            line = fh.readline()
            if not line or not line.endswith("\n"):
                if line:
                    fh.seek(fh.tell() - len(line))  # partial line, rewind
                time.sleep(poll)
                continue
            row = next(csv.reader([line.rstrip("\n")]))
            if header is None:
                header = row
                continue
            yield dict(zip(header, row))


def main():
    p = argparse.ArgumentParser(description="IDS detection + decision engine")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--replay", nargs="?", const="dataset/relabeled_ids_dataset.csv",
                     help="replay rows from a dataset CSV (demo mode)")
    src.add_argument("--live", metavar="CSV",
                     help="tail a cicflowmeter CSV for live flows")
    p.add_argument("--block", action="store_true",
                   help="actually DROP attacker IPs via iptables (default: dry-run)")
    p.add_argument("--min-confidence", type=float, default=0.5,
                   help="ignore detections below this probability (default 0.5)")
    p.add_argument("--delay", type=float, default=0.3, help="replay delay per flow (s)")
    p.add_argument("--limit", type=int, default=200, help="replay row count (0 = all)")
    args = p.parse_args()

    if args.live:
        rows = tail_rows(args.live)
        mode = f"LIVE ({args.live})"
    else:
        rows = replay_rows(args.replay or "dataset/relabeled_ids_dataset.csv",
                           args.limit, args.delay)
        mode = "REPLAY"

    print(f"IDS engine started | mode={mode} | "
          f"block={'ON' if args.block else 'dry-run'} | log={LOG_FILE}")
    for row in rows:
        handle(row, args.block, args.min_confidence)


if __name__ == "__main__":
    main()
