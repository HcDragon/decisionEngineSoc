import os
import json
import time
import threading
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(_DATA_DIR, exist_ok=True)
_STATE_FILE = os.path.join(_DATA_DIR, "live_workflow.json")

STAGE_NAMES = {
    1: "Ingestion",
    2: "RF Detection",
    3: "Context",
    4: "Risk Engine",
    5: "Policy Match",
    6: "SOAR Playbook",
    7: "Mitigation"
}

class WorkflowTracker:
    """
    Thread-safe and process-shared tracker for real-time SOAR workflow progression.
    Persists atomic JSON snapshots to disk so both CLI simulation scripts and
    Streamlit dashboard processes observe real-time stage updates without latency.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(WorkflowTracker, cls).__new__(cls)
                cls._instance._init_state()
            return cls._instance

    def _init_state(self):
        self._state_lock = threading.Lock()
        self._current_state = self._read_from_disk()
        if not self._current_state:
            self._current_state = self._default_state()
            self._write_to_disk()

    def _default_state(self) -> Dict[str, Any]:
        return {
            "attack_id": None,
            "attack_type": "None",
            "src_ip": "0.0.0.0",
            "dest_ip": "127.0.0.1",
            "target_url": "",
            "is_active": False,
            "current_stage": 0,
            "packet_count": 0,
            "packet_rate": 0.0,
            "elapsed": 0.0,
            "confidence": 0.0,
            "pred_label": "",
            "risk_score": 0.0,
            "severity": "LOW",
            "policy_id": "DEFAULT",
            "playbook_id": "DEFAULT",
            "decision": "MONITOR",
            "actions": [],
            "incident_id": None,
            "status_text": "System Idle",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "stages": {
                str(num): {
                    "name": name,
                    "status": "PENDING", # PENDING, ACTIVE, DONE, FAILED
                    "detail": "Awaiting trigger",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                for num, name in STAGE_NAMES.items()
            }
        }

    def _read_from_disk(self) -> Optional[Dict[str, Any]]:
        try:
            if os.path.exists(_STATE_FILE):
                with open(_STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def _write_to_disk(self):
        try:
            tmp_file = f"{_STATE_FILE}.tmp.{uuid.uuid4().hex[:6]}"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(self._current_state, f, indent=2)
            os.replace(tmp_file, _STATE_FILE)
        except Exception:
            pass

    def start_attack(
        self,
        attack_type: str,
        src_ip: str = "192.168.1.99",
        dest_ip: str = "127.0.0.1",
        target_url: str = "",
        total_packets: int = 512
    ):
        with self._state_lock:
            attack_id = f"ATK-{uuid.uuid4().hex[:8].upper()}"
            now_iso = datetime.now(timezone.utc).isoformat()
            self._current_state = {
                "attack_id": attack_id,
                "attack_type": attack_type,
                "src_ip": src_ip,
                "dest_ip": dest_ip,
                "target_url": target_url,
                "is_active": True,
                "current_stage": 1,
                "packet_count": 0,
                "packet_rate": 0.0,
                "elapsed": 0.0,
                "confidence": 0.0,
                "pred_label": attack_type,
                "risk_score": 0.0,
                "severity": "PENDING",
                "policy_id": "EVALUATING...",
                "playbook_id": "SELECTING...",
                "decision": "ANALYZING",
                "actions": [],
                "incident_id": None,
                "status_text": f"Simulating {attack_type} against {dest_ip}",
                "updated_at": now_iso,
                "stages": {
                    "1": {"name": "Ingestion", "status": "ACTIVE", "detail": f"Streaming to {dest_ip}", "updated_at": now_iso},
                    "2": {"name": "RF Detection", "status": "PENDING", "detail": "Awaiting vector", "updated_at": now_iso},
                    "3": {"name": "Context", "status": "PENDING", "detail": f"Target: {dest_ip}", "updated_at": now_iso},
                    "4": {"name": "Risk Engine", "status": "PENDING", "detail": "Awaiting factors", "updated_at": now_iso},
                    "5": {"name": "Policy Match", "status": "PENDING", "detail": "Awaiting rules", "updated_at": now_iso},
                    "6": {"name": "SOAR Playbook", "status": "PENDING", "detail": "Awaiting plan", "updated_at": now_iso},
                    "7": {"name": "Mitigation", "status": "PENDING", "detail": "Awaiting containment", "updated_at": now_iso}
                }
            }
            self._write_to_disk()

    def update_telemetry(self, attempts: int, rate: float, elapsed: float):
        with self._state_lock:
            if not self._current_state.get("is_active"):
                return
            self._current_state["packet_count"] = attempts
            self._current_state["packet_rate"] = round(rate, 1)
            self._current_state["elapsed"] = round(elapsed, 2)
            self._current_state["updated_at"] = datetime.now(timezone.utc).isoformat()
            if "1" in self._current_state["stages"]:
                self._current_state["stages"]["1"]["detail"] = f"{attempts} pkts ({rate:.0f} pps)"
                self._current_state["stages"]["1"]["status"] = "ACTIVE"
            self._write_to_disk()

    def advance_stage(self, stage_num: int, status: str = "ACTIVE", detail: str = ""):
        with self._state_lock:
            now_iso = datetime.now(timezone.utc).isoformat()
            self._current_state["current_stage"] = stage_num
            self._current_state["updated_at"] = now_iso
            s_key = str(stage_num)
            
            # If moving to a stage, ensure prior stages are marked DONE
            for prev in range(1, stage_num):
                pk = str(prev)
                if pk in self._current_state["stages"] and self._current_state["stages"][pk]["status"] != "DONE":
                    self._current_state["stages"][pk]["status"] = "DONE"

            if s_key in self._current_state["stages"]:
                self._current_state["stages"][s_key]["status"] = status
                if detail:
                    self._current_state["stages"][s_key]["detail"] = detail
                self._current_state["stages"][s_key]["updated_at"] = now_iso

            # Update overall status text
            stage_name = STAGE_NAMES.get(stage_num, f"Stage {stage_num}")
            self._current_state["status_text"] = f"Stage {stage_num}: {stage_name} [{status}] - {detail}"
            self._write_to_disk()

    def complete_pipeline(
        self,
        incident_id: str,
        risk_score: float,
        severity: str,
        decision: str,
        policy_id: str,
        playbook_id: str,
        actions: list,
        confidence: float = 0.0,
        pred_label: str = ""
    ):
        with self._state_lock:
            now_iso = datetime.now(timezone.utc).isoformat()
            self._current_state["is_active"] = False
            self._current_state["current_stage"] = 7
            self._current_state["incident_id"] = incident_id
            self._current_state["risk_score"] = round(risk_score, 1)
            self._current_state["severity"] = severity
            self._current_state["decision"] = decision
            self._current_state["policy_id"] = policy_id
            self._current_state["playbook_id"] = playbook_id
            self._current_state["actions"] = actions
            if confidence > 0:
                self._current_state["confidence"] = round(confidence, 1)
            if pred_label:
                self._current_state["pred_label"] = pred_label

            # Mark all stages as DONE
            for num in range(1, 8):
                k = str(num)
                if k in self._current_state["stages"]:
                    self._current_state["stages"][k]["status"] = "DONE"

            act_str = actions[0] if actions else "MONITOR_SOURCE"
            self._current_state["stages"]["7"]["detail"] = f"{act_str} [{decision}]"
            self._current_state["status_text"] = f"Pipeline Completed. Decision: {decision} ({incident_id})"
            self._current_state["updated_at"] = now_iso
            self._write_to_disk()

    def get_state(self) -> Dict[str, Any]:
        with self._state_lock:
            disk_state = self._read_from_disk()
            if disk_state:
                self._current_state = disk_state
            return dict(self._current_state)

tracker = WorkflowTracker()
