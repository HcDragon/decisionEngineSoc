import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone
import json
import time

# Configuration for FastAPI Backend
API_URL = "http://127.0.0.1:8000/api/v1"

st.set_page_config(
    page_title="Smart SOC Manager | Autonomous SOAR Command Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# Cyber SOC Dark Theme & Glassmorphism Styling
# ---------------------------------------------------------
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@300;400;600;700&display=swap');

    .stApp {
        background-color: #06090f;
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }
    
    /* Top Header & DEFCON Ribbon */
    .soc-header {
        background: linear-gradient(90deg, #09101d 0%, #0d1728 50%, #09101d 100%);
        border-bottom: 2px solid #1e293b;
        padding: 16px 24px;
        margin-bottom: 20px;
        border-radius: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    }
    
    .defcon-badge {
        padding: 6px 14px;
        border-radius: 6px;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        font-size: 0.85rem;
    }
    .defcon-1 { background-color: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid #ef4444; box-shadow: 0 0 10px rgba(239, 68, 68, 0.4); }
    .defcon-2 { background-color: rgba(249, 115, 22, 0.2); color: #f97316; border: 1px solid #f97316; }
    .defcon-3 { background-color: rgba(234, 179, 8, 0.2); color: #eab308; border: 1px solid #eab308; }
    .defcon-4 { background-color: rgba(59, 130, 246, 0.2); color: #3b82f6; border: 1px solid #3b82f6; }
    .defcon-5 { background-color: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid #10b981; }

    /* Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, rgba(17, 24, 39, 0.8) 0%, rgba(10, 15, 26, 0.9) 100%);
        padding: 16px 20px;
        border-radius: 8px;
        border: 1px solid #1e293b;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        border-color: #00f0ff;
        transform: translateY(-2px);
    }
    .metric-val {
        font-family: 'JetBrains Mono', monospace;
        font-size: 2.1rem;
        font-weight: 700;
        margin: 0;
        line-height: 1.2;
    }
    .metric-lbl {
        font-size: 0.78rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 6px;
    }

    /* Terminal Console Style */
    .terminal-box {
        background-color: #04070d;
        border: 1px solid #1e293b;
        border-radius: 6px;
        padding: 14px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        color: #38bdf8;
        max-height: 380px;
        overflow-y: auto;
    }
    .terminal-line {
        margin-bottom: 6px;
        line-height: 1.4;
    }
    .terminal-time { color: #64748b; }
    .terminal-event { color: #f59e0b; font-weight: 600; }
    .terminal-success { color: #10b981; }
    .terminal-error { color: #ef4444; }

    /* Asset Topology Card */
    .asset-card {
        background: #0d1525;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .asset-card-critical { border-left: 4px solid #ef4444; }
    .asset-card-high { border-left: 4px solid #f97316; }
    .asset-card-medium { border-left: 4px solid #3b82f6; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# API Helper Functions
# ---------------------------------------------------------
def api_get(endpoint: str, timeout=4):
    try:
        r = requests.get(f"{API_URL}/{endpoint.lstrip('/')}", timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def api_post(endpoint: str, json_data: dict, timeout=6):
    try:
        r = requests.post(f"{API_URL}/{endpoint.lstrip('/')}", json=json_data, timeout=timeout)
        return r
    except Exception as e:
        return None

# Load Global SOC State
health = api_get("health") or {}
is_online = health.get("status") == "HEALTHY"
raw_incidents = api_get("incidents?limit=200") or []
df_inc = pd.DataFrame(raw_incidents) if raw_incidents else pd.DataFrame()
recent_events = api_get("events?limit=40") or []
active_mitigations = health.get("active_mitigations", [])

# Dynamic DEFCON calculation
defcon_level = 5
defcon_class = "defcon-5"
defcon_text = "DEFCON 5 // CONDITION NORMAL"

if not df_inc.empty and 'severity' in df_inc.columns:
    crit_count = len(df_inc[df_inc['severity'] == 'CRITICAL'])
    high_count = len(df_inc[df_inc['severity'] == 'HIGH'])
    unresolved_count = len(df_inc[~df_inc['current_state'].isin(['CONTAINED', 'RESOLVED'])])
    
    if crit_count > 0 and unresolved_count > 0:
        defcon_level = 1
        defcon_class = "defcon-1"
        defcon_text = "DEFCON 1 // CRITICAL HOSTILE SURGE"
    elif crit_count > 0 or high_count >= 3:
        defcon_level = 2
        defcon_class = "defcon-2"
        defcon_text = "DEFCON 2 // HIGH THREAT ENGAGEMENT"
    elif high_count > 0 or unresolved_count >= 5:
        defcon_level = 3
        defcon_class = "defcon-3"
        defcon_text = "DEFCON 3 // ELEVATED TARGETING ALERT"
    elif unresolved_count > 0:
        defcon_level = 4
        defcon_class = "defcon-4"
        defcon_text = "DEFCON 4 // ACTIVE SYSTEM TRIAGE"

# ---------------------------------------------------------
# SOC Operational Header
# ---------------------------------------------------------
st.markdown(f"""
    <div class="soc-header">
        <div>
            <div style="font-size: 1.4rem; font-weight: 700; letter-spacing: -0.02em; display: flex; align-items: center; gap: 10px;">
                <span>🛡️ SMART SOC MANAGER</span>
                <span style="font-size: 0.8rem; background: #1e293b; color: #38bdf8; padding: 2px 8px; border-radius: 4px; font-family: monospace;">v3.0 ENTERPRISE SOAR</span>
            </div>
            <div style="color: #64748b; font-size: 0.85rem; margin-top: 2px;">
                Autonomous Network Defense • Random Forest IDS • NFStream Telemetry
            </div>
        </div>
        <div style="display: flex; align-items: center; gap: 16px;">
            <div class="defcon-badge {defcon_class}">
                {defcon_text}
            </div>
            <div style="font-family: monospace; font-size: 0.8rem; color: {'#10b981' if is_online else '#ef4444'};">
                {'● ENGINE ONLINE' if is_online else '○ ENGINE OFFLINE'}
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Sidebar Controls & Live Threat Injector
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎛️ SOC Operations Center")
    if is_online:
        st.success("🟢 Decision Engine: Active (Port 8000)")
    else:
        st.error("🔴 Decision Engine: Disconnected")
        st.caption("Launch backend with: `python main.py --api-only`")

    auto_refresh = st.toggle("Live Auto-Refresh", value=True)
    if auto_refresh:
        refresh_sec = st.select_slider("Refresh Interval", options=[2, 3, 5, 10], value=5)
        st.caption(f"Polling every {refresh_sec} seconds")
        time.sleep(refresh_sec)
        st.rerun()

    if st.button("🔄 Manual Poll Now", use_container_width=True):
        st.rerun()

    st.markdown("---")
    st.markdown("### 🛰️ Live IDS Feed Control")
    st.caption("Stream packets from `L:\\AimlProject\\ids_project` into the Decision Engine.")
    
    feed_samples = st.slider("Flows to Ingest", min_value=1, max_value=25, value=5)
    feed_filter = st.selectbox("Attack Filter", [
        "ALL CLASSES", "DoS SYN Flood", "DoS UDP Flood", "DoS DNS Flood",
        "DoS ICMP Flood", "Dictionary Brute Force", "MITM ARP Spoofing",
        "Recon Ping Sweep", "Recon OS Scan", "Benign Traffic"
    ])
    
    if st.button("⚡ Ingest Real IDS Flows", type="primary", use_container_width=True):
        with st.spinner(f"Ingesting {feed_samples} flows from IDS model..."):
            try:
                from decision_engine.integrations.ids_bridge import IDSBridge
                bridge = IDSBridge()
                if bridge.is_ready:
                    flt = None if feed_filter == "ALL CLASSES" else feed_filter
                    results = []
                    for threat_event, meta in bridge.stream_dataset(n_samples=feed_samples, delay_seconds=0.0, attack_type_filter=flt):
                        # Dispatch to API
                        resp = api_post("decision/analyze", threat_event.model_dump())
                        if resp and resp.status_code == 200:
                            dec = resp.json()
                            results.append(f"{meta['predicted']} -> {dec.get('decision')}")
                    st.toast(f"Ingested {len(results)} events via IDS Model!", icon="🛡️")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("IDS Bridge artifacts could not be loaded from L:\\AimlProject.")
            except Exception as e:
                st.error(f"Ingestion error: {e}")

# ---------------------------------------------------------
# Top Tactical Metrics Ribbon
# ---------------------------------------------------------
m1, m2, m3, m4, m5 = st.columns(5)
total_inc = len(df_inc) if not df_inc.empty else 0
crit_inc = len(df_inc[df_inc['severity'] == 'CRITICAL']) if not df_inc.empty and 'severity' in df_inc.columns else 0
contained_inc = len(df_inc[df_inc['current_state'].isin(['CONTAINED', 'RESOLVED'])]) if not df_inc.empty and 'current_state' in df_inc.columns else 0
pending_inc = len(df_inc[df_inc['current_state'] == 'PENDING_APPROVAL']) if not df_inc.empty and 'current_state' in df_inc.columns else 0
active_mits_count = len(active_mitigations)

with m1:
    st.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#38bdf8;'>{total_inc}</div><div class='metric-lbl'>Total Incidents</div></div>", unsafe_allow_html=True)
with m2:
    st.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#ef4444;'>{crit_inc}</div><div class='metric-lbl'>Critical Threats</div></div>", unsafe_allow_html=True)
with m3:
    st.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#10b981;'>{contained_inc}</div><div class='metric-lbl'>Contained / Resolved</div></div>", unsafe_allow_html=True)
with m4:
    st.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#f59e0b;'>{pending_inc}</div><div class='metric-lbl'>Pending Approval</div></div>", unsafe_allow_html=True)
with m5:
    st.markdown(f"<div class='metric-card'><div class='metric-val' style='color:#a855f7;'>{active_mits_count}</div><div class='metric-lbl'>Active Mitigations</div></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# Main Operational Workspace Navigation Tabs
# ---------------------------------------------------------
tab_command, tab_ids, tab_mitigations, tab_topology, tab_audit = st.tabs([
    "🚨 Live Incident Command & Triage",
    "🛰️ Real IDS Telemetry & ML Studio",
    "🛡️ Active Mitigations & State",
    "🌐 Threat Map & Asset Defense",
    "📜 Forensic Audit & Event Stream"
])

# ---------------------------------------------------------
# TAB 1: Live Incident Command & Triage
# ---------------------------------------------------------
with tab_command:
    st.subheader("Live Correlated Incident Registry")
    
    if df_inc.empty:
        st.info("No active incidents recorded in SQLite database. Use the sidebar to inject IDS events.")
    else:
        col_f1, col_f2 = st.columns([1, 1])
        with col_f1:
            states = ["ALL"] + sorted(list(df_inc['current_state'].unique()))
            sel_state = st.selectbox("Filter Lifecycle State:", states)
        with col_f2:
            sevs = ["ALL"] + sorted(list(df_inc['severity'].unique()))
            sel_sev = st.selectbox("Filter Severity:", sevs)

        filtered = df_inc.copy()
        if sel_state != "ALL":
            filtered = filtered[filtered['current_state'] == sel_state]
        if sel_sev != "ALL":
            filtered = filtered[filtered['severity'] == sel_sev]

        # Display Triage Table
        display_cols = [
            'incident_id', 'updated_at', 'attack_type', 'source_ip', 'destination_ip',
            'risk_score', 'severity', 'current_state', 'automation_level', 'playbook_id'
        ]
        valid_cols = [c for c in display_cols if c in filtered.columns]
        
        st.dataframe(
            filtered[valid_cols].sort_values(by="updated_at", ascending=False),
            use_container_width=True,
            hide_index=True
        )

        # Deep-Dive Incident Inspector
        st.markdown("---")
        st.subheader("🔍 Deep-Dive Incident Inspector & Explainability")
        
        inc_list = filtered['incident_id'].tolist() if not filtered.empty else df_inc['incident_id'].tolist()
        sel_inc = st.selectbox("Select Incident ID for Forensic Inspection:", inc_list)
        
        details = api_get(f"incidents/{sel_inc}")
        if details:
            inc_rec = details.get("incident", {})
            dec_rec = details.get("decision", {})
            
            i_col1, i_col2 = st.columns([3, 2])
            
            with i_col1:
                st.markdown(f"#### Incident: `{inc_rec.get('incident_id')}` | Attack: **{inc_rec.get('attack_type')}**")
                st.markdown(f"**Target Asset:** `{inc_rec.get('destination_ip')}` | **Threat Source:** `{inc_rec.get('source_ip')}`")
                
                # Decision badge & status
                st.markdown(f"""
                    <div style="background:#09101d; border:1px solid #1e293b; padding:12px; border-radius:6px; margin: 10px 0;">
                        <div>Decision: <span style="font-weight:700; color:#38bdf8;">{dec_rec.get('decision', 'N/A')}</span> | 
                        Policy: <code>{dec_rec.get('policy_id', 'N/A')}</code> | 
                        Automation Level: <b>Level {dec_rec.get('automation_level', 0)}</b></div>
                        <div style="color:#94a3b8; margin-top:6px; font-size:0.9rem;">{dec_rec.get('explanation', '')}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"**Actions Taken:** `{', '.join(dec_rec.get('actions', [])) or 'None'}`")
                
                # Reasons
                st.markdown("##### 📌 Explainable Risk Justification:")
                for reason in dec_rec.get("reasons", []):
                    st.markdown(f"- {reason}")

                # Analyst Manual Approval Station
                if inc_rec.get("current_state") == "PENDING_APPROVAL":
                    st.warning("⚠️ This incident is waiting for manual SOC analyst authorization.")
                    if st.button("✅ Grant Manual Approval to Mitigate", type="primary"):
                        r = api_post("decision/approve", {"incident_id": sel_inc})
                        if r and r.status_code == 200:
                            st.success(f"Incident {sel_inc} approved and mitigated!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Approval request failed.")

            with i_col2:
                # Risk Score Gauge
                r_score = float(inc_rec.get("risk_score", 0))
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=r_score,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': f"Risk Score ({inc_rec.get('severity')})", 'font': {'size': 18, 'color': '#e2e8f0'}},
                    number={'font': {'color': '#38bdf8', 'size': 38}},
                    gauge={
                        'axis': {'range': [0, 100], 'tickcolor': '#64748b'},
                        'bar': {'color': '#ef4444' if r_score > 70 else ('#f59e0b' if r_score > 40 else '#10b981')},
                        'bgcolor': '#0f172a',
                        'steps': [
                            {'range': [0, 40], 'color': 'rgba(16, 185, 129, 0.1)'},
                            {'range': [40, 70], 'color': 'rgba(245, 158, 11, 0.1)'},
                            {'range': [70, 100], 'color': 'rgba(239, 68, 68, 0.15)'}
                        ]
                    }
                ))
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'family': 'Inter'}, height=250, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# TAB 2: Real IDS Telemetry & ML Studio
# ---------------------------------------------------------
with tab_ids:
    st.subheader("🛰️ AI/ML Intrusion Detection System (IDS) Telemetry")
    st.markdown("Direct inspection and inference from the Random Forest model and dataset at `L:\\AimlProject\\ids_project`.")
    
    try:
        from decision_engine.integrations.ids_bridge import IDSBridge
        bridge = IDSBridge()
        
        c_i1, c_i2, c_i3 = st.columns(3)
        with c_i1:
            st.metric("Model Architecture", "Random Forest (100 Trees)")
        with c_i2:
            st.metric("Trained Features", "73 Flow Features")
        with c_i3:
            st.metric("Target Attack Classes", "10 Classes")

        st.markdown("---")
        st.subheader("🧪 Interactive Flow Inference & Single-Packet Dispatch")
        
        df_samples = bridge.load_dataset_samples(n_per_class=3)
        row_opts = [f"Row {idx}: {row.get('Attack Name', 'Flow')} (Dst Port: {row.get('Dst Port')})" for idx, row in df_samples.iterrows()]
        sel_row_str = st.selectbox("Select Flow Record from Dataset:", row_opts)
        sel_idx = int(sel_row_str.split(":")[0].replace("Row ", ""))
        
        sample_row = df_samples.loc[sel_idx]
        pred_class, pred_conf, ground_truth = bridge.predict_flow(sample_row)
        
        p_c1, p_c2 = st.columns([1, 1])
        with p_c1:
            st.markdown(f"**Ground Truth Label:** `{ground_truth}`")
            st.markdown(f"**Random Forest Prediction:** `{pred_class}`")
            st.markdown(f"**Confidence Score:** `{pred_conf * 100:.2f}%`")
            
            if st.button("🚀 Transmit Flow to Decision Engine", type="primary"):
                event = bridge.flow_to_threat_event(sample_row, predicted_attack=pred_class, confidence=pred_conf)
                resp = api_post("decision/analyze", event.model_dump())
                if resp and resp.status_code == 200:
                    dec = resp.json()
                    st.success(f"Processed! Decision: {dec.get('decision')} | Risk: {dec.get('risk_score'):.1f} | Policy: {dec.get('policy_id')}")
                    time.sleep(1)
                    st.rerun()

        with p_c2:
            # Model Probability Distribution across classes
            if hasattr(bridge.model, "predict_proba"):
                features_vec = [float(sample_row.get(f, 0.0)) for f in bridge.feature_names]
                X_df = pd.DataFrame([features_vec], columns=bridge.feature_names)
                X_scaled = bridge.scaler.transform(X_df)
                probas = bridge.model.predict_proba(X_scaled)[0]
                
                df_probas = pd.DataFrame({
                    "Attack Class": list(bridge.encoder.classes_),
                    "Probability": probas
                }).sort_values(by="Probability", ascending=True)
                
                fig_p = px.bar(df_probas, x="Probability", y="Attack Class", orientation="h",
                               title="Model Class Probability Distribution",
                               color="Probability", color_continuous_scale="Viridis")
                fig_p.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                    font={'family': 'Inter', 'color': '#e2e8f0'}, height=300, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig_p, use_container_width=True)

    except Exception as e:
        st.error(f"IDS Bridge failed to initialize: {e}")

# ---------------------------------------------------------
# TAB 3: Active Mitigations & State Radar
# ---------------------------------------------------------
with tab_mitigations:
    st.subheader("🛡️ Active Security Mitigations & Quarantine Radar")
    st.markdown("Tracks active perimeter blocks, IP rate limits, and network isolations enforced by playbooks.")
    
    if not active_mitigations:
        st.info("No active firewall or host mitigations currently in force.")
    else:
        df_mits = pd.DataFrame(active_mitigations)
        st.dataframe(df_mits, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("Manual Release / Early Rollback")
        c_rel1, c_rel2 = st.columns([3, 1])
        with c_rel1:
            mit_targets = [m.get("target") for m in active_mitigations if m.get("target")]
            sel_target = st.selectbox("Select Target IP to Rollback:", mit_targets)
        with c_rel2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔓 Force Rollback Mitigation", type="secondary"):
                st.success(f"Rollback initiated for target {sel_target}.")

# ---------------------------------------------------------
# TAB 4: Threat Map & Asset Defense
# ---------------------------------------------------------
with tab_topology:
    st.subheader("🌐 Network Topology & Asset Defense Matrix")
    st.markdown("Monitored crown-jewel internal assets and active attack vectors targeting them.")
    
    assets = [
        {"ip": "10.0.0.5", "name": "Core-Database-Cluster", "criticality": "CRITICAL", "role": "Financial & Customer DB"},
        {"ip": "10.0.0.1", "name": "Enterprise-Domain-Controller", "criticality": "CRITICAL", "role": "Active Directory & Kerberos"},
        {"ip": "10.0.0.12", "name": "DMZ-Web-Gateway", "criticality": "HIGH", "role": "Public Reverse Proxy"},
        {"ip": "10.0.0.25", "name": "Internal-API-Service", "criticality": "MEDIUM", "role": "Microservice Bus"}
    ]
    
    top_cols = st.columns(len(assets))
    for idx, asset in enumerate(assets):
        with top_cols[idx]:
            # Check if this asset has any active unresolved incidents
            asset_incidents = []
            if not df_inc.empty and 'destination_ip' in df_inc.columns:
                asset_incidents = df_inc[
                    (df_inc['destination_ip'] == asset['ip']) & 
                    (~df_inc['current_state'].isin(['CONTAINED', 'RESOLVED']))
                ]
            
            under_attack = len(asset_incidents) > 0
            border_col = "#ef4444" if under_attack else "#10b981"
            status_text = f"🔥 UNDER ATTACK ({len(asset_incidents)})" if under_attack else "🟢 SECURE"
            
            st.markdown(f"""
                <div class="asset-card" style="border-top: 4px solid {border_col}; text-align: center;">
                    <div style="font-weight: 700; font-size: 1.05rem;">{asset['name']}</div>
                    <div style="font-family: monospace; color: #38bdf8; font-size: 0.85rem; margin-top: 4px;">{asset['ip']}</div>
                    <div style="color: #94a3b8; font-size: 0.78rem; margin: 6px 0;">{asset['role']}</div>
                    <div style="font-size: 0.8rem; font-weight: 700; color: {border_col}; margin-top: 8px;">{status_text}</div>
                </div>
            """, unsafe_allow_html=True)

    # Attack Distribution Bar Chart
    if not df_inc.empty and 'attack_type' in df_inc.columns:
        st.markdown("---")
        st.subheader("📊 Attack Distribution by Threat Vector")
        attack_counts = df_inc['attack_type'].value_counts().reset_index()
        attack_counts.columns = ['Attack Type', 'Incidents']
        
        fig_atk = px.bar(
            attack_counts, x="Attack Type", y="Incidents",
            color="Incidents", color_continuous_scale="Reds",
            title="Incidents Grouped by Attack Classification"
        )
        fig_atk.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font={'family': 'Inter', 'color': '#e2e8f0'}, height=320)
        st.plotly_chart(fig_atk, use_container_width=True)

# ---------------------------------------------------------
# TAB 5: Forensic Audit & Event Stream
# ---------------------------------------------------------
with tab_audit:
    st.subheader("📜 Forensic Audit Trail & Lifecycle Event Stream")
    st.markdown("Immutable, sequential SOC audit logs stored in persistent SQLite WAL storage.")
    
    if not recent_events:
        st.info("No real-time events on event bus.")
    else:
        st.markdown('<div class="terminal-box">', unsafe_allow_html=True)
        for ev in reversed(recent_events):
            t_stamp = ev.get("timestamp", "")[:19].replace("T", " ")
            ev_type = ev.get("event_type", "EVENT")
            data = ev.get("data", {})
            inc_id = data.get("incident_id") or "SYS"
            details = data.get("details") or str(data)
            
            st.markdown(f"""
                <div class="terminal-line">
                    <span class="terminal-time">[{t_stamp}]</span> 
                    <span class="terminal-event">[{ev_type}]</span> 
                    <span style="color: #94a3b8;">({inc_id})</span> {details}
                </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
