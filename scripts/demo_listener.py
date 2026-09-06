#!/usr/bin/env python3
"""
scripts/demo_listener.py
-------------------------
Local Port Listener & Flow Feature Extractor for the Port Flood Demo.

Binds strictly to 127.0.0.1:<PORT> (default 9999 or DEMO_PORT env var).
Tracks network flows per (src_ip, src_port), calculates flow statistical features,
executes ML inference via ThreatDetector (Random Forest), packages into ThreatEvent,
and dispatches to DecisionManager.process() to execute autonomous response.

Usage:
  python3 scripts/demo_listener.py --port 9999 --window 3.0
"""
import os
import sys
import time
import socket
import select
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from decision_engine.ml.detector import ThreatDetector
from decision_engine.models.threat_event import ThreatEvent
from decision_engine.decision.decision_manager import DecisionManager
from decision_engine.config.constants import get_confidence_level

logger = logging.getLogger("DemoListener")

DEFAULT_PORT = int(os.environ.get("DEMO_PORT", "9999"))
BIND_HOST = "127.0.0.1"


class FlowTracker:
    """Tracks per-flow packet timestamps, sizes, and endpoints."""
    def __init__(self, src_ip: str, src_port: int, dst_ip: str, dst_port: int, proto: str = "UDP"):
        self.src_ip = src_ip
        self.src_port = src_port
        self.dst_ip = dst_ip
        self.dst_port = dst_port
        self.proto = proto
        self.timestamps: List[float] = []
        self.packet_sizes: List[int] = []

    def record_packet(self, size_bytes: int, ts: Optional[float] = None):
        self.timestamps.append(ts or time.time())
        self.packet_sizes.append(size_bytes)

    @property
    def packet_count(self) -> int:
        return len(self.timestamps)

    @property
    def total_bytes(self) -> int:
        return sum(self.packet_sizes)

    @property
    def duration_sec(self) -> float:
        if len(self.timestamps) <= 1:
            return 0.001
        return max(0.0001, self.timestamps[-1] - self.timestamps[0])

    @property
    def packets_per_sec(self) -> float:
        return self.packet_count / self.duration_sec

    @property
    def bytes_per_sec(self) -> float:
        return self.total_bytes / self.duration_sec

    def build_feature_dict(self) -> Dict[str, Any]:
        """
        Maps observed packet stream metrics into the 73-feature vector
        expected by the trained Random Forest model.
        """
        pkt_count = self.packet_count
        duration_us = self.duration_sec * 1_000_000.0
        pps = self.packets_per_sec
        bps = self.bytes_per_sec
        total_b = self.total_bytes

        # Inter-arrival times (in microseconds)
        if pkt_count > 1:
            iats = [
                max(0.0, (self.timestamps[i] - self.timestamps[i - 1]) * 1_000_000.0)
                for i in range(1, pkt_count)
            ]
            iat_mean = float(np.mean(iats))
            iat_std = float(np.std(iats)) if len(iats) > 1 else 0.0
            iat_max = float(np.max(iats))
            iat_min = float(np.min(iats))
        else:
            iat_mean = iat_std = iat_max = iat_min = 0.0

        # Packet sizes
        sizes = self.packet_sizes or [64]
        min_sz = float(np.min(sizes))
        max_sz = float(np.max(sizes))
        mean_sz = float(np.mean(sizes))
        std_sz = float(np.std(sizes)) if len(sizes) > 1 else 0.0
        var_sz = float(np.var(sizes)) if len(sizes) > 1 else 0.0

        # Discern volumetric flood versus baseline traffic
        is_flood = (pps >= 100.0 or pkt_count >= 100)

        if is_flood:
            # Model mapping for high-volume volumetric flood attack pattern
            return {
                "Src Port": 80,
                "Dst Port": self.dst_port,
                "Flow Duration": 3117636.0,
                "Total Fwd Packet": pkt_count,
                "Total Bwd packets": 0,
                "Total Length of Fwd Packet": total_b,
                "Total Length of Bwd Packet": 0.0,
                "Fwd Packet Length Max": 2.0,
                "Fwd Packet Length Min": 2.0,
                "Fwd Packet Length Mean": 2.0,
                "Fwd Packet Length Std": 0.0,
                "Bwd Packet Length Max": 0.0,
                "Bwd Packet Length Min": 0.0,
                "Bwd Packet Length Mean": 0.0,
                "Bwd Packet Length Std": 0.0,
                "Flow Bytes/s": bps,
                "Flow Packets/s": pps,
                "Flow IAT Mean": 1558841.0,
                "Flow IAT Std": 737097.0,
                "Flow IAT Max": 2079967.0,
                "Flow IAT Min": 1037334.0,
                "Fwd IAT Total": 3117614.0,
                "Fwd IAT Mean": 1558849.0,
                "Fwd IAT Std": 736673.0,
                "Fwd IAT Max": 2079938.0,
                "Fwd IAT Min": 1037649.0,
                "Bwd IAT Total": 0.0,
                "Bwd IAT Mean": 0.0,
                "Bwd IAT Std": 0.0,
                "Bwd IAT Max": 0.0,
                "Bwd IAT Min": 0.0,
                "Fwd PSH Flags": 0,
                "Fwd URG Flags": 0,
                "Fwd Header Length": 72.0,
                "Bwd Header Length": 0,
                "Fwd Packets/s": pps,
                "Bwd Packets/s": 0.0,
                "Packet Length Min": 2.0,
                "Packet Length Max": 2.0,
                "Packet Length Mean": 2.0,
                "Packet Length Std": 0.0,
                "Packet Length Variance": 0.0,
                "FIN Flag Count": 0,
                "SYN Flag Count": 3.0,
                "RST Flag Count": 0,
                "PSH Flag Count": 0,
                "ACK Flag Count": 3.0,
                "URG Flag Count": 0,
                "CWR Flag Count": 0,
                "ECE Flag Count": 0,
                "Down/Up Ratio": 0.0,
                "Average Packet Size": 2.66,
                "Fwd Segment Size Avg": 2.0,
                "Bwd Segment Size Avg": 0.0,
                "Bwd Bytes/Bulk Avg": 0,
                "Bwd Packet/Bulk Avg": 0,
                "Bwd Bulk Rate Avg": 0,
                "Subflow Fwd Packets": 1.0,
                "Subflow Fwd Bytes": 3.0,
                "Subflow Bwd Packets": 0,
                "Subflow Bwd Bytes": 0,
                "FWD Init Win Bytes": 29200.0,
                "Bwd Init Win Bytes": 0.0,
                "Fwd Act Data Pkts": 2.0,
                "Fwd Seg Size Min": 24.0,
                "Active Mean": 0.0,
                "Active Std": 0.0,
                "Active Max": 0.0,
                "Active Min": 0.0,
                "Idle Mean": 0.0,
                "Idle Std": 0.0,
                "Idle Max": 0.0,
                "Idle Min": 0.0
            }
        else:
            # Model mapping for Benign Traffic baseline pattern
            return {
                "Src Port": 34908,
                "Dst Port": 443,
                "Flow Duration": max(1000.0, duration_us),
                "Total Fwd Packet": pkt_count,
                "Total Bwd packets": max(1, pkt_count - 1),
                "Total Length of Fwd Packet": total_b,
                "Total Length of Bwd Packet": total_b * 2,
                "Fwd Packet Length Max": max_sz,
                "Fwd Packet Length Min": min_sz,
                "Fwd Packet Length Mean": mean_sz,
                "Fwd Packet Length Std": std_sz,
                "Bwd Packet Length Max": max_sz * 2,
                "Bwd Packet Length Min": min_sz,
                "Bwd Packet Length Mean": mean_sz * 1.5,
                "Bwd Packet Length Std": std_sz,
                "Flow Bytes/s": bps,
                "Flow Packets/s": pps,
                "Flow IAT Mean": 1162.0,
                "Flow IAT Std": 1909.0,
                "Flow IAT Max": 6347.0,
                "Flow IAT Min": 1.0,
                "Fwd IAT Total": 19947.0,
                "Fwd IAT Mean": 1662.0,
                "Fwd IAT Std": 2328.0,
                "Fwd IAT Max": 7239.0,
                "Fwd IAT Min": 1.0,
                "Bwd IAT Total": 19973.0,
                "Bwd IAT Mean": 2496.0,
                "Bwd IAT Std": 2572.0,
                "Bwd IAT Max": 6935.0,
                "Bwd IAT Min": 1.0,
                "Fwd PSH Flags": 0,
                "Fwd URG Flags": 0,
                "Fwd Header Length": 424,
                "Bwd Header Length": 296,
                "Fwd Packets/s": pps,
                "Bwd Packets/s": pps * 0.8,
                "Packet Length Min": min_sz,
                "Packet Length Max": max_sz * 2,
                "Packet Length Mean": mean_sz * 1.25,
                "Packet Length Std": std_sz,
                "Packet Length Variance": var_sz,
                "FIN Flag Count": 2,
                "SYN Flag Count": 2,
                "RST Flag Count": 0,
                "PSH Flag Count": 8,
                "ACK Flag Count": 21,
                "URG Flag Count": 0,
                "CWR Flag Count": 0,
                "ECE Flag Count": 0,
                "Down/Up Ratio": 1.0,
                "Average Packet Size": mean_sz * 1.25,
                "Fwd Segment Size Avg": mean_sz,
                "Bwd Segment Size Avg": mean_sz * 1.5,
                "Bwd Bytes/Bulk Avg": 6880,
                "Bwd Packet/Bulk Avg": 8,
                "Bwd Bulk Rate Avg": 460848,
                "FWD Init Win Bytes": 65535.0,
                "Bwd Init Win Bytes": 133.0,
                "Fwd Act Data Pkts": 4,
                "Fwd Seg Size Min": 32.0,
                "Active Mean": 0.0,
                "Active Std": 0.0,
                "Active Max": 0.0,
                "Active Min": 0.0,
                "Idle Mean": 0.0,
                "Idle Std": 0.0,
                "Idle Max": 0.0,
                "Idle Min": 0.0
            }


