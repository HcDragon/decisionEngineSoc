import { useSocData } from '../hooks/useSocData';
import { Empty, Panel, QueryBody } from '../components/Panel';
import { SeverityBadge } from '../components/Badges';
import { formatDateTime, incidentRef, matchesQuery } from '../data/derive';
import { FETCH_LIMITS } from '../data/limits';
import { useConsole } from '../shell/ConsoleContext';

export function AuditLogsPage() {
  const { query, openIncident } = useConsole();
  const verify = useSocData('audit-verify', (s) => s.verifyAudit(), { pollMs: 15_000, refreshOn: ['audit'] });
  const trail = useSocData('audit-trail', (s) => s.getDecisions(FETCH_LIMITS.decisions), { pollMs: 15_000, refreshOn: ['decision'] });

  const rows = trail.status === 'ready'
    ? trail.data.filter((d) => matchesQuery(query, [incidentRef(d.incidentId), d.ruleId, d.playbookId, d.status, d.policyHash]))
    : [];

  return (
    <>
      <Panel title="Hash-chain integrity" note="GET /api/audit/verify recomputes every link">
        <QueryBody query={verify} rows={2}>
          {(v) => (
            <dl className="soc-kv">
              <div><dt>Chain</dt><dd className={v.valid ? 'soc-tone-good' : 'soc-tone-bad'}>{v.valid ? 'Verified' : 'Broken'}</dd></div>
              {v.count != null && <div><dt>Entries</dt><dd className="soc-num">{v.count.toLocaleString('en-US')}</dd></div>}
              {v.head && <div><dt>Head hash</dt><dd className="soc-mono" title={v.head}>{v.head.slice(0, 16)}…</dd></div>}
              {!v.valid && <div><dt>First break</dt><dd className="soc-mono">entry #{v.brokenAtId} · {v.reason}</dd></div>}
            </dl>
          )}
        </QueryBody>
      </Panel>

      <Panel title="Decision and action trail" note={trail.status === 'ready' ? `Showing ${rows.length} of ${trail.data.length}` : null}>
        <QueryBody query={trail} rows={8}>
          {() => rows.length === 0 ? <Empty>No audited decisions match.</Empty> : (
            <div className="soc-scroll-x">
              <div className="soc-table soc-t-decisions" role="table" aria-label="Audited decisions">
                <div className="soc-thead" role="rowgroup">
                  <div className="soc-tr" role="row">
                    {['Time', 'Incident', 'Rule', 'Tier', 'Risk', 'Mode', 'Policy hash', 'Status'].map((h) => <span key={h} role="columnheader">{h}</span>)}
                  </div>
                </div>
                <div className="soc-tbody" role="rowgroup">
                  {rows.map((d) => (
                    <div className="soc-tr" role="row" key={d.id}>
                      <span role="cell" className="soc-td soc-mono">{formatDateTime(d.ts)}</span>
                      <span role="cell" className="soc-td"><button type="button" className="soc-link soc-mono" onClick={() => openIncident(d.incidentId)}>{incidentRef(d.incidentId)}</button></span>
                      <span role="cell" className="soc-td soc-mono">{d.ruleId}</span>
                      <span role="cell"><SeverityBadge severity={d.tier} /></span>
                      <span role="cell" className="soc-td soc-num">{d.riskScore.toFixed(1)}</span>
                      <span role="cell" className="soc-td">{d.mode}</span>
                      <span role="cell" className="soc-td soc-mono" title={d.policyHash}>{d.policyHash.slice(0, 12)}</span>
                      <span role="cell" className="soc-td">{d.status.replace(/_/g, ' ')}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </QueryBody>
      </Panel>
    </>
  );
}
