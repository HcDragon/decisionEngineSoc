"""Rate-based detection layer tests (TC-RATE-*).

Covers the two cross-flow / volumetric attacks the per-flow ML model cannot see:
a SYN flood collapsed into one out-of-distribution mega-flow, and SSH brute
force whose signal only exists across many short flows. These feed the decision
pipeline as override alerts (model_version = "rate-rule:*").
"""
from soc.backend.app.monitor.rate_rules import RateDetector


def _flood_flow(**kw):
    base = dict(src_ip="10.66.0.20", dst_ip="10.66.0.10", dst_port=22,
                packets=300_000, syn=293_000, ack=10, duration_ms=2000.0)
    base.update(kw)
    return base


# --- Rule 1: volumetric flood ------------------------------------------------

def test_flood_by_packets_per_second():
    """TC-RATE-FLOOD-PPS: a huge pps flow -> DoS SYN Flood override."""
    d = RateDetector()
    alert = d.inspect(**_flood_flow(), now=100.0)
    assert alert is not None
    assert alert["label"] == "DoS SYN Flood"
    assert alert["detector"] == "rate-rule:flood"
    assert alert["is_threat"] is True
    # deterministic rule -> high confidence + margin so R-CRIT-AUTO gates pass
    assert alert["confidence"] >= 0.85 and alert["margin"] >= 0.30


def test_flood_pps_does_not_fire_on_tiny_short_flow():
    """TC-RATE-FLOOD-FLOOR: a 2-packet RST flow with near-zero duration computes
    a bogus huge pps (NFStream packets/duration artifact) — the absolute packet
    floor must stop the flood rule from firing. Regression for the false
    'DoS SYN Flood 99%' on a 2-packet reverse flow during a brute-force run."""
    d = RateDetector()
    # 10.66.0.10:22 -> 10.66.0.20:35368, 2 packets, ~0.2ms -> pps ~ 10000
    alert = d.inspect(src_ip="10.66.0.10", dst_ip="10.66.0.20", dst_port=35368,
                      packets=2, syn=0, ack=1, duration_ms=0.2, now=50.0)
    assert alert is None


def test_flood_by_syn_skew_without_high_pps():
    """TC-RATE-FLOOD-SYN: low pps but SYN>>ACK still trips the flood rule."""
    d = RateDetector()
    # 600 SYN / 1 ACK over 100s -> pps = 6 (below 1000) but skew fires
    alert = d.inspect(src_ip="1.2.3.4", dst_ip="10.0.0.1", dst_port=80,
                      packets=600, syn=600, ack=1, duration_ms=100_000.0, now=5.0)
    assert alert is not None and alert["label"] == "DoS SYN Flood"


def test_flood_cooldown_suppresses_repeat_alerts():
    """TC-RATE-FLOOD-COOL: one flood shouldn't alert on every subsequent flow."""
    d = RateDetector()
    first = d.inspect(**_flood_flow(), now=100.0)
    second = d.inspect(**_flood_flow(), now=101.0)   # within cooldown
    assert first is not None and second is None
    # after cooldown expires it can fire again
    later = d.inspect(**_flood_flow(), now=100.0 + d.cooldown_s + 1)
    assert later is not None


# --- Rule 2: auth brute force ------------------------------------------------

def test_bruteforce_fires_after_threshold_short_flows():
    """TC-RATE-BRUTE: N short flows from one src to an auth port in-window."""
    d = RateDetector(brute_count=5, brute_window_s=10.0)
    results = []
    for i in range(5):
        results.append(d.inspect(src_ip="10.66.0.20", dst_ip="10.66.0.10",
                                  dst_port=22, packets=3, syn=1, ack=1,
                                  duration_ms=40.0, now=100.0 + i))
    # first four are individually benign (None); the fifth crosses the threshold
    assert results[:4] == [None, None, None, None]
    assert results[4] is not None
    assert results[4]["label"] == "Dictionary Brute Force"
    assert results[4]["detector"] == "rate-rule:bruteforce"


def test_bruteforce_window_expiry_resets_count():
    """TC-RATE-BRUTE-WIN: attempts spread beyond the window don't accumulate."""
    d = RateDetector(brute_count=5, brute_window_s=10.0)
    fired = False
    for i in range(8):
        # 4s apart -> only ~2-3 ever co-exist inside a 10s window
        a = d.inspect(src_ip="9.9.9.9", dst_ip="10.0.0.1", dst_port=22,
                      packets=3, syn=1, ack=1, duration_ms=40.0, now=i * 4.0)
        fired = fired or (a is not None)
    assert fired is False


def test_bruteforce_ignores_non_auth_ports():
    """TC-RATE-BRUTE-PORT: many short flows to a web port are not brute force."""
    d = RateDetector(brute_count=5, brute_window_s=10.0)
    alerts = [d.inspect(src_ip="8.8.8.8", dst_ip="10.0.0.1", dst_port=443,
                        packets=3, syn=1, ack=1, duration_ms=40.0, now=100.0 + i)
              for i in range(10)]
    assert all(a is None for a in alerts)


# --- negative: normal traffic ------------------------------------------------

def test_benign_flow_returns_no_alert():
    """TC-RATE-BENIGN: a normal data flow trips neither rule."""
    d = RateDetector()
    alert = d.inspect(src_ip="10.0.0.15", dst_ip="10.0.0.1", dst_port=443,
                      packets=24, syn=1, ack=22, duration_ms=800.0, now=100.0)
    assert alert is None
