import React, { useState } from 'react';
import {
  LayoutDashboard, ShieldAlert, Siren, Network, Server, BookOpen,
  FileBarChart, ScrollText, Activity, Settings as SettingsIcon,
  ArrowLeft, Bell, Radio, Search,
} from 'lucide-react';
import { Badge } from './ui';
import { DashboardPage } from './pages/Dashboard';
import { ThreatEventsPage } from './pages/ThreatEvents';
import { IncidentsPage } from './pages/Incidents';
import { NetworkTrafficPage } from './pages/NetworkTraffic';
import { DecisionEnginePage } from './pages/DecisionEngine';
import { SystemStatusPage } from './pages/SystemStatus';
import { AuditLogsPage } from './pages/AuditLogs';
import { SettingsPage } from './pages/Settings';
import { Placeholder } from './ui';
import { IncidentDetailModal } from '../IncidentDetailModal';

const NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'threats', label: 'Threat Events', icon: ShieldAlert },
  { id: 'incidents', label: 'Incidents', icon: Siren },
  { id: 'traffic', label: 'Network Traffic', icon: Network },
  { id: 'decision', label: 'Decision Engine', icon: Activity },
  { id: 'assets', label: 'Assets', icon: Server },
  { id: 'playbooks', label: 'Playbooks', icon: BookOpen },
  { id: 'reports', label: 'Reports', icon: FileBarChart },
  { id: 'audit', label: 'Audit Logs', icon: ScrollText },
  { id: 'system', label: 'System Status', icon: Server },
  { id: 'settings', label: 'Settings', icon: SettingsIcon },
];

