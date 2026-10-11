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
    // Transparent root so the landing background image (fixed in App.jsx) shows
    // through; surfaces are frosted-translucent for readability over it.
    <div className="min-h-screen w-full flex">
      {/* Sidebar */}
      <aside className="w-[220px] shrink-0 border-r border-[var(--border)] bg-[rgba(16,21,30,0.72)] backdrop-blur-xl flex flex-col sticky top-0 h-screen">
        <div className="px-4 h-14 flex items-center gap-2.5 border-b border-[var(--border)]">
          <div className="grid place-items-center h-8 w-8 rounded-md bg-[var(--accent-soft)] border border-[var(--accent)]/40">
            <ShieldAlert size={17} className="text-[var(--accent)]" />
          </div>
          <div className="leading-tight">
            <div className="text-[0.9rem] font-semibold text-[var(--text-main)] tracking-tight">Rashomon</div>
            <div className="text-[0.6rem] text-[var(--text-muted)]">SOC Console</div>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto py-2">
          {NAV.map((n) => {
            const Icon = n.icon; const active = page === n.id;
            return (
              <button key={n.id} onClick={() => setPage(n.id)}
                className={`w-full flex items-center gap-2.5 px-4 py-2 text-[0.8rem] transition-colors ${active ? 'bg-[var(--accent-soft)] text-[var(--text-main)] border-l-2 border-[var(--accent)]' : 'text-[var(--text-dim)] hover:text-[var(--text-main)] hover:bg-[var(--bg-hover)] border-l-2 border-transparent'}`}>
                <Icon size={15} /> {n.label}
              </button>
            );
          })}
        </nav>
        <button onClick={ctx.onBackToLanding} className="m-3 flex items-center justify-center gap-2 px-3 py-2 rounded-md text-[0.76rem] text-[var(--text-dim)] border border-[var(--border)] hover:text-[var(--text-main)] hover:border-[var(--border-strong)]">
          <ArrowLeft size={14} /> Back to site
        </button>
      </aside>

      {/* Main column */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Top bar */}
        <header className="h-14 shrink-0 border-b border-[var(--border)] bg-[rgba(16,21,30,0.72)] backdrop-blur-xl px-5 flex items-center gap-4 sticky top-0 z-20">
          <div className="text-[0.9rem] font-semibold text-[var(--text-main)]">{NAV.find(n => n.id === page)?.label}</div>
          <div className="flex-1 max-w-sm relative hidden md:block">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
            <input disabled placeholder="Search incidents, IPs, threat IDs…"
              className="w-full pl-8 pr-3 py-1.5 rounded-md bg-[var(--bg-inset)] border border-[var(--border)] text-[0.76rem] text-[var(--text-dim)] placeholder:text-[var(--text-muted)] cursor-not-allowed"
              title="Search is not yet backed by an API endpoint" />
          </div>
          <div className="ml-auto flex items-center gap-3">
            <Badge tone={live ? 'success' : 'warning'}>
              <Radio size={11} /> {live ? 'LIVE' : 'TEST / REPLAY'}
            </Badge>
            <Badge tone={connected ? 'success' : 'danger'}>
              <span className="h-1.5 w-1.5 rounded-full" style={{ background: connected ? 'var(--success)' : 'var(--danger)' }} />
              {connected ? 'Connected' : 'Offline'}
            </Badge>
            <div className="relative text-[var(--text-dim)]" title={`${openIncidents} open incident(s)`}>
              <Bell size={17} />
              {openIncidents > 0 && <span className="absolute -top-1.5 -right-1.5 h-4 min-w-4 px-1 grid place-items-center rounded-full text-[0.6rem] font-bold text-white" style={{ background: 'var(--danger)' }}>{openIncidents}</span>}
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-5">{render()}</main>
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
