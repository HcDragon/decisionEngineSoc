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
    <select
      value={v}
      onChange={(e) => set(e.target.value)}
      aria-label={label}
      className="bg-[#faf6f0] text-[#0d0d11] border-[2px] border-[#0d0d11] shadow-[2px_2px_0px_#0d0d11] rounded-lg px-2.5 py-1 text-[0.74rem] font-mono font-bold uppercase cursor-pointer"
    >
      <option value="all">{label.toUpperCase()}: ALL</option>
      {opts.map(o => <option key={o} value={o}>{o.toUpperCase()}</option>)}
    </select>
  );

  return (
    <Panel title={`Threat Events${rows.length ? ` (${rows.length})` : ''}`}
      right={
        <div className="flex items-center gap-2.5">
          <input
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder="Search IP / attack..."
            className="bg-[#faf6f0] text-[#0d0d11] border-[2px] border-[#0d0d11] shadow-[2px_2px_0px_#0d0d11] rounded-lg px-3 py-1 text-[0.76rem] font-mono font-medium w-44"
          />
          <Sel v={fam} set={setFam} opts={families} label="Attack" />
          <Sel v={src} set={setSrc} opts={['ml', 'rate-rule']} label="Source" />
        </div>
      }>
      {loading ? <Loading /> : error ? <ErrorState /> : rows.length === 0 ? <EmptyState>No threat events match current filters.</EmptyState> : (
        <div className="overflow-x-auto">
          <table className="w-full text-[0.78rem]">
            <thead>
              <tr className="text-white text-left border-b-[2px] border-[#0d0d11]">
                {['Time', 'Source IP', 'Destination IP', 'Attack Vector', 'Confidence', 'Margin', 'Detection', 'Incident'].map(h => (
                  <th key={h} className="pb-2.5 px-3 font-extrabold uppercase font-mono text-[0.72rem] text-[#c5bebe]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y-[1.5px] divide-[#1d171b]">
              {rows.slice(0, 100).map((a) => {
                const rule = String(a.model_version || '').startsWith('rate-rule');
                return (
                  <tr
                    key={a.id}
                    onClick={() => a.incident_id && openIncident(a.incident_id)}
                    className="hover:bg-[rgba(226,74,43,0.08)] transition-colors cursor-pointer"
                  >
                    <td className="py-2.5 px-3 font-mono text-[0.74rem] text-[#8c8385]">{(a.ts || '').replace('T', ' ').slice(11, 19)}</td>
                    <td className="py-2.5 px-3 font-mono font-bold text-white">{a.src_ip}:{a.src_port}</td>
                    <td className="py-2.5 px-3 font-mono text-[#c5bebe]">{a.dst_ip}:{a.dst_port}</td>
                    <td className="py-2.5 px-3">
                      <Badge tone={String(a.label).toLowerCase().includes('benign') ? 'neutral' : 'danger'}>
                        {a.label}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 tabular-nums font-mono font-bold text-white">{fmtConf(a.confidence)}</td>
                    <td className="py-2.5 px-3 tabular-nums font-mono text-[#c5bebe]">{Number(a.margin || 0).toFixed(2)}</td>
                    <td className="py-2.5 px-3">
                      <Badge tone={rule ? 'warning' : 'accent'}>
                        {rule ? 'RATE-RULE' : 'ML IDS'}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 text-[var(--torii-vermilion)] font-mono font-bold">{a.incident_id ? `#${a.incident_id}` : '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {rows.length > 100 && (
            <div className="text-[0.72rem] font-mono text-[var(--torii-amber)] font-bold mt-3">
              Showing first 100 of {rows.length} alerts
            </div>
          )}
        </div>
      )}
    </Panel>
  );
};
