from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from decision_engine.storage.db import Database
from decision_engine.audit.audit_logger import AuditLogger
from decision_engine.models.incident import IncidentState

class RecoveryManager:
    """
    Recovery and Escalation Manager.
    Maintains stateful mitigation records, checks expiration, reverts temporary mitigations,
    and escalates incidents when verification fails.
    """
    def __init__(self, db: Optional[Database] = None, audit_logger: Optional[AuditLogger] = None):
        self.db = db or Database()
        self.audit = audit_logger or AuditLogger()

    def process_expired_mitigations(self) -> List[Dict[str, Any]]:
        """
        Scans active mitigations in DB and marks expired ones as EXPIRED / ROLLED_BACK.
        """
        now = datetime.now(timezone.utc).isoformat()
        active = self.db.get_active_mitigations()
        expired = []

        for mit in active:
            expires_at = mit.get("expires_at")
            if expires_at and expires_at <= now:
                action_id = mit["action_id"]
                incident_id = mit["incident_id"]
                target = mit["target"]
                
                # Revert / expire mitigation state
                self.db.update_mitigation_status(action_id, "EXPIRED")
                
                # Check incident
                inc = self.db.get_incident(incident_id)
                if inc and inc.get("current_state") == IncidentState.CONTAINED.value:
                    inc["current_state"] = IncidentState.RESOLVED.value
                    inc["incident_status"] = "RESOLVED"
                    inc["recommended_action"] = "Mitigation window elapsed safely. Threat resolved."
                    self.db.save_incident(inc)

                self.audit.log(
                    event_type="MITIGATION_EXPIRED",
                    details=f"Temporary mitigation {action_id} on {target} expired safely. Incident marked RESOLVED.",
                    incident_id=incident_id,
                    action_id=action_id,
                    component="RECOVERY_MANAGER"
                )
                expired.append(mit)

        return expired

    def escalate_incident(self, incident_id: str, reason: str) -> Dict[str, Any]:
        """
        Escalates an incident when mitigation fails or persistent hostile traffic continues.
        """
        inc = self.db.get_incident(incident_id)
        if not inc:
            return {}

        inc["current_state"] = IncidentState.ESCALATED.value
        inc["incident_status"] = "ESCALATED"
        inc["severity"] = "CRITICAL"
        inc["analyst_required"] = True
        inc["recommended_action"] = f"ESCALATED: {reason}. Manual SOC Tier 2/3 intervention required immediately."
        inc["reasons"].append(f"Escalation triggered: {reason}")
        
        self.db.save_incident(inc)

        self.audit.log(
            event_type="INCIDENT_ESCALATED",
            details=f"Incident {incident_id} escalated to CRITICAL: {reason}",
            incident_id=incident_id,
            severity="CRITICAL",
            status="ESCALATED",
            component="RECOVERY_MANAGER"
        )

        return inc
