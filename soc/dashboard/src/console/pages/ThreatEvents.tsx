import { useState } from 'react';
import { useSocData } from '../hooks/useSocData';
import { Empty, Panel, QueryBody } from '../components/Panel';
import { SeverityBadge } from '../components/Badges';
import { familyLabel, formatClock, formatPercent, incidentRef, matchesQuery } from '../data/derive';
import { FETCH_LIMITS } from '../data/limits';
import { useConsole } from '../shell/ConsoleContext';

export function ThreatEventsPage() {
  const { query, openIncident } = useConsole();
  const q = useSocData('alerts', (s) => s.getAlerts(FETCH_LIMITS.alerts), { pollMs: 15_000, refreshOn: ['alert'] });
  const [family, setFamily] = useState('all');
  const [detector, setDetector] = useState('all');

  const families = q.status === 'ready' ? [...new Set(q.data.map((a) => a.family))].sort() : [];
  const rows = q.status === 'ready'
    ? q.data.filter((a) =>
        (family === 'all' || a.family === family) &&
        (detector === 'all' || a.detector === detector) &&
        matchesQuery(query, [a.srcIp, a.dstIp, a.label, a.family, a.incidentId != null ? incidentRef(a.incidentId) : null, a.id]))
    : [];

  return (
    <Panel title="Threat events" note={q.status === 'ready' ? `Showing ${rows.length} of ${q.data.length}` : null}>
      <div className="soc-controls" style={{ marginBottom: 14 }}>
        <label className="soc-field">Family
          <select className="soc-select" value={family} onChange={(e) => setFamily(e.target.value)}>
            <option value="all">All families</option>
            {families.map((f) => <option key={f} value={f}>{familyLabel(f)}</option>)}
          </select>
        </label>
        <label className="soc-field">Detector
          <select className="soc-select" value={detector} onChange={(e) => setDetector(e.target.value)}>
            <option value="all">ML model and rate rules</option>
            <option value="ml">ML model</option>
            <option value="rate-rule">Rate rules</option>
          </select>
        </label>
      </div>
      <QueryBody query={q} rows={8}>
        {() => rows.length === 0 ? <Empty>No threat events match.</Empty> : (
          <div className="soc-scroll-x">
            <div className="soc-table soc-t-alerts" role="table" aria-label="Threat events">
              <div className="soc-thead" role="rowgroup">
                <div className="soc-tr" role="row">
                  {['Time', 'Severity', 'Source', 'Destination', 'Threat', 'Conf.', 'Margin', 'Detector', 'Incident'].map((h) => <span key={h} role="columnheader">{h}</span>)}
                </div>
              </div>
              <div className="soc-tbody" role="rowgroup">
                {rows.map((a) => (
                  <div className="soc-tr" role="row" key={a.id}>
                    <span role="cell" className="soc-td soc-mono">{formatClock(a.ts)}</span>
                    <span role="cell"><SeverityBadge severity={a.severity} /></span>
                    <span role="cell" className="soc-td soc-mono">{a.srcIp}</span>
                    <span role="cell" className="soc-td soc-mono">{a.dstIp}{a.dstPort != null ? `:${a.dstPort}` : ''}</span>
                    <span role="cell" className="soc-td" title={a.label}>{a.label} <span className="soc-muted">· {familyLabel(a.family)}</span></span>
                    <span role="cell" className="soc-td soc-num">{formatPercent(a.confidence)}</span>
                    <span role="cell" className="soc-td soc-num">{a.margin.toFixed(2)}</span>
                    <span role="cell" className="soc-td">{a.detector === 'rate-rule' ? 'Rate rule' : 'ML model'}</span>
                    <span role="cell" className="soc-td">
                      {a.incidentId != null
                        ? <button type="button" className="soc-link soc-mono" onClick={() => openIncident(a.incidentId!)}>{incidentRef(a.incidentId)}</button>
                        : <span className="soc-muted">—</span>}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </QueryBody>
    </Panel>
  );
}
