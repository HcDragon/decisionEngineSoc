from typing import Dict, Any, Optional
from datetime import datetime, timezone
import uuid
from decision_engine.actions.adapters.base import BaseActionAdapter
from decision_engine.models.action import ActionResult, ActionStatus, ExecutionMode

class SimulationAdapter(BaseActionAdapter):
    """
    Safe Simulation Action Adapter.
    Strictly validates actions against the security allowlist and mocks execution safely without OS commands.
    """
    ALLOWLISTED_ACTIONS = {
        "LOG_EVENT": "Traffic flow metadata recorded in monitoring logs",
        "CREATE_INCIDENT": "Security incident initialized in SOC database",
        "NOTIFY_ANALYST": "High-priority notification dispatched to SOC analyst queue",
        "BLOCK_IP_SIMULATION": "Perimeter firewall rule simulated: source IP traffic dropped",
        "RATE_LIMIT_SIMULATION": "Firewall traffic policing rule simulated: rate limit applied",
        "ICMP_FILTER_SIMULATION": "ICMP protocol filtering rule simulated: echo-requests dropped",
        "RESET_CREDENTIALS_SIMULATION": "IAM credential quarantine simulated: forced password reset & session revocation",
        "ISOLATE_HOST_SIMULATION": "Host network segmentation rule simulated: endpoint isolated to remediation VLAN",
        "MONITOR_SOURCE": "Enhanced telemetry logging enabled for target source IP",
        "MONITOR_TRAFFIC": "Traffic flow observation initiated",
        "VERIFY_MITIGATION": "Mitigation verification check initiated",
        "RESOLVE_OR_ESCALATE": "State-aware incident conclusion evaluated",
        "ESCALATE_INCIDENT": "Incident escalation flag raised for Tier 2/Tier 3 response"
    }

    def execute_action(
        self,
        action: str,
        target: str,
        parameters: Optional[Dict[str, Any]] = None,
        incident_id: Optional[str] = None
    ) -> ActionResult:
        parameters = parameters or {}
        
        # Security Enforcement: Reject unallowlisted action types
        if action not in self.ALLOWLISTED_ACTIONS:
            return ActionResult(
                action=action,
                target=target,
                status=ActionStatus.FAILED,
                mode=ExecutionMode.SIMULATION,
                message=f"Action '{action}' is not in the security allowlist. Execution rejected for safety.",
                details={"error": "ALLOWLIST_VIOLATION", "parameters": parameters}
            )

        base_msg = self.ALLOWLISTED_ACTIONS[action]
        duration = parameters.get("duration_seconds")
        duration_msg = f" for {duration}s" if duration else ""
        full_msg = f"[SIMULATION] {base_msg} for target: {target}{duration_msg}."

        return ActionResult(
            action=action,
            target=target,
            status=ActionStatus.SUCCESS,
            mode=ExecutionMode.SIMULATION,
            message=full_msg,
            details={"parameters": parameters, "incident_id": incident_id}
        )
