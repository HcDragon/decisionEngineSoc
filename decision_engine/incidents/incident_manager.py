import uuid
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from decision_engine.models.threat_event import ThreatEvent
from decision_engine.models.incident import IncidentRecord, IncidentState
from decision_engine.storage.db import Database
from decision_engine.audit.audit_logger import AuditLogger
from decision_engine.events.event_bus import EventBus

class IncidentManager:
    """
    Incident Lifecycle and Deduplication Manager.
    Correlates recurring events within a sliding time window and tracks full lifecycle state transitions.
    """
    def __init__(
        self,
        correlation_window_seconds: int = 60,
        db: Optional[Database] = None,
        audit_logger: Optional[AuditLogger] = None,
        event_bus: Optional[EventBus] = None
    ):
        self.correlation_window = timedelta(seconds=correlation_window_seconds)
        self.db = db or Database()
        self.audit = audit_logger or AuditLogger()
        self.event_bus = event_bus or EventBus()

    def get_or_create_incident(self, event: ThreatEvent) -> Tuple[IncidentRecord, bool]:
        """
        Returns (IncidentRecord, is_new: bool).
        If an active incident for (source_ip, destination_ip) exists within the correlation window,
        it is updated and returned. Otherwise, a new incident is initialized.
        """
        existing = self.db.find_active_incident(event.source.ip, event.destination.ip)
        now = datetime.now(timezone.utc)

        if existing:
            updated_str = existing.get("updated_at") or existing.get("created_at")
            try:
                if "Z" in updated_str:
                    updated_str = updated_str.replace("Z", "+00:00")
                updated_dt = datetime.fromisoformat(updated_str)
                if updated_dt.tzinfo is None:
                    updated_dt = updated_dt.replace(tzinfo=timezone.utc)
                if abs((now - updated_dt).total_seconds()) <= self.correlation_window.total_seconds():
                    # Update existing incident
                    existing["event_count"] = existing.get("event_count", 1) + 1
                    existing["updated_at"] = now.isoformat()
                    existing["confidence"] = max(existing.get("confidence", 0.0), event.detection.confidence)
                    self.db.save_incident(existing)
                    
                    self.audit.log(
                        event_type="INCIDENT_CORRELATED",
                        details=f"Correlated recurring event {event.event_id} into existing active incident {existing['incident_id']} (Total events: {existing['event_count']})",
                        incident_id=existing["incident_id"],
                        event_id=event.event_id,
                        component="INCIDENT_MANAGER"
                    )
                    
                    if "current_state" in existing:
                        existing["current_state"] = str(existing["current_state"]).replace("IncidentState.", "")
                    inc_record = IncidentRecord(**existing)
                    return inc_record, False
            except Exception as ex:
                pass

        # Create new incident
        new_inc = IncidentRecord(
            incident_id=f"INC-{uuid.uuid4().hex[:8]}",
            event_id=event.event_id,
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            source_ip=event.source.ip,
            destination_ip=event.destination.ip,
            source_port=event.source.port,
            destination_port=event.destination.port,
            protocol=event.network.protocol,
            attack_type=event.detection.attack_type,
            confidence=event.detection.confidence,
            current_state=IncidentState.DETECTED,
            incident_status="LOGGED",
            event_count=1
        )
        self.db.save_incident(new_inc.model_dump() if hasattr(new_inc, "model_dump") else new_inc.dict())

        self.audit.log(
            event_type="INCIDENT_CREATED",
            details=f"Created new incident {new_inc.incident_id} for {new_inc.attack_type} ({event.source.ip} -> {event.destination.ip})",
            incident_id=new_inc.incident_id,
            event_id=event.event_id,
            component="INCIDENT_MANAGER"
        )

        return new_inc, True

    def transition_state(self, incident_id: str, new_state: IncidentState, reason: str) -> Optional[IncidentRecord]:
        inc_data = self.db.get_incident(incident_id)
        if not inc_data:
            return None

        old_state = inc_data.get("current_state", "UNKNOWN")
        inc_data["current_state"] = new_state.value
        inc_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Map to legacy status for dashboard backward compatibility
        if new_state in (IncidentState.CONTAINED, IncidentState.RESOLVED):
            inc_data["incident_status"] = "AUTO_MITIGATED" if not inc_data.get("analyst_required") else "MANUAL_MITIGATED"
            inc_data["is_mitigated"] = True
        elif new_state in (IncidentState.PENDING_APPROVAL, IncidentState.ESCALATED):
            inc_data["incident_status"] = "PENDING_APPROVAL"
        else:
            inc_data["incident_status"] = "LOGGED"

        inc_data["reasons"].append(f"State transition {old_state} -> {new_state.value}: {reason}")
        self.db.save_incident(inc_data)

        self.audit.log(
            event_type="INCIDENT_UPDATED",
            details=f"Transitioned {incident_id} state from {old_state} to {new_state.value}: {reason}",
            incident_id=incident_id,
            status=new_state.value,
            component="INCIDENT_MANAGER"
        )

        return IncidentRecord(**inc_data)
