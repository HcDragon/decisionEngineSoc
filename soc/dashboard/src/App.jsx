import React, { useState, useEffect } from 'react';
import { SecurifyHero } from './SecurifyHero';
import { LiveTelemetryBanner } from './components/LiveTelemetryBanner';
import { PlatformBento } from './components/PlatformBento';
import { SolutionsSection } from './components/SolutionsSection';
import { Footer } from './components/Footer';
import { SocConsole } from './components/SocConsole';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function App() {
  // Navigation View: 'landing' (Public SaaS + Hero) or 'console' (Smart SOC Operations)
  const [activeView, setActiveView] = useState(() => {
    if (typeof window !== 'undefined' && window.location.hash === '#console') {
      return 'console';
    }
    return 'landing';
  });

  useEffect(() => {
    const handleHash = () => {
      if (window.location.hash === '#console') {
        setActiveView('console');
      } else {
        setActiveView('landing');
      }
    };
    window.addEventListener('hashchange', handleHash);
    return () => window.removeEventListener('hashchange', handleHash);
  }, []);

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

  // Incident detail drill-down (click a row in Active SOC Incidents)
  const [detailId, setDetailId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const openIncident = async (id) => {
    setDetailId(id);
    setDetail(null);
    setDetailLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/incidents/${id}`);
      if (res.ok) setDetail(await res.json());
    } catch {
      /* ignore — modal shows a load error state */
    } finally {
      setDetailLoading(false);
    }
  };

  const closeIncident = () => {
    setDetailId(null);
    setDetail(null);
  };

  // Format confidence helper
  const fmtConf = (c) => `${(Number(c) <= 1 ? Number(c) * 100 : Number(c)).toFixed(0)}%`;

  const showToast = (msg) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3500);
  };

  // Fetch system status
  const fetchSystemStatus = React.useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) {
        const data = await res.json();
        setSystemHealth(data);
        if (data.automation_mode) setAutomationMode(data.automation_mode);
      }
    } catch {
      setSystemHealth({ status: 'disconnected', database: 'disconnected' });
    }
  }, []);

  // Fetch traffic status & stats
  const fetchTrafficStatus = React.useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/traffic/status`);
      if (res.ok) {
        const data = await res.json();
        setTrafficStats(data);
      }
    } catch {
      // Backend offline
    }
  }, []);

  // Fetch recent flows on the monitored port
  const fetchFlows = React.useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/traffic/flows?limit=30&threat_only=${threatOnly}`);
      if (res.ok) {
        const data = await res.json();
        setFlows(data);
      }
    } catch {
      // Ignore
    }
  }, [threatOnly]);

  // Fetch overview metrics
  const fetchOverview = React.useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/dashboard/overview`);
      if (res.ok) {
        const data = await res.json();
        setOverview(data);
        if (data.system) {
          setExecutorMode(data.system.executor);
        }
      }
    } catch {
      // Ignore
    }
  }, []);

  // Polling loop
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchSystemStatus();
      fetchTrafficStatus();
      fetchFlows();
      fetchOverview();
    }, 0);

    if (!isLivePolling) return () => clearTimeout(timer);
    const interval = setInterval(() => {
      fetchTrafficStatus();
      fetchFlows();
      fetchOverview();
    }, 1500);

    return () => {
      clearTimeout(timer);
      clearInterval(interval);
    };
  }, [isLivePolling, fetchSystemStatus, fetchTrafficStatus, fetchFlows, fetchOverview]);

  // Update Automation Mode
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
  const handlePortChange = async (e) => {
    if (e) e.preventDefault();
    const portNum = parseInt(portInput, 10);
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
    } catch {
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
    } catch {
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
    } catch {
      showToast('Failed to clear buffer');
    }
  };

  // Manual defence: contain (block) an incident source
  const handleRespond = async (incidentId) => {
    try {
      const res = await fetch(`${API_BASE}/api/incidents/${incidentId}/respond`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'block_ip' }),
      });
      const data = await res.json();
      if (res.ok) {
        showToast(
          data.status === 'already_blocked'
            ? `Source ${data.target} is already contained`
            : `Blocked ${data.target} (${data.enforcement})`
        );
        fetchOverview();
      } else {
        showToast(data.detail || 'Block refused');
      }
    } catch (err) {
      showToast(`Failed to block: ${err.message}`);
    }
  };

  // Manual defence: lift containment on an incident source
  const handleRelease = async (incidentId) => {
    try {
      const res = await fetch(`${API_BASE}/api/incidents/${incidentId}/release`, {
        method: 'POST',
      });
      const data = await res.json();
      if (res.ok) {
        showToast(`Released ${data.target} (${data.released} rule(s) lifted)`);
        fetchOverview();
      } else {
        showToast(data.detail || 'Release failed');
      }
    } catch (err) {
      showToast(`Failed to release: ${err.message}`);
    }
  };

  const navigateToConsole = () => {
    window.location.hash = '#console';
    setActiveView('console');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const navigateToLanding = () => {
    window.location.hash = '#';
    setActiveView('landing');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen text-white antialiased font-sans relative" style={{ background: '#0d0b0d' }}>

      {/* ── Global Fixed Background Image — consistent across ALL views and scroll ── */}
      <div
        className="fixed inset-0 w-full h-full pointer-events-none z-0"
        style={{
          backgroundImage: 'url(/assets/hero-bg.jpg)',
          backgroundSize: 'cover',
          backgroundPosition: 'center center',
          backgroundRepeat: 'no-repeat',
        }}
      >
        {/* Overlay: darkens just enough for text legibility while letting image breathe */}
        <div
          className="absolute inset-0"
          style={{
            background: 'linear-gradient(to bottom, rgba(13,11,13,0.38) 0%, rgba(13,11,13,0.22) 45%, rgba(13,11,13,0.52) 100%)',
          }}
        />
      </div>

      <div className="relative z-10 w-full min-h-screen">
        {activeView === 'console' ? (
          <SocConsole
            onBackToLanding={navigateToLanding}
            systemHealth={systemHealth}
            automationMode={automationMode}
            executorMode={executorMode}
            trafficStats={trafficStats}
            flows={flows}
            portInput={portInput}
            setPortInput={setPortInput}
            threatOnly={threatOnly}
            setThreatOnly={setThreatOnly}
            overview={overview}
            isLivePolling={isLivePolling}
            setIsLivePolling={setIsLivePolling}
            handlePortChange={handlePortChange}
            toggleTrafficMonitor={toggleTrafficMonitor}
            handleClearFlows={handleClearFlows}
            handleRespond={handleRespond}
            handleRelease={handleRelease}
            handleModeChange={handleModeChange}
            detailId={detailId}
            detail={detail}
            detailLoading={detailLoading}
            openIncident={openIncident}
            closeIncident={closeIncident}
            fmtConf={fmtConf}
          />
        ) : (
          <div className="flex flex-col w-full">
            {/* Hero — full-screen torii gate image (background managed inside SecurifyHero) */}
            <SecurifyHero
              onGetStarted={navigateToConsole}
              onOpenConsole={navigateToConsole}
            />

            {/* Below-hero sections — transparent, global bg image shows through */}
              {/* Real-time Telemetry Status Ticker */}
              <LiveTelemetryBanner
                systemHealth={systemHealth}
                trafficStats={trafficStats}
                overview={overview}
                automationMode={automationMode}
                onOpenConsole={navigateToConsole}
              />

              {/* Autonomous Architecture Bento Grid */}
              <PlatformBento onOpenConsole={navigateToConsole} />

              {/* Threat Solutions & Use Cases */}
              <SolutionsSection onOpenConsole={navigateToConsole} />

              {/* SaaS Footer */}
              <Footer onOpenConsole={navigateToConsole} />
          </div>
        )}
      </div>

      {/* Floating Notification Toast */}
      {toastMsg && (
        <div className="fixed bottom-6 right-6 z-50 border text-white px-5 py-3 rounded-2xl shadow-2xl text-xs font-mono flex items-center gap-3 backdrop-blur-xl"
          style={{ background: 'rgba(20,18,22,0.92)', borderColor: 'rgba(232,160,122,0.3)' }}>
          <span className="h-2 w-2 rounded-full animate-ping" style={{ background: '#e8a07a' }} />
          <span>{toastMsg}</span>
        </div>
      )}
    </div>
  );
}
