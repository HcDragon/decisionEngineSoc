from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class ObservedData(BaseModel):
    """Data directly observed in the live event stream."""
    source_ip: str
    destination_ip: str
    source_port: int
    destination_port: int
    protocol: str
    attack_type: str
    confidence: float
    packet_count: int
    flow_duration: float
    bytes: int
    packets_per_second: float

class DerivedData(BaseModel):
    """Data calculated or aggregated from event history and state."""
    repeated_detections_count: int = 1
    previous_incidents_count: int = 0
    concurrent_target_attacks: int = 0
    persistence_score: float = 0.0 # 0.0 to 100.0
    is_recurring_source: bool = False

class ConfiguredData(BaseModel):
    """Data loaded from authoritative configuration / environmental registries (CMDB, TIP)."""
    asset_criticality: Optional[int] = None # 0 - 100 scale, None if unassigned
    destination_role: Optional[str] = None   # e.g., "Web Gateway", "Core Database"
    threat_intel_score: Optional[int] = None # 0 - 100 scale, None if unknown
    threat_reputation_category: Optional[str] = None # "Known Malicious", "Suspicious", "Unknown"

class EnrichedContext(BaseModel):
    """
    Unified context model strictly segregating Observed, Derived, and Configured intelligence.
    """
    observed: ObservedData
    derived: DerivedData
    configured: ConfiguredData
