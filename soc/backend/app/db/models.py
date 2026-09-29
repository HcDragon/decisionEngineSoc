"""
SQLAlchemy 2.0 ORM Models for AI-Based Smart SOC Manager.
Covers alerts, incidents, decisions, actions, approvals, cases, virtual firewall, audit log, counters, feedback.
"""
from datetime import datetime, timezone
import enum
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.types import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class IncidentStatus(str, enum.Enum):
    OPEN = "open"
    CONTAINED = "contained"
    CLOSED = "closed"
    FALSE_POSITIVE = "false_positive"


class DecisionMode(str, enum.Enum):
    MONITOR = "monitor"
    RECOMMEND = "recommend"
    AUTO = "auto"


class DecisionStatus(str, enum.Enum):
    MONITORED = "monitored"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"
    EXPIRED = "expired"


class ApprovalVerdict(str, enum.Enum):
    APPROVE = "approve"
    REJECT = "reject"
    OVERRIDE = "override"


class VirtualFirewallKind(str, enum.Enum):
    BLOCK = "block"
    ISOLATE = "isolate"
    RATE_LIMIT = "rate_limit"


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key_src_ip: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    family: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    alert_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_risk: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[IncidentStatus] = mapped_column(
        SQLEnum(IncidentStatus, name="incident_status_enum"),
        default=IncidentStatus.OPEN,
        nullable=False,
        index=True
    )
    assigned_to: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    alerts: Mapped[List["Alert"]] = relationship("Alert", back_populates="incident", cascade="all, delete-orphan")
    decisions: Mapped[List["Decision"]] = relationship("Decision", back_populates="incident", cascade="all, delete-orphan")
    cases: Mapped[List["Case"]] = relationship("Case", back_populates="incident", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_incidents_src_family", "key_src_ip", "family"),
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    src_ip: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    dst_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    src_port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dst_port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    family: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    margin: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    probabilities: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    top_features: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    incident_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("incidents.id"), nullable=True, index=True)
    raw_features: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    incident: Mapped[Optional["Incident"]] = relationship("Incident", back_populates="alerts")
    feedback_entries: Mapped[List["Feedback"]] = relationship("Feedback", back_populates="alert", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_alerts_src_ts", "src_ip", "ts"),
    )


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(Integer, ForeignKey("incidents.id"), nullable=False, index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    tier: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # LOW, MEDIUM, HIGH, CRITICAL
    score_breakdown: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    rule_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    rule_trace: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    policy_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[DecisionMode] = mapped_column(
        SQLEnum(DecisionMode, name="decision_mode_enum"),
        nullable=False,
        index=True
    )
    playbook_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[DecisionStatus] = mapped_column(
        SQLEnum(DecisionStatus, name="decision_status_enum"),
        default=DecisionStatus.MONITORED,
        nullable=False,
        index=True
    )
    guardrail_results: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    explanation: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident", back_populates="decisions")
    actions: Mapped[List["Action"]] = relationship("Action", back_populates="decision", cascade="all, delete-orphan")
    approvals: Mapped[List["Approval"]] = relationship("Approval", back_populates="decision", cascade="all, delete-orphan")


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decision_id: Mapped[int] = mapped_column(Integer, ForeignKey("decisions.id"), nullable=False, index=True)
    step_id: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # block_ip, rate_limit, isolate_host, notify, etc.
    params: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    executor: Mapped[str] = mapped_column(String(50), nullable=False)  # dry_run, simulated, lab
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    rolled_back_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    decision: Mapped["Decision"] = relationship("Decision", back_populates="actions")
    virtual_firewall_entries: Mapped[List["VirtualFirewall"]] = relationship("VirtualFirewall", back_populates="action")


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decision_id: Mapped[int] = mapped_column(Integer, ForeignKey("decisions.id"), nullable=False, index=True)
    analyst: Mapped[str] = mapped_column(String(100), nullable=False)
    verdict: Mapped[ApprovalVerdict] = mapped_column(
        SQLEnum(ApprovalVerdict, name="approval_verdict_enum"),
        nullable=False
    )
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    # Relationships
    decision: Mapped["Decision"] = relationship("Decision", back_populates="approvals")


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(Integer, ForeignKey("incidents.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident", back_populates="cases")


class VirtualFirewall(Base):
    __tablename__ = "virtual_firewall"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[VirtualFirewallKind] = mapped_column(
        SQLEnum(VirtualFirewallKind, name="vf_kind_enum"),
        nullable=False,
        index=True
    )
    target: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    ttl_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    action_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("actions.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    action: Mapped[Optional["Action"]] = relationship("Action", back_populates="virtual_firewall_entries")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(100), nullable=False, default="system")
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)


class Counter(Base):
    __tablename__ = "counters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts_bucket: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index("idx_counters_bucket_label", "ts_bucket", "label", unique=True),
    )


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[int] = mapped_column(Integer, ForeignKey("alerts.id"), nullable=False, index=True)
    analyst: Mapped[str] = mapped_column(String(100), nullable=False)
    true_label: Mapped[str] = mapped_column(String(100), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    # Relationships
    alert: Mapped["Alert"] = relationship("Alert", back_populates="feedback_entries")
