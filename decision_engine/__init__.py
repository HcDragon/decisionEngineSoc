"""
Smart SOC Autonomous Decision Engine Package.
Enterprise-grade SOAR Decision Engine for cyber threat orchestration, risk scoring, and remediation.
"""
from decision_engine.decision.decision_manager import DecisionManager
from decision_engine.models.threat_event import ThreatEvent
from decision_engine.models.decision import SecurityDecision, DecisionType, AutomationLevel
from decision_engine.models.incident import IncidentRecord, IncidentState
from decision_engine.actions.simulation_executor import SimulationExecutor, ActionExecutor
from decision_engine.storage.db import Database
from decision_engine.events.event_bus import EventBus
from decision_engine.audit.audit_logger import AuditLogger

__version__ = "3.0.0"

__all__ = [
    "DecisionManager",
    "ThreatEvent",
    "SecurityDecision",
    "DecisionType",
    "AutomationLevel",
    "IncidentRecord",
    "IncidentState",
    "SimulationExecutor",
    "ActionExecutor",
    "Database",
    "EventBus",
    "AuditLogger"
]
