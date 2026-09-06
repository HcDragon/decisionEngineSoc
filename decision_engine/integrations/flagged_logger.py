"""
NFStream Flagged Flow Logger
Structured logging for network flows flagged by the NFStream layer and classified
by the upstream Random Forest IDS model.
"""
import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from decision_engine.config.constants import now_ist_iso

logger = logging.getLogger("NFStreamFlaggedLogger")

class NFStreamFlaggedLogger:
    """
    Structured logger that writes suspicious/flagged NFStream flows
    to logs/nfstream_flagged.log with full 5-tuple and ML metadata.
    """
    def __init__(self, log_dir: Optional[str] = None):
        if log_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            log_dir = os.path.join(base_dir, "logs")
        
        self.log_dir = os.path.abspath(log_dir)
        os.makedirs(self.log_dir, exist_ok=True)
        self.flagged_log_file = os.path.join(self.log_dir, "nfstream_flagged.log")
        self.all_flows_log_file = os.path.join(self.log_dir, "nfstream_all_flows.log")

    def log_flagged_flow(
        self,
        flow_data: Dict[str, Any],
        predicted_attack: str,
        confidence: float,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Records a flagged threat flow to the log file and returns the structured record.
        """
        now = now_ist_iso()
        
        src_ip = flow_data.get("source_ip") or flow_data.get("Src IP") or "0.0.0.0"
        src_port = flow_data.get("source_port") or flow_data.get("Src Port") or 0
        dst_ip = flow_data.get("destination_ip") or flow_data.get("Dst IP") or "0.0.0.0"
        dst_port = flow_data.get("destination_port") or flow_data.get("Dst Port") or 0
        protocol = flow_data.get("protocol") or flow_data.get("Protocol") or "TCP"
        
        packet_count = flow_data.get("packet_count") or (float(flow_data.get("Total Fwd Packet", 0)) + float(flow_data.get("Total Bwd packets", 0)))
        bytes_count = flow_data.get("bytes") or (float(flow_data.get("Total Length of Fwd Packet", 0)) + float(flow_data.get("Total Length of Bwd Packet", 0)))
        duration = flow_data.get("flow_duration") or flow_data.get("Flow Duration", 0.0)

        if not reason:
            if "Flood" in predicted_attack:
                reason = f"High-volume anomalous traffic surge detected ({int(packet_count)} packets)"
            elif "Brute" in predicted_attack:
                reason = f"Rapid authentication attempts targeting port {dst_port}"
            elif "Spoofing" in predicted_attack or "ARP" in predicted_attack:
                reason = "Hardware-to-IP address spoofing signature"
            elif "Recon" in predicted_attack or "Scan" in predicted_attack:
                reason = f"Network probing activity across port {dst_port}"
            else:
                reason = f"Statistical flow anomaly matching {predicted_attack}"

        record = {
            "timestamp": now,
            "status": "FLAGGED_SUSPICIOUS",
            "detection": {
                "model": "RandomForestClassifier-IDS",
                "attack_type": predicted_attack,
                "confidence": round(float(confidence), 4),
                "confidence_percentage": f"{confidence * 100:.1f}%"
            },
            "network_tuple": {
                "source_ip": str(src_ip),
                "source_port": int(src_port),
                "destination_ip": str(dst_ip),
                "destination_port": int(dst_port),
                "protocol": str(protocol)
            },
            "telemetry": {
                "packet_count": int(packet_count),
                "bytes": int(bytes_count),
                "duration_seconds": round(float(duration), 4)
            },
            "triage_reason": reason,
            "pipeline_action": "FORWARDED_TO_DECISION_ENGINE"
        }

        try:
            with open(self.flagged_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.error("Failed to write to flagged log file: %s", e)

        return record

    def log_flow(
        self,
        flow_data: Dict[str, Any],
        predicted_attack: str,
        confidence: float
    ) -> Dict[str, Any]:
        """
        Logs any flow (Normal or Flagged) into nfstream_all_flows.log.
        If attack is non-benign, also records to nfstream_flagged.log.
        """
        is_suspicious = "Benign" not in predicted_attack
        record = {
            "timestamp": now_ist_iso(),
            "status": "FLAGGED_SUSPICIOUS" if is_suspicious else "NORMAL_BYPASS",
            "attack_type": predicted_attack,
            "confidence": round(float(confidence), 4),
            "flow": flow_data
        }
        
        try:
            with open(self.all_flows_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.error("Failed to write to all flows log: %s", e)

        if is_suspicious:
            return self.log_flagged_flow(flow_data, predicted_attack, confidence)
        return record

    def get_recent_flagged_logs(self, limit: int = 50) -> list:
        """Retrieves the most recent flagged logs."""
        if not os.path.exists(self.flagged_log_file):
            return []
        
        logs = []
        try:
            with open(self.flagged_log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            logs.append(json.loads(line))
                        except Exception:
                            pass
        except Exception as e:
            logger.error("Error reading flagged log file: %s", e)
            
        return logs[-limit:]
