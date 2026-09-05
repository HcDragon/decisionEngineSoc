import sqlite3
import json
import os
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

class Database:
    """
    Persistent SQLite storage engine for Smart SOC Decision Engine.
    Configured with WAL mode and thread-local connections for concurrent read/write.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: Optional[str] = None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Database, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, db_path: Optional[str] = None):
        if getattr(self, "_initialized", False):
            return
            
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "soc_decision_engine.db")
            
        self.db_path = db_path
        self._local = threading.local()
        self._init_schema()
        self._initialized = True

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            self._local.conn = conn
        return self._local.conn

    def _init_schema(self):
        conn = self._get_connection()
        with conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    source_ip TEXT NOT NULL,
                    destination_ip TEXT NOT NULL,
                    source_port INTEGER DEFAULT 0,
                    destination_port INTEGER DEFAULT 0,
                    protocol TEXT DEFAULT 'TCP',
                    attack_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    risk_score REAL DEFAULT 0.0,
                    severity TEXT DEFAULT 'LOW',
                    policy_id TEXT DEFAULT 'UNKNOWN',
                    playbook_id TEXT DEFAULT 'UNKNOWN',
                    automation_level INTEGER DEFAULT 0,
                    current_state TEXT DEFAULT 'DETECTED',
                    incident_status TEXT DEFAULT 'LOGGED',
                    recommended_action TEXT DEFAULT '',
                    actions_taken TEXT DEFAULT '[]',
                    reasons TEXT DEFAULT '[]',
                    event_count INTEGER DEFAULT 1,
                    analyst_required INTEGER DEFAULT 0,
                    is_mitigated INTEGER DEFAULT 0,
                    raw_data TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS threat_events (
                    event_id TEXT PRIMARY KEY,
                    incident_id TEXT,
                    timestamp TEXT NOT NULL,
                    source_ip TEXT NOT NULL,
                    destination_ip TEXT NOT NULL,
                    attack_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    packet_count INTEGER DEFAULT 0,
                    flow_duration REAL DEFAULT 0.0,
                    bytes INTEGER DEFAULT 0,
                    raw_event TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS decisions (
                    decision_id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    risk_score REAL NOT NULL,
                    severity TEXT NOT NULL,
                    policy_id TEXT NOT NULL,
                    playbook_id TEXT NOT NULL,
                    automation_level INTEGER NOT NULL,
                    explanation TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    raw_decision TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS actions (
                    execution_id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT NOT NULL,
                    status TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS active_mitigations (
                    action_id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    target TEXT NOT NULL,
                    status TEXT DEFAULT 'ACTIVE',
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    verification_required INTEGER DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS verifications (
                    verification_id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL,
                    target TEXT NOT NULL,
                    status TEXT NOT NULL,
                    baseline_pps REAL NOT NULL,
                    observed_pps REAL NOT NULL,
                    reduction_percentage REAL NOT NULL,
                    reason TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    incident_id TEXT,
                    event_id TEXT,
                    action_id TEXT,
                    component TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT DEFAULT 'INFO',
                    status TEXT DEFAULT 'SUCCESS',
                    details TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_incidents_src_dest ON incidents (source_ip, destination_ip, current_state);
                CREATE INDEX IF NOT EXISTS idx_audit_incident ON audit_logs (incident_id);
                CREATE INDEX IF NOT EXISTS idx_events_timestamp ON threat_events (timestamp);
            """)

    def save_incident(self, incident: Dict[str, Any]):
        conn = self._get_connection()
        with conn:
            conn.execute("""
                INSERT INTO incidents (
                    incident_id, event_id, created_at, updated_at, source_ip, destination_ip,
                    source_port, destination_port, protocol, attack_type, confidence,
                    risk_score, severity, policy_id, playbook_id, automation_level,
                    current_state, incident_status, recommended_action, actions_taken,
                    reasons, event_count, analyst_required, is_mitigated, raw_data
                ) VALUES (
                    :incident_id, :event_id, :created_at, :updated_at, :source_ip, :destination_ip,
                    :source_port, :destination_port, :protocol, :attack_type, :confidence,
                    :risk_score, :severity, :policy_id, :playbook_id, :automation_level,
                    :current_state, :incident_status, :recommended_action, :actions_taken,
                    :reasons, :event_count, :analyst_required, :is_mitigated, :raw_data
                )
                ON CONFLICT(incident_id) DO UPDATE SET
                    updated_at = excluded.updated_at,
                    risk_score = excluded.risk_score,
                    severity = excluded.severity,
                    policy_id = excluded.policy_id,
                    playbook_id = excluded.playbook_id,
                    automation_level = excluded.automation_level,
                    current_state = excluded.current_state,
                    incident_status = excluded.incident_status,
                    recommended_action = excluded.recommended_action,
                    actions_taken = excluded.actions_taken,
                    reasons = excluded.reasons,
                    event_count = excluded.event_count,
                    analyst_required = excluded.analyst_required,
                    is_mitigated = excluded.is_mitigated,
                    raw_data = excluded.raw_data
            """, {
                "incident_id": incident["incident_id"],
                "event_id": incident["event_id"],
                "created_at": incident.get("created_at", datetime.now(timezone.utc).isoformat()),
                "updated_at": incident.get("updated_at", datetime.now(timezone.utc).isoformat()),
                "source_ip": incident["source_ip"],
                "destination_ip": incident["destination_ip"],
                "source_port": incident.get("source_port", 0),
                "destination_port": incident.get("destination_port", 80),
                "protocol": incident.get("protocol", "TCP"),
                "attack_type": incident["attack_type"],
                "confidence": float(incident.get("confidence", 0.0)),
                "risk_score": float(incident.get("risk_score", 0.0)),
                "severity": incident.get("severity", "LOW"),
                "policy_id": incident.get("policy_id", "UNKNOWN"),
                "playbook_id": incident.get("playbook_id", "UNKNOWN"),
                "automation_level": int(incident.get("automation_level", 0)),
                "current_state": (
                    incident.get("current_state").value if hasattr(incident.get("current_state"), "value")
                    else str(incident.get("current_state", "DETECTED")).replace("IncidentState.", "")
                ),
                "incident_status": str(incident.get("incident_status", "LOGGED")),
                "recommended_action": str(incident.get("recommended_action", "")),
                "actions_taken": json.dumps(incident.get("actions_taken", [])),
                "reasons": json.dumps(incident.get("reasons", [])),
                "event_count": int(incident.get("event_count", 1)),
                "analyst_required": 1 if incident.get("analyst_required") else 0,
                "is_mitigated": 1 if incident.get("is_mitigated") else 0,
                "raw_data": json.dumps({k: v for k, v in incident.items() if k != "raw_data"})
            })

    def get_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM incidents WHERE incident_id = ?", (incident_id,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["actions_taken"] = json.loads(d["actions_taken"]) if d.get("actions_taken") else []
        d["reasons"] = json.loads(d["reasons"]) if d.get("reasons") else []
        d["analyst_required"] = bool(d["analyst_required"])
        d["is_mitigated"] = bool(d["is_mitigated"])
        return d

    def find_active_incident(self, source_ip: str, destination_ip: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.execute("""
            SELECT * FROM incidents 
            WHERE source_ip = ? AND destination_ip = ? 
              AND current_state NOT IN ('RESOLVED', 'CLOSED')
            ORDER BY updated_at DESC LIMIT 1
        """, (source_ip, destination_ip))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["actions_taken"] = json.loads(d["actions_taken"]) if d.get("actions_taken") else []
        d["reasons"] = json.loads(d["reasons"]) if d.get("reasons") else []
        d["analyst_required"] = bool(d["analyst_required"])
        d["is_mitigated"] = bool(d["is_mitigated"])
        return d

    def list_incidents(self, state: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        if state:
            cur = conn.execute("SELECT * FROM incidents WHERE current_state = ? ORDER BY updated_at DESC LIMIT ?", (state, limit))
        else:
            cur = conn.execute("SELECT * FROM incidents ORDER BY updated_at DESC LIMIT ?", (limit,))
        results = []
        for row in cur.fetchall():
            d = dict(row)
            d["actions_taken"] = json.loads(d["actions_taken"]) if d.get("actions_taken") else []
            d["reasons"] = json.loads(d["reasons"]) if d.get("reasons") else []
            d["analyst_required"] = bool(d["analyst_required"])
            d["is_mitigated"] = bool(d["is_mitigated"])
            results.append(d)
        return results

    def save_threat_event(self, event_data: Dict[str, Any]):
        conn = self._get_connection()
        src_ip = event_data.get("source", {}).get("ip") or event_data.get("src_ip", "")
        dest_ip = event_data.get("destination", {}).get("ip") or event_data.get("dest_ip", "")
        attack_type = event_data.get("detection", {}).get("attack_type") or event_data.get("attack_type", "Unknown")
        confidence = float(event_data.get("detection", {}).get("confidence") or event_data.get("confidence", 0.0))
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO threat_events (
                    event_id, incident_id, timestamp, source_ip, destination_ip,
                    attack_type, confidence, packet_count, flow_duration, bytes, raw_event
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_data.get("event_id", ""),
                event_data.get("incident_id"),
                event_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                src_ip, dest_ip, attack_type, confidence,
                event_data.get("network", {}).get("packet_count", 0),
                event_data.get("network", {}).get("flow_duration", 0.0),
                event_data.get("network", {}).get("bytes", 0),
                json.dumps(event_data)
            ))

    def list_threat_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM threat_events ORDER BY timestamp DESC LIMIT ?", (limit,))
        results = []
        for row in cur.fetchall():
            d = dict(row)
            d["raw_event"] = json.loads(d["raw_event"]) if d.get("raw_event") else {}
            results.append(d)
        return results

    def save_decision(self, decision_data: Dict[str, Any]):
        conn = self._get_connection()
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO decisions (
                    decision_id, incident_id, event_id, decision, risk_score, severity,
                    policy_id, playbook_id, automation_level, explanation, timestamp, raw_decision
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decision_data["decision_id"],
                decision_data["incident_id"],
                decision_data["event_id"],
                str(decision_data["decision"]),
                float(decision_data["risk_score"]),
                decision_data["severity"],
                decision_data["policy_id"],
                decision_data["playbook_id"],
                int(decision_data["automation_level"]),
                decision_data.get("explanation", ""),
                decision_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                json.dumps(decision_data)
            ))

    def get_decision(self, incident_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.execute("SELECT raw_decision FROM decisions WHERE incident_id = ? ORDER BY timestamp DESC LIMIT 1", (incident_id,))
        row = cur.fetchone()
        return json.loads(row["raw_decision"]) if row else None

    def save_action_result(self, action_data: Dict[str, Any]):
        conn = self._get_connection()
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO actions (
                    execution_id, incident_id, action, target, status, mode, message, timestamp, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                action_data["execution_id"],
                action_data.get("incident_id", ""),
                action_data["action"],
                action_data["target"],
                str(action_data["status"]),
                str(action_data["mode"]),
                action_data["message"],
                action_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                json.dumps(action_data.get("details", {}))
            ))

    def save_active_mitigation(self, mit: Dict[str, Any]):
        conn = self._get_connection()
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO active_mitigations (
                    action_id, incident_id, action_type, target, status, created_at, expires_at, verification_required
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                mit["action_id"],
                mit["incident_id"],
                mit["action_type"],
                mit["target"],
                mit.get("status", "ACTIVE"),
                mit.get("created_at", datetime.now(timezone.utc).isoformat()),
                mit.get("expires_at"),
                1 if mit.get("verification_required", True) else 0
            ))

    def get_active_mitigations(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM active_mitigations WHERE status = 'ACTIVE'")
        return [dict(r) for r in cur.fetchall()]

    def update_mitigation_status(self, action_id: str, status: str):
        conn = self._get_connection()
        with conn:
            conn.execute("UPDATE active_mitigations SET status = ? WHERE action_id = ?", (status, action_id))

    def save_verification(self, ver: Dict[str, Any]):
        conn = self._get_connection()
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO verifications (
                    verification_id, incident_id, target, status, baseline_pps, observed_pps,
                    reduction_percentage, reason, timestamp, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ver["verification_id"],
                ver["incident_id"],
                ver["target"],
                str(ver["status"]),
                float(ver["baseline_pps"]),
                float(ver["observed_pps"]),
                float(ver["reduction_percentage"]),
                ver["reason"],
                ver.get("timestamp", datetime.now(timezone.utc).isoformat()),
                json.dumps(ver.get("details", {}))
            ))

    def get_verification(self, incident_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM verifications WHERE incident_id = ? ORDER BY timestamp DESC LIMIT 1", (incident_id,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["details"] = json.loads(d["details"]) if d.get("details") else {}
        return d

    def add_audit_log(self, entry: Dict[str, Any]):
        conn = self._get_connection()
        with conn:
            conn.execute("""
                INSERT INTO audit_logs (
                    timestamp, incident_id, event_id, action_id, component, event_type, severity, status, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.get("timestamp", datetime.now(timezone.utc).isoformat()),
                entry.get("incident_id"),
                entry.get("event_id"),
                entry.get("action_id"),
                entry.get("component", "DECISION_ENGINE"),
                entry["event_type"],
                entry.get("severity", "INFO"),
                entry.get("status", "SUCCESS"),
                str(entry.get("details", ""))
            ))

    def get_audit_logs(self, incident_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        if incident_id:
            cur = conn.execute("SELECT * FROM audit_logs WHERE incident_id = ? ORDER BY id ASC LIMIT ?", (incident_id, limit))
        else:
            cur = conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]
