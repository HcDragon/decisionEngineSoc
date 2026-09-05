from pydantic import BaseModel, Field, model_validator
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import uuid

class EndpointInfo(BaseModel):
    ip: str
    port: int = 0

class NetworkInfo(BaseModel):
    protocol: str = "TCP"
    packet_count: int = 0
    flow_duration: float = 0.0
    bytes: int = 0
    packets_per_second: float = 0.0

class DetectionInfo(BaseModel):
    model: str = "RandomForest"
    attack_type: str
    confidence: float
    confidence_level: str = "MEDIUM"

class SensorInfo(BaseModel):
    source: str = "NFStream"
    mode: str = "LIVE"

class ThreatEvent(BaseModel):
    """
    Standard Threat Event schema produced by the upstream Threat Detection Engine.
    Validates incoming events and provides backwards compatibility with legacy flat payloads.
    """
    event_id: str = Field(default_factory=lambda: f"EVT-{uuid.uuid4().hex[:12]}")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: EndpointInfo
    destination: EndpointInfo
    network: NetworkInfo
    detection: DetectionInfo
    sensor: SensorInfo = Field(default_factory=SensorInfo)

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
            
        # If legacy flat structure is provided, normalize to standard nested structure
        if "attack_type" in data and "detection" not in data:
            src_ip = data.get("src_ip") or data.get("source_ip") or "0.0.0.0"
            src_port = int(data.get("src_port") or data.get("source_port") or 0)
            dest_ip = data.get("dest_ip") or data.get("destination_ip") or "0.0.0.0"
            dest_port = int(data.get("dest_port") or data.get("destination_port") or 80)
            
            conf_val = float(data.get("confidence", 0.0))
            if conf_val > 1.0:
                conf_val = conf_val / 100.0
                
            conf_lvl = "HIGH" if conf_val >= 0.85 else ("MEDIUM" if conf_val >= 0.50 else "LOW")
            
            pkt_count = int(data.get("packet_count", 0))
            duration = float(data.get("flow_duration", 0.0))
            bytes_count = int(data.get("bytes", pkt_count * 64))
            pps = float(data.get("packets_per_second", (pkt_count / duration) if duration > 0 else pkt_count))

            normalized = {
                "event_id": data.get("event_id") or f"EVT-{uuid.uuid4().hex[:12]}",
                "timestamp": data.get("timestamp") or datetime.now(timezone.utc).isoformat(),
                "source": {"ip": src_ip, "port": src_port},
                "destination": {"ip": dest_ip, "port": dest_port},
                "network": {
                    "protocol": data.get("protocol", "TCP"),
                    "packet_count": pkt_count,
                    "flow_duration": duration,
                    "bytes": bytes_count,
                    "packets_per_second": pps
                },
                "detection": {
                    "model": data.get("model", "RandomForest"),
                    "attack_type": data.get("attack_type", "Unknown"),
                    "confidence": conf_val,
                    "confidence_level": conf_lvl
                },
                "sensor": {
                    "source": data.get("sensor_source", "NFStream"),
                    "mode": data.get("sensor_mode", "LIVE")
                }
            }
            return normalized
            
        # Ensure confidence is clamped/normalized 0.0 - 1.0 if nested
        if "detection" in data and isinstance(data["detection"], dict):
            conf = float(data["detection"].get("confidence", 0.0))
            if conf > 1.0:
                data["detection"]["confidence"] = conf / 100.0
        return data

    @property
    def src_ip(self) -> str:
        return self.source.ip

    @property
    def dest_ip(self) -> str:
        return self.destination.ip

    @property
    def attack_type(self) -> str:
        return self.detection.attack_type

    @property
    def confidence(self) -> float:
        return self.detection.confidence
