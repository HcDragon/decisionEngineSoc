import xgboost as xgb
import joblib
import pandas as pd
import os
from typing import Tuple

class TrafficPredictor:
    def __init__(self, model_path: str = "xgboost_model.pkl", encoder_path: str = "label_encoder.pkl"):
        self.model_path = model_path
        self.encoder_path = encoder_path
        self.model = None
        self.le = None
        self._load_model()
        
        # Simple protocol mapper to ensure consistency with training
        self.protocol_map = {"TCP": 0, "UDP": 1, "ICMP": 2}

    def _load_model(self):
        if os.path.exists(self.model_path) and os.path.exists(self.encoder_path):
            self.model = joblib.load(self.model_path)
            self.le = joblib.load(self.encoder_path)
            print("Loaded XGBoost model and Label Encoder successfully.")
        else:
            print("Warning: ML model files not found. Using fallback heuristics.")

    def predict(self, src_port: int, dest_port: int, protocol_str: str, packet_count: int, flow_duration: float) -> Tuple[str, float]:
        """
        Returns (predicted_attack_type, confidence_score)
        """
        if self.model is None or self.le is None:
            # Fallback mock heuristic if model isn't trained yet
            return self._heuristic_fallback(dest_port, protocol_str, packet_count)
            
        protocol_encoded = self.protocol_map.get(protocol_str.upper(), 0)
        
        # Format input exactly as training
        input_data = pd.DataFrame([{
            'src_port': src_port,
            'dest_port': dest_port,
            'protocol': protocol_encoded,
            'packet_count': packet_count,
            'flow_duration': flow_duration
        }])
        
        # Inference
        probs = self.model.predict_proba(input_data)[0]
        pred_idx = probs.argmax()
        confidence = float(probs[pred_idx])
        attack_type = self.le.inverse_transform([pred_idx])[0]
        
        return attack_type, confidence

    def _heuristic_fallback(self, dest_port: int, protocol: str, packets: int) -> Tuple[str, float]:
        """Fallback if no model is loaded."""
        if packets > 10000 and protocol.upper() == "TCP":
            return "DoS SYN Flood", 0.95
        elif packets > 10000 and protocol.upper() == "UDP":
            return "DoS UDP Flood", 0.90
        elif dest_port == 22 and packets > 100:
            return "Dictionary Brute Force", 0.85
        elif packets > 10000 and protocol.upper() == "ICMP":
            return "DoS ICMP Flood", 0.92
        elif dest_port == 53 and packets > 5000:
            return "DoS DNS Flood", 0.88
        return "Benign Traffic", 0.99
