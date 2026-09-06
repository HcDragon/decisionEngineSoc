from typing import Optional, Dict, Any
from decision_engine.models.threat_event import ThreatEvent
from decision_engine.models.context import EnrichedContext, ObservedData, DerivedData, ConfiguredData
from decision_engine.storage.db import Database
from decision_engine.audit.audit_logger import AuditLogger

from decision_engine.context.registries import ASSET_REGISTRY, THREAT_INTEL_REGISTRY

class ContextEnricher:
    """
    Context Enrichment Layer.
    Combines incoming ThreatEvent with environmental telemetry and authoritative registries.
    Strictly separates Observed, Derived, and Configured data without fabricating unknown fields.
    """
    def __init__(self, db: Optional[Database] = None, audit_logger: Optional[AuditLogger] = None):
        self.db = db or Database()
        self.audit = audit_logger or AuditLogger()
        
        # Configured Registries (Authoritative CMDB & TIP integrations)
        self.asset_registry = dict(ASSET_REGISTRY)
        self.threat_intel_registry = dict(THREAT_INTEL_REGISTRY)

    def enrich(self, event: ThreatEvent) -> EnrichedContext:
        # 1. Extract Observed Data
        observed = ObservedData(
            source_ip=event.source.ip,
            destination_ip=event.destination.ip,
            source_port=event.source.port,
            destination_port=event.destination.port,
            protocol=event.network.protocol,
            attack_type=event.detection.attack_type,
            confidence=event.detection.confidence,
            packet_count=event.network.packet_count,
            flow_duration=event.network.flow_duration,
            bytes=event.network.bytes,
            packets_per_second=event.network.packets_per_second
        )

        # 2. Calculate Derived Data from Persistent History
        existing_inc = self.db.find_active_incident(event.source.ip, event.destination.ip)
        repeated_count = (existing_inc["event_count"] + 1) if existing_inc else 1
        
        # Check historical incidents involving this source IP
        historical_incidents = self.db.count_incidents_by_source_ip(event.source.ip)
        
        persistence = min(100.0, repeated_count * 20.0)
        is_recurring = repeated_count > 1 or historical_incidents > 0

        derived = DerivedData(
            repeated_detections_count=repeated_count,
            previous_incidents_count=historical_incidents,
            concurrent_target_attacks=0,
            persistence_score=persistence,
            is_recurring_source=is_recurring
        )

        # 3. Lookup Configured Data
        asset_info = self.asset_registry.get(event.destination.ip)
        asset_crit = asset_info["criticality"] if asset_info else None
        dest_role = asset_info["role"] if asset_info else None

        ti_info = self.threat_intel_registry.get(event.source.ip)
        ti_score = ti_info["score"] if ti_info else None
        ti_category = ti_info["category"] if ti_info else None

        configured = ConfiguredData(
            asset_criticality=asset_crit,
            destination_role=dest_role,
            threat_intel_score=ti_score,
            threat_reputation_category=ti_category
        )

        enriched = EnrichedContext(
            observed=observed,
            derived=derived,
            configured=configured
        )

        self.audit.log(
            event_type="CONTEXT_ENRICHED",
            details=f"Enriched context for {event.source.ip} -> {event.destination.ip} (AssetCrit: {asset_crit}, Rep: {ti_score})",
            event_id=event.event_id,
            component="CONTEXT_ENRICHER"
        )

        return enriched
