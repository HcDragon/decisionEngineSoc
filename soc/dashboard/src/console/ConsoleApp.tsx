import { useCallback, useMemo, useRef, useState } from 'react';
import './styles/fonts.css';
import './styles/tokens.css';
import './styles/console.css';
import type { SocDataSource } from './data/source';
import { ApiSocDataSource } from './data/api';
import { SocDataProvider, useSocSource } from './data/context';
import { useSocData } from './hooks/useSocData';
import { useStreamConnected } from './hooks/useLive';
import { useTheme } from './hooks/useTheme';
import { ConsoleContext } from './shell/ConsoleContext';
import { Sidebar } from './shell/Sidebar';
import { Breadcrumbs, TitleRow } from './shell/TopBars';
import { IncidentDrawer } from './shell/IncidentDrawer';
import { pageMeta, type PageId } from './shell/nav';
import { DashboardPage } from './pages/Dashboard';
import { ThreatEventsPage } from './pages/ThreatEvents';
import { IncidentsPage } from './pages/Incidents';
import { DecisionEnginePage } from './pages/DecisionEngine';
import { NetworkTrafficPage } from './pages/NetworkTraffic';
import { AuditLogsPage } from './pages/AuditLogs';
import { SystemStatusPage } from './pages/SystemStatus';
import { SettingsPage } from './pages/Settings';

/** Composition root: the only place that picks the SocDataSource implementation. */
function createSource(apiBase: string): SocDataSource {
  return new ApiSocDataSource(apiBase);
}

function Shell({ onExit }: { onExit: () => void }) {
  const { theme, toggle } = useTheme();
  const [page, setPage] = useState<PageId>('dashboard');
  const [query, setQuery] = useState('');
  const [incident, setIncident] = useState<number | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const source = useSocSource();
  const status = useSocData('status', (s) => s.getStatus(), { pollMs: 5_000 });
  const [captureBusy, setCaptureBusy] = useState(false);
  const streamLive = useStreamConnected();

  const notify = useCallback((message: string) => {
    setToast(message);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 4000);
  }, []);
  // Return focus to whatever opened the drawer (re-found by label if it re-rendered).
  const opener = useRef<{ el: HTMLElement | null; label: string | null }>({ el: null, label: null });
  const openIncident = useCallback((id: number) => {
    const el = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    opener.current = { el, label: el?.getAttribute('aria-label') ?? null };
    setIncident(id);
  }, []);
  const closeIncident = useCallback(() => {
    setIncident(null);
    requestAnimationFrame(() => {
      const { el, label } = opener.current;
      const target = el?.isConnected ? el
        : label ? document.querySelector<HTMLElement>(`.soc [aria-label="${CSS.escape(label)}"]`) : null;
      target?.focus();
    });
  }, []);
  const api = useMemo(() => ({ query, openIncident, notify }), [query, openIncident, notify]);

  const snap = status.status === 'ready' ? status.data : null;

  const toggleCapture = async () => {
    if (!snap) return;
    setCaptureBusy(true);
    const r = await source.setCapture(!snap.captureRunning, snap.monitoredPort || undefined);
    setCaptureBusy(false);
    notify(r.message);
    status.retry();
  };
  const meta = pageMeta(page);
  const navigate = (p: PageId) => { setPage(p); window.scrollTo({ top: 0 }); };

  const footnote = !snap ? null
    : snap.connected && snap.dataMode === 'emulated' ? 'The NFStream sensor is running in emulated-stream mode, so capture figures are synthetic rather than observed traffic.'
    : null;

  const body = (() => {
    switch (page) {
      case 'dashboard': return <DashboardPage />;
      case 'threats': return <ThreatEventsPage />;
      case 'incidents': return <IncidentsPage />;
      case 'decision': return <DecisionEnginePage />;
      case 'traffic': return <NetworkTrafficPage />;
      case 'audit': return <AuditLogsPage />;
      case 'system': return <SystemStatusPage />;
      case 'settings': return <SettingsPage theme={theme} onToggleTheme={toggle} />;
    }
  })();

  return (
    <ConsoleContext.Provider value={api}>
      <div className="soc">
        <Sidebar page={page} onNavigate={navigate} status={snap} onExit={onExit} />
        <main className="soc-content">
          <Breadcrumbs pageLabel={meta.label} status={snap} streamLive={streamLive} theme={theme} onToggleTheme={toggle}
            onToggleCapture={toggleCapture} captureBusy={captureBusy} />
          <TitleRow title={meta.title} subtitle={meta.subtitle} query={query} onQuery={setQuery} />
          {body}
          {footnote && <p className="soc-footnote">{footnote}</p>}
        </main>
        {incident !== null && <IncidentDrawer id={incident} onClose={closeIncident} />}
        <div className="soc-sr" aria-live="polite">{toast ?? ''}</div>
        {toast && <div className="soc-toast" aria-hidden="true">{toast}</div>}
      </div>
    </ConsoleContext.Provider>
  );
}

export default function ConsoleApp({ apiBase, onExit }: { apiBase: string; onExit: () => void }) {
  const source = useMemo(() => createSource(apiBase), [apiBase]);
  return (
    <SocDataProvider source={source}>
      <Shell onExit={onExit} />
    </SocDataProvider>
  );
}
