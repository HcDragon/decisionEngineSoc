from typing import Optional, List, Dict, Any, Tuple
from decision_engine.models.context import EnrichedContext
from decision_engine.models.risk import RiskAssessment
from decision_engine.models.policy import PolicyDefinition, PolicyMatchResult
from decision_engine.policy.policy_loader import PolicyLoader
from decision_engine.audit.audit_logger import AuditLogger

class PolicyEngine:
    """
    Evaluates enriched context and risk score against prioritized security policies.
    Implements deterministic conflict resolution and records matching rationale.
    """
    def __init__(self, loader: Optional[PolicyLoader] = None, audit_logger: Optional[AuditLogger] = None):
        self.loader = loader or PolicyLoader()
        self.audit = audit_logger or AuditLogger()

    def evaluate(self, context: EnrichedContext, risk: RiskAssessment, event_id: Optional[str] = None, incident_id: Optional[str] = None) -> PolicyMatchResult:
        all_policies = self.loader.reload()
        attack_type = context.observed.attack_type
        conf = context.observed.confidence
        risk_score = risk.risk_score

        matched_policies: List[PolicyDefinition] = []

        # 1. Filter out disabled and evaluate conditions
        for policy in all_policies:
            if not policy.enabled:
                continue

            cond = policy.conditions
            
            # Check attack_type condition
            if cond.attack_type:
                # Case-insensitive substring or exact match check
                type_match = any(
                    target.lower() in attack_type.lower() or attack_type.lower() in target.lower()
                    for target in cond.attack_type
                )
                if not type_match:
                    continue

            # Check min confidence condition
            if cond.confidence and "minimum" in cond.confidence:
                if conf < cond.confidence["minimum"]:
                    continue

            # Check min risk condition
            if cond.risk and "minimum" in cond.risk:
                if risk_score < cond.risk["minimum"]:
                    continue

            matched_policies.append(policy)

        # 2. Conflict Resolution: Rank by priority (DESC), then risk threshold (DESC)
        if matched_policies:
            matched_policies.sort(key=lambda p: (p.priority, p.conditions.risk.get("minimum", 0) if p.conditions.risk else 0), reverse=True)
            selected = matched_policies[0]
            reason = (
                f"Matched {len(matched_policies)} applicable policy/policies. "
                f"Selected '{selected.policy_id}' ({selected.name}) with highest priority {selected.priority}."
            )
        else:
            # Fallback policy
            selected = PolicyDefinition(
                policy_id="DEFAULT-FALLBACK",
                name="Default Dynamic Fallback Policy",
                enabled=True,
                priority=0,
                decision="NOTIFY",
                severity="LOW",
                automation_level=1,
                playbook_id="PB-DEFAULT",
                notification_required=True
            )
            reason = "No specific policy conditions matched. Applied safe default fallback policy."

        self.audit.log(
            event_type="POLICY_MATCHED",
            details=f"Selected Policy {selected.policy_id} (Priority: {selected.priority}): {reason}",
            incident_id=incident_id,
            event_id=event_id,
            component="POLICY_ENGINE"
        )

        return PolicyMatchResult(
            selected_policy=selected,
            all_matched_policies=matched_policies,
            selection_reason=reason
        )
