#!/usr/bin/env python3
"""
No-sudo lab traffic generator for the SOC Manager.

Generates REAL packets (captured by NFStream) whose flow shapes trip the SOC's
heuristic detector, without needing nmap/hping3/root. Targets the host's primary
non-loopback IP by default (loopback 127.0.0.1 is allowlisted and suppressed).

Modes:
  recon    : many short TCP connects to a CLOSED port  -> 'Recon OS Scan'
  flood    : one TCP connection pushing a burst of tiny packets to a built-in
             sink -> 'DoS SYN Flood' (dos_flood)
  udpflood : one UDP socket firing a high-rate burst of tiny datagrams at a
             port -> dos_flood (trips the rate-rule pps branch). Used by the
             UDP-flood and DNS-flood scenarios; needs no hping3/root.
  brute    : many short-lived TCP connects to an AUTH port (22/21/23/3389/...)
             -> 'Dictionary Brute Force' (brute_force). Each connect is its own
             2-3 packet flow; >=5 within the detector's window trip the rule.
             Needs no hydra -- the signal is the burst of short auth flows.

Usage:
  python3 attack/gen_traffic.py recon     --port 9999 --count 60
  python3 attack/gen_traffic.py flood     --port 9900 --packets 500
  python3 attack/gen_traffic.py udpflood  --port 53   --packets 20000
  python3 attack/gen_traffic.py brute     --port 22   --count 16
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


def run_udpflood(target: str, port: int, packets: int, duration: float = 6.0) -> None:
    """One connected UDP socket firing many tiny datagrams at `target:port`.

    A connected UDP socket keeps a single stable ephemeral source port, so every
    datagram belongs to ONE 5-tuple flow -- NFStream aggregates them into a
    single high-packet-count flow that trips the rate-rule flood branch
    (packets >= SOC_FLOOD_MIN_PKTS and pps >= SOC_FLOOD_PPS). Spread over
    `duration` so the flow reliably spans the live capture window while keeping
    the per-second rate well above the pps threshold (default needs >1000 pps)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((target, port))        # fixes the source port -> one flow
    sent = 0
    end = time.time() + duration
    # Pace in small batches so the burst spans `duration` instead of finishing
    # in a sub-second blip (which can miss NFStream's warm-up), yet still pushes
    # thousands of packets/sec.
    batch = max(1, packets // max(1, int(duration * 200)))
    while sent < packets or time.time() < end:
        for _ in range(batch):
            try:
                s.send(b"x")         # 1-byte datagram -> tiny packet
                sent += 1
            except OSError:
                break
        time.sleep(0.005)
        if sent >= packets and time.time() >= end:
            break
    s.close()
    rate = sent / duration if duration else sent
    print(f"[udpflood] pushed {sent} UDP datagrams to {target}:{port} "
          f"over ~{duration:.0f}s (~{int(rate)} pkts/s)")


def run_brute(target: str, port: int, count: int, duration: float = 7.0) -> None:
    """Many short-lived TCP connects to an AUTH port, one flow each.

    The rate detector flags brute force on >=5 short flows from one source to
    the same auth port within its window (default 10s). Each connect here -- it
    completes the handshake if the port is open, or is refused if closed --
    is an individual 2-3 packet flow, so a burst of `count` of them trips
    'Dictionary Brute Force' without hydra. Spread across `duration` so the
    flows land inside one detector window and the live capture."""
    done = 0
    gap = max(0.01, duration / max(1, count))
    for _ in range(count):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.4)
        try:
            s.connect((target, port))
            # Minimal auth-shaped exchange so open-port flows stay short.
            try:
                s.sendall(b"USER admin\r\n")
                s.recv(32)
            except OSError:
                pass
            s.close()
        except (ConnectionRefusedError, OSError):
            pass
        done += 1
        time.sleep(gap)
    print(f"[brute] made {done} short auth connects to {target}:{port} "
          f"over ~{duration:.0f}s")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["recon", "flood", "udpflood", "brute"])
    ap.add_argument("--target", default=None, help="target IP (default: primary non-loopback IP)")
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--count", type=int, default=60, help="recon/brute: number of probes/connects")
    ap.add_argument("--packets", type=int, default=500, help="flood/udpflood: tiny packets to send")
    args = ap.parse_args()
    target = args.target or primary_ip()
    print(f"[gen] mode={args.mode} target={target} port={args.port}")
    if args.mode == "recon":
        run_recon(target, args.port, args.count)
    elif args.mode == "flood":
        run_flood(target, args.port, args.packets)
    elif args.mode == "udpflood":
        run_udpflood(target, args.port, args.packets)
    else:
        run_brute(target, args.port, args.count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
