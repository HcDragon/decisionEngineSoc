import uuid
from typing import Optional, Dict, Any, Union
from datetime import datetime, timezone

from decision_engine.models.threat_event import ThreatEvent
from decision_engine.models.context import EnrichedContext
from decision_engine.models.risk import RiskAssessment, RiskSeverity
from decision_engine.models.policy import PolicyMatchResult, PolicyDefinition
from decision_engine.models.decision import SecurityDecision, DecisionType, AutomationLevel
from decision_engine.models.incident import IncidentRecord, IncidentState
from decision_engine.models.playbook import PlaybookExecutionRecord
from decision_engine.models.verification import VerificationResult, VerificationStatus

from decision_engine.storage.db import Database
from decision_engine.events.event_bus import EventBus
from decision_engine.audit.audit_logger import AuditLogger
from decision_engine.context.context_enricher import ContextEnricher
from decision_engine.risk.risk_engine import RiskEngine
from decision_engine.policy.policy_engine import PolicyEngine
from decision_engine.playbooks.playbook_engine import PlaybookEngine
from decision_engine.actions.action_executor import SOARActionExecutor
from decision_engine.verification.verification_engine import VerificationEngine
from decision_engine.recovery.recovery_manager import RecoveryManager
from decision_engine.incidents.incident_manager import IncidentManager

