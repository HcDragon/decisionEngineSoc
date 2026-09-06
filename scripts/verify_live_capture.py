"""
Step 5 Verification Script — Live NFStream Capture (Read-Only)
Captures up to 20 real flows from the active interface, classifies them
via the Random Forest IDS model, and prints results. Does NOT call
DecisionManager.process() or any downstream pipeline stage.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decision_engine.integrations.nfstream_sensor import NFStreamSensor
from decision_engine.integrations.ids_bridge import IDSBridge

INTERFACE = os.environ.get("NFSTREAM_INTERFACE", "en0")
MAX_FLOWS = 20

def main():
    print(f"[*] Interface      : {INTERFACE}")
    bridge = IDSBridge()
    sensor = NFStreamSensor(interface=INTERFACE, ids_bridge=bridge)

    print(f"[*] sensor.is_available : {sensor.is_available}")
    if not sensor.is_available:
        print("[!] NFStream not available or IDS model not ready. Aborting.")
        sys.exit(1)

    print(f"[*] Capturing up to {MAX_FLOWS} live flows from {INTERFACE} ...\n")
    print(f"{'#':<4} {'SRC IP:PORT':<25} {'DST IP:PORT':<25} {'ATTACK TYPE':<30} {'CONF':>6}")
    print("-" * 95)

    count = 0
    for threat_event, meta in sensor.stream_live(max_flows=MAX_FLOWS):
        count += 1
        src = f"{threat_event.source.ip}:{threat_event.source.port}"
        dst = f"{threat_event.destination.ip}:{threat_event.destination.port}"
        attack = meta.get("predicted", "Unknown")
        conf = meta.get("confidence", 0.0)
        print(f"{count:<4} {src:<25} {dst:<25} {attack:<30} {conf:>6.2%}")

    print(f"\n[+] Captured and classified {count} flows.")
    print(f"[+] Flagged flows logged to: logs/nfstream_flagged.log")

if __name__ == "__main__":
    main()
