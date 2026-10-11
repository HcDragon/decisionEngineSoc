"""NFStream flow -> IDS model feature adapter.

The `ids_project` RandomForest was trained on CICFlowMeter-style features (72
columns, see ``ids_project/feature_names.pkl``). NFStream exposes the same
underlying flow statistics but under different attribute names and units, so a
live NFStream flow cannot be fed to the model directly — the naive
``getattr(flow, name.lower().replace(" ", "_"))`` mapping resolves only 1 of 72
columns (``Dst Port``) and leaves the rest zero, which the model reads as benign.

This module maps each model feature to the NFStream attribute(s) that carry the
same quantity, converting units where CICFlowMeter and NFStream disagree:

  * CICFlowMeter durations / inter-arrival times are MICROSECONDS; NFStream's
    ``*_duration_ms`` / ``*_piat_ms`` are MILLISECONDS -> multiply by 1000.
  * Rates (Bytes/s, Packets/s) are computed from bidirectional totals over the
    flow's duration in seconds.
  * CICFlowMeter "Fwd" == NFStream ``src2dst``; "Bwd" == ``dst2src``.

Requires the NFStreamer to run with ``statistical_analysis=True`` so the
per-direction packet-size (`*_ps`), inter-arrival (`*_piat_ms`) and TCP-flag
(`*_syn_packets` ...) attributes are populated.

A handful of CICFlowMeter features have no NFStream equivalent (TCP header
length, bulk-transfer averages, init window bytes, active/idle split); those are
0-filled. ``UNMAPPED`` lists them so the coverage is explicit rather than silent.
"""
from __future__ import annotations

from typing import Any, List, Tuple

# Model features with no NFStream source (explicitly 0-filled, not silently).
UNMAPPED = {
    "Fwd Header Length", "Bwd Header Length",
    "Bwd Bytes/Bulk Avg", "Bwd Packet/Bulk Avg", "Bwd Bulk Rate Avg",
    "FWD Init Win Bytes", "Bwd Init Win Bytes",
    "Active Mean", "Active Std", "Active Max", "Active Min",
    "Idle Mean", "Idle Std", "Idle Max", "Idle Min",
}


