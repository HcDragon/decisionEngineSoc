"""
Network Traffic Monitor & NFStream Engine Integration.
Provides dual-mode network flow monitoring (Native NFStream with BPF filter on target port,
or resilient high-fidelity flow emulation with IDS classification when host pcap drivers are unavailable).
"""
import asyncio
from datetime import datetime, timezone
import logging
import math
import random
import threading
import time
import platform
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("soc.monitor")

# OS Platform Detection
SYSTEM_OS = platform.system()
IS_MACOS = SYSTEM_OS == "Darwin"
IS_WINDOWS = SYSTEM_OS == "Windows"
IS_LINUX = SYSTEM_OS == "Linux"

# Check NFStream availability
HAS_NFSTREAM = False
NFStreamer = None
try:
    from nfstream import NFStreamer as _NFStreamer
    NFStreamer = _NFStreamer
    HAS_NFSTREAM = True
except Exception as e:
    logger.warning(f"Native NFStreamer could not be imported: {e}. Safe emulation fallback will be used.")



class FlowRecord(BaseModel):
    id: str
    timestamp: str
    src_ip: str
    src_port: int
    dst_ip: str
    dst_port: int
    protocol: str  # TCP, UDP, ICMP
    application_name: str
    bidirectional_packets: int
    bidirectional_bytes: int
    duration_ms: float
    threat_label: str = "Benign Traffic"
    is_threat: bool = False
    confidence: float = 0.99
    risk_score: float = 0.0


def _default_iface() -> str:
    try:
        from soc.backend.app.config import settings
        return settings.SOC_CAPTURE_IFACE or "any"
    except Exception:
        return "any"


class PortMonitorConfig(BaseModel):
    target_port: int = 8000
    interface: str = Field(default_factory=_default_iface)
    promiscuous_mode: bool = True
    active_timeout: int = 2
    idle_timeout: int = 1
    sample_rate_ms: int = 1000


class PortMonitorStats(BaseModel):
    monitored_port: int
    engine_mode: str  # "native_nfstream" or "emulated_stream"
    status: str       # "running" or "stopped"
    total_flows: int
    total_packets: int
    total_bytes: int
    current_packets_per_sec: float
    current_kb_per_sec: float
    threat_flows_count: int
    active_connections: int
    protocol_distribution: Dict[str, int]
    top_sources: List[Dict[str, Any]]


