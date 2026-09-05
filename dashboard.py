import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import time

# Configuration for FastAPI Backend
API_URL = "http://127.0.0.1:8000/api/v1"

st.set_page_config(
    page_title="Smart SOC Autonomous Decision Engine",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enterprise Dark Theme Styling
st.markdown("""
    <style>
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 18px 24px;
        border-radius: 10px;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        text-align: center;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 4px;
    }
    .status-badge {
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Smart SOC Autonomous Decision Engine")
st.markdown("##### Enterprise Security Orchestration, Automation, and Response (SOAR)")

# API Fetch Helpers
def fetch_incidents(state=None):
    try:
        url = f"{API_URL}/incidents" + (f"?state={state}" if state else "")
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return []

def fetch_incident_details(incident_id):
    try:
        res = requests.get(f"{API_URL}/incidents/{incident_id}", timeout=3)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None

def fetch_health():
    try:
        res = requests.get(f"{API_URL}/health", timeout=3)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return {}

def fetch_recent_events():
    try:
        res = requests.get(f"{API_URL}/events?limit=30", timeout=3)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return []

def approve_incident(incident_id):
    try:
        res = requests.post(f"{API_URL}/decision/approve", json={"incident_id": incident_id}, timeout=5)
        if res.status_code == 200:
            st.success(f"Successfully approved and mitigated incident {incident_id}")
            time.sleep(1)
            st.rerun()
        else:
            st.error(f"Approval failed: {res.text}")
    except Exception as e:
        st.error(f"Connection error: {e}")

# Sidebar
with st.sidebar:
    st.header("⚙️ SOC Controller")
    health = fetch_health()
    if health.get("status") == "HEALTHY":
        st.success("🟢 Decision Engine: ONLINE (Port 8000)")
    else:
        st.error("🔴 Decision Engine: DISCONNECTED")
        st.caption("Launch FastAPI with: `python main.py`")

    st.markdown("---")
    st.subheader("🧪 Test Threat Simulation")
    st.caption("Simulate incoming threat event from Threat Detection Engine.")
    
    test_attack = st.selectbox("Select Attack Type", [
        "DoS SYN Flood", "DoS UDP Flood", "DoS DNS Flood", "DoS ICMP Flood",
        "Dictionary Brute Force", "Reconnaissance", "Benign Traffic"
    ])
    
    test_conf = st.slider("ML Confidence", 0.50, 1.00, 0.98, step=0.01)
    test_target = st.selectbox("Destination Asset", [
        "10.0.0.5 (Core Database - Tier 1)",
        "10.0.0.10 (Load Balancer - Tier 2)",
        "10.0.0.20 (App Server - Tier 3)",
        "10.0.0.50 (Workstation - Tier 4)"
    ])

    if st.button("Transmit Threat Event", type="primary", use_container_width=True):
        dest_ip = test_target.split(" ")[0]
        pps_val = 60000 if "Flood" in test_attack else (50 if "Benign" in test_attack else 500)
        pkt_val = 150000 if "Flood" in test_attack else 50
        
        payload = {
            "event_id": f"EVT-SIM-{int(time.time())}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": {"ip": f"192.168.1.{int(time.time()) % 200 + 10}", "port": 52172},
            "destination": {"ip": dest_ip, "port": 80},
            "network": {
                "protocol": "TCP" if "UDP" not in test_attack and "ICMP" not in test_attack else ("UDP" if "UDP" in test_attack else "ICMP"),
                "packet_count": pkt_val,
                "flow_duration": 2.5,
                "bytes": pkt_val * 64,
                "packets_per_second": pps_val
            },
            "detection": {
                "model": "RandomForest",
                "attack_type": test_attack,
                "confidence": test_conf,
                "confidence_level": "HIGH" if test_conf >= 0.85 else "MEDIUM"
            },
            "sensor": {"source": "NFStream", "mode": "LIVE"}
        }
        
        try:
            r = requests.post(f"{API_URL}/decision/analyze", json=payload, timeout=5)
            if r.status_code == 200:
                res_data = r.json()
                st.toast(f"Decision: {res_data.get('decision')} | Risk: {res_data.get('risk_score')}", icon="🛡️")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"Error: {r.text}")
        except Exception as err:
            st.error(f"Failed to connect: {err}")

# Load Incidents
all_incidents = fetch_incidents()
df_inc = pd.DataFrame(all_incidents) if all_incidents else pd.DataFrame()

# Top Metric Cards
c1, c2, c3, c4 = st.columns(4)
total_inc = len(df_inc) if not df_inc.empty else 0
crit_inc = len(df_inc[df_inc['severity'] == 'CRITICAL']) if not df_inc.empty and 'severity' in df_inc.columns else 0
contained_inc = len(df_inc[df_inc['current_state'].isin(['CONTAINED', 'RESOLVED'])]) if not df_inc.empty and 'current_state' in df_inc.columns else 0
pending_inc = len(df_inc[df_inc['current_state'] == 'PENDING_APPROVAL']) if not df_inc.empty and 'current_state' in df_inc.columns else 0

with c1:
    st.markdown(f"<div class='metric-card'><div class='metric-value' style='color:#38bdf8;'>{total_inc}</div><div class='metric-label'>Total Incidents</div></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='metric-card'><div class='metric-value' style='color:#ef4444;'>{crit_inc}</div><div class='metric-label'>Critical Threats</div></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='metric-card'><div class='metric-value' style='color:#10b981;'>{contained_inc}</div><div class='metric-label'>Contained / Resolved</div></div>", unsafe_allow_html=True)
with c4:
    st.markdown(f"<div class='metric-card'><div class='metric-value' style='color:#f59e0b;'>{pending_inc}</div><div class='metric-label'>Pending Approval</div></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Main Navigation Tabs
tab_incidents, tab_inspector, tab_mitigations, tab_audit = st.tabs([
    "📋 Live Incident Registry",
    "🔍 Explainable Decision Inspector",
    "🛡️ Active Mitigations & State",
    "📜 Forensic Audit Stream"
])

# TAB 1: Live Incident Registry
with tab_incidents:
    st.subheader("Live Correlated Incidents")
    if df_inc.empty:
        st.info("No active incidents recorded. Transmit a threat event via the sidebar or live sensor.")
    else:
        # State Filter
        state_options = ["ALL"] + sorted(list(df_inc['current_state'].unique()))
        sel_state = st.selectbox("Filter by Lifecycle State:", state_options)
        
        filtered_df = df_inc if sel_state == "ALL" else df_inc[df_inc['current_state'] == sel_state]
        
        # Display Table
        show_cols = [
            'incident_id', 'updated_at', 'attack_type', 'source_ip', 'destination_ip',
            'risk_score', 'severity', 'current_state', 'automation_level', 'playbook_id', 'event_count'
        ]
        valid_cols = [c for c in show_cols if c in filtered_df.columns]
        st.dataframe(
            filtered_df[valid_cols].sort_values(by="updated_at", ascending=False),
            use_container_width=True,
            hide_index=True
        )

# TAB 2: Explainable Decision Inspector
with tab_inspector:
    st.subheader("Explainable Security Decision & Mathematical Breakdown")
    if df_inc.empty:
        st.info("No incidents available for inspection.")
    else:
        inc_ids = df_inc['incident_id'].tolist()
        sel_inc_id = st.selectbox("Select Incident to Inspect:", inc_ids)
        
        details = fetch_incident_details(sel_inc_id)
        if details:
            inc_data = details.get("incident", {})
            dec_data = details.get("decision", {})
            audit_data = details.get("audit_trail", [])
            
            col_dec, col_gauge = st.columns([2, 1])
            with col_dec:
                st.markdown(f"### Decision: **{dec_data.get('decision', 'N/A')}**")
                st.markdown(f"**Policy:** `{dec_data.get('policy_id')}` | **Playbook:** `{dec_data.get('playbook_id')}` | **Level:** {dec_data.get('automation_level')}")
                st.info(f"💡 **Explanation:** {dec_data.get('explanation')}")
                st.write(f"**Actions Executed:** `{', '.join(dec_data.get('actions', [])) or 'None'}`")
                
                # Check for manual approval button
                if inc_data.get("current_state") == "PENDING_APPROVAL":
                    st.warning("⚠️ This incident is waiting for manual analyst approval.")
                    if st.button(f"Grant Approval for {sel_inc_id}", type="primary"):
                        approve_incident(sel_inc_id)
            
            with col_gauge:
                risk_val = float(dec_data.get("risk_score", 0.0))
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=risk_val,
                    title={'text': "Normalized Risk Score (0-100)"},
                    gauge={
                        'axis': {'range': [0, 100]},
                        'bar': {'color': "#ef4444" if risk_val >= 80 else ("#f59e0b" if risk_val >= 60 else "#10b981")},
                        'steps': [
                            {'range': [0, 20], 'color': "#1e293b"},
                            {'range': [21, 60], 'color': "#334155"},
                            {'range': [61, 80], 'color': "#475569"},
                            {'range': [81, 100], 'color': "#64748b"},
                        ]
                    }
                ))
                fig.update_layout(height=240, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"})
                st.plotly_chart(fig, use_container_width=True)

            # Evidence Reasons
            st.markdown("#### Evidence & Contributing Factors")
            for r in dec_data.get("reasons", []):
                st.write(f"- {r}")

# TAB 3: Active Mitigations & State
with tab_mitigations:
    st.subheader("Stateful Active Mitigations & Outcome Verification")
    active_mits = health.get("active_mitigations", [])
    if not active_mits:
        st.success("✅ No temporary mitigations currently active.")
    else:
        st.dataframe(pd.DataFrame(active_mits), use_container_width=True, hide_index=True)

# TAB 4: Forensic Audit Stream
with tab_audit:
    st.subheader("Forensic Audit Log Trail")
    events = fetch_recent_events()
    if not events:
        st.info("No audit events logged yet.")
    else:
        for ev in reversed(events):
            data = ev.get("data", {})
            st.markdown(f"`{ev.get('timestamp')}` | **[{ev.get('event_type')}]** — {data.get('details', '')}")