def _f(flow: Any, name: str, default: float = 0.0) -> float:
    """Read an NFStream attribute as float, tolerating absence/None/garbage."""
    v = getattr(flow, name, None)
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def flow_feature_map(flow: Any) -> dict:
    """Map one NFStream flow to {model_feature_name: value} (CIC units)."""
    dur_ms = _f(flow, "bidirectional_duration_ms")
    dur_s = dur_ms / 1000.0 if dur_ms > 0 else 0.0
    fwd_pkts = _f(flow, "src2dst_packets")
    bwd_pkts = _f(flow, "dst2src_packets")
    bi_pkts = _f(flow, "bidirectional_packets")
    bi_bytes = _f(flow, "bidirectional_bytes")
    fwd_bytes = _f(flow, "src2dst_bytes")
    bwd_bytes = _f(flow, "dst2src_bytes")
    bi_std_ps = _f(flow, "bidirectional_stddev_ps")

    US = 1000.0  # ms -> us
    return {
        "Dst Port": _f(flow, "dst_port"),
        "Flow Duration": dur_ms * US,
        "Total Fwd Packet": fwd_pkts,
        "Total Bwd packets": bwd_pkts,
        "Total Length of Fwd Packet": fwd_bytes,
        "Total Length of Bwd Packet": bwd_bytes,
        "Fwd Packet Length Max": _f(flow, "src2dst_max_ps"),
        "Fwd Packet Length Min": _f(flow, "src2dst_min_ps"),
        "Fwd Packet Length Mean": _f(flow, "src2dst_mean_ps"),
        "Fwd Packet Length Std": _f(flow, "src2dst_stddev_ps"),
        "Bwd Packet Length Max": _f(flow, "dst2src_max_ps"),
        "Bwd Packet Length Min": _f(flow, "dst2src_min_ps"),
        "Bwd Packet Length Mean": _f(flow, "dst2src_mean_ps"),
        "Bwd Packet Length Std": _f(flow, "dst2src_stddev_ps"),
        "Flow Bytes/s": bi_bytes / dur_s if dur_s else 0.0,
        "Flow Packets/s": bi_pkts / dur_s if dur_s else 0.0,
        "Flow IAT Mean": _f(flow, "bidirectional_mean_piat_ms") * US,
        "Flow IAT Std": _f(flow, "bidirectional_stddev_piat_ms") * US,
        "Flow IAT Max": _f(flow, "bidirectional_max_piat_ms") * US,
        "Flow IAT Min": _f(flow, "bidirectional_min_piat_ms") * US,
        "Fwd IAT Total": _f(flow, "src2dst_duration_ms") * US,
        "Fwd IAT Mean": _f(flow, "src2dst_mean_piat_ms") * US,
        "Fwd IAT Std": _f(flow, "src2dst_stddev_piat_ms") * US,
        "Fwd IAT Max": _f(flow, "src2dst_max_piat_ms") * US,
        "Fwd IAT Min": _f(flow, "src2dst_min_piat_ms") * US,
        "Bwd IAT Total": _f(flow, "dst2src_duration_ms") * US,
        "Bwd IAT Mean": _f(flow, "dst2src_mean_piat_ms") * US,
        "Bwd IAT Std": _f(flow, "dst2src_stddev_piat_ms") * US,
        "Bwd IAT Max": _f(flow, "dst2src_max_piat_ms") * US,
        "Bwd IAT Min": _f(flow, "dst2src_min_piat_ms") * US,
        "Fwd PSH Flags": _f(flow, "src2dst_psh_packets"),
        "Fwd URG Flags": _f(flow, "src2dst_urg_packets"),
        "Fwd Header Length": 0.0,
        "Bwd Header Length": 0.0,
        "Fwd Packets/s": fwd_pkts / dur_s if dur_s else 0.0,
        "Bwd Packets/s": bwd_pkts / dur_s if dur_s else 0.0,
        "Packet Length Min": _f(flow, "bidirectional_min_ps"),
        "Packet Length Max": _f(flow, "bidirectional_max_ps"),
        "Packet Length Mean": _f(flow, "bidirectional_mean_ps"),
        "Packet Length Std": bi_std_ps,
        "Packet Length Variance": bi_std_ps * bi_std_ps,
        "FIN Flag Count": _f(flow, "bidirectional_fin_packets"),
        "SYN Flag Count": _f(flow, "bidirectional_syn_packets"),
        "RST Flag Count": _f(flow, "bidirectional_rst_packets"),
        "PSH Flag Count": _f(flow, "bidirectional_psh_packets"),
        "ACK Flag Count": _f(flow, "bidirectional_ack_packets"),
        "URG Flag Count": _f(flow, "bidirectional_urg_packets"),
        "CWR Flag Count": _f(flow, "bidirectional_cwr_packets"),
        "ECE Flag Count": _f(flow, "bidirectional_ece_packets"),
        "Down/Up Ratio": (bwd_pkts / fwd_pkts) if fwd_pkts else 0.0,
        "Average Packet Size": _f(flow, "bidirectional_mean_ps"),
        "Fwd Segment Size Avg": _f(flow, "src2dst_mean_ps"),
        "Bwd Segment Size Avg": _f(flow, "dst2src_mean_ps"),
        "Bwd Bytes/Bulk Avg": 0.0,
        "Bwd Packet/Bulk Avg": 0.0,
        "Bwd Bulk Rate Avg": 0.0,
        "Subflow Fwd Packets": fwd_pkts,
        "Subflow Fwd Bytes": fwd_bytes,
        "Subflow Bwd Packets": bwd_pkts,
        "Subflow Bwd Bytes": bwd_bytes,
        "FWD Init Win Bytes": 0.0,
        "Bwd Init Win Bytes": 0.0,
        "Fwd Act Data Pkts": fwd_pkts,
        "Fwd Seg Size Min": _f(flow, "src2dst_min_ps"),
        "Active Mean": 0.0, "Active Std": 0.0, "Active Max": 0.0, "Active Min": 0.0,
        "Idle Mean": 0.0, "Idle Std": 0.0, "Idle Max": 0.0, "Idle Min": 0.0,
    }


def build_feature_row(flow: Any, feature_names: List[str]) -> Tuple[List[float], int]:
    """Return (ordered values aligned to feature_names, count of real-mapped features).

    The second element is how many columns were populated from an actual NFStream
    attribute (excludes the deliberately 0-filled UNMAPPED set and anything the
    model expects that this adapter doesn't know), for one-time coverage logging.
    """
    fmap = flow_feature_map(flow)
    row = [float(fmap.get(name, 0.0)) for name in feature_names]
    mapped = sum(1 for n in feature_names if n in fmap and n not in UNMAPPED)
    return row, mapped
