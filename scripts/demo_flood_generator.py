#!/usr/bin/env python3
"""
scripts/demo_flood_generator.py
--------------------------------
Synthetic traffic generator for the Port Flood Demo.

Sends packets strictly to 127.0.0.1 (local loopback).
WARNING: This is a synthetic self-test tool intended ONLY for local
demonstration with demo_listener.py. Never point at remote or production hosts.

Modes:
  --mode attack : High-frequency burst of packets simulating a volumetric port flood.
  --mode benign : Low-rate, evenly-spaced packet transmission simulating normal baseline traffic.

Usage:
  python3 scripts/demo_flood_generator.py --mode attack --port 9999
  python3 scripts/demo_flood_generator.py --mode benign --port 9999
"""
import os
import sys
import time
import socket
import argparse
from typing import Dict, Any

DEFAULT_PORT = int(os.environ.get("DEMO_PORT", "9999"))
TARGET_HOST = "127.0.0.1"  # STRICT: Local loopback only!


def run_generator(
    mode: str = "attack",
    port: int = DEFAULT_PORT,
    count: int = 1500,
    duration: float = 1.5,
    proto: str = "udp",
    host: str = TARGET_HOST,
    quiet: bool = False
) -> Dict[str, Any]:
    """
    Generates synthetic packets to host:port.
    
    Returns:
        Dict summarizing packets_sent, bytes_sent, elapsed_sec, pps, bps.
    """
    # Safety assertion: prevent accidental redirection
    if host not in ("127.0.0.1", "localhost"):
        raise ValueError(f"Safety Violation: Traffic must stay on 127.0.0.1, got '{host}'")

    proto = proto.lower()
    if not quiet:
        mode_label = "PORT FLOOD (ATTACK)" if mode == "attack" else "BENIGN BASELINE"
        print(f"\n[*] ==================================================")
        print(f"[*] Starting Traffic Generator: [{mode_label}]")
        print(f"[*] Target      : {host}:{port} ({proto.upper()})")
        print(f"[*] Planned     : {count} packets over ~{duration:.1f}s")
        print(f"[*] ==================================================")

    packets_sent = 0
    bytes_sent = 0
    start_time = time.time()

    if proto == "udp":
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            if mode == "attack":
                # High-speed burst
                payload = b"SYNTHETIC_PORT_FLOOD_BURST_PAYLOAD_PKT_#"
                interval = duration / max(1, count)
                next_time = start_time
                for i in range(count):
                    data = payload + str(i).encode("ascii")
                    sock.sendto(data, (host, port))
                    packets_sent += 1
                    bytes_sent += len(data)
                    # Tight micro-pacing if needed, otherwise fire burst
                    if interval > 0.001:
                        next_time += interval
                        sleep_time = next_time - time.time()
                        if sleep_time > 0:
                            time.sleep(sleep_time)
            else:
                # Benign mode: slow, steady pace (e.g. 5-10 packets spaced out)
                benign_count = min(count, 10)
                interval = duration / max(1, benign_count)
                payload = b"BENIGN_HEARTBEAT_STATUS_OK_MSG_#"
                for i in range(benign_count):
                    data = payload + str(i).encode("ascii")
                    sock.sendto(data, (host, port))
                    packets_sent += 1
                    bytes_sent += len(data)
                    time.sleep(interval)
        finally:
            sock.close()
    else:
        # TCP mode (connects and sends payload)
        payload = b"DEMO_TCP_DATA_BURST_"
        if mode == "attack":
            for i in range(count):
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.5)
                    s.connect((host, port))
                    data = payload + str(i).encode("ascii")
                    s.sendall(data)
                    packets_sent += 1
                    bytes_sent += len(data)
                    s.close()
                except Exception:
                    # Port may drop connections under flood
                    pass
        else:
            benign_count = min(count, 5)
            interval = duration / max(1, benign_count)
            for i in range(benign_count):
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(1.0)
                    s.connect((host, port))
                    data = payload + str(i).encode("ascii")
                    s.sendall(data)
                    packets_sent += 1
                    bytes_sent += len(data)
                    s.close()
                except Exception as e:
                    if not quiet:
                        print(f"[!] TCP connection error: {e}")
                time.sleep(interval)

    elapsed = max(0.0001, time.time() - start_time)
    pps = packets_sent / elapsed
    bps = bytes_sent / elapsed

    stats = {
        "mode": mode,
        "packets_sent": packets_sent,
        "bytes_sent": bytes_sent,
        "elapsed_sec": round(elapsed, 4),
        "pps": round(pps, 2),
        "bps": round(bps, 2),
        "target": f"{host}:{port}",
        "protocol": proto.upper()
    }

    if not quiet:
        print(f"[+] Generator Finished: {packets_sent} packets ({bytes_sent} bytes) sent in {elapsed:.3f}s")
        print(f"[+] Average Packet Rate: {pps:.1f} pkts/sec | Throughput: {bps:.1f} bytes/sec\n")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Synthetic Port Flood Demo Traffic Generator (127.0.0.1)")
    parser.add_argument("--mode", choices=["attack", "benign"], default="attack",
                        help="Traffic profile: 'attack' (flood burst) or 'benign' (low steady rate)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"Target port on 127.0.0.1 (default: {DEFAULT_PORT} or DEMO_PORT)")
    parser.add_argument("--count", type=int, default=None,
                        help="Number of packets to send (default: 1500 for attack, 6 for benign)")
    parser.add_argument("--duration", type=float, default=None,
                        help="Approximate burst duration in seconds (default: 1.5s for attack, 3.0s for benign)")
    parser.add_argument("--proto", choices=["udp", "tcp"], default="udp",
                        help="Socket protocol: 'udp' (default) or 'tcp'")

    args = parser.parse_args()

    count = args.count if args.count is not None else (1500 if args.mode == "attack" else 6)
    duration = args.duration if args.duration is not None else (1.5 if args.mode == "attack" else 3.0)

    run_generator(
        mode=args.mode,
        port=args.port,
        count=count,
        duration=duration,
        proto=args.proto
    )


if __name__ == "__main__":
    main()
