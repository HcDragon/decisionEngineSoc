import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from decision_engine.models.action import ActionResult, ActionStatus, ExecutionMode, ActiveMitigationState
from decision_engine.actions.adapters.base import BaseActionAdapter
from decision_engine.actions.adapters.simulation_adapter import SimulationAdapter
from decision_engine.storage.db import Database
from decision_engine.audit.audit_logger import AuditLogger
from decision_engine.events.event_bus import EventBus

class SOARActionExecutor:
    """
    Central SOAR Action Executor.
    Enforces automation levels, delegates to registered adapters, records audit events,
    and maintains stateful mitigation tracking with expiration windows.
    """
    def __init__(
        self,
        adapter: Optional[BaseActionAdapter] = None,
        db: Optional[Database] = None,
        audit_logger: Optional[AuditLogger] = None,
        event_bus: Optional[EventBus] = None
    ):
        self.adapter = adapter or SimulationAdapter()
        self.db = db or Database()
        self.audit = audit_logger or AuditLogger()
        self.event_bus = event_bus or EventBus()

    def execute_step(
        self,
        action: str,
        target: str,
        automation_level: int,
        parameters: Optional[Dict[str, Any]] = None,
        incident_id: Optional[str] = None,
        approved: bool = False
    ) -> ActionResult:
        parameters = parameters or {}
        is_containment_action = action in (
            "BLOCK_IP_SIMULATION", "RATE_LIMIT_SIMULATION",
            "ICMP_FILTER_SIMULATION", "RESET_CREDENTIALS_SIMULATION",
            "ISOLATE_HOST_SIMULATION"
        )

        # 1. Enforce Automation Level Constraints
        if is_containment_action:
            if automation_level < 2:
                # Level 0 & 1 cannot execute containment
                return ActionResult(
                    action=action,
                    target=target,
                    status=ActionStatus.SKIPPED,
                    mode=ExecutionMode.SIMULATION,
                    message=f"Action '{action}' skipped. Policy automation level {automation_level} permits monitoring/logging only."
                )
            elif automation_level in (2, 3) and not approved:
                # Level 2 & 3 require analyst confirmation
                return ActionResult(
                    action=action,
                    target=target,
                    status=ActionStatus.WAITING_APPROVAL,
                    mode=ExecutionMode.SIMULATION,
                    message=f"Action '{action}' pending manual analyst approval (Level {automation_level})."
                )

        # 2. Dispatch to Adapter
        self.audit.log(
            event_type="ACTION_STARTED",
            details=f"Starting action '{action}' on target {target} (AutoLevel: {automation_level})",
            incident_id=incident_id,
            action_id=action,
            component="ACTION_EXECUTOR"
        )

        result: ActionResult = self.adapter.execute_action(
            action=action,
            target=target,
            parameters=parameters,
            incident_id=incident_id
        )

        # 3. Persist Action Record
        self.db.save_action_result({
            "execution_id": result.execution_id,
            "incident_id": incident_id or "",
            "action": result.action,
            "target": result.target,
            "status": result.status.value,
            "mode": result.mode.value,
            "message": result.message,
            "timestamp": result.timestamp,
            "details": result.details
        })

        # 4. If action creates a temporary mitigation, track state and expiration
        if result.status == ActionStatus.SUCCESS and is_containment_action:
            duration_secs = parameters.get("duration_seconds", 300)
            now = datetime.now(timezone.utc)
            expires_at = (now + timedelta(seconds=duration_secs)).isoformat()
            
            mit_record = {
                "action_id": result.execution_id,
                "incident_id": incident_id or "",
                "action_type": action,
                "target": target,
                "status": "ACTIVE",
                "created_at": now.isoformat(),
                "expires_at": expires_at,
                "verification_required": True
            }
            self.db.save_active_mitigation(mit_record)

        self.audit.log(
            event_type="ACTION_COMPLETED",
            details=f"Completed action '{action}' with status: {result.status.value}",
            incident_id=incident_id,
            action_id=result.execution_id,
            status=result.status.value,
            component="ACTION_EXECUTOR"
        )

        return result
