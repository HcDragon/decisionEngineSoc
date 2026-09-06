#!/usr/bin/env python3
"""
scripts/run_demo.py
--------------------
Master runner script for the Standalone "Port Flood -> Detect -> Decide -> Respond" Demo.

Executes both an Attack Burst (Port Flood) and a Benign Traffic Baseline
against a local port listener on 127.0.0.1, exercising the full SOC decision pipeline:
  Telemetry Capture -> ML Feature Extraction -> Random Forest Classification ->
  Risk Calculation -> Policy Engine -> Playbook Execution -> Closed-Loop Verification.

Usage:
  python3 scripts/run_demo.py
  python3 scripts/run_demo.py --port 9999 --proto udp
"""
import os
import sys
import time
import threading
import argparse
from typing import List, Tuple, Any

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts.demo_flood_generator import run_generator, TARGET_HOST
from scripts.demo_listener import PortListener, print_decision_report, FlowTracker
from decision_engine.models.threat_event import ThreatEvent


def print_banner():
    banner = r"""
================================================================================
   STANDALONE PORT FLOOD -> DETECT -> DECIDE -> RESPOND SOC PIPELINE DEMO
================================================================================
  Demonstrating the full closed-loop autonomous incident response engine:
    1. Local Traffic Generator (127.0.0.1)
    2. Real-time Flow Feature Extraction
    3. AI/ML Threat Classification (100-Tree Random Forest)
    4. Multi-Factor Contextual Risk Assessment
    5. Priority-Driven Policy Matching
    6. Autonomous SOAR Playbook Execution & Closed-Loop Outcome Verification
================================================================================
"""
    print(banner)


def run_scenario(
    name: str,
    mode: str,
    port: int,
    proto: str,
    gen_count: int,
    gen_duration: float,
    listener_window: float
) -> Tuple[FlowTracker, ThreatEvent, Any]:
    """Runs a single listener-capture scenario and returns (flow, event, decision)."""
    print(f"\n{'='*75}")
    print(f"  RUNNING SCENARIO: {name}")
    print(f"{'='*75}")

    listener = PortListener(port=port, proto=proto)
    capture_results = []
    ready_evt = threading.Event()

    def listener_thread():
        results = listener.capture_window(
            window_seconds=listener_window,
            ready_callback=lambda: ready_evt.set()
        )
        capture_results.extend(results)

    # 1. Start listener thread
    t = threading.Thread(target=listener_thread, daemon=True)
    t.start()

    # Wait for listener to bind socket
    ready_evt.wait(timeout=2.0)
    time.sleep(0.1)

    # 2. Trigger traffic generator
    gen_stats = run_generator(
        mode=mode,
        port=port,
        count=gen_count,
        duration=gen_duration,
        proto=proto,
        host=TARGET_HOST,
        quiet=False
    )

    # 3. Wait for listener window to complete
    t.join(timeout=listener_window + 2.0)

    if not capture_results:
        raise RuntimeError(f"Scenario '{name}' failed: Listener did not record any packets.")

    flow, event, decision = capture_results[0]
    print_decision_report(flow, event, decision)
    return flow, event, decision


def print_comparison_table(attack_res, benign_res):
    """Prints a clear side-by-side comparison summary between Attack and Benign flows."""
    att_flow, att_event, att_dec = attack_res
    ben_flow, ben_event, ben_dec = benign_res

    att_decision_str = att_dec.decision.value if hasattr(att_dec.decision, "value") else str(att_dec.decision)
    ben_decision_str = ben_dec.decision.value if hasattr(ben_dec.decision, "value") else str(ben_dec.decision)

    print("\n" + "#"*80)
    print("                      DEMO PIPELINE COMPARISON SUMMARY")
    print("#"*80)
    fmt = "{:<26} | {:<24} | {:<24}"
    print(fmt.format("PIPELINE STAGE / METRIC", "SCENARIO 1: PORT FLOOD", "SCENARIO 2: BENIGN BASELINE"))
    print("-" * 80)
    print(fmt.format("Traffic Profile", "High-Rate Burst", "Low-Rate Steady Flow"))
    print(fmt.format("Packets Observed", f"{att_event.network.packet_count:,} pkts", f"{ben_event.network.packet_count:,} pkts"))
    print(fmt.format("Volume Observed", f"{att_event.network.bytes:,} bytes", f"{ben_event.network.bytes:,} bytes"))
    print(fmt.format("Observed Rate", f"{att_event.network.packets_per_second:,.1f} pps", f"{ben_event.network.packets_per_second:,.1f} pps"))
    print(fmt.format("Target Endpoint", f"{att_event.destination.ip}:{att_event.destination.port}", f"{ben_event.destination.ip}:{ben_event.destination.port}"))
    print("-" * 80)
    print(fmt.format("AI/ML Classification", att_event.detection.attack_type, ben_event.detection.attack_type))
    print(fmt.format("Detection Confidence", f"{att_event.detection.confidence:.1%}", f"{ben_event.detection.confidence:.1%}"))
    print(fmt.format("Risk Engine Score", f"{att_dec.risk_score:.1f} ({att_dec.severity})", f"{ben_dec.risk_score:.1f} ({ben_dec.severity})"))
    print(fmt.format("Matched Policy", att_dec.policy_id, ben_dec.policy_id))
    print(fmt.format("SOAR Playbook", att_dec.playbook_id, ben_dec.playbook_id))
    print(fmt.format("Automation Level", f"Level {att_dec.automation_level}", f"Level {ben_dec.automation_level}"))
    att_icon = "🛑 " if "CONTAIN" in att_decision_str else ("⚠️ " if "NOTIFY" in att_decision_str else "✅ ")
    ben_icon = "🛑 " if "CONTAIN" in ben_decision_str else ("⚠️ " if "NOTIFY" in ben_decision_str else "✅ ")
    print(fmt.format("FINAL DECISION", f"{att_icon}{att_decision_str}", f"{ben_icon}{ben_decision_str}"))
    print("#"*80)
    print("  [✓] All pipeline stages executed successfully in full autonomy.\n")


def main():
    parser = argparse.ArgumentParser(description="Master Runner for Port Flood Demo")
    parser.add_argument("--port", type=int, default=int(os.environ.get("DEMO_PORT", "9999")),
                        help="Port on 127.0.0.1 to use for demo (default: 9999)")
    parser.add_argument("--proto", choices=["udp", "tcp"], default="udp",
                        help="Socket protocol: 'udp' (default) or 'tcp'")

    args = parser.parse_args()

    print_banner()

    # Scenario 1: Port Flood Attack
    attack_result = run_scenario(
        name="Volumetric Port Flood Attack (SYN / UDP Burst)",
        mode="attack",
        port=args.port,
        proto=args.proto,
        gen_count=1500,
        gen_duration=1.2,
        listener_window=2.5
    )

    # Brief breather between scenarios
    time.sleep(1.0)

    # Scenario 2: Benign Baseline Traffic
    benign_result = run_scenario(
        name="Normal Benign Heartbeat / Operational Traffic",
        mode="benign",
        port=args.port,
        proto=args.proto,
        gen_count=6,
        gen_duration=2.0,
        listener_window=3.0
    )

    # Side-by-side comparison
    print_comparison_table(attack_result, benign_result)


if __name__ == "__main__":
    main()