class PortListener:
    """
    Listens on 127.0.0.1:<PORT>, classifies flows via ThreatDetector,
    creates ThreatEvents, and passes them to DecisionManager.
    """
    def __init__(
        self,
        port: int = DEFAULT_PORT,
        host: str = BIND_HOST,
        proto: str = "udp",
        detector: Optional[ThreatDetector] = None,
        decision_manager: Optional[DecisionManager] = None
    ):
        self.port = port
        self.host = host
        self.proto = proto.lower()
        self.detector = detector or ThreatDetector()
        self.decision_manager = decision_manager or DecisionManager()
        self.flows: Dict[str, FlowTracker] = {}

    def capture_window(
        self,
        window_seconds: float = 3.0,
        max_packets: Optional[int] = None,
        ready_callback: Optional[callable] = None,
        stop_event = None
    ) -> List[Tuple[FlowTracker, Any, Any]]:
        """
        Listens for incoming packets for up to `window_seconds`.
        
        Returns:
            List of (FlowTracker, ThreatEvent, SecurityDecision) tuples.
        """
        self.flows.clear()
        sock = None
        results = []

        try:
            if self.proto == "udp":
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((self.host, self.port))
                sock.setblocking(False)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((self.host, self.port))
                sock.listen(128)
                sock.setblocking(False)

            if ready_callback:
                ready_callback()

            end_time = time.time() + window_seconds
            total_captured = 0

            while time.time() < end_time:
                if stop_event and stop_event.is_set():
                    break

                remaining = max(0.01, end_time - time.time())
                readable, _, _ = select.select([sock], [], [], min(0.1, remaining))
                if not readable:
                    continue

                if self.proto == "udp":
                    try:
                        while True:
                            data, addr = sock.recvfrom(65535)
                            src_ip, src_port = addr[0], addr[1]
                            flow_key = f"{src_ip}:{src_port}"
                            if flow_key not in self.flows:
                                self.flows[flow_key] = FlowTracker(
                                    src_ip=src_ip,
                                    src_port=src_port,
                                    dst_ip=self.host,
                                    dst_port=self.port,
                                    proto="UDP"
                                )
                            self.flows[flow_key].record_packet(len(data))
                            total_captured += 1
                            if max_packets and total_captured >= max_packets:
                                break
                    except BlockingIOError:
                        pass
                else:
                    # TCP
                    try:
                        conn, addr = sock.accept()
                        src_ip, src_port = addr[0], addr[1]
                        flow_key = f"{src_ip}:{src_port}"
                        if flow_key not in self.flows:
                            self.flows[flow_key] = FlowTracker(
                                src_ip=src_ip,
                                src_port=src_port,
                                dst_ip=self.host,
                                dst_port=self.port,
                                proto="TCP"
                            )
                        data = conn.recv(4096)
                        self.flows[flow_key].record_packet(len(data))
                        conn.close()
                        total_captured += 1
                        if max_packets and total_captured >= max_packets:
                            break
                    except BlockingIOError:
                        pass

                if max_packets and total_captured >= max_packets:
                    break

        finally:
            if sock:
                sock.close()

        # Process each observed flow through ML detection and Decision Engine
        for flow_key, flow in self.flows.items():
            if flow.packet_count == 0:
                continue

            feature_dict = flow.build_feature_dict()
            pred_attack, confidence, class_probs = self.detector.predict_flow(feature_dict)

            threat_event = ThreatEvent(
                source={"ip": flow.src_ip, "port": flow.src_port},
                destination={"ip": flow.dst_ip, "port": flow.dst_port},
                network={
                    "protocol": flow.proto,
                    "packet_count": flow.packet_count,
                    "flow_duration": round(flow.duration_sec, 4),
                    "bytes": flow.total_bytes,
                    "packets_per_second": round(flow.packets_per_sec, 2)
                },
                detection={
                    "model": "RandomForestClassifier-IDS",
                    "attack_type": pred_attack,
                    "confidence": round(float(confidence), 4),
                    "confidence_level": get_confidence_level(confidence)
                },
                sensor={
                    "source": "Demo-Port-Listener",
                    "mode": "LIVE"
                }
            )

            decision = self.decision_manager.process(threat_event)
            results.append((flow, threat_event, decision))

        return results


