"""
Traffic Monitoring and Dashboard API Endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from soc.backend.app.db.session import get_db
from soc.backend.app.db.models import Incident, Alert, VirtualFirewall, Counter, IncidentStatus
from soc.backend.app.monitor.streamer import (
    traffic_monitor,
    FlowRecord,
    PortMonitorStats,
)
from soc.backend.app.config import settings

router = APIRouter(prefix="/api", tags=["Traffic & Dashboard"])


class ChangePortRequest(BaseModel):
    port: int = Field(..., ge=1, le=65535, description="Port number to monitor")


class StartMonitorRequest(BaseModel):
    port: Optional[int] = Field(None, ge=1, le=65535, description="Optional port number to monitor")


@router.get("/traffic/status", response_model=PortMonitorStats)
async def get_traffic_status():
    """Get real-time monitoring status and telemetry for the monitored port."""
    return traffic_monitor.get_status()


@router.post("/traffic/start")
async def start_traffic_monitor(payload: Optional[StartMonitorRequest] = None):
    """Start traffic monitoring on the target port."""
    target_port = payload.port if payload and payload.port else None
    traffic_monitor.start(port=target_port)
    return {
        "status": "started",
        "monitored_port": traffic_monitor.config.target_port,
        "engine_mode": traffic_monitor.engine_mode,
    }


@router.post("/traffic/stop")
async def stop_traffic_monitor():
    """Stop traffic monitoring."""
    traffic_monitor.stop()
    return {
        "status": "stopped",
        "monitored_port": traffic_monitor.config.target_port,
    }


@router.post("/traffic/port")
async def set_monitored_port(payload: ChangePortRequest):
    """Dynamically change the port being monitored by NFStream."""
    traffic_monitor.set_port(payload.port)
    return {
        "status": "port_updated",
        "monitored_port": payload.port,
        "is_running": traffic_monitor.is_running,
    }


@router.get("/traffic/flows", response_model=List[FlowRecord])
async def get_monitored_flows(
    limit: int = Query(50, ge=1, le=200),
    threat_only: bool = Query(False),
):
    """Retrieve the recent captured/metered flows for the active monitored port."""
    return traffic_monitor.get_flows(limit=limit, threat_only=threat_only)


@router.post("/traffic/clear")
async def clear_flow_buffer():
    """Flush the flow buffer."""
    traffic_monitor.clear()
    return {"status": "cleared"}


@router.get("/dashboard/overview")
async def get_dashboard_overview(db: Session = Depends(get_db)):
    """Aggregate high-level SOC system metrics for the dashboard."""
    # Count open incidents
    open_incidents = db.query(Incident).filter(Incident.status == IncidentStatus.OPEN).count()
    contained_incidents = db.query(Incident).filter(Incident.status == IncidentStatus.CONTAINED).count()
    total_alerts = db.query(Alert).count()
    
    # Active firewall blocks
    active_blocks = db.query(VirtualFirewall).filter(VirtualFirewall.active == True).count()

    traffic_stats = traffic_monitor.get_status()

    # Recent incidents
    recent_incidents = (
        db.query(Incident)
        .order_by(Incident.last_seen.desc())
        .limit(10)
        .all()
    )

    incidents_data = [
        {
            "id": inc.id,
            "src_ip": inc.key_src_ip,
            "family": inc.family,
            "max_risk": inc.max_risk,
            "alert_count": inc.alert_count,
            "status": inc.status.value,
            "last_seen": inc.last_seen.isoformat(),
        }
        for inc in recent_incidents
    ]

    return {
        "system": {
            "environment": settings.ENVIRONMENT,
            "automation_mode": settings.AUTOMATION_MODE,
            "executor": settings.SOC_EXECUTOR,
            "lab_mode": settings.SOC_LAB_MODE,
        },
        "stats": {
            "open_incidents": open_incidents,
            "contained_incidents": contained_incidents,
            "total_alerts": total_alerts,
            "active_blocks": active_blocks,
        },
        "traffic": traffic_stats.model_dump(),
        "recent_incidents": incidents_data,
    }
