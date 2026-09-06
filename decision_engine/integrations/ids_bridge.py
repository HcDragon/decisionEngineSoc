import os
import glob
import time
import random
import logging
from typing import Dict, Any, List, Optional, Tuple, Generator, Union
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import joblib

from decision_engine.models.threat_event import ThreatEvent
from decision_engine.ml.detector import ThreatDetector

logger = logging.getLogger("IDSBridge")

from decision_engine.context.registries import MONITORED_ASSETS, PERSISTENT_ATTACKER_IPS, PERSISTENT_TARGET_MAP
from decision_engine.config.constants import get_confidence_level, now_ist_iso

# External IP subnets to synthesize realistic threat actors
EXTERNAL_ATTACKER_SUBNETS = [
    "198.51.100.",  # TEST-NET-2
    "203.0.113.",   # TEST-NET-3
    "192.0.2.",     # TEST-NET-1
    "45.33.32.",
    "185.220.101.",
    "162.243.128."
]

class IDSBridge:
    """
    Bridge connecting the upstream AI/ML Intrusion Detection System (IDS)
    to the Smart SOC Decision Engine.
    
    Consumes network flow telemetry, runs inference via the integrated
    ThreatDetector, and normalizes detections into strongly-typed ThreatEvent instances.
    """
    def __init__(self, ids_project_dir: Optional[str] = None):
        self.detector = ThreatDetector(artifacts_dir=ids_project_dir)
        self.project_dir = self.detector.artifacts_dir
        self.model_path = self.detector.model_path
        self.encoder_path = self.detector.encoder_path
        self.scaler_path = self.detector.scaler_path
        self.features_path = self.detector.features_path
        self.dataset_dir = self.detector.dataset_dir
        self._cached_df = None

    @property
    def model(self):
        return self.detector.model

    @model.setter
    def model(self, value):
        self.detector.model = value

    @property
    def encoder(self):
        return self.detector.encoder

    @encoder.setter
    def encoder(self, value):
        self.detector.encoder = value

    @property
    def scaler(self):
        return self.detector.scaler

    @scaler.setter
    def scaler(self, value):
        self.detector.scaler = value

    @property
    def feature_names(self):
        return self.detector.feature_names

    @feature_names.setter
    def feature_names(self, value):
        self.detector.feature_names = value

    def load_artifacts(self) -> bool:
        """Loads model weights, scaler, encoder, and feature names via ThreatDetector."""
        return self.detector.load_artifacts()

    @property
    def is_ready(self) -> bool:
        """Returns True if the ML model and all required transformers are loaded."""
        return self.detector.is_ready

    def predict_flow(self, flow_data: Union[pd.Series, Dict[str, Any]]) -> Tuple[str, float, Optional[str]]:
        """
        Runs ML inference on a network flow using the native ThreatDetector.
        
        Returns:
            (predicted_attack_type, confidence_score, actual_label_if_available)
        """
        actual_label = None
        if isinstance(flow_data, pd.Series):
            actual_label = flow_data.get("Attack Name") or flow_data.get("Label")
        elif isinstance(flow_data, dict):
            actual_label = flow_data.get("Attack Name") or flow_data.get("Label")

        predicted_attack, confidence, _ = self.detector.predict_flow(flow_data)
        return predicted_attack, confidence, actual_label

    def flow_to_threat_event(
        self,
        flow_data: Union[pd.Series, Dict[str, Any]],
        predicted_attack: Optional[str] = None,
        confidence: Optional[float] = None,
        source_ip: Optional[str] = None,
        destination_ip: Optional[str] = None
    ) -> ThreatEvent:
        """
        Transforms raw network flow metrics and IDS ML predictions into a standardized ThreatEvent.
        """
        if isinstance(flow_data, pd.Series):
            data = flow_data.to_dict()
        else:
            data = dict(flow_data)

        # Run inference if not already provided
        if predicted_attack is None or confidence is None:
            if self.is_ready:
                predicted_attack, confidence, _ = self.predict_flow(data)
            else:
                predicted_attack = data.get("Attack Name", "Unknown")
                confidence = 0.95

        # Extract network flow telemetry
        src_port = int(data.get("Src Port") or data.get("Source Port") or random.randint(30000, 65000))
        dst_port = int(data.get("Dst Port") or data.get("Destination Port") or 80)
        
        # Protocol mapping (6 -> TCP, 17 -> UDP, 1 -> ICMP)
        raw_proto = str(data.get("Protocol", "6")).strip()
        if raw_proto in ("6", "6.0", "TCP"):
            proto_name = "TCP"
        elif raw_proto in ("17", "17.0", "UDP"):
            proto_name = "UDP"
        elif raw_proto in ("1", "1.0", "ICMP"):
            proto_name = "ICMP"
        else:
            proto_name = "TCP"

        fwd_pkts = float(data.get("Total Fwd Packet", 10))
        bwd_pkts = float(data.get("Total Bwd packets", 5))
        total_packets = int(fwd_pkts + bwd_pkts)
        
        duration_us = float(data.get("Flow Duration", 1000000.0))
        # Flow duration in CICIDS is usually microseconds
        duration_sec = duration_us / 1_000_000.0 if duration_us > 10000 else (duration_us if duration_us > 0 else 1.0)
        
        fwd_bytes = float(data.get("Total Length of Fwd Packet", fwd_pkts * 64))
        bwd_bytes = float(data.get("Total Length of Bwd Packet", bwd_pkts * 64))
        total_bytes = int(fwd_bytes + bwd_bytes)
        
        pps_val = float(data.get("Flow Packets/s", (total_packets / duration_sec) if duration_sec > 0 else total_packets))

        # Assign source and destination IPs
        if not source_ip:
            if predicted_attack == "Benign Traffic":
                source_ip = f"10.0.1.{random.randint(10, 200)}"
            else:
                persistent_pool = PERSISTENT_ATTACKER_IPS.get(predicted_attack, PERSISTENT_ATTACKER_IPS.get("default", []))
                # 70% probability reuse persistent attacker IP to exercise correlation, 30% random
                if persistent_pool and random.random() < 0.70:
                    source_ip = random.choice(persistent_pool)
                else:
                    subnet = random.choice(EXTERNAL_ATTACKER_SUBNETS)
                    source_ip = f"{subnet}{random.randint(1, 254)}"

        if not destination_ip:
            if source_ip in PERSISTENT_TARGET_MAP:
                destination_ip = PERSISTENT_TARGET_MAP[source_ip]
                target_asset = next((a for a in MONITORED_ASSETS if a["ip"] == destination_ip), None)
            else:
                target_asset = random.choice(MONITORED_ASSETS)
                destination_ip = target_asset["ip"]
            if target_asset and dst_port in (0, 80, 8080):
                dst_port = random.choice(target_asset["ports"])

        conf_level = get_confidence_level(confidence)

        payload = {
            "timestamp": now_ist_iso(),
            "source": {
                "ip": source_ip,
                "port": src_port
            },
            "destination": {
                "ip": destination_ip,
                "port": dst_port
            },
            "network": {
                "protocol": proto_name,
                "packet_count": max(1, total_packets),
                "flow_duration": round(duration_sec, 4),
                "bytes": max(64, total_bytes),
                "packets_per_second": round(pps_val, 2)
            },
            "detection": {
                "model": "RandomForestClassifier-IDS",
                "attack_type": predicted_attack,
                "confidence": round(float(confidence), 4),
                "confidence_level": conf_level
            },
            "sensor": {
                "source": "CICIDS2017-NFStream-IDS",
                "mode": "LIVE"
            }
        }

        return ThreatEvent(**payload)

    def load_dataset_samples(self, n_per_class: int = 5, force_reload: bool = False) -> pd.DataFrame:
        """
        Loads cached flow samples from the dataset for simulation and live testing.
        Samples evenly across attack types.
        """
        if self._cached_df is not None and not force_reload and len(self._cached_df) >= (n_per_class * 8):
            return self._cached_df

        csv_files = glob.glob(os.path.join(self.dataset_dir, "*.csv"))
        if not csv_files:
            raise FileNotFoundError(f"No dataset CSV files found in {self.dataset_dir}")

        dfs = []
        for csv_path in csv_files:
            df = pd.read_csv(csv_path)
            df.columns = df.columns.str.strip()
            label_col = next((c for c in ["Multi_Label", "Attack Name", "Label"] if c in df.columns), None)
            if label_col:
                samples = [g.sample(min(len(g), n_per_class), random_state=42) for _, g in df.groupby(label_col)]
                dfs.append(pd.concat(samples, ignore_index=True))
            else:
                dfs.append(df.head(50))

        combined = pd.concat(dfs, ignore_index=True).sample(frac=1, random_state=42).reset_index(drop=True)
        self._cached_df = combined
        return combined

    def stream_dataset(
        self,
        n_samples: int = 10,
        delay_seconds: float = 0.5,
        attack_type_filter: Optional[str] = None
    ) -> Generator[Tuple[ThreatEvent, Dict[str, Any]], None, None]:
        """
        Yields (ThreatEvent, flow_metadata) tuples sampled from the real IDS dataset.
        """
        df = self.load_dataset_samples(n_per_class=max(10, (n_samples // 4) + 1))
        if attack_type_filter and "Attack Name" in df.columns:
            df = df[df["Attack Name"] == attack_type_filter]

        if len(df) < n_samples:
            sample_rows = df.sample(n=n_samples, replace=True)
        else:
            sample_rows = df.head(n_samples)
        for idx, row in sample_rows.iterrows():
            pred, conf, actual = self.predict_flow(row)
            threat_event = self.flow_to_threat_event(row, predicted_attack=pred, confidence=conf)
            meta = {
                "row_index": idx,
                "predicted": pred,
                "confidence": conf,
                "actual": actual,
                "match": (pred == actual) if actual else None
            }
            yield threat_event, meta
            if delay_seconds > 0:
                time.sleep(delay_seconds)

    def stream_continuous(
        self,
        delay_seconds: float = 1.2,
        attack_type_filter: Optional[str] = None
    ) -> Generator[Tuple[ThreatEvent, Dict[str, Any]], None, None]:
        """
        Continuously yields (ThreatEvent, flow_metadata) tuples sampled from the real IDS dataset in an infinite loop.
        """
        df = self.load_dataset_samples(n_per_class=25)
        if attack_type_filter and "Attack Name" in df.columns:
            filtered = df[df["Attack Name"] == attack_type_filter]
            if not filtered.empty:
                df = filtered

        while True:
            shuffled = df.sample(frac=1).reset_index(drop=True)
            for idx, row in shuffled.iterrows():
                pred, conf, actual = self.predict_flow(row)
                threat_event = self.flow_to_threat_event(row, predicted_attack=pred, confidence=conf)
                meta = {
                    "row_index": idx,
                    "predicted": pred,
                    "confidence": conf,
                    "actual": actual,
                    "match": (pred == actual) if actual else None
                }
                yield threat_event, meta
                if delay_seconds > 0:
                    time.sleep(delay_seconds)
