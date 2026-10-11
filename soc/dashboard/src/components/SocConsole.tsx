import React from 'react';
import {
  Activity,
  Radio,
  AlertTriangle,
  Cpu,
  Lock,
  Play,
  Square,
  RefreshCw,
  ShieldCheck,
  Hand,
  Ban,
  Unlock,
  Filter,
  CheckCircle2,
  ArrowLeft,
} from 'lucide-react';
import { IncidentDetailModal } from './IncidentDetailModal';
import { PipelineMesh } from './PipelineMesh';

interface SocConsoleProps {
  onBackToLanding: () => void;
  apiBase: string;
  systemHealth: any;
  automationMode: string;
  executorMode: string;
  trafficStats: any;
  flows: any[];
  portInput: string;
  setPortInput: (val: string) => void;
  threatOnly: boolean;
  setThreatOnly: React.Dispatch<React.SetStateAction<boolean>>;
  overview: any;
  isLivePolling: boolean;
  setIsLivePolling: React.Dispatch<React.SetStateAction<boolean>>;
  handlePortChange: (e: React.FormEvent) => void;
  toggleTrafficMonitor: () => void;
  handleClearFlows: () => void;
  handleRespond: (id: string | number) => void;
  handleRelease: (id: string | number) => void;
  handleModeChange: (mode: 'auto' | 'recommend_only' | 'off') => void;
  detailId: string | number | null;
  detail: any;
  detailLoading: boolean;
  openIncident: (id: string | number) => void;
  closeIncident: () => void;
  fmtConf: (c: number | undefined) => string;
}

