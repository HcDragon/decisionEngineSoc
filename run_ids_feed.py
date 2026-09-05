"""
IDS Live Feed Runner
Streams real network traffic flows from L:\\AimlProject\\ids_project through the
Random Forest ML model and pushes classified Threat Events into the Decision Engine.
"""
import sys
import time
import argparse
import logging
import requests

from decision_engine.integrations.ids_bridge import IDSBridge
from decision_engine.decision.decision_manager import DecisionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("IDSFeed")

def main():
    parser = argparse.ArgumentParser(description="Stream real IDS packet flows into the Smart SOC Decision Engine.")
    parser.add_argument("--samples", type=int, default=20, help="Total flow samples to stream (default: 20)")
    parser.add_argument("--delay", type=float, default=0.8, help="Delay in seconds between events (default: 0.8)")
    parser.add_argument("--filter", type=str, default=None, help="Filter by specific attack type")
    parser.add_argument("--api", action="store_true", help="Send events via HTTP REST API rather than direct engine")
    parser.add_argument("--endpoint", type=str, default="http://127.0.0.1:8000/api/v1/decision/analyze", help="API URL")
    args = parser.parse_args()

    logger.info("Initializing IDS Bridge connecting to L:\\AimlProject\\ids_project...")
    bridge = IDSBridge()
    if not bridge.is_ready:
        logger.error("Failed to load IDS model or feature artifacts from L:\\AimlProject\\ids_project")
        sys.exit(1)

    manager = None
    if not args.api:
        logger.info("Operating in direct in-process Decision Engine mode.")
        manager = DecisionManager()
    else:
        logger.info("Operating in HTTP mode targeting %s", args.endpoint)

    print("\n" + "=" * 70)
    print("  SMART SOC MANAGER - LIVE IDS INGESTION & ORCHESTRATION FEED")
    print(f"  Streaming {args.samples} flows | Delay: {args.delay}s | Filter: {args.filter or 'ALL'}")
    print("=" * 70 + "\n")

    count = 0
    for threat_event, meta in bridge.stream_dataset(n_samples=args.samples, delay_seconds=args.delay, attack_type_filter=args.filter):
        count += 1
        predicted = meta["predicted"]
        conf = meta["confidence"]
        actual = meta["actual"]
        match_symbol = "✓" if (predicted == actual) else "!"

        print(f"[{count:>3}/{args.samples}] [{match_symbol}] IDS Detection: {predicted:<24} (Conf: {conf*100:>5.1f}%) | Actual: {str(actual):<18}")
        print(f"      Source: {threat_event.source.ip}:{threat_event.source.port} -> Target: {threat_event.destination.ip}:{threat_event.destination.port}")

        if args.api:
            try:
                payload = threat_event.model_dump() if hasattr(threat_event, "model_dump") else threat_event.dict()
                resp = requests.post(args.endpoint, json=payload, timeout=5)
                if resp.status_code == 200:
                    dec = resp.json()
                    print(f"      Decision: {dec.get('decision')} | Risk: {dec.get('risk_score'):.1f} | Policy: {dec.get('policy_id')} | Status: {dec.get('incident_status')}")
                else:
                    print(f"      API Error {resp.status_code}: {resp.text}")
            except Exception as e:
                print(f"      Failed to send to API: {e}")
        else:
            decision = manager.process(threat_event)
            print(f"      Decision: {decision.decision.value} | Risk: {decision.risk_score:.1f} | Policy: {decision.policy_id} | Status: {decision.incident_status}")

        print("-" * 70)

    print(f"\nCompleted streaming {count} flows into Decision Engine.\n")

if __name__ == "__main__":
    main()
