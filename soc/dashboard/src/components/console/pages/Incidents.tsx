import React, { useState } from 'react';
import { Ban, Unlock, Lock } from 'lucide-react';
import { Panel, Badge, usePoll, Loading, ErrorState, EmptyState, severityTone } from '../ui';

export const IncidentsPage: React.FC<{ ctx: any }> = ({ ctx }) => {
  const { apiBase, openIncident, handleRespond, handleRelease, automationMode } = ctx;
  const { data, loading, error } = usePoll<any>(`${apiBase}/api/incidents?limit=100`, 3000);
  const [statusFilter, setStatusFilter] = useState('all');
  const isAuto = automationMode === 'auto';

  const incidents: any[] = data?.incidents || [];
  const rows = incidents.filter(i => statusFilter === 'all' || i.status === statusFilter);

  return (
    <Panel title={`Incidents${rows.length ? ` (${rows.length})` : ''}`}
      right={
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          className="bg-[var(--bg-inset)] border border-[var(--border)] rounded-md px-2 py-1 text-[0.74rem] text-[var(--text-dim)]">
          {['all', 'open', 'contained'].map(s => <option key={s} value={s}>status: {s}</option>)}
        </select>
      }>
      {loading ? <Loading /> : error ? <ErrorState /> : rows.length === 0 ? <EmptyState>no incidents — the engine is monitoring.</EmptyState> : (
        <div className="overflow-x-auto">
          <table className="w-full text-[0.76rem]">
            <thead><tr className="text-[var(--text-muted)] text-left border-b border-[var(--border)]">
              {['ID', 'Source', 'Family', 'Risk', 'Alerts', 'Rule → Mode', 'Status', ''].map(h => <th key={h} className="pb-2 font-medium px-2">{h}</th>)}
            </tr></thead>
            <tbody className="divide-y divide-[var(--border)]">
              {rows.map((i) => {
                const d = i.latest_decision || {};
                const contained = i.status === 'contained';
                return (
                  <tr key={i.id} onClick={() => openIncident(i.id)} className="hover:bg-[var(--bg-hover)] cursor-pointer">
                    <td className="py-2 px-2 text-[var(--accent)] font-semibold">#{i.id}</td>
                    <td className="py-2 px-2 font-mono text-[var(--text-main)]">{i.src_ip}</td>
                    <td className="py-2 px-2 text-[var(--text-dim)] capitalize">{i.family}</td>
                    <td className="py-2 px-2"><Badge tone={severityTone(i.max_risk)}>{Number(i.max_risk).toFixed(1)}</Badge></td>
                    <td className="py-2 px-2 tabular-nums text-[var(--text-dim)]">{i.alert_count}</td>
                    <td className="py-2 px-2 text-[var(--text-muted)] font-mono text-[0.72rem]">{d.rule_id || '—'} → {d.mode || '—'}</td>
                    <td className="py-2 px-2"><Badge tone={severityTone(i.status)}>{i.status}</Badge></td>
                    <td className="py-2 px-2 text-right" onClick={(e) => e.stopPropagation()}>
                      {isAuto ? (
                        contained ? <Badge tone="success"><Lock size={11} /> auto-contained</Badge> : <span className="text-[0.7rem] text-[var(--text-muted)]">auto</span>
                      ) : contained ? (
                        <button onClick={() => handleRelease(i.id)} className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[0.72rem] border border-[var(--border)] text-[var(--text-dim)] hover:text-[var(--text-main)] hover:border-[var(--border-strong)]"><Unlock size={12} /> Release</button>
                      ) : (
                        <button onClick={() => handleRespond(i.id)} className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[0.72rem] border border-[var(--danger)]/40 text-[#ff8085] hover:bg-[var(--danger-soft)]"><Ban size={12} /> Block</button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
};