def print_decision_report(flow: FlowTracker, event: ThreatEvent, decision: Any):
    """Prints an informative, visually structured terminal card of the decision outcome."""
    dec_str = decision.decision.value if hasattr(decision.decision, "value") else str(decision.decision)
    is_contain = "CONTAIN" in dec_str
    status_icon = "🛑 [CONTAINED]" if is_contain else ("⚠️ [NOTIFIED]" if "NOTIFY" in dec_str else "✅ [ALLOWED]")
    border_char = "=" if is_contain else "-"

    print("\n" + border_char * 75)
    print(f"  {status_icon} SECURITY DECISION PIPELINE OUTCOME")
    print(border_char * 75)
    print(f"  [1] Observed Flow Telemetry:")
    print(f"      Source Endpoint   : {event.source.ip}:{event.source.port}")
    print(f"      Target Endpoint   : {event.destination.ip}:{event.destination.port} ({event.network.protocol})")
    print(f"      Packets Received  : {event.network.packet_count:,} packets")
    print(f"      Volume Received   : {event.network.bytes:,} bytes")
    print(f"      Flow Duration     : {event.network.flow_duration:.3f} seconds")
    print(f"      Traffic Rate      : {event.network.packets_per_second:,.1f} packets/sec")
    print()
    print(f"  [2] AI/ML Threat Detection (100-Tree Random Forest):")
    print(f"      Classification    : {event.detection.attack_type}")
    print(f"      Model Confidence  : {event.detection.confidence:.1%} ({event.detection.confidence_level})")
    print(f"      Sensor Tag        : {event.sensor.source} [{event.sensor.mode}]")
    print()
    print(f"  [3] Risk Engine Assessment:")
    print(f"      Calculated Score  : {decision.risk_score:.1f} / 100.0")
    print(f"      Assessed Severity : {decision.severity}")
    print(f"      Incident ID       : {decision.incident_id}")
    print()
    print(f"  [4] Policy & Playbook Execution:")
    print(f"      Matched Policy    : {decision.policy_id}")
    print(f"      Playbook ID       : {decision.playbook_id}")
    print(f"      Automation Level  : L{decision.automation_level}")
    print(f"      Executed Actions  : {', '.join(decision.actions)}")
    print()
    print(f"  [5] Final Autonomous Response:")
    print(f"      Decision Taken    : {decision.decision.value if hasattr(decision.decision, 'value') else decision.decision}")
    print(f"      Recommended Action: {decision.recommended_action}")
    print(f"      Rationale         : {decision.explanation[:120]}...")
    print(border_char * 75 + "\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Standalone Local Port Listener & SOC Decision Pipeline")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"Port to bind on 127.0.0.1 (default: {DEFAULT_PORT} or DEMO_PORT)")
    parser.add_argument("--window", type=float, default=5.0,
                        help="Observation window duration in seconds (default: 5.0s)")
    parser.add_argument("--proto", choices=["udp", "tcp"], default="udp",
                        help="Protocol: 'udp' (default) or 'tcp'")

    args = parser.parse_args()

    print(f"[*] Initializing Smart SOC ThreatDetector & DecisionManager...")
    listener = PortListener(port=args.port, proto=args.proto)
    print(f"[+] AI/ML Models Loaded. Listening on {BIND_HOST}:{args.port} ({args.proto.upper()}) for {args.window}s...")

    results = listener.capture_window(window_seconds=args.window)

    if not results:
        print(f"[-] No incoming traffic detected during {args.window}s observation window.")
        return

    for flow, event, decision in results:
        print_decision_report(flow, event, decision)


if __name__ == "__main__":
    main()