class NetworkTrafficMonitor:
    """
    Manages network flow monitoring on a specific port.
    Integrates NFStream with safe fallback and automated IDS threat assessment.
    """
    def __init__(self, target_port: int = 8000):
        self.config = PortMonitorConfig(target_port=target_port)
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Engine mode detection
        self.has_native = HAS_NFSTREAM
        self.engine_mode = "native_nfstream" if HAS_NFSTREAM else "emulated_stream"

        # Telemetry metrics
        self.flows: List[FlowRecord] = []
        self.max_flow_history = 300
        self.total_flows_count = 0
        self.total_packets_count = 0
        self.total_bytes_count = 0
        self.threat_flows_count = 0
        self.protocol_counts = {"TCP": 0, "UDP": 0, "ICMP": 0}
        self.top_sources_map: Dict[str, int] = {}
        
        # Rate tracking
        self.last_rate_check = time.time()
        self.packets_in_window = 0
        self.bytes_in_window = 0
        self.current_pps = 0.0
        self.current_kbps = 0.0

        # Model predictor reference (lazy loaded)
        self._model = None
        self._scaler = None
        self._encoder = None
        self._feature_names = None
        self._model_loaded = False

    def _try_load_model(self):
        """Attempt to load the pre-trained IDS model for real-time flow classification."""
        if self._model_loaded:
            return
        try:
            import joblib
            from soc.backend.app.config import settings
            model_path = settings.model_path
            if (model_path / "model.pkl").exists():
                self._model = joblib.load(model_path / "model.pkl")
                self._encoder = joblib.load(model_path / "label_encoder.pkl")
                self._scaler = joblib.load(model_path / "scaler.pkl")
                self._feature_names = joblib.load(model_path / "feature_names.pkl")
                self._model_loaded = True
                logger.info("IDS Model successfully loaded into Network Traffic Monitor.")
        except Exception as e:
            logger.warning(f"Could not load IDS model for real-time flow tagging: {e}")
            self._model_loaded = False

    def start(self, port: Optional[int] = None):
        """Start monitoring traffic on the target port."""
        with self._lock:
            if port is not None:
                self.config.target_port = port
            if self.is_running:
                logger.info(f"Monitor is already running on port {self.config.target_port}.")
                return
            self._stop_event.clear()
            self.is_running = True
            self._try_load_model()
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            logger.info(f"Traffic monitoring started on port {self.config.target_port} (mode: {self.engine_mode})")

    def stop(self):
        """Stop monitoring."""
        with self._lock:
            if not self.is_running:
                return
            self._stop_event.set()
            self.is_running = False
            logger.info(f"Traffic monitoring stopped on port {self.config.target_port}.")
        if self._thread and self._thread.is_alive():
            try:
                self._thread.join(timeout=0.6)
            except Exception:
                pass

    def set_port(self, port: int):
        """Dynamically switch the monitored port."""
        restart = self.is_running
        if restart:
            self.stop()
        self.config.target_port = port
        if restart:
            self.start(port)

    def _run_loop(self):
        """Main monitoring loop."""
        # Try native capture first if NFStream is imported
        if self.has_native and NFStreamer is not None:
            try:
                bpf = f"port {self.config.target_port}"
                source_iface = self.config.interface
                if source_iface == "any" or not source_iface:
                    if IS_MACOS:
                        # On macOS, the "any" pseudo-device does not exist in BSD BPF.
                        # None lets NFStreamer auto-select the active default interface (e.g. en0).
                        source_iface = None
                    else:
                        # On Linux the libpcap "any" pseudo-device captures across all
                        # interfaces; passing None here fails with "specify a valid
                        # network interface name as source". Keep the literal "any".
                        source_iface = "any"

                logger.info(f"Attempting native NFStreamer tap on interface: {source_iface or 'auto'} (filter: '{bpf}')")
                streamer = NFStreamer(
                    source=source_iface,
                    bpf_filter=bpf,
                    promiscuous_mode=self.config.promiscuous_mode,
                    idle_timeout=self.config.idle_timeout,
                    active_timeout=self.config.active_timeout,
                )
                self.engine_mode = "native_nfstream"
                for flow in streamer:
                    if self._stop_event.is_set():
                        break
                    self._record_native_flow(flow)
                return
            except PermissionError as pe:
                if IS_MACOS:
                    logger.warning(
                        f"macOS BPF permission denied ({pe}). "
                        "To capture real network packets on MacBook without sudo, run: "
                        "'sudo chmod o+r /dev/bpf*' in Terminal, or launch with sudo. "
                        "Switching to safe emulation stream."
                    )
                else:
                    logger.warning(f"Packet capture permission error ({pe}). Switching to emulation stream.")
                self.engine_mode = "emulated_stream"
            except Exception as e:
                logger.warning(f"Native NFStreamer execution error ({e}). Switching to emulation stream.")
                self.engine_mode = "emulated_stream"


        # Fallback stream generator
        self._run_emulation_loop()

    def _record_native_flow(self, flow: Any):
        """Record flow data from native NFStreamer flow object."""
        try:
            proto = "TCP" if getattr(flow, "protocol", 6) == 6 else ("UDP" if getattr(flow, "protocol", 17) == 17 else "OTHER")
            pkts = int(getattr(flow, "bidirectional_packets", 1))
            bytes_len = int(getattr(flow, "bidirectional_bytes", 64))
            dur = float(getattr(flow, "bidirectional_duration_ms", 10.0))
            app = str(getattr(flow, "application_name", f"port_{self.config.target_port}"))

            # Best-effort live classification by the IDS model (if artifacts loaded).
            label, conf, is_threat = self._classify_native(flow)

            rec = FlowRecord(
                id=f"flow-{int(time.time() * 1000)}-{random.randint(100, 999)}",
                timestamp=datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3],
                src_ip=str(getattr(flow, "src_ip", "192.168.1.100")),
                src_port=int(getattr(flow, "src_port", random.randint(1024, 65535))),
                dst_ip=str(getattr(flow, "dst_ip", "10.0.0.1")),
                dst_port=int(getattr(flow, "dst_port", self.config.target_port)),
                protocol=proto,
                application_name=app,
                bidirectional_packets=pkts,
                bidirectional_bytes=bytes_len,
                duration_ms=dur,
                threat_label=label,
                is_threat=is_threat,
                confidence=conf,
                risk_score=5.0,
            )
            self._append_flow(rec)
        except Exception as err:
            logger.error(f"Error parsing native flow: {err}")

    def _classify_native(self, flow: Any) -> tuple:
        """Classify a live NFStream flow with the IDS model.

        Returns ``(label, confidence_fraction, is_threat)``. Falls back to benign
        when the model artifacts are absent or the flow's features cannot be
        aligned to the model's expected columns (see docs/ASSUMPTIONS.md §2 and
        DEMO_SIMULATION.md §6 — the training set has no IP columns and live
        NFStream features won't line up 1:1, so this is best-effort).
        """
        if not self._model_loaded or self._model is None or self._feature_names is None:
            # No ML artifacts: fall back to the flow-metadata heuristic detector so
            # real network-layer attacks on the monitored target still surface.
            return self._heuristic_classify(flow)
        try:
            import numpy as np

            # Build a feature vector aligned to the model's expected columns,
            # pulling any same-named attribute off the NFStream flow, 0-filling
            # the rest. Unknown columns stay 0 rather than crashing the capture.
            row = []
            for name in self._feature_names:
                attr = str(name).strip().lower().replace(" ", "_")
                val = getattr(flow, attr, None)
                try:
                    row.append(float(val) if val is not None else 0.0)
                except (TypeError, ValueError):
                    row.append(0.0)
            X = np.array([row], dtype=float)
            if self._scaler is not None:
                X = self._scaler.transform(X)

            pred = self._model.predict(X)
            label = str(self._encoder.inverse_transform(pred)[0]) if self._encoder is not None else str(pred[0])

            conf = 0.90
            if hasattr(self._model, "predict_proba"):
                proba = self._model.predict_proba(X)[0]
                conf = float(np.max(proba))

            is_threat = label.strip().lower() not in ("benign", "benign traffic", "normal")
            return (label, conf, is_threat)
        except Exception as e:
            logger.debug(f"Live model classification failed, using heuristic: {e}")
            return self._heuristic_classify(flow)

    # Ports where a burst of short sessions from one source looks like a
    # credential brute-force rather than normal traffic.
    _AUTH_PORTS = {21, 22, 23, 389, 445, 1433, 3306, 3389, 5432, 5900}

    def _heuristic_classify(self, flow: Any) -> tuple:
        """Signature-free, flow-metadata heuristic detector used when no ML model
        is loaded. Recognises clear NETWORK-layer attack shapes from NFStream's
        per-flow counters (packets/bytes/duration/ports). Deliberately conservative
        so normal web browsing of the target is not flagged.

        Cannot see HTTP payloads, so application-layer attacks (SQLi/XSS/login
        abuse against Juice Shop) are invisible here by design — only network-layer
        attacks (floods, scans, auth brute force) are detectable from flow shape.
        The SOC's correlation + repeat-offender logic aggregates these per source.
        """
        try:
            pkts = int(getattr(flow, "bidirectional_packets", 0) or 0)
            nbytes = int(getattr(flow, "bidirectional_bytes", 0) or 0)
            dur = float(getattr(flow, "bidirectional_duration_ms", 0.0) or 0.0)
            proto = int(getattr(flow, "protocol", 6) or 6)
            dst_port = int(getattr(flow, "dst_port", 0) or 0)
            bytes_per_pkt = nbytes / pkts if pkts else 0.0

            # 1) Flood: a single flow carrying a large burst of tiny packets.
            #    Real HTTP flows carry far more bytes/packet, so this won't trip
            #    on page loads. UDP vs SYN(TCP) by protocol.
            if pkts >= 200 and bytes_per_pkt <= 100:
                if proto == 17:
                    return ("DoS UDP Flood", 0.80, True)
                return ("DoS SYN Flood", 0.80, True)

            # 2) Recon scan probe: a connection with no real payload — a bare
            #    SYN/SYN-ACK/RST exchange, the shape nmap leaves on each probed
            #    port. A refused probe is ~2 packets / ~130 bytes; allow a little
            #    headroom while staying far below any real data flow (a tiny HTTP
            #    GET is already ~12 packets / ~1900 bytes).
            if pkts <= 4 and nbytes <= 300 and dur <= 200.0:
                return ("Recon OS Scan", 0.62, True)

            # 3) Auth brute force: short repeated sessions against a login service.
            #    Only meaningful when the monitored service is an auth port.
            if dst_port in self._AUTH_PORTS and 3 <= pkts <= 40 and dur <= 3000.0:
                return ("Dictionary Brute Force", 0.68, True)

            return ("Benign Traffic", 0.95, False)
        except Exception as e:
            logger.debug(f"Heuristic classify fell back to benign: {e}")
            return ("Benign Traffic", 0.95, False)

    def _run_emulation_loop(self):
        """Generate representative flow traffic on target port with attack scenarios."""
        target_port = self.config.target_port
        app_names = {
            80: "HTTP",
            443: "HTTPS",
            8000: "SOC-REST-API",
            22: "SSH",
            53: "DNS",
            3000: "SOC-Dashboard",
            8080: "HTTP-Proxy",
        }
        app_name = app_names.get(target_port, f"Custom-Port-{target_port}")

        known_attackers = ["192.168.1.105", "10.0.0.99", "185.220.101.5", "45.154.255.88", "198.51.100.24"]
        known_clients = ["10.0.0.15", "10.0.0.22", "192.168.1.50", "172.16.0.4", "10.66.0.12"]
        target_server = "10.10.1.5"

        while not self._stop_event.is_set():
            if self._stop_event.wait(timeout=random.uniform(0.3, 0.7)):
                break


            # 15% chance of simulated anomalous/attack traffic on this port
            is_anomaly = random.random() < 0.15
            
            if is_anomaly:
                src_ip = random.choice(known_attackers)
                src_port = random.randint(1024, 65530)
                threats = [
                    ("DoS SYN Flood", 88.5, 92.0),
                    ("Dictionary Brute Force", 82.0, 78.5),
                    ("Recon OS Scan", 65.0, 71.0),
                    ("DoS UDP Flood", 79.0, 85.0),
                ]
                threat_label, conf, risk = random.choice(threats)
                protocol = "UDP" if "UDP" in threat_label else "TCP"
                packets = random.randint(40, 250)
                bytes_len = packets * random.randint(64, 512)
                duration = random.uniform(5.0, 350.0)
                is_threat_bool = True
            else:
                src_ip = random.choice(known_clients)
                src_port = random.randint(30000, 65000)
                threat_label = "Benign Traffic"
                conf = round(random.uniform(96.0, 99.8), 1)
                risk = round(random.uniform(2.0, 15.0), 1)
                protocol = "UDP" if target_port == 53 else "TCP"
                packets = random.randint(4, 30)
                bytes_len = packets * random.randint(128, 1460)
                duration = random.uniform(10.0, 800.0)
                is_threat_bool = False

            rec = FlowRecord(
                id=f"flow-{int(time.time() * 1000)}-{random.randint(100, 999)}",
                timestamp=datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3],
                src_ip=src_ip,
                src_port=src_port,
                dst_ip=target_server,
                dst_port=target_port,
                protocol=protocol,
                application_name=app_name,
                bidirectional_packets=packets,
                bidirectional_bytes=bytes_len,
                duration_ms=round(duration, 2),
                threat_label=threat_label,
                is_threat=is_threat_bool,
                confidence=conf,
                risk_score=risk,
            )
            self._append_flow(rec)

    def _append_flow(self, rec: FlowRecord):
        """Append flow record and update metrics."""
        with self._lock:
            self.flows.insert(0, rec)
            if len(self.flows) > self.max_flow_history:
                self.flows.pop()

            self.total_flows_count += 1
            self.total_packets_count += rec.bidirectional_packets
            self.total_bytes_count += rec.bidirectional_bytes
            if rec.is_threat:
                self.threat_flows_count += 1

            self.protocol_counts[rec.protocol] = self.protocol_counts.get(rec.protocol, 0) + 1
            self.top_sources_map[rec.src_ip] = self.top_sources_map.get(rec.src_ip, 0) + rec.bidirectional_packets

            # Rate estimation
            now = time.time()
            elapsed = now - self.last_rate_check
            self.packets_in_window += rec.bidirectional_packets
            self.bytes_in_window += rec.bidirectional_bytes

            if elapsed >= 1.0:
                self.current_pps = round(self.packets_in_window / elapsed, 1)
                self.current_kbps = round((self.bytes_in_window / 1024.0) / elapsed, 2)
                self.packets_in_window = 0
                self.bytes_in_window = 0
                self.last_rate_check = now

        # Feed the decision engine OUTSIDE the lock (DB work must not block
        # get_status / other appends). Benign flows are telemetry-only.
        self._dispatch_to_engine(rec)

    def _dispatch_to_engine(self, rec: "FlowRecord") -> None:
        """Run the full decision pipeline for a threat-candidate flow.

        Resilient by contract: any failure here must never kill the capture
        thread, so all errors are swallowed with a warning. Benign flows are
        skipped cheaply before a DB session is opened.
        """
        if rec.threat_label == "Benign Traffic" and not rec.is_threat:
            return
        try:
            from soc.backend.app.db.session import SessionLocal
            from soc.backend.app.policy.loader import get_policy
            from soc.backend.app.decision.pipeline import process_flow

            policy = get_policy()
            db = SessionLocal()
            try:
                result = process_flow(
                    db,
                    policy,
                    src_ip=rec.src_ip,
                    dst_ip=rec.dst_ip,
                    src_port=rec.src_port,
                    dst_port=rec.dst_port,
                    label=rec.threat_label,
                    confidence=rec.confidence,
                    model_version=f"monitor:{self.engine_mode}",
                    raw_features={
                        "protocol": rec.protocol,
                        "bidirectional_packets": rec.bidirectional_packets,
                        "bidirectional_bytes": rec.bidirectional_bytes,
                        "duration_ms": rec.duration_ms,
                        "application_name": rec.application_name,
                    },
                )
                if result:
                    logger.info(
                        "Decision raised: incident=%s family=%s risk=%s tier=%s rule=%s mode=%s",
                        result["incident_id"], result["family"], result["risk_score"],
                        result["tier"], result["rule_id"], result["mode"],
                    )
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Decision pipeline dispatch failed for flow {rec.id}: {e}")

    def get_status(self) -> PortMonitorStats:
        """Get live operational stats for the monitored port."""
        with self._lock:
            # Sort top sources
            sorted_sources = sorted(
                [{"ip": ip, "packets": pkts} for ip, pkts in self.top_sources_map.items()],
                key=lambda x: x["packets"],
                reverse=True
            )[:5]

            return PortMonitorStats(
                monitored_port=self.config.target_port,
                engine_mode=self.engine_mode,
                status="running" if self.is_running else "stopped",
                total_flows=self.total_flows_count,
                total_packets=self.total_packets_count,
                total_bytes=self.total_bytes_count,
                current_packets_per_sec=self.current_pps,
                current_kb_per_sec=self.current_kbps,
                threat_flows_count=self.threat_flows_count,
                active_connections=min(len(self.top_sources_map), 42),
                protocol_distribution=dict(self.protocol_counts),
                top_sources=sorted_sources,
            )

    def get_flows(self, limit: int = 50, threat_only: bool = False) -> List[FlowRecord]:
        """Get recent flows on the monitored port."""
        with self._lock:
            result = self.flows
            if threat_only:
                result = [f for f in result if f.is_threat]
            return result[:limit]

    def clear(self):
        """Flush flow history."""
        with self._lock:
            self.flows.clear()


# Global singleton instance for network monitoring
traffic_monitor = NetworkTrafficMonitor(target_port=8000)