class DecisionManager:
    """
    Master Decision Engine Pipeline Orchestrator.
    Executes the 11-stage autonomous security orchestration workflow from raw Threat Event to Verification and Recovery.
    """
    def __init__(
        self,
        db: Optional[Database] = None,
        event_bus: Optional[EventBus] = None,
        audit_logger: Optional[AuditLogger] = None
    ):
        self.db = db or Database()
        self.event_bus = event_bus or EventBus()
        self.audit = audit_logger or AuditLogger(self.db, self.event_bus)
        
        self.context_enricher = ContextEnricher(self.db, self.audit)
        self.risk_engine = RiskEngine(audit_logger=self.audit)
        self.policy_engine = PolicyEngine(audit_logger=self.audit)
        self.action_executor = SOARActionExecutor(db=self.db, audit_logger=self.audit, event_bus=self.event_bus)
        self.playbook_engine = PlaybookEngine(action_executor=self.action_executor, audit_logger=self.audit)
        self.verification_engine = VerificationEngine(self.db, self.audit)
        self.recovery_manager = RecoveryManager(self.db, self.audit)
        self.incident_manager = IncidentManager(db=self.db, audit_logger=self.audit, event_bus=self.event_bus)

    def process(self, raw_input: Union[ThreatEvent, Dict[str, Any]]) -> SecurityDecision:
        """
        Executes the complete Decision Engine pipeline for a threat event.
        """
        # Stage 1: Validation
        if isinstance(raw_input, ThreatEvent):
            event = raw_input
        elif hasattr(raw_input, "model_dump"):
            event = ThreatEvent(**raw_input.model_dump())
        elif hasattr(raw_input, "dict"):
            event = ThreatEvent(**raw_input.dict())
        elif isinstance(raw_input, dict):
            event = ThreatEvent(**raw_input)
        else:
            event = ThreatEvent(**dict(raw_input))

        # Persist event
        self.db.save_threat_event(event.model_dump() if hasattr(event, "model_dump") else event.dict())

        # Stage 2: Incident Correlation & Deduplication
        incident, is_new = self.incident_manager.get_or_create_incident(event)

        self.audit.log(
            event_type="THREAT_RECEIVED",
            details=f"Received threat event for {event.detection.attack_type} ({event.source.ip} -> {event.destination.ip})",
            incident_id=incident.incident_id,
            event_id=event.event_id,
            component="DECISION_MANAGER"
        )

        self.incident_manager.transition_state(incident.incident_id, IncidentState.TRIAGING, "Commenced automated triage")

        # Stage 3: Context Enrichment
        context: EnrichedContext = self.context_enricher.enrich(event)

        # Stage 4: Risk Assessment
        risk: RiskAssessment = self.risk_engine.assess_risk(context, event_id=event.event_id, incident_id=incident.incident_id)
        self.incident_manager.transition_state(
            incident.incident_id,
            IncidentState.RISK_ASSESSED,
            f"Evaluated risk score: {risk.risk_score} ({risk.severity.value})"
        )

        # Stage 5: Policy Evaluation & Priority Resolution
        policy_result: PolicyMatchResult = self.policy_engine.evaluate(context, risk, event_id=event.event_id, incident_id=incident.incident_id)
        selected_policy: PolicyDefinition = policy_result.selected_policy
        self.incident_manager.transition_state(
            incident.incident_id,
            IncidentState.POLICY_MATCHED,
            f"Matched policy {selected_policy.policy_id} (Priority: {selected_policy.priority})"
        )

        # Stage 6: Security Decision Generation
        auto_lvl = selected_policy.automation_level
        analyst_req = (auto_lvl in (1, 2, 3)) or (selected_policy.notification_required and auto_lvl < 5)
        
        # Derive Decision Type
        decision_type_str = selected_policy.decision.upper()
        try:
            decision_type = DecisionType(decision_type_str)
        except ValueError:
            decision_type = DecisionType.CONTAIN if auto_lvl >= 4 else DecisionType.MONITOR

        # Build explainable reasons list
        reasons = [f.explanation for f in risk.factors]
        reasons.append(policy_result.selection_reason)

        rec_action = (
            f"Playbook {selected_policy.playbook_id} selected. "
            f"{'Automatically applying mitigation actions.' if auto_lvl >= 4 else 'Requires manual approval or analyst notification.'}"
        )

        explanation = (
            f"Decision: {decision_type.value}. Risk evaluated at {risk.risk_score:.1f} ({risk.severity.value}). "
            f"Policy '{selected_policy.policy_id}' selected ({policy_result.selection_reason}). "
            f"Automation Level: {auto_lvl} ({'Automated' if auto_lvl >= 4 else 'Human-in-the-Loop'})."
        )

        legacy_status = "AUTO_MITIGATED" if auto_lvl >= 4 else ("PENDING_APPROVAL" if auto_lvl in (2, 3) else "LOGGED")

        decision = SecurityDecision(
            incident_id=incident.incident_id,
            event_id=event.event_id,
            decision=decision_type,
            risk_score=risk.risk_score,
            severity=risk.severity.value,
            policy_id=selected_policy.policy_id,
            playbook_id=selected_policy.playbook_id,
            automation_level=auto_lvl,
            analyst_required=analyst_req,
            recommended_action=rec_action,
            actions=[], # Populated after playbook execution
            reasons=reasons,
            explanation=explanation,
            src_ip=event.source.ip,
            attack_type=event.detection.attack_type,
            incident_status=legacy_status
        )

        # Stage 7: Playbook Execution
        pb_record: PlaybookExecutionRecord = self.playbook_engine.execute_playbook(
            playbook_id=selected_policy.playbook_id,
            target=event.source.ip,
            automation_level=auto_lvl,
            incident_id=incident.incident_id,
            approved=False
        )

        actions_taken = [step["action"] for step in pb_record.step_results if step["status"] == "SUCCESS"]
        decision.actions = actions_taken

        # Stage 8: Stateful Incident Update & Stage 9: Verification
        if pb_record.status == "WAITING_APPROVAL":
            decision.incident_status = "PENDING_APPROVAL"
            self.incident_manager.transition_state(
                incident.incident_id,
                IncidentState.PENDING_APPROVAL,
                "Mitigation action pending manual analyst approval"
            )
        elif auto_lvl >= 4 and actions_taken:
            decision.incident_status = "AUTO_MITIGATED"
            self.incident_manager.transition_state(
                incident.incident_id,
                IncidentState.RESPONSE_STARTED,
                f"Automated playbook mitigation executed ({', '.join(actions_taken)})"
            )
        elif auto_lvl == 0:
            decision.incident_status = "LOGGED"

            # Stage 9: Security Outcome Verification
            baseline_pps = context.observed.packets_per_second
            ver_result: VerificationResult = self.verification_engine.verify_mitigation(
                incident_id=incident.incident_id,
                target=event.source.ip,
                baseline_pps=baseline_pps
            )

            if ver_result.status == VerificationStatus.SUCCESS:
                self.incident_manager.transition_state(
                    incident.incident_id,
                    IncidentState.CONTAINED,
                    ver_result.reason
                )
            else:
                self.recovery_manager.escalate_incident(
                    incident_id=incident.incident_id,
                    reason=ver_result.reason
                )
        elif auto_lvl == 0:
            self.incident_manager.transition_state(
                incident.incident_id,
                IncidentState.RESOLVED,
                "Benign traffic verified and safely recorded"
            )

        # Update persistent incident and decision records
        current_inc = self.db.get_incident(incident.incident_id)
        if current_inc:
            current_inc["risk_score"] = risk.risk_score
            current_inc["severity"] = risk.severity.value
            current_inc["policy_id"] = selected_policy.policy_id
            current_inc["playbook_id"] = selected_policy.playbook_id
            current_inc["automation_level"] = auto_lvl
            current_inc["recommended_action"] = rec_action
            current_inc["actions_taken"] = actions_taken
            current_inc["reasons"] = reasons
            current_inc["analyst_required"] = analyst_req
            self.db.save_incident(current_inc)

        self.db.save_decision(decision.model_dump() if hasattr(decision, "model_dump") else decision.dict())

        self.audit.log(
            event_type="DECISION_CREATED",
            details=f"Decision {decision.decision.value} created for Incident {incident.incident_id} (Risk: {decision.risk_score})",
            incident_id=incident.incident_id,
            event_id=event.event_id,
            component="DECISION_MANAGER"
        )

        return decision

    def process_prediction(self, raw_input: Union[ThreatEvent, Dict[str, Any]]) -> SecurityDecision:
        """Backwards-compatibility wrapper for process()."""
        return self.process(raw_input)

    def approve_incident(self, incident_id: str) -> Dict[str, Any]:
        """
        Allows a SOC analyst to manually approve an incident pending action execution (Level 2/3).
        Resumes the playbook with approved=True.
        """
        inc = self.db.get_incident(incident_id)
        if not inc:
            return {"status": "error", "message": f"Incident {incident_id} not found."}

        playbook_id = inc.get("playbook_id", "PB-DEFAULT")
        target = inc.get("source_ip", "")

        pb_record = self.playbook_engine.execute_playbook(
            playbook_id=playbook_id,
            target=target,
            automation_level=inc.get("automation_level", 2),
            incident_id=incident_id,
            approved=True
        )

        actions_taken = [step["action"] for step in pb_record.step_results if step["status"] == "SUCCESS"]
        inc["actions_taken"].extend(actions_taken)
        inc["current_state"] = IncidentState.CONTAINED.value
        inc["incident_status"] = "MANUAL_MITIGATED"
        inc["is_mitigated"] = True
        inc["recommended_action"] = "Manual Approval Granted. Playbook executed successfully."
        self.db.save_incident(inc)

        self.audit.log(
            event_type="INCIDENT_APPROVED",
            details=f"Analyst granted manual approval for incident {incident_id}. Executed: {', '.join(actions_taken)}",
            incident_id=incident_id,
            status="SUCCESS",
            component="DECISION_MANAGER"
        )

        return {
            "status": "success",
            "message": f"Incident {incident_id} manually approved and mitigated.",
            "actions_executed": actions_taken
        }
