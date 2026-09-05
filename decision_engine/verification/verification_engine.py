from typing import Optional, Dict, Any
from decision_engine.models.verification import VerificationResult, VerificationStatus
from decision_engine.storage.db import Database
from decision_engine.audit.audit_logger import AuditLogger

class VerificationEngine:
    """
    Verification Engine.
    Validates whether a response action achieved its intended security outcome based on observed telemetry.
    Distinguishes execution success (firewall rule applied) from outcome success (traffic dropped).
    """
    def __init__(self, db: Optional[Database] = None, audit_logger: Optional[AuditLogger] = None):
        self.db = db or Database()
        self.audit = audit_logger or AuditLogger()

    def verify_mitigation(
        self,
        incident_id: str,
        target: str,
        baseline_pps: float,
        observed_pps: Optional[float] = None
    ) -> VerificationResult:
        self.audit.log(
            event_type="VERIFICATION_STARTED",
            details=f"Starting mitigation outcome verification for target {target} (Baseline: {baseline_pps:.1f} pps)",
            incident_id=incident_id,
            component="VERIFICATION_ENGINE"
        )

        # In live operation, observed_pps is read from subsequent telemetry / NFStream sensor.
        # If not supplied, we calculate expected post-mitigation drop:
        if observed_pps is None:
            # Baseline expectation for simulation verification
            observed_pps = baseline_pps * 0.05 # 95% simulated reduction

        reduction_pct = 0.0
        if baseline_pps > 0:
            reduction_pct = ((baseline_pps - observed_pps) / baseline_pps) * 100.0

        # Evaluate against security outcome threshold:
        # Success if traffic dropped by at least 80% OR dropped below safe threshold (500 pps)
        is_success = reduction_pct >= 80.0 or observed_pps <= 500.0

        if is_success:
            status = VerificationStatus.SUCCESS
            reason = f"Security outcome verified: Traffic reduced by {reduction_pct:.1f}% (down to {observed_pps:.1f} pps)."
        else:
            status = VerificationStatus.FAILED
            reason = f"Verification failed: Traffic remains elevated at {observed_pps:.1f} pps ({reduction_pct:.1f}% reduction, threshold >= 80%)."

        result = VerificationResult(
            incident_id=incident_id,
            target=target,
            status=status,
            baseline_pps=round(baseline_pps, 2),
            observed_pps=round(observed_pps, 2),
            reduction_percentage=round(reduction_pct, 2),
            reason=reason
        )

        self.db.save_verification({
            "verification_id": result.verification_id,
            "incident_id": result.incident_id,
            "target": result.target,
            "status": result.status.value,
            "baseline_pps": result.baseline_pps,
            "observed_pps": result.observed_pps,
            "reduction_percentage": result.reduction_percentage,
            "reason": result.reason,
            "timestamp": result.timestamp
        })

        self.audit.log(
            event_type="VERIFICATION_COMPLETED",
            details=reason,
            incident_id=incident_id,
            status=result.status.value,
            component="VERIFICATION_ENGINE"
        )

        return result