export const SocConsole: React.FC<SocConsoleProps> = ({
  onBackToLanding,
  apiBase,
  systemHealth,
  automationMode,
  executorMode,
  trafficStats,
  flows,
  portInput,
  setPortInput,
  threatOnly,
  setThreatOnly,
  overview,
  isLivePolling,
  setIsLivePolling,
  handlePortChange,
  toggleTrafficMonitor,
  handleClearFlows,
  handleRespond,
  handleRelease,
  handleModeChange,
  detailId,
  detail,
  detailLoading,
  openIncident,
  closeIncident,
  fmtConf,
}) => {
  const isAuto = automationMode === 'auto';
  const isManual = automationMode === 'recommend_only';
  const isHealthy = systemHealth?.status === 'healthy';

  // Protocol percentage calculation
  const totalProtoCount = Math.max(
    1,
    (trafficStats.protocol_distribution.TCP || 0) +
      (trafficStats.protocol_distribution.UDP || 0) +
      (trafficStats.protocol_distribution.ICMP || 0)
  );
  const tcpPct = Math.round(((trafficStats.protocol_distribution.TCP || 0) / totalProtoCount) * 100);
  const udpPct = Math.round(((trafficStats.protocol_distribution.UDP || 0) / totalProtoCount) * 100);
  const icmpPct = Math.max(0, 100 - tcpPct - udpPct);

  // Filter flows
  const displayedFlows = threatOnly
    ? flows.filter((f) => f.is_threat || f.threat || ((f.threat_label || f.label) && !(f.threat_label || f.label).toLowerCase().includes('benign')))
    : flows;

  return (
    <div className="min-h-screen text-white flex flex-col font-sans select-none relative overflow-x-hidden">
      {/* Subtle ambient glow for console — single cool-blue tone */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute -top-36 -left-36 w-[520px] h-[520px] rounded-full bg-sky-400/10 blur-[130px] animate-orb-1 opacity-60" />
        <div className="absolute -top-10 -right-20 w-[480px] h-[480px] rounded-full bg-blue-500/10 blur-[140px] animate-orb-2 opacity-50" />
        <div className="absolute top-1/2 left-1/3 w-[560px] h-[560px] rounded-full bg-cyan-400/8 blur-[150px] animate-orb-3 opacity-40" />
      </div>

      {/* Console Top Header (Frosted Glass) */}
      <header className="sticky top-0 z-40 bg-white/[0.06] border-b border-white/15 backdrop-blur-2xl px-4 sm:px-8 py-3.5 flex items-center justify-between gap-4 flex-wrap relative shadow-[0_8px_32px_0_rgba(0,0,0,0.25)]">
        {/* Glowing bottom gradient line */}
        <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-gradient-to-r from-sky-400 via-blue-400 to-cyan-400 shadow-[0_0_10px_rgba(56,189,248,0.5)]" />

        {/* Brand & Back Button */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onBackToLanding}
            className="flex items-center gap-2 bg-white/[0.08] hover:bg-white/[0.14] border border-white/10 hover:border-white/20 backdrop-blur-xl rounded-full px-3.5 py-1.5 text-xs text-neutral-300 hover:text-white transition-all cursor-pointer shadow-sm hover:shadow-[0_0_15px_rgba(255,255,255,0.1)]"
            title="Return to Public Landing Page"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>roshomon</span>
          </button>

          <div className="h-4 w-px bg-white/10 hidden sm:block" />

          <div>
            <div className="text-white text-sm font-semibold tracking-tight flex items-center gap-2">
              <span>AI Smart SOC Manager</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 backdrop-blur-md">
                LIVE
              </span>
            </div>
            <div className="text-[11px] text-neutral-400">Autonomous Decision Engine &amp; NFStream Tap</div>
          </div>
        </div>

        {/* Center / Right Controls */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Health indicator */}
          <div
            className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-mono border backdrop-blur-2xl ${
              isHealthy
                ? 'bg-black/40 border-white/10 text-neutral-300'
                : 'bg-rose-500/20 border-rose-500/40 text-rose-300'
            }`}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                isHealthy ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]' : 'bg-rose-500'
              }`}
            />
            <span>API: {isHealthy ? 'PORT 8000 (CONNECTED)' : 'STANDBY'}</span>
          </div>

          {/* Executor Badge */}
          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-mono bg-black/40 border border-blue-500/40 text-blue-300 backdrop-blur-2xl">
            <Cpu className="h-3.5 w-3.5" />
            <span>EXECUTOR: {executorMode.toUpperCase()}</span>
          </div>

          {/* Defence Mode Segmented Switcher */}
          <div className="inline-flex p-1 bg-black/50 border border-white/10 rounded-full text-xs font-medium backdrop-blur-2xl">
            <button
              type="button"
              onClick={() => handleModeChange('auto')}
              className={`px-3 py-1 rounded-full flex items-center gap-1.5 transition-colors cursor-pointer ${
                isAuto
                  ? 'bg-emerald-500 text-black font-semibold shadow-[0_0_12px_rgba(16,185,129,0.4)]'
                  : 'text-neutral-400 hover:text-white'
              }`}
              title="Autonomous containment: engine blocks malicious sources on its own"
            >
              <ShieldCheck className="h-3.5 w-3.5" />
              <span>AUTOMATIC</span>
            </button>

            <button
              type="button"
              onClick={() => handleModeChange('recommend_only')}
              className={`px-3 py-1 rounded-full flex items-center gap-1.5 transition-colors cursor-pointer ${
                isManual
                  ? 'bg-amber-500 text-black font-semibold shadow-[0_0_12px_rgba(245,158,11,0.4)]'
                  : 'text-neutral-400 hover:text-white'
              }`}
              title="Manual mode: analyst approves containment from incidents panel"
            >
              <Hand className="h-3.5 w-3.5" />
              <span>MANUAL</span>
            </button>

            <button
              type="button"
              onClick={() => handleModeChange('off')}
              className={`px-3 py-1 rounded-full transition-colors cursor-pointer ${
                automationMode === 'off'
                  ? 'bg-neutral-700 text-white font-semibold'
                  : 'text-neutral-400 hover:text-white'
              }`}
              title="Monitor only — no automated response"
            >
              <span>OFF</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-8 space-y-6 relative z-10">
        {/* Project Context & Lab Topology Frosted Pill Strip */}
        <section className="backdrop-blur-2xl bg-black/40 border border-white/10 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3 shadow-[0_8px_32px_0_rgba(0,0,0,0.37)] text-xs font-mono">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-cyan-400 flex items-center gap-1.5 font-semibold">
              <span className="h-2 w-2 rounded-full bg-cyan-400 animate-ping" />
              TOPOLOGY:
            </span>
            <span className="px-2.5 py-1 rounded-full bg-white/[0.05] border border-white/10 text-neutral-300">
              victim_ns <span className="text-neutral-500 font-normal">(10.66.0.1)</span>
            </span>
            <span className="text-neutral-500">↔</span>
            <span className="px-2.5 py-1 rounded-full bg-white/[0.05] border border-white/10 text-neutral-300">
              router_ns <span className="text-neutral-500 font-normal">(10.66.0.254 · nft)</span>
            </span>
            <span className="text-neutral-500">↔</span>
            <span className="px-2.5 py-1 rounded-full bg-white/[0.05] border border-white/10 text-neutral-300">
              attacker_ns <span className="text-neutral-500 font-normal">(10.66.0.2)</span>
            </span>
          </div>

          <div className="flex items-center gap-2 flex-wrap text-[11px] text-neutral-400">
            <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-300">
              NFStream 57-DPI
            </span>
            <span className="px-2.5 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-300">
              ML 7-Stage Gate
            </span>
            <span className="px-2.5 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-300">
              120s Auto-Reap TTL
            </span>
            <span className="px-2.5 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300">
              SHA-256 Ledger
            </span>
          </div>
        </section>

        {/* Live Pipeline Mesh — real-time SSE-driven architecture view (additive) */}
        <PipelineMesh apiBase={apiBase} />

        {/* Posture Banner when in Manual Mode */}
        {isManual && (
          <div className="p-4 rounded-2xl bg-amber-500/15 border border-amber-500/40 backdrop-blur-2xl flex items-center justify-between gap-4 text-xs text-amber-300 shadow-[0_8px_32px_rgba(245,158,11,0.2)]">
            <div className="flex items-center gap-3">
              <Hand className="h-5 w-5 text-amber-400 shrink-0" />
              <span>
                <b>MANUAL DEFENCE ARMED:</b> The autonomous engine recommends mitigation actions, but requires analyst approval to apply nft containment rules.
              </span>
            </div>
            <button
              type="button"
              onClick={() => handleModeChange('auto')}
              className="px-3 py-1 rounded-full bg-amber-400 text-black font-semibold hover:bg-amber-300 transition-colors whitespace-nowrap cursor-pointer shadow-md"
            >
              switch to auto
            </button>
          </div>
        )}

        {/* Bento Metrics Grid (Frosted Glass) */}
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Port Ingestion */}
          <div className="group relative overflow-hidden backdrop-blur-2xl bg-black/40 border border-white/10 hover:border-cyan-500/50 hover:bg-black/50 rounded-2xl p-5 transition-all duration-300 shadow-[0_8px_32px_0_rgba(0,0,0,0.45)] hover:shadow-[0_8px_32px_0_rgba(6,182,212,0.25)]">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-cyan-400 to-blue-500" />
            <div className="text-xs text-cyan-300/80 font-mono flex items-center justify-between">
              <span>Port {trafficStats.monitored_port} Ingestion</span>
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-ping" />
            </div>
            <div className="text-3xl font-medium text-white tracking-tight mt-2 flex items-baseline">
              {trafficStats.current_packets_per_sec}
              <span className="text-xs text-neutral-400 font-normal ml-1.5">pkts/s</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-cyan-400 mt-3 pt-3 border-t border-white/5">
              <Activity size={13} />
              <span>bandwidth: {trafficStats.current_kb_per_sec} KB/s</span>
            </div>
          </div>

          {/* Card 2: Monitored Buffer */}
          <div className="group relative overflow-hidden backdrop-blur-2xl bg-black/40 border border-white/10 hover:border-emerald-500/50 hover:bg-black/50 rounded-2xl p-5 transition-all duration-300 shadow-[0_8px_32px_0_rgba(0,0,0,0.45)] hover:shadow-[0_8px_32px_0_rgba(16,185,129,0.25)]">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-400 to-teal-500" />
            <div className="text-xs text-emerald-300/80 font-mono flex items-center justify-between">
              <span>Monitored Flow Buffer</span>
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            </div>
            <div className="text-3xl font-medium text-white tracking-tight mt-2 flex items-baseline">
              {trafficStats.total_flows.toLocaleString()}
              <span className="text-xs text-neutral-400 font-normal ml-1.5">flows</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-emerald-400 mt-3 pt-3 border-t border-white/5">
              <Radio size={13} />
              <span>total: {(trafficStats.total_bytes / 1024).toFixed(1)} KB metered</span>
            </div>
          </div>

          {/* Card 3: Threat Anomaly Rate */}
          <div className="group relative overflow-hidden backdrop-blur-2xl bg-black/40 border border-white/10 hover:border-rose-500/50 hover:bg-black/50 rounded-2xl p-5 transition-all duration-300 shadow-[0_8px_32px_0_rgba(0,0,0,0.45)] hover:shadow-[0_8px_32px_0_rgba(244,63,94,0.25)]">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-rose-500 to-amber-500" />
            <div className="text-xs text-rose-300/80 font-mono flex items-center justify-between">
              <span>Threat Anomaly Rate</span>
              <span className={`h-1.5 w-1.5 rounded-full ${trafficStats.threat_flows_count > 0 ? 'bg-rose-400 animate-pulse' : 'bg-emerald-400'}`} />
            </div>
            <div
              className={`text-3xl font-medium tracking-tight mt-2 flex items-baseline ${
                trafficStats.threat_flows_count > 0 ? 'text-rose-400' : 'text-emerald-400'
              }`}
            >
              {trafficStats.total_flows > 0
                ? ((trafficStats.threat_flows_count / trafficStats.total_flows) * 100).toFixed(1)
                : '0.0'}
              <span className="text-xs text-neutral-400 font-normal ml-1.5">%</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-rose-400 mt-3 pt-3 border-t border-white/5">
              <AlertTriangle size={13} />
              <span>{trafficStats.threat_flows_count} IDS threat detections</span>
            </div>
          </div>

          {/* Card 4: Active Containment */}
          <div className="group relative overflow-hidden backdrop-blur-2xl bg-black/40 border border-white/10 hover:border-purple-500/50 hover:bg-black/50 rounded-2xl p-5 transition-all duration-300 shadow-[0_8px_32px_0_rgba(0,0,0,0.45)] hover:shadow-[0_8px_32px_0_rgba(168,85,247,0.25)]">
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-purple-500 to-indigo-500" />
            <div className="text-xs text-purple-300/80 font-mono flex items-center justify-between">
              <span>Active Containment</span>
              <span className="h-1.5 w-1.5 rounded-full bg-purple-400" />
            </div>
            <div className="text-3xl font-medium text-white tracking-tight mt-2 flex items-baseline">
              {overview?.stats?.active_blocks ?? 0}
              <span className="text-xs text-neutral-400 font-normal ml-1.5">blocks</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-purple-400 mt-3 pt-3 border-t border-white/5">
              <Lock size={13} />
              <span>virtual firewall guardrails active</span>
            </div>
          </div>
        </section>

        {/* Traffic Monitor Controls Strip (Frosted Glass) */}
        <section className="backdrop-blur-2xl bg-black/40 border border-white/10 rounded-2xl p-4 sm:p-5 flex flex-wrap items-center justify-between gap-4 shadow-[0_8px_32px_0_rgba(0,0,0,0.45)]">
          <form onSubmit={handlePortChange} className="flex items-center gap-2">
            <span className="text-xs text-neutral-400 font-mono uppercase">target port:</span>
            <input
              type="number"
              value={portInput}
              onChange={(e) => setPortInput(e.target.value)}
              className="w-24 bg-black/50 border border-white/15 rounded-xl px-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-cyan-400 backdrop-blur-md transition-colors"
            />
            <button
              type="submit"
              className="bg-white/[0.08] hover:bg-white/[0.15] border border-white/10 text-white text-xs px-3.5 py-1.5 rounded-xl transition-all cursor-pointer hover:shadow-sm backdrop-blur-md"
            >
              set port
            </button>
          </form>

          <div className="flex items-center gap-2 flex-wrap">
            <button
              type="button"
              onClick={toggleTrafficMonitor}
              className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-medium transition-all cursor-pointer backdrop-blur-md ${
                trafficStats.status === 'running'
                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 hover:bg-rose-500/30 shadow-[0_0_15px_rgba(244,63,94,0.2)]'
                  : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 hover:bg-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.2)]'
              }`}
            >
              {trafficStats.status === 'running' ? <Square size={13} /> : <Play size={13} />}
              <span>{trafficStats.status === 'running' ? 'pause monitor' : 'start monitor'}</span>
            </button>

            <button
              type="button"
              onClick={handleClearFlows}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs bg-white/[0.06] hover:bg-white/[0.12] border border-white/10 text-neutral-300 hover:text-white transition-all cursor-pointer backdrop-blur-md"
            >
              <RefreshCw size={13} />
              <span>clear flow buffer</span>
            </button>

            <button
              type="button"
              onClick={() => setIsLivePolling((prev) => !prev)}
              className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-medium border transition-all cursor-pointer backdrop-blur-md ${
                isLivePolling
                  ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.2)]'
                  : 'bg-white/[0.05] border-white/10 text-neutral-400'
              }`}
            >
              <span className={`h-2 w-2 rounded-full ${isLivePolling ? 'bg-emerald-400 animate-pulse' : 'bg-neutral-600'}`} />
              <span>{isLivePolling ? 'live polling on' : 'polling paused'}</span>
            </button>
          </div>
        </section>

        {/* Protocol Distribution & Traffic Stats (Frosted Glass) */}
        <section className="backdrop-blur-2xl bg-black/40 border border-white/10 rounded-2xl p-5 shadow-[0_8px_32px_0_rgba(0,0,0,0.45)]">
          <div className="flex items-center justify-between text-xs text-neutral-400 font-mono uppercase mb-3">
            <span>protocol distribution</span>
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5 text-blue-400">
                <span className="h-2 w-2 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.8)]" /> TCP {tcpPct}%
              </span>
              <span className="flex items-center gap-1.5 text-emerald-400">
                <span className="h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]" /> UDP {udpPct}%
              </span>
              <span className="flex items-center gap-1.5 text-purple-400">
                <span className="h-2 w-2 rounded-full bg-purple-500 shadow-[0_0_8px_rgba(168,85,247,0.8)]" /> ICMP {icmpPct}%
              </span>
            </div>
          </div>
          {/* Multi-segmented bar */}
          <div className="h-2.5 w-full bg-black/60 border border-white/5 rounded-full overflow-hidden flex shadow-inner">
            <div style={{ width: `${tcpPct}%` }} className="bg-gradient-to-r from-blue-600 to-cyan-400 transition-all duration-300 shadow-[0_0_10px_rgba(59,130,246,0.5)]" />
            <div style={{ width: `${udpPct}%` }} className="bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-300 shadow-[0_0_10px_rgba(16,185,129,0.5)]" />
            <div style={{ width: `${icmpPct}%` }} className="bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-300 shadow-[0_0_10px_rgba(168,85,247,0.5)]" />
          </div>
        </section>

        {/* Active Incidents & Decision Panel (Frosted Glass) */}
        <section className="backdrop-blur-2xl bg-black/40 border border-white/10 rounded-3xl p-6 shadow-[0_8px_32px_0_rgba(0,0,0,0.45)]">
          <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
            <div>
              <span className="text-xs font-mono uppercase text-cyan-400/80">decision engine output</span>
              <h3 className="text-xl font-medium text-white tracking-tight mt-0.5">
                Active SOC Incidents ({overview?.incidents?.length || 0})
              </h3>
            </div>
            <div className="text-xs text-neutral-400 font-mono">
              click any incident row to inspect ML vectors &amp; guardrails
            </div>
          </div>

          <div className="space-y-3">
            {(!overview?.incidents || overview.incidents.length === 0) && (
              <div className="text-center py-12 text-neutral-400 text-sm border border-dashed border-white/10 rounded-2xl bg-white/[0.02] backdrop-blur-md">
                no active incidents detected. system is monitoring port {trafficStats.monitored_port}.
              </div>
            )}

            {(overview?.incidents || []).map((inc: any) => {
              const d = inc.decisions?.[0];
              const isBlocked = inc.status === 'contained' || inc.status === 'blocked';
              const isThreat = inc.severity === 'critical' || inc.severity === 'high';

              return (
                <div
                  key={inc.id}
                  onClick={() => openIncident(inc.id)}
                  className="backdrop-blur-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 hover:border-white/20 rounded-2xl p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all cursor-pointer group shadow-[0_4px_20px_0_rgba(0,0,0,0.25)]"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-mono text-neutral-400">#{inc.id}</span>
                      <span
                        className={`text-xs font-mono uppercase px-2.5 py-0.5 rounded-full border backdrop-blur-md ${
                          isThreat
                            ? 'bg-rose-500/20 border-rose-500/40 text-rose-300 shadow-[0_0_10px_rgba(244,63,94,0.2)]'
                            : 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300 shadow-[0_0_10px_rgba(16,185,129,0.2)]'
                        }`}
                      >
                        {inc.classification || inc.title || 'SUSPICIOUS FLOW'}
                      </span>
                      <span className="text-xs text-neutral-400 font-mono">
                        tier {inc.severity || 'high'}
                      </span>
                      {d && (
                        <span className="text-xs text-neutral-400 font-mono">
                          rule: {d.rule_id} · risk {Number(d.risk_score || 0).toFixed(1)}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-neutral-400 font-mono">
                      src: <span className="text-white font-medium">{inc.source_ip || inc.target || '10.66.0.2'}</span> · time: {inc.created_at?.replace('T', ' ').slice(0, 19) || 'now'}
                    </div>
                  </div>

                  {/* Manual / Auto Action Button */}
                  <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                    {isAuto && (
                      <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-mono bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 shadow-[0_0_10px_rgba(16,185,129,0.2)] backdrop-blur-md">
                        <CheckCircle2 size={13} />
                        <span>auto-contained</span>
                      </span>
                    )}

                    {isManual && !isBlocked && (
                      <button
                        type="button"
                        onClick={() => handleRespond(inc.id)}
                        className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-semibold bg-rose-500 text-white hover:bg-rose-600 transition-all cursor-pointer shadow-[0_0_15px_rgba(244,63,94,0.3)] backdrop-blur-md"
                      >
                        <Ban size={13} />
                        <span>block ip</span>
                      </button>
                    )}

                    {isManual && isBlocked && (
                      <button
                        type="button"
                        onClick={() => handleRelease(inc.id)}
                        className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-semibold bg-white/[0.08] hover:bg-white/[0.15] border border-white/10 text-neutral-300 hover:text-white transition-all cursor-pointer backdrop-blur-md"
                      >
                        <Unlock size={13} />
                        <span>release block</span>
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={() => openIncident(inc.id)}
                      className="px-3 py-1.5 rounded-full text-xs bg-white/[0.06] hover:bg-white/[0.12] border border-white/10 hover:border-white/20 text-neutral-300 group-hover:text-white transition-all shadow-sm backdrop-blur-md"
                    >
                      details →
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Live Flow Buffer Table (Frosted Glass) */}
        <section className="backdrop-blur-2xl bg-black/40 border border-white/10 rounded-3xl p-6 shadow-[0_8px_32px_0_rgba(0,0,0,0.45)]">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-4">
            <div>
              <span className="text-xs font-mono uppercase text-cyan-400/80">raw packet inspection</span>
              <h3 className="text-xl font-medium text-white tracking-tight mt-0.5">
                Live Flow Buffer ({displayedFlows.length})
              </h3>
            </div>
            <button
              type="button"
              onClick={() => setThreatOnly((prev) => !prev)}
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono border transition-all cursor-pointer backdrop-blur-md ${
                threatOnly
                  ? 'bg-rose-500/25 border-rose-500/50 text-rose-300 shadow-[0_0_12px_rgba(244,63,94,0.25)]'
                  : 'bg-white/[0.05] border-white/10 text-neutral-400 hover:text-white'
              }`}
            >
              <Filter size={12} />
              <span>{threatOnly ? 'threats only (active)' : 'show all flows'}</span>
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-white/10 text-neutral-400">
                  <th className="pb-3 font-normal">source ip : port</th>
                  <th className="pb-3 font-normal">destination ip : port</th>
                  <th className="pb-3 font-normal">proto</th>
                  <th className="pb-3 font-normal">packets</th>
                  <th className="pb-3 font-normal">bytes</th>
                  <th className="pb-3 font-normal">classifier</th>
                  <th className="pb-3 font-normal">status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-neutral-300">
                {displayedFlows.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-neutral-500 italic">
                      no flows in buffer. start traffic generator in attack lab to populate.
                    </td>
                  </tr>
                )}
                {displayedFlows.slice(0, 15).map((f: any, idx: number) => {
                  // Backend sends `is_threat` / `threat_label` (old `threat`/`label` kept as fallback).
                  const flowLabel = f.threat_label || f.label || '';
                  const isThreatFlow = f.is_threat || f.threat || (flowLabel !== '' && !flowLabel.toLowerCase().includes('benign'));
                  return (
                    <tr
                      key={idx}
                      className={`hover:bg-white/[0.06] transition-colors ${
                        isThreatFlow ? 'bg-rose-500/15' : ''
                      }`}
                    >
                      <td className="py-3 font-medium text-white">
                        {f.src_ip || '10.66.0.2'}:{f.src_port || '—'}
                      </td>
                      <td className="py-3 text-neutral-400">
                        {f.dst_ip || '10.66.0.1'}:{f.dst_port || trafficStats.monitored_port}
                      </td>
                      <td className="py-3">
                        <span className="px-2 py-0.5 rounded bg-white/[0.06] border border-white/10 text-neutral-300 backdrop-blur-sm">
                          {f.protocol || (f.proto === 6 ? 'TCP' : f.proto === 17 ? 'UDP' : 'IP')}
                        </span>
                      </td>
                      <td className="py-3">{f.bidirectional_packets || f.packets || 1}</td>
                      <td className="py-3">{f.bidirectional_bytes || f.bytes || 64} B</td>
                      <td className="py-3">
                        <span
                          className={`px-2 py-0.5 rounded backdrop-blur-sm ${
                            isThreatFlow
                              ? 'bg-rose-500/20 border border-rose-500/40 text-rose-300 font-semibold shadow-[0_0_10px_rgba(244,63,94,0.15)]'
                              : 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-300'
                          }`}
                        >
                          {flowLabel || (isThreatFlow ? 'THREAT' : 'BENIGN')}
                        </span>
                      </td>
                      <td className="py-3">
                        {isThreatFlow ? (
                          <span className="text-rose-400 flex items-center gap-1 font-semibold">
                            <AlertTriangle size={11} /> flagged
                          </span>
                        ) : (
                          <span className="text-neutral-500">allowed</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      </main>

      {/* Incident Detail Forensic Modal */}
      {detailId && (
        <IncidentDetailModal
          detailId={detailId}
          detail={detail}
          loading={detailLoading}
          onClose={closeIncident}
          fmtConf={fmtConf}
        />
      )}
    </div>
  );
};
