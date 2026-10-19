import { Icon } from '../components/Icon';
import { ToriiMark } from '../../brand/ToriiMark';
import type { SystemSnapshot } from '../data/types';
import { executorLabel } from '../data/derive';
import { NAV, type PageId } from './nav';

interface Props {
  page: PageId;
  onNavigate: (p: PageId) => void;
  status: SystemSnapshot | null;
  onExit: () => void;
}

export function Sidebar({ page, onNavigate, status, onExit }: Props) {
  const openCount = status?.connected ? status.activeIncidents : null;
  return (
    <aside className="soc-sidebar">
      <div className="soc-brand">
        <span className="soc-brand-mark"><ToriiMark size={28} /></span>
        <div>
          <div className="soc-brand-name">RASHOMON</div>
        </div>
      </div>

      <nav className="soc-nav" aria-label="Primary">
        {NAV.map((g) => (
          <div className="soc-nav-group" key={g.group}>
            <p className="soc-nav-label" id={`soc-nav-${g.group}`}>{g.group}</p>
            <ul aria-labelledby={`soc-nav-${g.group}`}>
              {g.pages.map((p) => (
                <li key={p.id}>
                  <button type="button" className="soc-nav-item" aria-current={page === p.id ? 'page' : undefined} onClick={() => onNavigate(p.id)}>
                    <Icon name={p.icon} />
                    <span>{p.label}</span>
                    {p.id === 'incidents' && openCount != null && openCount > 0 && (
                      <span className="soc-nav-badge" aria-label={`${openCount} open incidents`}>{openCount}</span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="soc-sidebar-foot">
        {status?.connected ? (
          <>
            <strong>{executorLabel(status.executor)} executor</strong>
            <span className="soc-num">{status.flowsCaptured.toLocaleString('en-US')} flows captured · {status.activeIncidents} active incidents</span>
          </>
        ) : (
          <>
            <strong>Backend unreachable</strong>
            <span>Live state unavailable</span>
          </>
        )}
        <button type="button" className="soc-back" onClick={onExit}>Back to site</button>
      </div>
    </aside>
  );
}