export const ConsoleShell: React.FC<any> = (ctx) => {
  const [page, setPage] = useState('dashboard');
  const { systemHealth, trafficStats, overview } = ctx;

  const connected = systemHealth?.status === 'healthy';
  const engine = trafficStats?.engine_mode;
  const live = engine === 'native_nfstream';
  const openIncidents = overview?.stats?.open_incidents ?? (overview?.incidents?.length ?? 0);

  const render = () => {
    switch (page) {
      case 'dashboard': return <DashboardPage ctx={ctx} goto={setPage} />;
      case 'threats': return <ThreatEventsPage ctx={ctx} />;
      case 'incidents': return <IncidentsPage ctx={ctx} />;
      case 'traffic': return <NetworkTrafficPage ctx={ctx} />;
      case 'decision': return <DecisionEnginePage ctx={ctx} />;
      case 'audit': return <AuditLogsPage ctx={ctx} />;
      case 'system': return <SystemStatusPage ctx={ctx} />;
      case 'settings': return <SettingsPage ctx={ctx} />;
      case 'assets': return <Placeholder title="Assets" reason="Asset inventory is defined in soc/config/assets.yaml but is not exposed by a backend API endpoint, so there is no live data to show here." />;
      case 'playbooks': return <Placeholder title="Playbook Catalog" reason="Playbook definitions live in soc/config/playbooks/*.yaml and aren't served by an API. Active mitigations and per-incident playbook execution are shown on the Incidents page." />;
      case 'reports': return <Placeholder title="Reports" reason="No reporting endpoint exists in the backend. Threat, incident and audit data can be reviewed on their respective pages." />;
      default: return null;
    }
  };

  return (
    <div className="min-h-screen w-full flex font-sans">
      {/* Neobrutalist Sidebar */}
      <aside className="w-[230px] shrink-0 border-r-[3px] border-[#0d0d11] bg-[rgba(26,21,24,0.96)] flex flex-col sticky top-0 h-screen shadow-[4px_0px_0px_#0d0d11] z-30">
        <div className="px-4 h-16 flex items-center gap-3 border-b-[2.5px] border-[#0d0d11] bg-[#1d171b]">
          <div className="grid place-items-center h-9 w-9 rounded-xl bg-[#faf6f0] border-[2px] border-[#0d0d11] shadow-[2px_2px_0px_#0d0d11]">
            <ShieldAlert size={18} className="text-[var(--torii-vermilion)]" />
          </div>
          <div className="leading-tight">
            <div className="text-[0.92rem] font-extrabold uppercase tracking-wider text-white">RASHOMON</div>
            <div className="text-[0.64rem] font-mono font-bold text-[var(--torii-amber)]">SOC CONSOLE</div>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto py-2">
          {NAV.map((n) => {
            const Icon = n.icon;
            const active = page === n.id;
            return (
              <button
                key={n.id}
                onClick={() => setPage(n.id)}
                className={`w-full flex items-center gap-3 px-4 py-2.5 text-[0.8rem] uppercase font-bold tracking-wide transition-all ${
                  active
                    ? 'bg-[var(--torii-vermilion)] text-white border-y-[1.5px] border-r-[2.5px] border-[#0d0d11] shadow-[2.5px_2.5px_0px_#0d0d11]'
                    : 'text-[#c5bebe] hover:text-white hover:bg-[rgba(255,255,255,0.06)]'
                }`}
              >
                <Icon size={16} /> {n.label}
              </button>
            );
          })}
        </nav>
        <button
          onClick={ctx.onBackToLanding}
          className="m-3 flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-xl text-[0.74rem] font-extrabold uppercase tracking-wider bg-[#faf6f0] text-[#0d0d11] border-[2px] border-[#0d0d11] shadow-[2.5px_2.5px_0px_#0d0d11] hover:bg-white active:translate-x-[1px] active:translate-y-[1px] transition-all cursor-pointer"
        >
          <ArrowLeft size={14} /> Back to site
        </button>
      </aside>

      {/* Main column */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Neobrutalist Top bar */}
        <header className="h-16 shrink-0 border-b-[3px] border-[#0d0d11] bg-[rgba(26,21,24,0.96)] px-6 flex items-center gap-4 sticky top-0 z-20 shadow-[0_4px_0px_#0d0d11]">
          <div className="text-[1rem] font-extrabold uppercase tracking-wider text-white">
            {NAV.find((n) => n.id === page)?.label}
          </div>
          <div className="flex-1 max-w-sm relative hidden md:block">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#544d49]" />
            <input
              disabled
              placeholder="Search incidents, IPs, threat IDs..."
              className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-[#faf6f0] border-[2px] border-[#0d0d11] shadow-[2px_2px_0px_#0d0d11] text-[0.78rem] text-[#0d0d11] placeholder:text-[#706764] font-mono font-medium cursor-not-allowed"
              title="Search is not yet backed by an API endpoint"
            />
          </div>
          <div className="ml-auto flex items-center gap-3">
            <Badge tone={live ? 'success' : 'warning'}>
              <Radio size={12} /> {live ? 'LIVE' : 'TEST / REPLAY'}
            </Badge>
            <Badge tone={connected ? 'success' : 'danger'}>
              <span
                className="h-2 w-2 rounded-full border border-[#0d0d11]"
                style={{ background: connected ? 'var(--torii-sage)' : 'var(--torii-vermilion)' }}
              />
              {connected ? 'CONNECTED' : 'OFFLINE'}
            </Badge>
            <div
              className="relative text-white p-2 rounded-xl bg-[#faf6f0] border-[2px] border-[#0d0d11] shadow-[2px_2px_0px_#0d0d11] cursor-pointer"
              title={`${openIncidents} open incident(s)`}
            >
              <Bell size={16} className="text-[#0d0d11]" />
              {openIncidents > 0 && (
                <span
                  className="absolute -top-1.5 -right-1.5 h-5 min-w-5 px-1 grid place-items-center rounded-full text-[0.62rem] font-mono font-extrabold text-white border border-[#0d0d11] shadow-[1px_1px_0px_#0d0d11]"
                  style={{ background: 'var(--torii-vermilion)' }}
                >
                  {openIncidents}
                </span>
              )}
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6">{render()}</main>
      </div>

      {/* Incident forensic detail — opened from any page via ctx.openIncident */}
      {ctx.detailId !== null && (
        <IncidentDetailModal
          detailId={ctx.detailId}
          detail={ctx.detail}
          loading={ctx.detailLoading}
          onClose={ctx.closeIncident}
          fmtConf={ctx.fmtConf}
        />
      )}
    </div>
  );
};
