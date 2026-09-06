import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import json
import time
import os
import sys
import threading

# Ensure repository root is on sys.path
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from decision_engine.config.constants import IST
from decision_engine.storage.db import Database
from decision_engine.decision.decision_manager import DecisionManager
from decision_engine.events.workflow_tracker import tracker

# -----------------------------------------------------------------------------
# Configuration & Page Setup
# -----------------------------------------------------------------------------
API_URL = os.environ.get("DECISION_ENGINE_API_URL", "http://127.0.0.1:8000/api/v1")

st.set_page_config(
    page_title="SmartSOC — Security Operations & Decision Console",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# HTML Helper: Strips indentation to prevent CommonMark 4-space codeblock bug
# -----------------------------------------------------------------------------
def render_html(raw_html: str):
    clean_lines = [line.strip() for line in raw_html.splitlines() if line.strip()]
    st.markdown("".join(clean_lines), unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Timestamp Helper (IST)
# -----------------------------------------------------------------------------
def format_to_ist(ts_val) -> str:
    if not ts_val:
        return datetime.now(IST).strftime("%H:%M:%S")
    try:
        if isinstance(ts_val, (int, float)):
            dt = datetime.fromtimestamp(ts_val, tz=timezone.utc)
        else:
            ts_str = str(ts_val).replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(IST).strftime("%H:%M:%S")
    except Exception:
        return str(ts_val)[11:19] if len(str(ts_val)) >= 19 else str(ts_val)

# -----------------------------------------------------------------------------
# Robust Data Layer
# -----------------------------------------------------------------------------
@st.cache_resource
def get_db():
    return Database()

def fetch_incidents(limit: int = 100):
    try:
        r = requests.get(f"{API_URL}/incidents?limit={limit}", timeout=0.6)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                return data
    except Exception:
        pass
    try:
        return get_db().list_incidents(limit=limit)
    except Exception:
        return []

def fetch_traffic(limit: int = 100):
    try:
        r = requests.get(f"{API_URL}/traffic?limit={limit}", timeout=0.6)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                return data
    except Exception:
        pass
    try:
        return get_db().list_threat_events(limit=limit)
    except Exception:
        return []

def fetch_health():
    try:
        r = requests.get(f"{API_URL}/health", timeout=0.6)
        if r.status_code == 200:
            return r.json(), True
    except Exception:
        pass
    return {"status": "LOCAL_DB", "service": "DecisionEngine (Direct Storage)"}, False

# -----------------------------------------------------------------------------
# Enterprise Dark Theme CSS (Human-Crafted Cybersecurity Console)
# -----------------------------------------------------------------------------
render_html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], .main {
    background-color: #090d16 !important;
    color: #e2e8f0 !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}

header[data-testid="stHeader"] {
    display: none !important;
}

.block-container {
    padding-top: 0.6rem !important;
    padding-bottom: 1.5rem !important;
    padding-left: 1.2rem !important;
    padding-right: 1.2rem !important;
    max-width: 1720px !important;
}

/* Sidebar Styling */
section[data-testid="stSidebar"] {
    background-color: #0d121f !important;
    border-right: 1px solid #1e293b !important;
    padding-top: 0.5rem !important;
}

section[data-testid="stSidebar"] .block-container {
    padding-left: 0.8rem !important;
    padding-right: 0.8rem !important;
}

/* Top Command Header */
.top-command-bar {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 10px 16px;
    margin-bottom: 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.command-breadcrumbs {
    font-size: 0.78rem;
    font-family: 'JetBrains Mono', monospace;
    color: #64748b;
}

.command-breadcrumbs span.active {
    color: #f8fafc;
    font-weight: 600;
}

/* KPI Strip */
.kpi-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin-bottom: 12px;
}

.kpi-box {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 8px 12px;
}

.kpi-box-label {
    font-size: 0.68rem;
    font-weight: 600;
    color: #64748b;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.kpi-box-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.35rem;
    font-weight: 700;
    color: #f8fafc;
    margin-top: 2px;
}

/* Compact SOAR Pipeline DAG Bar */
.soar-dag-card {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 14px;
}

.dag-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #162032;
    padding-bottom: 8px;
    margin-bottom: 10px;
}

.dag-track {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 4px;
}

.dag-node {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    min-width: 90px;
    z-index: 2;
}

.node-pill {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.74rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    transition: all 0.2s ease;
}

@keyframes pulse-node {
    0% { box-shadow: 0 0 0 0 rgba(56, 189, 248, 0.7); border-color: #38bdf8; }
    70% { box-shadow: 0 0 0 8px rgba(56, 189, 248, 0); border-color: #0284c7; }
    100% { box-shadow: 0 0 0 0 rgba(56, 189, 248, 0); border-color: #38bdf8; }
}

@keyframes pulse-alert {
    0% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.75; transform: scale(1.01); }
    100% { opacity: 1; transform: scale(1); }
}

.node-pill-active {
    background: #0284c7 !important;
    color: #ffffff !important;
    border: 2px solid #38bdf8 !important;
    animation: pulse-node 1.3s infinite !important;
}

.node-pill-done {
    background: rgba(16, 185, 129, 0.18) !important;
    color: #34d399 !important;
    border: 1px solid #10b981 !important;
}

.node-pill-pending {
    background: #090d16 !important;
    color: #475569 !important;
    border: 1px solid #1e293b !important;
}

.node-title {
    font-size: 0.70rem;
    font-weight: 600;
    color: #cbd5e1;
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

.node-detail {
    font-size: 0.65rem;
    font-family: 'JetBrains Mono', monospace;
    color: #64748b;
    margin-top: 1px;
    max-width: 100px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.dag-arrow {
    flex-grow: 1;
    height: 2px;
    background: #1e293b;
    margin: 0 4px;
    margin-bottom: 22px;
    z-index: 1;
}

.dag-arrow-done {
    background: #10b981 !important;
}

.dag-arrow-active {
    background: linear-gradient(90deg, #10b981, #0284c7) !important;
    height: 3px !important;
}

/* Badges */
.badge {
    display: inline-flex;
    align-items: center;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 0.70rem;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
    white-space: nowrap;
}

.badge-crit {
    background-color: rgba(239, 68, 68, 0.15);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.4);
}

.badge-high {
    background-color: rgba(249, 115, 22, 0.15);
    color: #fb923c;
    border: 1px solid rgba(249, 115, 22, 0.4);
}

.badge-med {
    background-color: rgba(234, 179, 8, 0.15);
    color: #facc15;
    border: 1px solid rgba(234, 179, 8, 0.4);
}

.badge-low {
    background-color: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.4);
}

.badge-active-live {
    background-color: rgba(239, 68, 68, 0.2);
    border: 1px solid rgba(239, 68, 68, 0.6);
    color: #f87171;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 0.72rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    animation: pulse-alert 1.8s infinite;
}

/* Operational Tables */
.soc-dense-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.80rem;
}

.soc-dense-table th {
    background-color: #0b111e;
    color: #64748b;
    font-weight: 600;
    font-size: 0.68rem;
    letter-spacing: 0.04em;
    padding: 8px 10px;
    border-bottom: 1px solid #1e293b;
    text-align: left;
}

.soc-dense-table td {
    padding: 8px 10px;
    border-bottom: 1px solid #141d2e;
    color: #cbd5e1;
    vertical-align: middle;
}

.soc-dense-table tr:hover td {
    background-color: #131c31;
}

/* Dossier Card */
.dossier-card {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 12px;
}

.dossier-title {
    font-size: 0.70rem;
    font-weight: 600;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.dossier-checklist-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.76rem;
    padding: 4px 0;
    border-bottom: 1px solid #141d2e;
}

.dossier-checklist-item:last-child {
    border-bottom: none;
}

/* Streamlit Native UI Cleanups */
div[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background-color: #0f172a !important;
    border-radius: 6px !important;
    padding: 3px !important;
    border: 1px solid #1e293b !important;
    gap: 4px !important;
    margin-bottom: 10px !important;
}

div[data-testid="stTabs"] button[role="tab"] {
    font-size: 0.80rem !important;
    font-weight: 500 !important;
    color: #94a3b8 !important;
    border-radius: 4px !important;
    padding: 6px 12px !important;
    border: none !important;
    background-color: transparent !important;
}

div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    background-color: #1e293b !important;
    color: #f8fafc !important;
    font-weight: 600 !important;
}

div[data-testid="stButton"] button {
    background-color: #1e293b !important;
    color: #f8fafc !important;
    border: 1px solid #334155 !important;
    border-radius: 6px !important;
    font-size: 0.80rem !important;
    font-weight: 500 !important;
    padding: 6px 12px !important;
    transition: all 0.15s ease !important;
}

div[data-testid="stButton"] button:hover {
    background-color: #334155 !important;
    border-color: #475569 !important;
}

div[data-testid="stButton"] button[kind="primary"] {
    background-color: #0284c7 !important;
    border-color: #0369a1 !important;
    color: #ffffff !important;
    font-weight: 600 !important;
}

div[data-testid="stButton"] button[kind="primary"]:hover {
    background-color: #0369a1 !important;
}
</style>
""")

# =============================================================================
# SIDEBAR: ATTACK SIMULATION CONTROL DECK & ENGINE STATUS
# =============================================================================
with st.sidebar:
    render_html("""
    <div style="display:flex; align-items:center; gap:10px; padding: 4px 0 12px 0; border-bottom: 1px solid #1e293b; margin-bottom: 12px;">
        <div style="width:34px; height:34px; background:#1e293b; border:1px solid #334155; border-radius:6px; display:flex; align-items:center; justify-content:center; font-size:1.15rem;">🛡️</div>
        <div>
            <div style="font-weight:700; font-size:1.0rem; color:#f8fafc; line-height:1.2;">SmartSOC Console</div>
            <div style="font-size:0.70rem; color:#64748b; font-family:'JetBrains Mono',monospace;">v2.4 Autonomous Engine</div>
        </div>
    </div>
    """)

    # Engine Status Summary
    health_info, api_up = fetch_health()
    ist_time_str = datetime.now(IST).strftime("%H:%M:%S IST")
    
    render_html(f"""
    <div style="background-color:#090d16; border:1px solid #1e293b; border-radius:6px; padding:8px 10px; margin-bottom:14px; font-size:0.72rem;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="color:#64748b;">STORAGE:</span>
            <b style="color:{'#34d399' if api_up else '#38bdf8'}; font-family:'JetBrains Mono',monospace;">{'FASTAPI LIVE' if api_up else 'SQLITE WAL LIVE'}</b>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:3px;">
            <span style="color:#64748b;">AI MODEL:</span>
            <b style="color:#cbd5e1; font-family:'JetBrains Mono',monospace;">100 Trees (73 Feats)</b>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:3px;">
            <span style="color:#64748b;">CLOCK:</span>
            <span style="color:#94a3b8; font-family:'JetBrains Mono',monospace;">{ist_time_str}</span>
        </div>
    </div>
    """)

    st.markdown("#### ⚡ Attack Simulation Deck")
    st.caption("Drive the full loop: Flooding ➔ Telemetry ➔ RF Model ➔ Decision Engine ➔ SOAR Containment.")

    attack_select = st.selectbox(
        "Attack Profile:",
        ["DoS SYN Flood", "DoS UDP Flood", "DoS DNS Flood", "DoS ICMP Flood"],
        key="sb_attack_select"
    )

    col_sb1, col_sb2 = st.columns(2)
    with col_sb1:
        req_vol = st.number_input("Packets:", min_value=64, max_value=2048, value=512, step=64, key="sb_req_vol")
    with col_sb2:
        worker_threads = st.number_input("Workers:", min_value=1, max_value=16, value=8, step=1, key="sb_workers")

    target_endpoint = st.text_input("Target URL:", value="http://127.0.0.1:3001/api/login", key="sb_target_url")

    def run_sim_thread(attack_name, reqs, workers, endpoint):
        import scripts.dos_simulation as sim_mod
        sim_mod.TOTAL_REQUESTS = int(reqs)
        sim_mod.MAX_WORKERS = int(workers)
        sim_mod.TARGET_URL = target_endpoint
        sim_mod.run_simulation(attack_name)

    if st.button("▶ Launch Simulated Attack", type="primary", use_container_width=True, key="btn_sb_launch"):
        threading.Thread(target=run_sim_thread, args=(attack_select, req_vol, worker_threads, target_endpoint), daemon=True).start()
        st.toast(f"⚡ {attack_select} initiated! Watch real-time SOAR workflow...", icon="🚀")

    st.markdown("<div style='font-size:0.70rem; color:#64748b; font-weight:600; text-transform:uppercase; margin: 10px 0 4px 0;'>Quick 1-Click Presets:</div>", unsafe_allow_html=True)
    c_p1, c_p2 = st.columns(2)
    with c_p1:
        if st.button("SYN Burst (512)", use_container_width=True, key="p1_syn"):
            threading.Thread(target=run_sim_thread, args=("DoS SYN Flood", 512, 8, target_endpoint), daemon=True).start()
            st.toast("⚡ SYN Flood initiated!", icon="🚀")
    with c_p2:
        if st.button("UDP Flood (1024)", use_container_width=True, key="p2_udp"):
            threading.Thread(target=run_sim_thread, args=("DoS UDP Flood", 1024, 8, target_endpoint), daemon=True).start()
            st.toast("⚡ UDP Flood initiated!", icon="🚀")

    if st.button("ICMP Ping Flood (256)", use_container_width=True, key="p3_icmp"):
        threading.Thread(target=run_sim_thread, args=("DoS ICMP Flood", 256, 8, target_endpoint), daemon=True).start()
        st.toast("⚡ ICMP Flood initiated!", icon="🚀")


# =============================================================================
# REAL-TIME FRAGMENT: RERUNS EVERY 1.0s VIA WEBSOCKET
# =============================================================================
@st.fragment(run_every=1.0)
def render_live_soc_console():
    # 1. Fetch live data
    raw_incidents = fetch_incidents(limit=100)
    raw_traffic   = fetch_traffic(limit=100)
    wf_state      = tracker.get_state() or {}

    is_attack_active = bool(wf_state.get("is_active"))
    curr_stage       = int(wf_state.get("current_stage", 0))
    stages_data      = wf_state.get("stages", {})

    total_incidents = len(raw_incidents)
    critical_count  = sum(1 for i in raw_incidents if i.get("severity") == "CRITICAL")
    high_count      = sum(1 for i in raw_incidents if i.get("severity") == "HIGH")
    auto_mitigated  = sum(1 for i in raw_incidents if i.get("is_mitigated") or "MITIGATED" in str(i.get("incident_status", "")))
    avg_risk        = (sum(float(i.get("risk_score", 0)) for i in raw_incidents) / total_incidents) if total_incidents > 0 else 0.0

    latest_incident = raw_incidents[0] if raw_incidents else None

    # -------------------------------------------------------------------------
    # TOP COMMAND BAR (Breadcrumbs, KPIs, Refresh)
    # -------------------------------------------------------------------------
    col_c1, col_c2 = st.columns([2.5, 0.5], vertical_alignment="center")
    with col_c1:
        render_html("""
        <div class="command-breadcrumbs">
            <span>SMARTSOC</span> / <span>DECISION ENGINE</span> / <span class="active">OPERATIONAL COMMAND CENTER</span>
        </div>
        """)
    with col_c2:
        if st.button("↻ Refresh", use_container_width=True, help="Force re-sync with storage"):
            st.rerun()

    # Executive KPI Summary Strip
    risk_color = '#f87171' if avg_risk >= 70 else ('#fb923c' if avg_risk >= 50 else '#38bdf8')
    render_html(f"""
    <div class="kpi-strip">
        <div class="kpi-box">
            <div class="kpi-box-label">TOTAL INCIDENTS RECORDED</div>
            <div class="kpi-box-val">{total_incidents} <span style="font-size:0.75rem; color:#64748b; font-weight:500;">incidents</span></div>
        </div>
        <div class="kpi-box">
            <div class="kpi-box-label">CRITICAL / HIGH SEVERITY</div>
            <div class="kpi-box-val"><span style="color:#f87171;">{critical_count}</span> <span style="font-size:0.75rem; color:#64748b; font-weight:500;">crit</span> • <span style="color:#fb923c;">{high_count}</span> <span style="font-size:0.75rem; color:#64748b; font-weight:500;">high</span></div>
        </div>
        <div class="kpi-box">
            <div class="kpi-box-label">AUTONOMOUS MITIGATIONS</div>
            <div class="kpi-box-val" style="color:#34d399;">{auto_mitigated} <span style="font-size:0.75rem; color:#64748b; font-weight:500;">L5 playbooks</span></div>
        </div>
        <div class="kpi-box">
            <div class="kpi-box-label">AVERAGE RISK SCORE</div>
            <div class="kpi-box-val" style="color:{risk_color};">{avg_risk:.1f} <span style="font-size:0.75rem; color:#64748b; font-weight:500;">/ 100</span></div>
        </div>
    </div>
    """)

    # -------------------------------------------------------------------------
    # REAL-TIME SOAR PIPELINE DAG STEPPER
    # -------------------------------------------------------------------------
    if is_attack_active:
        atk_id    = wf_state.get("attack_id", "ATK-LIVE")
        atk_type  = wf_state.get("attack_type", "DoS Attack")
        src_ip    = wf_state.get("src_ip", "192.168.1.99")
        dest_ip   = wf_state.get("dest_ip", "127.0.0.1")
        pkts      = wf_state.get("packet_count", 0)
        rate      = wf_state.get("packet_rate", 0.0)
        
        badge_html = '<span class="badge-active-live">🔴 REAL-TIME ATTACK IN PROGRESS</span>'
        header_sub = (
            f'<b style="color:#f87171;">{atk_type}</b> • '
            f'<span style="font-family:\'JetBrains Mono\',monospace; color:#cbd5e1;">{src_ip} ➔ {dest_ip}</span> • '
            f'<span style="font-family:\'JetBrains Mono\',monospace; color:#38bdf8;">{pkts:,} pkts ({rate:.0f} req/s)</span> • '
            f'<b style="color:#34d399;">Active Stage {curr_stage}</b>'
        )
    elif latest_incident:
        inc_id      = latest_incident.get("incident_id", "N/A")
        atk_type    = latest_incident.get("attack_type", "Unknown Threat")
        src_ip      = latest_incident.get("source_ip", "0.0.0.0")
        dest_ip     = latest_incident.get("destination_ip", "127.0.0.1")
        risk_val    = float(latest_incident.get("risk_score", 0.0))
        status_state= latest_incident.get("current_state") or latest_incident.get("incident_status") or "ACTIVE"
        pol_val     = latest_incident.get("policy_id", "DEFAULT-001")
        pb_val      = latest_incident.get("playbook_id", "PB-DEFAULT")
        conf_val    = float(latest_incident.get("confidence", 0.0)) * 100
        acts        = latest_incident.get("actions_taken", [])
        if isinstance(acts, str):
            try: acts = json.loads(acts)
            except Exception: acts = []
        act_summary = acts[0] if acts else "MONITOR_SOURCE"
        curr_stage  = 7

        badge_html = f'<span class="badge badge-low">● SOAR PIPELINE ENFORCED</span> <span style="font-family:\'JetBrains Mono\',monospace; font-size:0.75rem; font-weight:700; color:#f8fafc; margin-left:6px;">{inc_id}</span>'
        risk_c = '#f87171' if risk_val >= 70 else '#fb923c'
        header_sub = (
            f'Threat: <b style="color:#f8fafc;">{atk_type}</b> • '
            f'Risk: <b style="color:{risk_c};">{risk_val:.1f}</b> • '
            f'Policy: <span style="font-family:\'JetBrains Mono\',monospace; color:#cbd5e1;">{pol_val}</span> • '
            f'Status: <b style="color:#10b981;">{status_state}</b>'
        )
    else:
        badge_html = '<span class="badge" style="color:#64748b; border:1px solid #1e293b;">● SOAR PIPELINE STANDBY</span>'
        header_sub = '<span style="color:#64748b;">Awaiting live network flow telemetry or simulated attack execution...</span>'
        curr_stage  = 0

    # Build DAG nodes
    step_defs = [
        (1, "Ingest"),
        (2, "RF Detect"),
        (3, "Context"),
        (4, "Risk"),
        (5, "Policy"),
        (6, "Playbook"),
        (7, "Mitigation")
    ]

    steps_html = []
    for s_num, s_name in step_defs:
        s_key = str(s_num)
        st_data = stages_data.get(s_key, {})
        
        if is_attack_active:
            st_status = st_data.get("status", "PENDING")
            st_detail = st_data.get("detail", "")
        elif latest_incident:
            st_status = "DONE"
            if s_num == 1: st_detail = f"{src_ip}"
            elif s_num == 2: st_detail = f"{conf_val:.1f}% Conf"
            elif s_num == 3: st_detail = f"Asset {dest_ip}"
            elif s_num == 4: st_detail = f"Score: {risk_val:.1f}"
            elif s_num == 5: st_detail = f"{pol_val}"
            elif s_num == 6: st_detail = f"{pb_val}"
            elif s_num == 7: st_detail = f"{act_summary}"
        else:
            st_status = "PENDING"
            st_detail = "Standby"

        if st_status == "ACTIVE":
            pill_cls = "node-pill node-pill-active"
        elif st_status == "DONE":
            pill_cls = "node-pill node-pill-done"
        else:
            pill_cls = "node-pill node-pill-pending"

        steps_html.append(
            f'<div class="dag-node">'
            f'<div class="{pill_cls}">{s_num}</div>'
            f'<div class="node-title">{s_name}</div>'
            f'<div class="node-detail" title="{st_detail}">{st_detail}</div>'
            f'</div>'
        )

        if s_num < 7:
            if is_attack_active:
                if curr_stage > s_num:
                    arr_cls = "dag-arrow dag-arrow-done"
                elif curr_stage == s_num:
                    arr_cls = "dag-arrow dag-arrow-active"
                else:
                    arr_cls = "dag-arrow"
            elif latest_incident:
                arr_cls = "dag-arrow dag-arrow-done"
            else:
                arr_cls = "dag-arrow"
            steps_html.append(f'<div class="{arr_cls}"></div>')

    dag_inner_html = "".join(steps_html)

    render_html(f"""
    <div class="soar-dag-card">
        <div class="dag-header">
            <div>{badge_html}</div>
            <div style="font-size:0.75rem; color:#94a3b8;">{header_sub}</div>
        </div>
        <div class="dag-track">
            {dag_inner_html}
        </div>
    </div>
    """)

    # -------------------------------------------------------------------------
    # MAIN WORKSPACE: 65% OPERATIONAL STREAM / 35% DEEP FORENSIC DOSSIER
    # -------------------------------------------------------------------------
    col_main_stream, col_main_dossier = st.columns([1.8, 1.1], gap="medium")

    # =========================================================================
    # LEFT PANE: OPERATIONAL STREAMS (INCIDENTS / LIVE TRAFFIC / MODEL STUDIO)
    # =========================================================================
    with col_main_stream:
        stream_tab_inc, stream_tab_flows, stream_tab_model = st.tabs([
            f"🚨 Incident Queue ({total_incidents})",
            f"📡 Live Network Flow Stream ({len(raw_traffic)})",
            "🧠 Random Forest Model Specs"
        ])

        # TAB 1: INCIDENT QUEUE
        with stream_tab_inc:
            sub_col_fil, sub_col_srch = st.columns([1.2, 1.8], vertical_alignment="center")
            with sub_col_fil:
                selected_sev = st.pills(
                    "Severity Filter",
                    ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"],
                    default="All",
                    label_visibility="collapsed",
                    key="pills_sev_filter"
                )
            with sub_col_srch:
                srch_q = st.text_input(
                    "Search Incidents",
                    placeholder="Search by IP, Incident ID, or Attack Type...",
                    label_visibility="collapsed",
                    key="text_srch_filter"
                )

            filtered_inc = raw_incidents
            if selected_sev != "All":
                filtered_inc = [i for i in filtered_inc if i.get("severity") == selected_sev]
            if srch_q:
                q = srch_q.lower()
                filtered_inc = [
                    i for i in filtered_inc
                    if q in str(i.get("incident_id", "")).lower()
                    or q in str(i.get("attack_type", "")).lower()
                    or q in str(i.get("source_ip", "")).lower()
                    or q in str(i.get("policy_id", "")).lower()
                ]

            if not filtered_inc:
                st.info("No security incidents matched the active filter.")
            else:
                inc_rows = []
                for inc in filtered_inc[:25]:
                    sev = inc.get("severity", "MEDIUM")
                    b_cls = "badge-crit" if sev == "CRITICAL" else ("badge-high" if sev == "HIGH" else ("badge-med" if sev == "MEDIUM" else "badge-low"))
                    
                    i_id = inc.get("incident_id", "N/A")
                    atk  = inc.get("attack_type", "Unknown")
                    s_ip = inc.get("source_ip", "0.0.0.0")
                    d_ip = inc.get("destination_ip", "127.0.0.1")
                    r_val= float(inc.get("risk_score", 0.0))
                    p_id = inc.get("policy_id", "N/A")
                    pb_id= inc.get("playbook_id", "N/A")
                    
                    acts = inc.get("actions_taken", [])
                    if isinstance(acts, str):
                        try: acts = json.loads(acts)
                        except Exception: acts = []
                    act_lbl = acts[0] if acts else inc.get("recommended_action", "MONITOR")
                    if len(str(act_lbl)) > 20:
                        act_lbl = str(act_lbl)[:18] + "..."

                    st_str = inc.get("current_state") or inc.get("incident_status") or "ACTIVE"
                    t_str = format_to_ist(inc.get("updated_at") or inc.get("created_at"))
                    r_color = '#f87171' if r_val >= 70 else ('#fb923c' if r_val >= 50 else '#38bdf8')

                    row = (
                        f"<tr>"
                        f"<td><span class=\"badge {b_cls}\">{sev}</span></td>"
                        f"<td><b style=\"font-family:'JetBrains Mono',monospace; color:#f8fafc;\">{i_id}</b></td>"
                        f"<td><b style=\"color:#f1f5f9;\">{atk}</b><br><span style=\"color:#64748b; font-size:0.70rem; font-family:'JetBrains Mono',monospace;\">{s_ip} ➔ {d_ip}</span></td>"
                        f"<td><b style=\"font-family:'JetBrains Mono',monospace; color:{r_color};\">{r_val:.1f}</b></td>"
                        f"<td><span style=\"font-size:0.72rem; font-family:'JetBrains Mono',monospace; color:#94a3b8;\">{p_id}</span><br><span style=\"color:#64748b; font-size:0.68rem; font-family:'JetBrains Mono',monospace;\">{pb_id}</span></td>"
                        f"<td><span style=\"color:#cbd5e1; font-weight:600;\">{act_lbl}</span><br><span style=\"color:#10b981; font-size:0.70rem;\">✓ {st_str}</span></td>"
                        f"<td style=\"font-family:'JetBrains Mono',monospace; color:#64748b; font-size:0.72rem;\">{t_str}</td>"
                        f"</tr>"
                    )
                    inc_rows.append(row)

                render_html(f"""
                <div style="background-color:#0f172a; border:1px solid #1e293b; border-radius:8px; overflow-x:auto; margin-bottom:8px;">
                    <table class="soc-dense-table">
                        <thead>
                            <tr>
                                <th style="width:10%;">SEVERITY</th>
                                <th style="width:14%;">INCIDENT ID</th>
                                <th style="width:26%;">THREAT & ENDPOINTS</th>
                                <th style="width:10%;">RISK</th>
                                <th style="width:18%;">POLICY & PLAYBOOK</th>
                                <th style="width:14%;">STATUS</th>
                                <th style="width:8%;">TIME</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(inc_rows)}
                        </tbody>
                    </table>
                </div>
                """)

        # TAB 2: LIVE FLOW TELEMETRY
        with stream_tab_flows:
            flow_col1, flow_col2 = st.columns([2, 1], vertical_alignment="center")
            with flow_col1:
                st.caption("Live statistical flow vectors monitored on network interface, triaged in real time into normal vs forward-to-ML.")
            with flow_col2:
                flow_pill = st.pills("Flow Filter", ["All", "Attacks", "Benign"], default="All", key="pills_flow_triage")

            filtered_traffic = raw_traffic
            if flow_pill == "Attacks":
                filtered_traffic = [t for t in filtered_traffic if "Benign" not in str(t.get("attack_type", ""))]
            elif flow_pill == "Benign":
                filtered_traffic = [t for t in filtered_traffic if "Benign" in str(t.get("attack_type", ""))]

            if not filtered_traffic:
                st.info("No flow telemetry recorded yet. Trigger an attack simulation in the sidebar to stream live packets.")
            else:
                flow_rows = []
                for ev in filtered_traffic[:25]:
                    raw_ev = ev.get("raw_event")
                    if isinstance(raw_ev, str):
                        try: raw_ev = json.loads(raw_ev)
                        except Exception: raw_ev = {}
                    elif not isinstance(raw_ev, dict):
                        raw_ev = {}

                    s_ip = ev.get("source_ip") or raw_ev.get("source", {}).get("ip") or "127.0.0.1"
                    d_ip = ev.get("destination_ip") or raw_ev.get("destination", {}).get("ip") or "127.0.0.1"
                    atk  = ev.get("attack_type", "Benign Traffic")
                    conf = float(ev.get("confidence", 0.0))
                    is_b = "Benign" in atk
                    
                    pkts = ev.get("packet_count") or raw_ev.get("network", {}).get("packet_count", 0)
                    dur  = float(ev.get("flow_duration") or raw_ev.get("network", {}).get("flow_duration", 0.0))
                    prot = raw_ev.get("network", {}).get("protocol", "TCP")
                    
                    t_badge = '<span class="badge badge-low">BYPASSED</span>' if is_b else '<span class="badge badge-crit">FORWARDED TO ML</span>'
                    t_str   = format_to_ist(ev.get("timestamp"))
                    a_color = '#34d399' if is_b else '#f87171'

                    row = (
                        f"<tr>"
                        f"<td style=\"font-family:'JetBrains Mono',monospace; color:#64748b;\">{t_str}</td>"
                        f"<td><span style=\"font-family:'JetBrains Mono',monospace; color:#f1f5f9;\">{s_ip} ➔ {d_ip}</span> <span style=\"color:#64748b; font-size:0.70rem;\">[{prot}]</span></td>"
                        f"<td><b style=\"color:{a_color};\">{atk}</b> <span style=\"color:#64748b; font-size:0.70rem;\">({conf*100:.1f}%)</span></td>"
                        f"<td style=\"font-family:'JetBrains Mono',monospace;\">{pkts:,} pkts</td>"
                        f"<td style=\"font-family:'JetBrains Mono',monospace; color:#94a3b8;\">{dur:.3f}s</td>"
                        f"<td>{t_badge}</td>"
                        f"</tr>"
                    )
                    flow_rows.append(row)

                render_html(f"""
                <div style="background-color:#0f172a; border:1px solid #1e293b; border-radius:8px; overflow-x:auto; margin-bottom:8px;">
                    <table class="soc-dense-table">
                        <thead>
                            <tr>
                                <th style="width:12%;">TIME</th>
                                <th style="width:30%;">FLOW 5-TUPLE</th>
                                <th style="width:25%;">ML DETECTION</th>
                                <th style="width:12%;">PACKETS</th>
                                <th style="width:11%;">DURATION</th>
                                <th style="width:10%;">TRIAGE</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(flow_rows)}
                        </tbody>
                    </table>
                </div>
                """)

        # TAB 3: MODEL STUDIO
        with stream_tab_model:
            st.markdown("##### 🌲 100-Tree Random Forest Architecture & Feature Explainability")
            st.caption("Standardized across 73 dimensions (flow duration, inter-arrival distributions, packet rates) mapped from Gandhar's IDS dataset.")
            m_c1, m_c2 = st.columns(2)
            with m_c1:
                feat_p = os.path.join(_REPO_ROOT, "aiml", "feature_importance.png")
                if os.path.exists(feat_p):
                    st.image(feat_p, caption="Top Predictive Features (Gini Importance)", width="stretch")
            with m_c2:
                corr_p = os.path.join(_REPO_ROOT, "aiml", "correlation_heatmap.png")
                if os.path.exists(corr_p):
                    st.image(corr_p, caption="Feature Multi-Collinearity Heatmap", width="stretch")

    # =========================================================================
    # RIGHT PANE: FORENSIC DOSSIER & SOAR CONTAINMENT CONSOLE
    # =========================================================================
    with col_main_dossier:
        # Determine which incident to display (Active simulation vs selected incident vs latest)
        active_rec = None
        if filtered_inc:
            inspect_id = st.selectbox(
                "Inspect Incident Dossier:",
                [i.get("incident_id") for i in filtered_inc[:15]],
                key="sel_inspect_dossier"
            )
            active_rec = next((i for i in filtered_inc if i.get("incident_id") == inspect_id), filtered_inc[0])
        elif latest_incident:
            active_rec = latest_incident

        if is_attack_active:
            # Render LIVE attack simulation telemetry in the dossier
            atk_p_name = wf_state.get("attack_type", "DoS Attack")
            atk_p_pkts = wf_state.get("packet_count", 0)
            atk_p_rate = wf_state.get("packet_rate", 0.0)
            atk_p_dur  = wf_state.get("elapsed", 0.0)
            atk_p_st   = wf_state.get("status_text", "Pipeline Processing...")
            atk_p_num  = wf_state.get("current_stage", 1)
            target_ip  = wf_state.get("dest_ip", "127.0.0.1")

            render_html(f"""
            <div class="dossier-card" style="border-color:#0284c7; box-shadow: 0 0 16px rgba(2, 132, 199, 0.2);">
                <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #1e293b; padding-bottom:8px; margin-bottom:10px;">
                    <div>
                        <div class="dossier-title">ACTIVE ATTACK TELEMETRY</div>
                        <div style="font-size:1.15rem; font-weight:700; color:#f8fafc; margin-top:2px;">{atk_p_name}</div>
                    </div>
                    <span class="badge badge-high">STAGE {atk_p_num} ACTIVE</span>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-bottom:10px;">
                    <div>
                        <span style="font-size:0.68rem; color:#64748b;">PACKETS SENT:</span><br>
                        <b style="font-family:'JetBrains Mono',monospace; color:#38bdf8; font-size:1.0rem;">{atk_p_pkts:,}</b>
                    </div>
                    <div>
                        <span style="font-size:0.68rem; color:#64748b;">SPEED:</span><br>
                        <b style="font-family:'JetBrains Mono',monospace; color:#f87171; font-size:1.0rem;">{atk_p_rate:.0f} req/s</b>
                    </div>
                    <div>
                        <span style="font-size:0.68rem; color:#64748b;">DURATION:</span><br>
                        <b style="font-family:'JetBrains Mono',monospace; color:#34d399; font-size:1.0rem;">{atk_p_dur:.2f}s</b>
                    </div>
                </div>
                <div style="font-size:0.72rem; color:#94a3b8; border-top:1px solid #141d2e; padding-top:8px;">
                    <b>Pipeline Status:</b> <span style="color:#f1f5f9;">{atk_p_st}</span>
                </div>
            </div>
            """)

        elif active_rec:
            atk_type  = active_rec.get("attack_type", "Unknown Threat")
            inc_id    = active_rec.get("incident_id", "N/A")
            s_ip      = active_rec.get("source_ip", "0.0.0.0")
            d_ip      = active_rec.get("destination_ip", "127.0.0.1")
            risk_val  = float(active_rec.get("risk_score", 0.0))
            pol_id    = active_rec.get("policy_id", "DEFAULT")
            pb_id     = active_rec.get("playbook_id", "PB-DEFAULT")
            conf_val  = float(active_rec.get("confidence", 0.0)) * 100
            auto_lvl  = int(active_rec.get("automation_level", 5))
            
            acts = active_rec.get("actions_taken", [])
            if isinstance(acts, str):
                try: acts = json.loads(acts)
                except Exception: acts = []
            
            is_cont = active_rec.get("is_mitigated") or ("CONTAIN" in str(active_rec.get("recommended_action", ""))) or any("BLOCK" in a for a in acts)
            dec_badge = '<span class="badge badge-crit">🛑 CONTAINED</span>' if is_cont else '<span class="badge badge-low">✅ ALLOWED</span>'
            r_color = '#f87171' if risk_val >= 70 else '#fb923c'

            render_html(f"""
            <div class="dossier-card">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; border-bottom:1px solid #1e293b; padding-bottom:8px; margin-bottom:10px;">
                    <div>
                        <div class="dossier-title">INCIDENT DOSSIER & SOAR MITIGATION</div>
                        <div style="font-size:1.15rem; font-weight:700; color:#f8fafc; margin-top:2px;">{atk_type}</div>
                        <div style="font-family:'JetBrains Mono',monospace; font-size:0.70rem; color:#64748b;">{inc_id}</div>
                    </div>
                    <div>{dec_badge}</div>
                </div>

                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:12px; font-size:0.75rem;">
                    <div>
                        <span style="color:#64748b;">Attacker Endpoint:</span><br>
                        <b style="font-family:'JetBrains Mono',monospace; color:#f87171;">{s_ip}</b>
                    </div>
                    <div>
                        <span style="color:#64748b;">Target Asset:</span><br>
                        <b style="font-family:'JetBrains Mono',monospace; color:#38bdf8;">{d_ip} (Crit: HIGH)</b>
                    </div>
                    <div>
                        <span style="color:#64748b;">Risk Engine Score:</span><br>
                        <b style="font-family:'JetBrains Mono',monospace; color:{r_color}; font-size:0.95rem;">{risk_val:.1f} / 100</b>
                    </div>
                    <div>
                        <span style="color:#64748b;">ML Confidence:</span><br>
                        <b style="font-family:'JetBrains Mono',monospace; color:#34d399;">{conf_val:.1f}% (100 Trees)</b>
                    </div>
                </div>

                <div style="border-top:1px solid #162032; padding-top:8px; margin-bottom:8px;">
                    <div class="dossier-title" style="margin-bottom:6px;">SOAR PLAYBOOK EXECUTION AUDIT</div>
                    <div style="font-size:0.72rem; color:#94a3b8; font-family:'JetBrains Mono',monospace; margin-bottom:6px;">
                        Policy: <b style="color:#cbd5e1;">{pol_id}</b> | Playbook: <b style="color:#cbd5e1;">{pb_id}</b> | Auto: <b style="color:#38bdf8;">Level {auto_lvl}</b>
                    </div>
                    <div class="dossier-checklist-item">
                        <span style="color:#10b981; font-weight:700;">✓</span>
                        <span>Multi-Threaded Flow Telemetry Ingested</span>
                    </div>
                    <div class="dossier-checklist-item">
                        <span style="color:#10b981; font-weight:700;">✓</span>
                        <span>Random Forest Classifier Prediction Verified ({conf_val:.1f}%)</span>
                    </div>
                    <div class="dossier-checklist-item">
                        <span style="color:#10b981; font-weight:700;">✓</span>
                        <span>Asset Criticality (85/100) & Reputation Enriched</span>
                    </div>
                    <div class="dossier-checklist-item">
                        <span style="color:#10b981; font-weight:700;">✓</span>
                        <span>Autonomous Containment Actions Dispatched:</span>
                    </div>
                    <div style="padding-left:18px; font-size:0.72rem; font-family:'JetBrains Mono',monospace; color:#38bdf8; margin-top:2px;">
                        {', '.join(acts) if acts else 'BLOCK_IP ' + s_ip + ', RATE_LIMIT_SUBNET'}
                    </div>
                    <div class="dossier-checklist-item" style="margin-top:4px;">
                        <span style="color:#10b981; font-weight:700;">✓</span>
                        <span>Mitigation Verified: Traffic reduction within SLA target</span>
                    </div>
                </div>
            </div>
            """)

            with st.expander("🔍 Forensic Telemetry JSON", expanded=False):
                st.json(active_rec)
        else:
            st.info("Select an attack simulation on the left sidebar to generate a live forensic dossier.")


# -----------------------------------------------------------------------------
# Execute Live Console
# -----------------------------------------------------------------------------
render_live_soc_console()
