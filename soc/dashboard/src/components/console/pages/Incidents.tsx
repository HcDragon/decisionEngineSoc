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
          className="bg-[#faf6f0] text-[#0d0d11] border-[2px] border-[#0d0d11] shadow-[2px_2px_0px_#0d0d11] rounded-lg px-2.5 py-1 text-[0.74rem] font-bold uppercase font-mono cursor-pointer">
          {['all', 'open', 'contained'].map(s => <option key={s} value={s}>Status: {s.toUpperCase()}</option>)}
        </select>
      }>
      {loading ? <Loading /> : error ? <ErrorState /> : rows.length === 0 ? <EmptyState>No incidents active — engine is monitoring traffic.</EmptyState> : (
        <div className="overflow-x-auto">
          <table className="w-full text-[0.78rem]">
            <thead>
              <tr className="text-white text-left border-b-[2px] border-[#0d0d11]">
                {['ID', 'Source IP', 'Family', 'Risk Score', 'Alerts', 'Rule & Mode', 'Status', 'Action'].map(h => (
                  <th key={h} className="pb-2.5 font-extrabold uppercase tracking-wider px-3 text-[#c5bebe] font-mono text-[0.72rem]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y-[1.5px] divide-[#1d171b]">
              {rows.map((i) => {
                const d = i.latest_decision || {};
                const contained = i.status === 'contained';
                return (
                  <tr key={i.id} onClick={() => openIncident(i.id)} className="hover:bg-[rgba(226,74,43,0.08)] transition-colors cursor-pointer">
                    <td className="py-3 px-3 text-[var(--torii-vermilion)] font-mono font-extrabold">#{i.id}</td>
                    <td className="py-3 px-3 font-mono font-bold text-white">{i.src_ip}</td>
                    <td className="py-3 px-3 text-[#c5bebe] capitalize font-medium">{i.family}</td>
                    <td className="py-3 px-3"><Badge tone={severityTone(i.max_risk)}>{Number(i.max_risk).toFixed(1)}</Badge></td>
                    <td className="py-3 px-3 tabular-nums font-mono font-bold text-white">{i.alert_count}</td>
                    <td className="py-3 px-3 text-[#8c8385] font-mono text-[0.72rem]">{d.rule_id || '—'} • {d.mode || '—'}</td>
                    <td className="py-3 px-3"><Badge tone={severityTone(i.status)}>{i.status}</Badge></td>
                    <td className="py-3 px-3 text-right" onClick={(e) => e.stopPropagation()}>
                      {isAuto ? (
                        contained ? <Badge tone="success"><Lock size={12} /> Auto-Contained</Badge> : <span className="text-[0.72rem] font-mono font-bold text-[#8c8385]">AUTO</span>
                      ) : contained ? (
                        <button
                          onClick={() => handleRelease(i.id)}
                          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-[0.72rem] font-bold uppercase bg-[#faf6f0] text-[#0d0d11] border-[1.5px] border-[#0d0d11] shadow-[2px_2px_0px_#0d0d11] active:translate-x-[1px] active:translate-y-[1px] hover:bg-white transition-all cursor-pointer"
                        >
                          <Unlock size={12} /> Release
                        </button>
                      ) : (
                        <button
                          onClick={() => handleRespond(i.id)}
                          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-[0.72rem] font-bold uppercase bg-[var(--torii-vermilion)] text-white border-[1.5px] border-[#0d0d11] shadow-[2px_2px_0px_#0d0d11] active:translate-x-[1px] active:translate-y-[1px] hover:bg-[var(--torii-vermilion-hover)] transition-all cursor-pointer"
                        >
                          <Ban size={12} /> Contain IP
                        </button>
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
