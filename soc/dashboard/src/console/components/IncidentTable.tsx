import { useState, type ReactNode } from 'react';
import type { Incident, Severity } from '../data/types';
import { SEVERITIES } from '../data/types';
import { familyLabel, filterIncidents, formatAge, incidentRef, queueState, severityCounts } from '../data/derive';
import { SEVERITY_LABEL, SeverityBadge, StatusText } from './Badges';
import { Empty } from './Panel';
import { useConsole } from '../shell/ConsoleContext';

type Filter = Severity | 'all';
const FILTERS: Filter[] = ['all', ...SEVERITIES];

interface Props {
  incidents: Incident[];
  /** Extra trailing column (e.g. Contain / Release buttons on the Incidents page). */
  actions?: (i: Incident) => ReactNode;
}

/** Severity filter + CSS-grid incident table. Counts reflect the active search. */
export function IncidentTable({ incidents, actions }: Props) {
  const { query, openIncident } = useConsole();
  const [filter, setFilter] = useState<Filter>('all');
  const searched = filterIncidents(incidents, 'all', query);
  const counts = severityCounts(searched);
  const shown = filterIncidents(searched, filter);
  const now = Date.now();
  const head = ['ID', 'Incident', 'Severity', 'Status', 'Asset', 'Rule', 'Age', ...(actions ? ['Action'] : [])];

  return (
    <>
      <div className="soc-filters" role="group" aria-label="Filter incidents by severity">
        {FILTERS.map((f) => (
          <button key={f} type="button" className="soc-filter" aria-pressed={filter === f} onClick={() => setFilter(f)}>
            {f === 'all' ? 'All' : SEVERITY_LABEL[f]} <span className="soc-num">{counts[f]}</span>
          </button>
        ))}
      </div>
      <p className="soc-sr" aria-live="polite">Showing {shown.length} of {incidents.length} incidents</p>
      <div className="soc-scroll-x">
        <div className={`soc-table ${actions ? 'soc-t-incidents-full' : 'soc-t-incidents'}`} role="table" aria-label="Incident queue">
          <div className="soc-thead" role="rowgroup">
            <div className="soc-tr" role="row">{head.map((h) => <span key={h} role="columnheader">{h}</span>)}</div>
          </div>
          <div className="soc-tbody" role="rowgroup">
            {shown.length === 0 && (
              <div className="soc-tr" role="row"><span role="cell" style={{ gridColumn: '1 / -1' }}>
                <Empty>{incidents.length ? 'No incidents match the current filter.' : 'No incidents recorded yet.'}</Empty>
              </span></div>
            )}
            {shown.map((i) => {
              const st = queueState(i);
              const d = i.latestDecision;
              return (
                <div className="soc-tr" role="row" key={i.id}>
                  <span role="cell" className="soc-td">
                    <button type="button" className="soc-link soc-mono" onClick={() => openIncident(i.id)} aria-label={`Open ${incidentRef(i.id)} details`}>
                      {incidentRef(i.id)}
                    </button>
                  </span>
                  <span role="cell" className="soc-td" title={`${familyLabel(i.family)} from ${i.srcIp}`}>
                    {familyLabel(i.family)} <span className="soc-muted">· {i.alertCount} alerts</span>
                  </span>
                  <span role="cell"><SeverityBadge severity={i.severity} /></span>
                  <span role="cell" className="soc-td"><StatusText {...st} /></span>
                  <span role="cell" className="soc-td soc-mono">{i.srcIp}</span>
                  <span role="cell" className="soc-td soc-mono" title={d?.playbookId ? `Playbook ${d.playbookId}` : undefined}>
                    {d?.ruleId ?? <span className="soc-unassigned">No decision</span>}
                  </span>
                  <span role="cell" className="soc-td soc-mono">{formatAge(now - i.firstSeen)}</span>
                  {actions && <span role="cell" className="soc-td">{actions(i)}</span>}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </>
  );
}
