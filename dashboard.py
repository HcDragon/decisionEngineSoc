import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime
import random
import time

# Configuration for FastAPI Backend
API_URL = "http://127.0.0.1:8000/api/v1/decision"

# Page Settings
st.set_page_config(page_title="Smart SOC Command Center", layout="wide", initial_sidebar_state="expanded")

# Dark Theme styling via markdown injection
st.markdown("""
    <style>
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    div.stButton > button:first-child {
        background-color: #E63946;
        color: white;
        border-radius: 5px;
        border: none;
    }
    div.stButton > button:first-child:hover {
        background-color: #D62828;
    }
    .metric-box {
        background-color: #1E2127;
        padding: 20px;
        border-radius: 8px;
        text-align: center;
        border-left: 4px solid #457B9D;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Smart SOC Command Center")
st.markdown("### AI-Powered Autonomous Security Operations")
st.markdown("---")

# Fetch data from API
def fetch_incidents():
    try:
        response = requests.get(f"{API_URL}/incidents")
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error("Failed to connect to backend API. Is FastAPI running on port 8000 (uvicorn api.router:app)?")
    return []

def approve_incident(incident_id):
    try:
        response = requests.post(f"{API_URL}/approve", json={"incident_id": incident_id})
        if response.status_code == 200:
            st.success(f"Successfully approved mitigation for {incident_id}")
        else:
            st.error(f"Failed to approve: {response.text}")
    except Exception as e:
        st.error(f"Error: {e}")

def simulate_traffic():
    # Randomly pick an attack scenario to simulate
    scenarios = [
        {"src_port": 12345, "dest_port": 80, "protocol": "TCP", "packet_count": 15000, "flow_duration": 2.5},  # SYN Flood
        {"src_port": 54321, "dest_port": 53, "protocol": "UDP", "packet_count": 8000, "flow_duration": 1.2},   # DNS Flood
        {"src_port": 11111, "dest_port": 22, "protocol": "TCP", "packet_count": 500, "flow_duration": 30.0},   # Brute Force
        {"src_port": 33333, "dest_port": 443, "protocol": "TCP", "packet_count": 50, "flow_duration": 1.0},    # Benign
    ]
    flow = random.choice(scenarios)
    if flow["dest_port"] == 80:
        attack_type = "DoS SYN Flood"
    elif flow["dest_port"] == 53:
        attack_type = "DNS Flood"
    elif flow["dest_port"] == 22:
        attack_type = "Brute Force"
    else:
        attack_type = "Benign"

    network_flow = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "src_ip": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
        "dest_ip": "10.0.0.5",
        "src_port": flow["src_port"],
        "dest_port": flow["dest_port"],
        "protocol": flow["protocol"],
        "packet_count": flow["packet_count"],
        "flow_duration": flow["flow_duration"]
    }

    payload = {
        "attack_type": attack_type,
        "confidence": round(random.uniform(85.0, 99.9), 2),
        "flow_context": network_flow
    }
    
    with st.spinner("Analyzing Network Flow via ML..."):
        try:
            res = requests.post(f"{API_URL}/analyze", json=payload)
            if res.status_code == 200:
                data = res.json()
                st.toast(f"Detected: {data['attack_type']} | Risk: {data['risk_score']}")
            else:
                st.error(f"Failed to analyze traffic. API Error: {res.text}")
        except Exception as e:
            st.error(f"API Connection Error: {e}")
        time.sleep(1)

# Sidebar Simulation Button
with st.sidebar:
    st.header("Traffic Simulator")
    st.write("Generate synthetic network traffic to trigger the Decision Engine.")
    if st.button("Simulate Incoming Traffic"):
        simulate_traffic()
        st.rerun()

incidents = fetch_incidents()

if not incidents:
    st.info("No incidents to display. Click 'Simulate Incoming Traffic' in the sidebar.")
else:
    df = pd.DataFrame(incidents)
    
    # Compute Top Metrics
    total_alerts = len(df)
    high_risk = len(df[df['risk_score'] >= 80])
    auto_blocked = len(df[df['incident_status'] == 'AUTO_MITIGATED'])
    
    # Display Top Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='metric-box'><h2>{total_alerts}</h2><p>Total Alerts</p></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='metric-box'><h2 style='color:#E63946;'>{high_risk}</h2><p>High Risk Incidents</p></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='metric-box'><h2 style='color:#2A9D8F;'>{auto_blocked}</h2><p>Auto-Blocked Threats</p></div>", unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Dashboard Layout: Chart and Action Panel
    col_chart, col_actions = st.columns([2, 1])
    
    with col_chart:
        st.subheader("Risk Score Distribution")
        # Visualizing risk scores using Plotly
        fig = px.bar(df, x='incident_id', y='risk_score', color='risk_score', 
                     color_continuous_scale='Reds', title="Incident Risk Scores by ID")
        fig.update_layout(xaxis_title="Incident ID", yaxis_title="Risk Score")
        st.plotly_chart(fig, use_container_width=True)
        
    with col_actions:
        st.subheader("Action Control Panel")
        st.markdown("Review and approve **Level 2** and **Level 3** incidents.")
        
        # Filter for pending manual approval
        pending_incidents = df[df['incident_status'] == 'PENDING_APPROVAL']
        
        if pending_incidents.empty:
            st.success("✅ No actions require manual approval.")
        else:
            for _, row in pending_incidents.iterrows():
                with st.expander(f"⚠️ {row['attack_type']} | {row['src_ip']}"):
                    st.write(f"**Risk Score:** {row['risk_score']:.2f}")
                    st.write(f"**Automation Level:** {row['automation_level']}")
                    st.write(f"**Playbook:** `{row['playbook']}`")
                    st.write(f"**Action:** {row['recommended_action']}")
                    
                    if st.button("Approve Mitigation", key=row['incident_id']):
                        approve_incident(row['incident_id'])
                        st.rerun()

    # Full Data Table
    st.markdown("---")
    st.subheader("Live Incident Table")
    
    display_cols = ['incident_id', 'generated_time', 'src_ip', 'attack_type', 'confidence', 'risk_score', 'automation_level', 'playbook', 'incident_status']
    
    # Styling the dataframe
    st.dataframe(df[display_cols].sort_values(by="generated_time", ascending=False), use_container_width=True, hide_index=True)
