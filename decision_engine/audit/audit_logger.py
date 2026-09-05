import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from decision_engine.storage.db import Database
from decision_engine.events.event_bus import EventBus

# Configure standard logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s")
logger = logging.getLogger("DecisionEngine.Audit")

class AuditLogger:
    """
    Central structured audit logger that records forensic decision trails to SQLite and emits to EventBus.
    """
    def __init__(self, db: Optional[Database] = None, event_bus: Optional[EventBus] = None):
        self.db = db or Database()
        self.event_bus = event_bus or EventBus()

    def log(
        self,
        event_type: str,
        details: str,
        incident_id: Optional[str] = None,
        event_id: Optional[str] = None,
        action_id: Optional[str] = None,
        component: str = "DECISION_ENGINE",
        severity: str = "INFO",
        status: str = "SUCCESS",
        metadata: Optional[Dict[str, Any]] = None
    ):
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Structured log record
        entry = {
            "timestamp": timestamp,
            "incident_id": incident_id,
            "event_id": event_id,
            "action_id": action_id,
            "component": component,
            "event_type": event_type,
            "severity": severity,
            "status": status,
            "details": details,
            "metadata": metadata or {}
        }
        
        # 1. Output to structured python logger
        msg = f"[{component}] [{event_type}] inc={incident_id} evt={event_id}: {details}"
        if severity.upper() == "CRITICAL" or severity.upper() == "ERROR":
            logger.error(msg)
        elif severity.upper() == "WARNING" or severity.upper() == "HIGH":
            logger.warning(msg)
        else:
            logger.info(msg)

        # 2. Persist to DB
        try:
            self.db.add_audit_log(entry)
        except Exception as e:
            logger.error(f"Failed to persist audit log to DB: {e}")

        # 3. Publish to EventBus
        try:
            self.event_bus.publish(event_type, entry)
        except Exception as e:
            logger.error(f"Failed to broadcast audit event to EventBus: {e}")

    def get_trail(self, incident_id: str) -> list:
        return self.db.get_audit_logs(incident_id=incident_id)
