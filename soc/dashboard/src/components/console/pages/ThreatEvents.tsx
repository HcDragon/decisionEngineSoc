import React, { useMemo, useState } from 'react';
import { Panel, Badge, usePoll, Loading, ErrorState, EmptyState } from '../ui';

export const ThreatEventsPage: React.FC<{ ctx: any }> = ({ ctx }) => {
  const { apiBase, fmtConf, openIncident } = ctx;
  const { data, loading, error } = usePoll<any>(`${apiBase}/api/alerts?limit=200`, 4000);
  const [fam, setFam] = useState('all');
  const [src, setSrc] = useState('all');
  const [q, setQ] = useState('');

  const alerts: any[] = data?.alerts || [];
  const families = useMemo(() => Array.from(new Set(alerts.map(a => a.family))).sort(), [alerts]);
  const rows = alerts.filter(a =>
    (fam === 'all' || a.family === fam) &&
    (src === 'all' || (src === 'rate-rule' ? String(a.model_version).startsWith('rate-rule') : !String(a.model_version).startsWith('rate-rule'))) &&
    (!q || `${a.src_ip} ${a.dst_ip} ${a.label}`.toLowerCase().includes(q.toLowerCase()))
  );

  const Sel: React.FC<{ v: string; set: (s: string) => void; opts: string[]; label: string }> = ({ v, set, opts, label }) => (
    <select value={v} onChange={(e) => set(e.target.value)} aria-label={label}
      className="bg-[var(--bg-inset)] border border-[var(--border)] rounded-md px-2 py-1 text-[0.74rem] text-[var(--text-dim)]">
      <option value="all">{label}: all</option>
      {opts.map(o => <option key={o} value={o}>{o}</option>)}
    </select>
  );

  return (
    <Panel title={`Threat Events${rows.length ? ` (${rows.length})` : ''}`}
      right={
        <div className="flex items-center gap-2">
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="search ip / attack"
            className="bg-[var(--bg-inset)] border border-[var(--border)] rounded-md px-2 py-1 text-[0.74rem] text-[var(--text-dim)] w-40" />
          <Sel v={fam} set={setFam} opts={families} label="attack" />
          <Sel v={src} set={setSrc} opts={['ml', 'rate-rule']} label="source" />
        </div>
      }>
      {loading ? <Loading /> : error ? <ErrorState /> : rows.length === 0 ? <EmptyState>no threat events match.</EmptyState> : (
        <div className="overflow-x-auto">
          <table className="w-full text-[0.76rem]">
            <thead><tr className="text-[var(--text-muted)] text-left border-b border-[var(--border)]">
              {['Time', 'Source', 'Destination', 'Attack', 'Confidence', 'Margin', 'Detection', 'Incident'].map(h => <th key={h} className="pb-2 font-medium px-2">{h}</th>)}
            </tr></thead>
            <tbody className="divide-y divide-[var(--border)]">
              {rows.slice(0, 100).map((a) => {
                const rule = String(a.model_version || '').startsWith('rate-rule');
                return (
                  <tr key={a.id} onClick={() => a.incident_id && openIncident(a.incident_id)}
                    className="hover:bg-[var(--bg-hover)] cursor-pointer">
                    <td className="py-2 px-2 font-mono text-[0.72rem] text-[var(--text-muted)]">{(a.ts || '').replace('T', ' ').slice(11, 19)}</td>
                    <td className="py-2 px-2 font-mono text-[var(--text-main)]">{a.src_ip}:{a.src_port}</td>
                    <td className="py-2 px-2 font-mono text-[var(--text-dim)]">{a.dst_ip}:{a.dst_port}</td>
                    <td className="py-2 px-2"><Badge tone={String(a.label).toLowerCase().includes('benign') ? 'neutral' : 'danger'}>{a.label}</Badge></td>
                    <td className="py-2 px-2 tabular-nums text-[var(--text-dim)]">{fmtConf(a.confidence)}</td>
                    <td className="py-2 px-2 tabular-nums text-[var(--text-muted)]">{Number(a.margin || 0).toFixed(2)}</td>
                    <td className="py-2 px-2"><Badge tone={rule ? 'warning' : 'accent'}>{rule ? 'rate-rule' : 'ML'}</Badge></td>
                    <td className="py-2 px-2 text-[var(--accent)]">{a.incident_id ? `#${a.incident_id}` : '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {rows.length > 100 && <div className="text-[0.7rem] text-[var(--text-muted)] mt-2">showing first 100 of {rows.length}</div>}
        </div>
      )}
    </Panel>
  );
};
