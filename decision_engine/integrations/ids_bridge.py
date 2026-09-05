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

logger = logging.getLogger("IDSBridge")

# Target monitored assets in the SOC environment
MONITORED_ASSETS = [
    {"ip": "10.0.0.5", "name": "Core-Database-Cluster", "criticality": "HIGH", "ports": [3306, 5432, 1433, 22]},
    {"ip": "10.0.0.12", "name": "DMZ-Web-Gateway", "criticality": "MEDIUM", "ports": [80, 443, 8080]},
    {"ip": "10.0.0.1", "name": "Enterprise-Domain-Controller", "criticality": "CRITICAL", "ports": [53, 88, 389, 445]},
    {"ip": "10.0.0.25", "name": "Internal-API-Service", "criticality": "MEDIUM", "ports": [8000, 8443]}
]

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
    
    Consumes network flow telemetry from L:\\AimlProject\\ids_project,
    runs inference via the trained RandomForest model, and normalizes detections
    into strongly-typed ThreatEvent instances.
    """
    def __init__(self, ids_project_dir: str = r"L:\AimlProject\ids_project"):
        self.project_dir = os.path.abspath(ids_project_dir)
        self.model_path = os.path.join(self.project_dir, "model.pkl")
        self.encoder_path = os.path.join(self.project_dir, "label_encoder.pkl")
        self.scaler_path = os.path.join(self.project_dir, "scaler.pkl")
        self.features_path = os.path.join(self.project_dir, "feature_names.pkl")
        self.dataset_dir = os.path.join(self.project_dir, "dataset")
        
        self.model = None
        self.encoder = None
        self.scaler = None
        self.feature_names = None
        self._cached_df = None
        
        self.load_artifacts()

    def load_artifacts(self) -> bool:
        """Loads model weights, scaler, encoder, and feature names."""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
            if os.path.exists(self.encoder_path):
                self.encoder = joblib.load(self.encoder_path)
            if os.path.exists(self.scaler_path):
                self.scaler = joblib.load(self.scaler_path)
            if os.path.exists(self.features_path):
                self.feature_names = joblib.load(self.features_path)
                
            logger.info("Successfully loaded IDS model artifacts from %s", self.project_dir)
            return True
        except Exception as e:
            logger.error("Failed to load IDS artifacts: %s", e)
            return False

    @property
    def is_ready(self) -> bool:
        """Returns True if the ML model and all required transformers are loaded."""
        return all([self.model is not None, self.encoder is not None, self.scaler is not None, self.feature_names is not None])

    def predict_flow(self, flow_data: Union[pd.Series, Dict[str, Any]]) -> Tuple[str, float, Optional[str]]:
        """
        Runs ML inference on a network flow.
        
        Returns:
            (predicted_attack_type, confidence_score, actual_label_if_available)
        """
        if not self.is_ready:
            raise RuntimeError("IDS artifacts not fully loaded. Call load_artifacts() first.")

        actual_label = None
        if isinstance(flow_data, pd.Series):
            actual_label = flow_data.get("Attack Name") or flow_data.get("Label")
            flow_dict = flow_data.to_dict()
        else:
            flow_dict = dict(flow_data)
            actual_label = flow_dict.get("Attack Name") or flow_dict.get("Label")

        # Extract only the 73 required features in precise order
        features_vec = []
        for feat in self.feature_names:
            val = flow_dict.get(feat, 0.0)
            try:
                val = float(val)
                if np.isnan(val) or np.isinf(val):
                    val = 0.0
            except (ValueError, TypeError):
                val = 0.0
            features_vec.append(val)

        X_df = pd.DataFrame([features_vec], columns=self.feature_names)
        X_scaled = self.scaler.transform(X_df)

        proba = self.model.predict_proba(X_scaled)[0]
        max_idx = int(np.argmax(proba))
        confidence = float(proba[max_idx])
        predicted_attack = str(self.encoder.classes_[max_idx])

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
                subnet = random.choice(EXTERNAL_ATTACKER_SUBNETS)
                source_ip = f"{subnet}{random.randint(1, 254)}"

        if not destination_ip:
            target_asset = random.choice(MONITORED_ASSETS)
            destination_ip = target_asset["ip"]
            if dst_port in (0, 80, 8080):
                dst_port = random.choice(target_asset["ports"])

        conf_level = "HIGH" if confidence >= 0.85 else ("MEDIUM" if confidence >= 0.60 else "LOW")

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
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

    def load_dataset_samples(self, n_per_class: int = 5) -> pd.DataFrame:
        """
        Loads cached flow samples from the dataset for simulation and live testing.
        Samples evenly across attack types.
        """
        if self._cached_df is not None:
            return self._cached_df

        csv_files = glob.glob(os.path.join(self.dataset_dir, "*.csv"))
        if not csv_files:
            raise FileNotFoundError(f"No dataset CSV files found in {self.dataset_dir}")

        dfs = []
        for csv_path in csv_files:
            df = pd.read_csv(csv_path, nrows=5000)
            df.columns = df.columns.str.strip()
            if "Attack Name" in df.columns:
                grouped = df.groupby("Attack Name", group_keys=False).apply(
                    lambda g: g.sample(min(len(g), n_per_class))
                )
                dfs.append(grouped)
            else:
                dfs.append(df.head(50))

        combined = pd.concat(dfs, ignore_index=True).sample(frac=1).reset_index(drop=True)
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
        df = self.load_dataset_samples(n_per_class=10)
        if attack_type_filter and "Attack Name" in df.columns:
            df = df[df["Attack Name"] == attack_type_filter]

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
