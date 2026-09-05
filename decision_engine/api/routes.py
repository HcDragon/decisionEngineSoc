from fastapi import FastAPI, HTTPException, Body, Query, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from decision_engine.models.threat_event import ThreatEvent
from decision_engine.models.decision import SecurityDecision
from decision_engine.models.incident import IncidentRecord
from decision_engine.decision.decision_manager import DecisionManager
from decision_engine.storage.db import Database
from decision_engine.events.event_bus import EventBus
from decision_engine.api.streaming import sse_event_generator

app = FastAPI(
    title="Smart SOC Autonomous Decision Engine",
    description="Enterprise-grade SOAR Decision Engine for cyber threat orchestration and remediation.",
    version="3.0.0"
)

# Global Singletons
db = Database()
event_bus = EventBus()
decision_manager = DecisionManager(db=db, event_bus=event_bus)

# In-memory incident cache for backward compatibility
INCIDENTS_DB: Dict[str, Any] = {}

# Continuous Live Traffic Sensor State
SENSOR_STATE = {
    "active": True,
    "total_inferred": 0,
    "last_flow_time": None
}

def _sensor_background_worker():
    """Continuously consumes real network flows from IDSBridge and feeds them into Decision Engine."""
    try:
        import time as _time
        from decision_engine.integrations.ids_bridge import IDSBridge
        bridge = IDSBridge()
        if not bridge.is_ready:
            return
        for threat_event, meta in bridge.stream_continuous(delay_seconds=1.2):
            if not SENSOR_STATE.get("active", True):
                _time.sleep(0.8)
                continue
            try:
                decision_manager.process(threat_event)
                SENSOR_STATE["total_inferred"] = SENSOR_STATE.get("total_inferred", 0) + 1
                SENSOR_STATE["last_flow_time"] = datetime.now(timezone.utc).isoformat()
            except Exception:
                pass
    except Exception:
        pass

import os as _os
import threading as _threading
if _os.environ.get("PYTEST_CURRENT_TEST") is None and _os.environ.get("DISABLE_SENSOR") != "1":
    _sensor_thread = _threading.Thread(target=_sensor_background_worker, daemon=True)
    _sensor_thread.start()

@app.get("/", include_in_schema=False)
async def root():
    """Redirects root URL to interactive Swagger documentation."""
    return RedirectResponse(url="/docs")

@app.get("/api/v1/sensor/status")
async def get_sensor_status():
    """Returns the live status of the continuous network traffic sensor."""
    return SENSOR_STATE

@app.post("/api/v1/sensor/toggle")
async def toggle_sensor():
    """Pauses or resumes the continuous network traffic sensor."""
    SENSOR_STATE["active"] = not SENSOR_STATE.get("active", True)
    return SENSOR_STATE

@app.get("/api/v1/health")
async def health_check():
    """Service health status and active state telemetry."""
    active_mits = db.get_active_mitigations()
    return {
        "status": "HEALTHY",
        "service": "DecisionEngine",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "CONNECTED",
        "active_mitigations_count": len(active_mits),
        "active_mitigations": active_mits
    }

@app.post("/api/v1/decision/analyze", response_model=Dict[str, Any])
async def analyze_threat_event(payload: Dict[str, Any] = Body(...)):
    """
    Ingests a Threat Event from the upstream AI/ML Threat Detection Engine.
    Executes the 11-stage autonomous SOAR orchestration pipeline.
    """
    try:
        decision = decision_manager.process(payload)
        INCIDENTS_DB[decision.incident_id] = decision
        return decision.model_dump() if hasattr(decision, "model_dump") else decision.dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process threat event: {str(e)}")

@app.get("/api/v1/incidents")
async def get_incidents(
    state: Optional[str] = Query(None, description="Filter by state (e.g. DETECTED, CONTAINED, RESOLVED, ESCALATED)"),
    limit: int = Query(100, ge=1, le=500)
):
    """Retrieves all logged SOC incidents with optional state filtering."""
    return db.list_incidents(state=state, limit=limit)

@app.get("/api/v1/decision/incidents")
async def get_decision_incidents():
    """Backward compatibility endpoint returning in-memory or persisted incidents."""
    if INCIDENTS_DB:
        return [v.model_dump() if hasattr(v, "model_dump") else v for v in INCIDENTS_DB.values()]
    return db.list_incidents()

@app.get("/api/v1/incidents/{incident_id}")
async def get_incident_details(incident_id: str):
    """Retrieves a specific incident by ID along with its audit trail and decision."""
    inc = db.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found.")
    
    dec = db.get_decision(incident_id)
    audit_trail = db.get_audit_logs(incident_id=incident_id)
    verification = db.get_verification(incident_id)
    
    return {
        "incident": inc,
        "decision": dec,
        "audit_trail": audit_trail,
        "verification": verification
    }

@app.get("/api/v1/traffic")
async def get_recent_traffic(limit: int = Query(100, ge=1, le=500)):
    """Retrieves recent network traffic flow records from the ingestion sensor."""
    return db.list_threat_events(limit=limit)

@app.get("/api/v1/decisions/{incident_id}")
async def get_decision_by_incident(incident_id: str):
    """Retrieves the explainable security decision for a specific incident."""
    dec = db.get_decision(incident_id)
    if not dec:
        raise HTTPException(status_code=404, detail=f"Decision for incident {incident_id} not found.")
    return dec

@app.get("/api/v1/audit/{incident_id}")
async def get_audit_trail(incident_id: str):
    """Retrieves the complete forensic audit log trail for an incident."""
    return db.get_audit_logs(incident_id=incident_id)

@app.get("/api/v1/events")
async def get_recent_lifecycle_events(limit: int = Query(50, ge=1, le=200)):
    """Retrieves recent real-time lifecycle events from the internal event bus."""
    return event_bus.get_recent_events(limit=limit)

@app.get("/api/v1/events/stream")
async def stream_lifecycle_events(request: Request):
    """
    Server-Sent Events (SSE) live streaming endpoint.
    Streams real-time Decision Engine lifecycle events directly to the dashboard.
    """
    return StreamingResponse(
        sse_event_generator(request, event_bus),
        media_type="text/event-stream"
    )

@app.post("/api/v1/decision/approve")
async def approve_incident(payload: Dict[str, Any] = Body(...)):
    """
    Allows a human analyst to grant manual approval for pending incidents (Level 2/3).
    Resumes playbook mitigation execution.
    """
    incident_id = payload.get("incident_id")
    if not incident_id:
        raise HTTPException(status_code=400, detail="Missing required field 'incident_id'.")
        
    result = decision_manager.approve_incident(incident_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result["message"])
        
    if incident_id in INCIDENTS_DB:
        if hasattr(INCIDENTS_DB[incident_id], "incident_status"):
            INCIDENTS_DB[incident_id].incident_status = "MANUAL_MITIGATED"
        elif isinstance(INCIDENTS_DB[incident_id], dict):
            INCIDENTS_DB[incident_id]["incident_status"] = "MANUAL_MITIGATED"

    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
