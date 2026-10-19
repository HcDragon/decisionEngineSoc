import { Icon } from '../components/Icon';
import type { SystemSnapshot } from '../data/types';
import { executorLabel, formatClock } from '../data/derive';
import type { Theme } from '../hooks/useTheme';

interface CrumbProps {
  pageLabel: string;
  status: SystemSnapshot | null;
  streamLive: boolean;
  theme: Theme;
  onToggleTheme: () => void;
  onToggleCapture: () => void;
  captureBusy: boolean;
}

export function Breadcrumbs({ pageLabel, status, streamLive, theme, onToggleTheme, onToggleCapture, captureBusy }: CrumbProps) {
  const connected = !!status?.connected;
  const next = theme === 'dark' ? 'light' : 'dark';
  return (
    <div className="soc-crumbs">
      <nav aria-label="Breadcrumb">
        <ol>
          <li>Rashomon</li>
          <li aria-current="page">{pageLabel}</li>
        </ol>
      </nav>
      <div className="soc-crumbs-meta">
        <span className={`soc-pill ${connected ? 'soc-pill--up' : 'soc-pill--down'}`} role="status"
          title={connected ? (streamLive ? 'API reachable, live event stream connected' : 'API reachable, live stream reconnecting') : 'Backend unreachable'}>
          <span className={`soc-dot ${!connected ? 'soc-dot--off' : streamLive ? 'soc-dot--live' : 'soc-dot--static'}`} aria-hidden="true" />
          {connected ? 'Connected' : 'Disconnected'}
        </span>
        <span className="soc-num">Updated {status ? formatClock(status.checkedAt) : '—'}</span>
        {status?.connected && <span className="soc-tag" title="Active response executor">{executorLabel(status.executor)}</span>}
        {status?.connected && (
          <span className="soc-capture">
            <span className={`soc-status ${status.captureRunning ? 'soc-st-contained' : 'soc-st-investigating'}`}>
              {status.captureRunning ? `Capture on · port ${status.monitoredPort}` : 'Capture off'}
            </span>
            <button type="button" className={`soc-btn soc-btn--sm ${status.captureRunning ? 'soc-btn--danger' : 'soc-btn--primary'}`}
              onClick={onToggleCapture} disabled={captureBusy}
              aria-label={status.captureRunning ? 'Stop NFStream capture' : 'Start NFStream capture'}>
              {captureBusy ? 'Working…' : status.captureRunning ? 'Stop capture' : 'Start capture'}
            </button>
          </span>
        )}
        <button type="button" className="soc-btn soc-btn--sm" onClick={onToggleTheme} aria-label={`Switch to ${next} theme`}>
          <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={16} /> {next === 'light' ? 'Light' : 'Dark'}
        </button>
      </div>
    </div>
  );
}

export function TitleRow({ title, subtitle, query, onQuery }: { title: string; subtitle: string; query: string; onQuery: (q: string) => void }) {
  return (
    <div className="soc-title-row">
      <div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <div className="soc-search">
        <label htmlFor="soc-search" className="soc-sr">Search by incident, IP or threat ID</label>
        <Icon name="search" />
        <input id="soc-search" className="soc-input" type="search" value={query} onChange={(e) => onQuery(e.target.value)}
          placeholder="Search incident, IP or threat ID" autoComplete="off" />
      </div>
    </div>
  );
}
