import React, { useState, useEffect, useRef } from 'react';
import {
  Shield,
  Activity,
  Radio,
  Server,
  AlertTriangle,
  Play,
  Square,
  RefreshCw,
  Cpu,
  Lock,
  Wifi,
  Filter,
  CheckCircle2,
  Sliders,
  Terminal,
  Database
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function App() {
  // System State
  const [systemHealth, setSystemHealth] = useState(null);
  const [automationMode, setAutomationMode] = useState('recommend_only');
  const [executorMode, setExecutorMode] = useState('dry_run');
  const [toastMsg, setToastMsg] = useState(null);

  // Traffic & NFStream State
  const [trafficStats, setTrafficStats] = useState({
    monitored_port: 8000,
    engine_mode: 'emulated_stream',
    status: 'running',
    total_flows: 0,
    total_packets: 0,
    total_bytes: 0,
    current_packets_per_sec: 0,
    current_kb_per_sec: 0,
    threat_flows_count: 0,
    active_connections: 0,
    protocol_distribution: { TCP: 0, UDP: 0, ICMP: 0 },
    top_sources: [],
  });

  const [flows, setFlows] = useState([]);
  const [portInput, setPortInput] = useState('8000');
  const [threatOnly, setThreatOnly] = useState(false);
  const [overview, setOverview] = useState(null);
  const [isLivePolling, setIsLivePolling] = useState(true);

  const showToast = (msg) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3500);
  };

  // Fetch system status
  const fetchSystemStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) {
        const data = await res.json();
        setSystemHealth(data);
        if (data.automation_mode) setAutomationMode(data.automation_mode);
      }
    } catch (err) {
      setSystemHealth({ status: 'disconnected', database: 'disconnected' });
    }
  };

  // Fetch traffic status & stats
  const fetchTrafficStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/traffic/status`);
      if (res.ok) {
        const data = await res.json();
        setTrafficStats(data);
      }
    } catch (err) {
      // offline / backend not yet reloaded
    }
  };

  // Fetch recent flows on the monitored port
  const fetchFlows = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/traffic/flows?limit=30&threat_only=${threatOnly}`);
      if (res.ok) {
        const data = await res.json();
        setFlows(data);
      }
    } catch (err) {
      // Ignore
    }
  };

  // Fetch overview metrics
  const fetchOverview = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/dashboard/overview`);
      if (res.ok) {
        const data = await res.json();
        setOverview(data);
        if (data.system) {
          setExecutorMode(data.system.executor);
        }
      }
    } catch (err) {
      // Ignore
    }
  };

  // Polling loop
  useEffect(() => {
    fetchSystemStatus();
    fetchTrafficStatus();
    fetchFlows();
    fetchOverview();

    if (!isLivePolling) return;
    const interval = setInterval(() => {
      fetchTrafficStatus();
      fetchFlows();
      fetchOverview();
    }, 1500);

    return () => clearInterval(interval);
  }, [isLivePolling, threatOnly]);

  // Update Automation Mode (Kill switch)
  const handleModeChange = async (mode) => {
    try {
      const res = await fetch(`${API_BASE}/system/mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ automation: mode }),
      });
      if (res.ok) {
        setAutomationMode(mode);
        showToast(`Automation mode switched to: ${mode.toUpperCase()}`);
      }
    } catch (err) {
      showToast(`Failed to update mode: ${err.message}`);
    }
  };

  // Switch Monitored Port
  const handleSetPort = async (newPort) => {
    const portNum = parseInt(newPort, 10);
    if (isNaN(portNum) || portNum < 1 || portNum > 65535) {
      showToast('Invalid port number (1-65535)');
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/traffic/port`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ port: portNum }),
      });
      if (res.ok) {
        setPortInput(String(portNum));
        fetchTrafficStatus();
        fetchFlows();
        showToast(`NFStream target port set to: ${portNum}`);
      }
    } catch (err) {
      showToast('Error switching port');
    }
  };

  // Start / Stop Traffic Monitor
  const toggleTrafficMonitor = async () => {
    const isRunning = trafficStats.status === 'running';
    const endpoint = isRunning ? '/api/traffic/stop' : '/api/traffic/start';
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ port: parseInt(portInput, 10) }),
      });
      if (res.ok) {
        fetchTrafficStatus();
        showToast(isRunning ? 'Traffic monitor paused' : 'Traffic monitor started');
      }
    } catch (err) {
      showToast('Failed to toggle monitor');
    }
  };

  // Flush flow buffer
  const handleClearFlows = async () => {
    try {
      await fetch(`${API_BASE}/api/traffic/clear`, { method: 'POST' });
      setFlows([]);
      fetchTrafficStatus();
      showToast('Flow buffer cleared');
    } catch (err) {
      showToast('Failed to clear buffer');
    }
  };

  // Protocol calculation
  const totalProtoCount = Math.max(
    1,
    (trafficStats.protocol_distribution.TCP || 0) +
    (trafficStats.protocol_distribution.UDP || 0) +
    (trafficStats.protocol_distribution.ICMP || 0)
  );

  const tcpPct = Math.round(((trafficStats.protocol_distribution.TCP || 0) / totalProtoCount) * 100);
  const udpPct = Math.round(((trafficStats.protocol_distribution.UDP || 0) / totalProtoCount) * 100);
  const icmpPct = Math.max(0, 100 - tcpPct - udpPct);

  return (
    <div className="app-container">
      {/* Header Bar */}
      <header className="header-bar">
        <div className="logo-area">
          <div className="logo-icon">
            <Shield size={24} />
          </div>
          <div>
            <div className="brand-title">AI Smart SOC Manager</div>
            <div className="brand-subtitle">Autonomous Decision Engine & NFStream</div>
          </div>
        </div>

        <div className="header-controls">
          {/* Health indicator */}
          <div className={`status-badge ${systemHealth?.status === 'healthy' ? '' : 'degraded'}`}>
            <span className={`radar-dot ${systemHealth?.status === 'healthy' ? '' : 'threat'}`} />
            API: {systemHealth?.status === 'healthy' ? 'CONNECTED (PORT 8000)' : 'STANDBY'}
          </div>

          {/* Executor Badge */}
          <div className="status-badge" style={{ borderColor: 'rgba(56, 189, 248, 0.3)' }}>
            <Cpu size={14} color="#00f0ff" />
            EXECUTOR: {executorMode.toUpperCase()}
          </div>

          {/* Global Kill Switch */}
          <div className="mode-switcher" title="Global Automation Kill Switch">
            <button
              className={`mode-btn ${automationMode === 'off' ? 'active-off' : ''}`}
              onClick={() => handleModeChange('off')}
            >
              OFF
            </button>
            <button
              className={`mode-btn ${automationMode === 'recommend_only' ? 'active-recommend' : ''}`}
              onClick={() => handleModeChange('recommend_only')}
            >
              RECOMMEND
            </button>
            <button
              className={`mode-btn ${automationMode === 'auto' ? 'active-auto' : ''}`}
              onClick={() => handleModeChange('auto')}
            >
              AUTO
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {/* Metric Cards Row */}
        <section className="metrics-grid">
          <div className="metric-card">
            <div className="metric-label">Port {trafficStats.monitored_port} Throughput</div>
            <div className="metric-value">
              {trafficStats.current_packets_per_sec}
              <span className="metric-unit">pkts/s</span>
            </div>
            <div className="metric-footer">
              <Activity size={13} color="#00f0ff" />
              Bandwidth: {trafficStats.current_kb_per_sec} KB/s
            </div>
          </div>

          <div className="metric-card accent-emerald">
            <div className="metric-label">Monitored Flows</div>
            <div className="metric-value">
              {trafficStats.total_flows.toLocaleString()}
              <span className="metric-unit">flows</span>
            </div>
            <div className="metric-footer">
              <Radio size={13} color="#00ffc2" />
              Total: {(trafficStats.total_bytes / 1024).toFixed(1)} KB metered
            </div>
          </div>

          <div className="metric-card accent-crimson">
            <div className="metric-label">Threat Anomaly Rate</div>
            <div className="metric-value" style={{ color: trafficStats.threat_flows_count > 0 ? '#ff3366' : '#00ffc2' }}>
              {trafficStats.total_flows > 0
                ? ((trafficStats.threat_flows_count / trafficStats.total_flows) * 100).toFixed(1)
                : '0.0'}
              <span className="metric-unit">%</span>
            </div>
            <div className="metric-footer">
              <AlertTriangle size={13} color="#ff3366" />
              {trafficStats.threat_flows_count} IDS threat detections
            </div>
          </div>

          <div className="metric-card accent-purple">
            <div className="metric-label">Active Containment</div>
            <div className="metric-value">
              {overview?.stats?.active_blocks ?? 0}
              <span className="metric-unit">blocks</span>
            </div>
            <div className="metric-footer">
              <Lock size={13} color="#9d4edd" />
              Virtual Firewall Guardrails Active
            </div>
          </div>
        </section>

        {/* Port Selector & NFStream Controls Bar */}
        <section className="port-selector-bar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Wifi size={18} color="#00f0ff" />
              <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Target Port:</span>
            </div>

            {/* Quick Port Presets */}
            <div className="port-presets">
              {[
                { label: '80 (HTTP)', port: 80 },
                { label: '443 (HTTPS)', port: 443 },
                { label: '8000 (SOC API)', port: 8000 },
                { label: '22 (SSH)', port: 22 },
                { label: '53 (DNS)', port: 53 },
              ].map((p) => (
                <button
                  key={p.port}
                  className={`preset-btn ${trafficStats.monitored_port === p.port ? 'active' : ''}`}
                  onClick={() => handleSetPort(p.port)}
                >
                  {p.label}
                </button>
              ))}
            </div>

            {/* Custom Port Form */}
            <div className="custom-port-form">
              <input
                type="number"
                min="1"
                max="65535"
                className="port-input"
                value={portInput}
                onChange={(e) => setPortInput(e.target.value)}
                placeholder="Port"
              />
              <button className="action-btn secondary" onClick={() => handleSetPort(portInput)}>
                Set Port
              </button>
            </div>
          </div>

          {/* Engine Mode & Monitoring Action */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span
              className="badge"
              style={{
                background: 'rgba(0, 240, 255, 0.12)',
                color: '#00f0ff',
                border: '1px solid rgba(0, 240, 255, 0.3)',
                padding: '6px 12px',
              }}
              title="NFStream DPI Engine Mode"
            >
              <Terminal size={13} />
              {trafficStats.engine_mode === 'native_nfstream'
                ? 'NFStream: Native BPF'
                : 'NFStream: Emulated Tap'}
            </span>

            <button
              className={`action-btn ${trafficStats.status === 'running' ? 'danger' : 'primary'}`}
              onClick={toggleTrafficMonitor}
            >
              {trafficStats.status === 'running' ? (
                <>
                  <Square size={14} /> Pause Tap
                </>
              ) : (
                <>
                  <Play size={14} /> Start Tap
                </>
              )}
            </button>

            <button className="action-btn secondary" onClick={handleClearFlows} title="Flush recent buffer">
              <RefreshCw size={14} /> Flush
            </button>
          </div>
        </section>

        {/* Dashboard Split View: Live Flow Stream + Telemetry Breakdown */}
        <div className="dashboard-grid">
          {/* Left Panel: Real-Time Flow Stream */}
          <div className="glass-card">
            <div className="card-header">
              <div className="card-title">
                <Radio size={18} />
                Live NFStream Flows (Port {trafficStats.monitored_port})
                <span className="radar-dot" style={{ marginLeft: 6 }} />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <button
                  className={`preset-btn ${threatOnly ? 'active' : ''}`}
                  onClick={() => setThreatOnly(!threatOnly)}
                  style={{ display: 'flex', alignItems: 'center', gap: '5px' }}
                >
                  <Filter size={13} /> {threatOnly ? 'Threats Only' : 'All Flows'}
                </button>
              </div>
            </div>

            <div className="table-container">
              <table className="flow-table">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Source (IP:Port)</th>
                    <th>Destination</th>
                    <th>Proto</th>
                    <th>Packets</th>
                    <th>Bytes</th>
                    <th>Dur (ms)</th>
                    <th>IDS Prediction</th>
                  </tr>
                </thead>
                <tbody>
                  {flows.length === 0 ? (
                    <tr>
                      <td colSpan="8" style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                        Waiting for network flow packets on Port {trafficStats.monitored_port}...
                      </td>
                    </tr>
                  ) : (
                    flows.map((flow) => (
                      <tr key={flow.id} className={flow.is_threat ? 'threat-row' : ''}>
                        <td>{flow.timestamp}</td>
                        <td style={{ color: flow.is_threat ? 'var(--accent-crimson)' : 'var(--text-main)' }}>
                          {flow.src_ip}:{flow.src_port}
                        </td>
                        <td>{flow.dst_ip}:{flow.dst_port}</td>
                        <td>
                          <span className={`badge protocol-${flow.protocol.toLowerCase()}`}>
                            {flow.protocol}
                          </span>
                        </td>
                        <td>{flow.bidirectional_packets}</td>
                        <td>{(flow.bidirectional_bytes / 1024).toFixed(1)} KB</td>
                        <td>{flow.duration_ms}</td>
                        <td>
                          {flow.is_threat ? (
                            <span className="badge threat">
                              <AlertTriangle size={11} /> {flow.threat_label} ({flow.confidence}%)
                            </span>
                          ) : (
                            <span className="badge benign">
                              <CheckCircle2 size={11} /> Benign ({flow.confidence}%)
                            </span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right Panel: Protocol Breakdown & SOC Incidents */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {/* Protocol Distribution Card */}
            <div className="glass-card">
              <div className="card-header">
                <div className="card-title">
                  <Activity size={18} /> Protocol Breakdown
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                  Port {trafficStats.monitored_port}
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: 4 }}>
                <span style={{ color: 'var(--accent-cyan)' }}>TCP: {tcpPct}%</span>
                <span style={{ color: 'var(--accent-purple)' }}>UDP: {udpPct}%</span>
                <span style={{ color: 'var(--accent-amber)' }}>ICMP: {icmpPct}%</span>
              </div>

              <div className="bar-track">
                <div className="bar-segment-tcp" style={{ width: `${tcpPct}%` }} />
                <div className="bar-segment-udp" style={{ width: `${udpPct}%` }} />
                <div className="bar-segment-icmp" style={{ width: `${icmpPct}%` }} />
              </div>

              {/* Top Talkers */}
              <div style={{ marginTop: '20px' }}>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', marginBottom: '10px' }}>
                  Top Traffic Sources on Port {trafficStats.monitored_port}
                </div>
                {trafficStats.top_sources.length === 0 ? (
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>No source IPs recorded yet</div>
                ) : (
                  trafficStats.top_sources.map((src, i) => (
                    <div
                      key={src.ip}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        padding: '6px 0',
                        borderBottom: '1px solid rgba(70, 110, 180, 0.08)',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '0.8rem',
                      }}
                    >
                      <span>#{i + 1} {src.ip}</span>
                      <span style={{ color: 'var(--accent-cyan)' }}>{src.packets} pkts</span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Recent SOC Incidents Card */}
            <div className="glass-card" style={{ flex: 1 }}>
              <div className="card-header">
                <div className="card-title">
                  <AlertTriangle size={18} color="#ff3366" /> Active SOC Incidents
                </div>
                <span className="badge benign" style={{ fontSize: '0.7rem' }}>
                  {overview?.stats?.open_incidents ?? 0} Open
                </span>
              </div>

              <div>
                {!overview?.recent_incidents || overview.recent_incidents.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    <CheckCircle2 size={24} color="#00ffc2" style={{ margin: '0 auto 8px', display: 'block' }} />
                    No active threats on network. System normal.
                  </div>
                ) : (
                  overview.recent_incidents.map((inc) => (
                    <div key={inc.id} className="incident-item">
                      <div className="incident-info">
                        <span className="incident-ip">{inc.src_ip}</span>
                        <span className="incident-family">{inc.family} ({inc.alert_count} alerts)</span>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <span className={`incident-risk ${inc.max_risk >= 75 ? 'risk-critical' : inc.max_risk >= 50 ? 'risk-high' : 'risk-med'}`}>
                          Risk {inc.max_risk.toFixed(1)}
                        </span>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                          {inc.status}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Floating Notification Toast */}
      {toastMsg && (
        <div className="toast-notice">
          {toastMsg}
        </div>
      )}
    </div>
  );
}
