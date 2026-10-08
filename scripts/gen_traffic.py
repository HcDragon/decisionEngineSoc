#!/usr/bin/env python3
"""
No-sudo lab traffic generator for the SOC Manager.

Generates REAL packets (captured by NFStream) whose flow shapes trip the SOC's
heuristic detector, without needing nmap/hping3/root. Targets the host's primary
non-loopback IP by default (loopback 127.0.0.1 is allowlisted and suppressed).

Modes:
  recon  : many short TCP connects to a CLOSED port  -> 'Recon OS Scan'
  flood  : one connection pushing a burst of tiny packets to a built-in sink
           -> 'DoS SYN Flood'

Usage:
  python3 gen_traffic.py recon  --port 9999 --count 60
  python3 gen_traffic.py flood  --port 9900 --packets 500
"""
import argparse
import socket
import sys
import threading
import time


def primary_ip() -> str:
    """Best-effort primary non-loopback IPv4 of this host."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def run_recon(target: str, port: int, count: int, duration: float = 7.0) -> None:
    """Rapid TCP connects to a (closed) port: each yields a tiny SYN/RST flow.
    Spread over `duration` seconds so the traffic reliably overlaps the live
    capture window (a sub-second burst can miss NFStream's warm-up)."""
    ok = 0
    gap = max(0.01, duration / max(1, count))
    for i in range(count):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.3)
        try:
            s.connect((target, port))   # expected to refuse (closed port)
            s.close()
        except (ConnectionRefusedError, OSError):
            ok += 1
        time.sleep(gap)
    print(f"[recon] sent {count} connect probes to {target}:{port} over ~{duration:.0f}s (refused/closed: {ok})")


def _sink(port: int, stop: threading.Event) -> None:
    """Tiny echo sink so the flood has a peer and packets flow on the port."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", port))
    srv.listen(8)
    srv.settimeout(0.5)
    conns = []
    while not stop.is_set():
        try:
            c, _ = srv.accept()
            c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            conns.append(c)
            threading.Thread(target=_echo, args=(c, stop), daemon=True).start()
        except socket.timeout:
            continue
        except OSError:
            break
    for c in conns:
        try:
            c.close()
        except OSError:
            pass
    srv.close()


def _echo(c: socket.socket, stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            data = c.recv(16)
            if not data:
                break
            c.sendall(b".")
        except OSError:
            break


def run_flood(target: str, port: int, packets: int, duration: float = 7.0) -> None:
    """One connection, many tiny round-trips -> a single high-packet, low-byte
    flow that matches the DoS flood signature. Sustained over `duration` seconds
    so the flow reliably spans the live capture window."""
    stop = threading.Event()
    t = threading.Thread(target=_sink, args=(port, stop), daemon=True)
    t.start()
    time.sleep(0.6)
    c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    c.connect((target, port))
    sent = 0
    end = time.time() + duration
    # Keep sending for the whole duration, at least `packets` round-trips.
    while sent < packets or time.time() < end:
        try:
            c.sendall(b"x")      # 1 byte -> tiny packet (Nagle disabled)
            c.recv(4)
            sent += 1
            if sent % 50 == 0:
                time.sleep(0.01)  # pace so it spans the window, stays well >200 pkts
        except OSError:
            break
    c.close()
    time.sleep(0.3)
    stop.set()
    print(f"[flood] pushed {sent} tiny packets over one connection to {target}:{port} (~{duration:.0f}s)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["recon", "flood"])
    ap.add_argument("--target", default=None, help="target IP (default: primary non-loopback IP)")
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--count", type=int, default=60, help="recon: number of connect probes")
    ap.add_argument("--packets", type=int, default=500, help="flood: tiny packets to send")
    args = ap.parse_args()
    target = args.target or primary_ip()
    print(f"[gen] mode={args.mode} target={target} port={args.port}")
    if args.mode == "recon":
        run_recon(target, args.port, args.count)
    else:
        run_flood(target, args.port, args.packets)
    return 0


if __name__ == "__main__":
    sys.exit(main())
