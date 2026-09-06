from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from decision_engine.models.playbook import PlaybookDefinition, PlaybookStep, PlaybookExecutionRecord
from decision_engine.models.action import ActionResult, ActionStatus, ExecutionMode
from decision_engine.models.verification import VerificationResult, VerificationStatus
from decision_engine.playbooks.playbook_loader import PlaybookLoader
from decision_engine.actions.action_executor import SOARActionExecutor
from decision_engine.verification.verification_engine import VerificationEngine
from decision_engine.audit.audit_logger import AuditLogger

class PlaybookEngine:
    """
    Playbook Orchestration Engine.
    Executes modular response workflows step-by-step and tracks execution progress.
    """
    def __init__(
        self,
        loader: Optional[PlaybookLoader] = None,
        action_executor: Optional[SOARActionExecutor] = None,
        audit_logger: Optional[AuditLogger] = None,
        verification_engine: Optional[VerificationEngine] = None
    ):
        self.loader = loader or PlaybookLoader()
        self.executor = action_executor or SOARActionExecutor()
        self.audit = audit_logger or AuditLogger()
        self.verification_engine = verification_engine or VerificationEngine(audit_logger=self.audit)

    def execute_playbook(
        self,
        playbook_id: str,
        target: str,
        automation_level: int,
        incident_id: str,
        approved: bool = False,
        baseline_pps: float = 100.0
    ) -> PlaybookExecutionRecord:
        playbook: Optional[PlaybookDefinition] = self.loader.get_playbook(playbook_id)
        if not playbook:
            playbook = PlaybookDefinition(
                playbook_id=playbook_id,
                name="Fallback Playbook",
                steps=[PlaybookStep(step_number=1, action="CREATE_INCIDENT"), PlaybookStep(step_number=2, action="NOTIFY_ANALYST")]
            )

        record = PlaybookExecutionRecord(
            playbook_id=playbook.playbook_id,
            incident_id=incident_id,
            total_steps=len(playbook.steps)
        )

        self.audit.log(
            event_type="PLAYBOOK_STARTED",
            details=f"Executing playbook {playbook.playbook_id} ({playbook.name}) with {len(playbook.steps)} steps",
            incident_id=incident_id,
            component="PLAYBOOK_ENGINE"
        )

        all_success = True
        waiting_approval = False

        for step in playbook.steps:
            record.current_step = step.step_number
            if step.action == "VERIFY_MITIGATION":
                # Real closed-loop verification
                ver_res: VerificationResult = self.verification_engine.verify_mitigation(
                    incident_id=incident_id,
                    target=target,
                    baseline_pps=baseline_pps
                )
                step_status = ActionStatus.SUCCESS if ver_res.status == VerificationStatus.SUCCESS else ActionStatus.FAILED
                res = ActionResult(
                    action=step.action,
                    target=target,
                    status=step_status,
                    mode=ExecutionMode.SIMULATION,
                    message=ver_res.reason,
                    details={
                        "reduction_percentage": ver_res.reduction_percentage,
                        "observed_pps": ver_res.observed_pps,
                        "verification_status": ver_res.status.value
                    }
                )
            else:
                res: ActionResult = self.executor.execute_step(
                    action=step.action,
                    target=target,
                    automation_level=automation_level,
                    parameters=step.parameters,
                    incident_id=incident_id,
                    approved=approved
                )

            record.step_results.append({
                "step_number": step.step_number,
                "action": res.action,
                "status": res.status.value,
                "message": res.message
            })

            if res.status == ActionStatus.WAITING_APPROVAL:
                waiting_approval = True
                break
            elif res.status == ActionStatus.FAILED and step.required:
                all_success = False
                break

        if waiting_approval:
            record.status = "WAITING_APPROVAL"
        elif all_success:
            record.status = "COMPLETED"
            record.completed_at = datetime.now(timezone.utc).isoformat()
        else:
            record.status = "FAILED"
            record.completed_at = datetime.now(timezone.utc).isoformat()

        self.audit.log(
            event_type="PLAYBOOK_COMPLETED",
            details=f"Playbook {playbook.playbook_id} execution status: {record.status}",
            incident_id=incident_id,
            status=record.status,
            component="PLAYBOOK_ENGINE"
        )

        return record
