#!/usr/bin/env python3
"""
Unified End-to-End SOC Pipeline Runner
Connects the AI/ML Intrusion Detection System (Random Forest Classifier)
and the Autonomous SOC Decision Engine (Policies, Playbooks, NFStream Flagged Logs).
"""
import os
import sys
import time
import argparse
import logging
from typing import Optional

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from decision_engine.integrations.ids_bridge import IDSBridge
from decision_engine.integrations.nfstream_sensor import NFStreamSensor
from decision_engine.integrations.flagged_logger import NFStreamFlaggedLogger
from decision_engine.decision.decision_manager import DecisionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("UnifiedPipeline")

def run_pipeline(
    samples: int = 15,
    delay: float = 0.6,
    attack_filter: Optional[str] = None,
    interface: str = "en0",
    use_live_sensor: bool = False
):
    print("=" * 80)
    print("  SMART SOC MANAGER - UNIFIED AI/ML & DECISION ENGINE PIPELINE")
    print("=" * 80)
    print(f"[*] Workspace Root       : {BASE_DIR}")
    print(f"[*] Integrated AIML Dir  : {os.path.join(BASE_DIR, 'aiml')}")
    print(f"[*] Logs Directory       : {os.path.join(BASE_DIR, 'logs')}")
    print(f"[*] Flagged Flow Log     : {os.path.join(BASE_DIR, 'logs', 'nfstream_flagged.log')}")
    print("-" * 80)

    # 1. Initialize AIML Bridge
    logger.info("Loading Random Forest IDS Classifier & Transformers...")
    bridge = IDSBridge()
    if not bridge.is_ready:
        logger.error("Failed to load Random Forest model artifacts! Check aiml/ directory.")
        sys.exit(1)
    
    logger.info(
        "Random Forest Model Ready: %d trees, %d features, %d classes: %s",
        getattr(bridge.model, "n_estimators", 100),
        len(bridge.feature_names),
        len(bridge.encoder.classes_),
        list(bridge.encoder.classes_)
    )

    # 2. Initialize NFStream Sensor & Flagged Logger
    flagged_logger = NFStreamFlaggedLogger()
    sensor = NFStreamSensor(interface=interface, ids_bridge=bridge, flagged_logger=flagged_logger)
    
    # 3. Initialize Autonomous Decision Engine
    logger.info("Initializing Autonomous SOC Decision Engine (11-stage pipeline)...")
    decision_manager = DecisionManager()

    print("\n" + "=" * 80)
    print("  COMMENCING TRAFFIC INGESTION & AUTONOMOUS REMEDIATION PIPELINE")
    print(f"  Target Samples: {samples} | Delay: {delay}s | Filter: {attack_filter or 'ALL FLOWS'}")
    print("=" * 80 + "\n")

    count = 0
    flagged_count = 0
    mitigated_count = 0

    # Select stream source
    if use_live_sensor and sensor._has_nfstream:
        logger.info("Streaming from LIVE network interface: %s", interface)
        stream_gen = sensor.stream_live(max_flows=samples)
    else:
        logger.info("Streaming real network flows from integrated CICIDS2017 dataset...")
        stream_gen = bridge.stream_dataset(n_samples=samples, delay_seconds=delay, attack_type_filter=attack_filter)

    for threat_event, meta in stream_gen:
        count += 1
        predicted = meta.get("predicted", threat_event.detection.attack_type)
        conf = float(meta.get("confidence", threat_event.detection.confidence))
        actual = meta.get("actual")
        is_attack = "Benign" not in predicted

        # Flagged flow logging
        flow_dict = {
            "source_ip": threat_event.source.ip,
            "source_port": threat_event.source.port,
            "destination_ip": threat_event.destination.ip,
            "destination_port": threat_event.destination.port,
            "protocol": threat_event.network.protocol,
            "packet_count": threat_event.network.packet_count,
            "flow_duration": threat_event.network.flow_duration,
            "bytes": threat_event.network.bytes
        }
        flagged_rec = flagged_logger.log_flow(flow_dict, predicted, conf)

        if is_attack:
            flagged_count += 1
            status_tag = "⚠️  FLAGGED [ATTACK]"
        else:
            status_tag = "✅ NORMAL [BYPASS]"

        match_info = f" (Actual: {actual})" if actual else ""
        print(f"[{count:02d}/{samples:02d}] {status_tag} {predicted:<24} Conf: {conf*100:>5.1f}%{match_info}")
        print(f"      5-Tuple: {threat_event.source.ip}:{threat_event.source.port} -> {threat_event.destination.ip}:{threat_event.destination.port} [{threat_event.network.protocol}]")

        # Ingest into Decision Engine
        decision = decision_manager.process(threat_event)
        
        # Display Decision Engine orchestration results
        dec_type = decision.decision.value if hasattr(decision.decision, "value") else str(decision.decision)
        auto_lvl = f"Level {decision.automation_level}"
        risk = decision.risk_score
        actions = getattr(decision, "actions", [])
        
        if decision.incident_status in ("AUTO_MITIGATED", "CONTAINED", "MANUAL_MITIGATED"):
            mitigated_count += 1

        print(f"      Decision Engine : Decision: {dec_type:<8} | Risk: {risk:>5.1f}/100 | {auto_lvl} | Policy: {decision.policy_id}")
        if actions:
            print(f"      Actions Executed: {actions}")
        if decision.explanation:
            print(f"      Explanation     : {decision.explanation[:85]}...")
        print("-" * 80)

        if delay > 0 and (count < samples):
            time.sleep(delay)

    print("\n" + "=" * 80)
    print("  PIPELINE EXECUTION COMPLETE")
    print(f"  Total Ingested Flows : {count}")
    print(f"  Flagged Threat Flows : {flagged_count}")
    print(f"  Remediated Incidents : {mitigated_count}")
    print(f"  Flagged Log File     : {flagged_logger.flagged_log_file}")
    print("=" * 80 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Unified SOC Decision Engine & AIML Pipeline Runner")
    parser.add_argument("--samples", type=int, default=15, help="Number of flow packets to stream (default: 15)")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between flows in seconds (default: 0.5)")
    parser.add_argument("--filter", type=str, default=None, help="Filter by attack type (e.g. 'DoS SYN Flood')")
    parser.add_argument("--interface", type=str, default="en0", help="Network interface for live sniffing (default: en0)")
    parser.add_argument("--live", action="store_true", help="Use live hardware NFStream capture instead of dataset replay")
    args = parser.parse_args()

    run_pipeline(
        samples=args.samples,
        delay=args.delay,
        attack_filter=args.filter,
        interface=args.interface,
        use_live_sensor=args.live
    )

if __name__ == "__main__":
    main()
