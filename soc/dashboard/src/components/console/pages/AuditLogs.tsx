import React from 'react';
import { ShieldCheck, ShieldAlert } from 'lucide-react';
import { Panel, Badge, usePoll, Loading, ErrorState, EmptyState } from '../ui';

export const AuditLogsPage: React.FC<{ ctx: any }> = ({ ctx }) => {
  const { apiBase, openIncident } = ctx;
  const verify = usePoll<any>(`${apiBase}/api/audit/verify`, 8000);
  const decisions = usePoll<any>(`${apiBase}/api/decisions?limit=100`, 4000);

  const v = verify.data;
  const rows: any[] = decisions.data?.decisions || [];

  return (
    <div className="flex flex-col gap-6">
      <Panel title="Hash-Chained Audit Integrity">
        {verify.loading ? <Loading /> : verify.error ? <ErrorState /> : (
          <div className="flex items-center gap-4 flex-wrap">
            <Badge tone={v?.valid ? 'success' : 'danger'}>
              {v?.valid ? <ShieldCheck size={14} /> : <ShieldAlert size={14} />} {v?.valid ? 'CHAIN VERIFIED' : 'CHAIN COMPROMISED'}
            </Badge>
            <span className="text-[0.82rem] font-mono font-bold text-white bg-[#faf6f0] text-[#0d0d11] px-3 py-1 rounded-md border-[1.5px] border-[#0d0d11] shadow-[1.5px_1.5px_0px_#0d0d11]">
              {v?.count ?? 0} Recorded Ledger Entries
            </span>
            <span className="text-[0.72rem] font-mono text-[var(--torii-amber)] font-bold truncate">
              HEAD: {String(v?.head || '').slice(0, 28)}...
            </span>
          </div>
        )}
        <div className="text-[0.72rem] text-[#c5bebe] font-mono mt-3 leading-relaxed">
          The backend exposes cryptographic chain verification (`/api/audit/verify`). The decision/action trail below is the tamper-evident auditable record of autonomous and manual operations.
        </div>
      </Panel>

      <Panel title="Decision &amp; Action Trail">
        {decisions.loading ? <Loading /> : decisions.error ? <ErrorState /> : rows.length === 0 ? <EmptyState>No audit activity recorded yet.</EmptyState> : (
          <div className="overflow-x-auto">
            <table className="w-full text-[0.78rem]">
              <thead>
                <tr className="text-white text-left border-b-[2px] border-[#0d0d11]">
                  {['Timestamp', 'Incident', 'Rule ID', 'Decision Mode', 'Execution Status', 'Playbook ID'].map(h => (
                    <th key={h} className="pb-2.5 px-3 font-extrabold uppercase font-mono text-[0.72rem] text-[#c5bebe]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y-[1.5px] divide-[#1d171b]">
                {rows.map((d) => (
                  <tr key={d.id} onClick={() => d.incident_id && openIncident(d.incident_id)} className="hover:bg-[rgba(226,74,43,0.08)] transition-colors cursor-pointer">
                    <td className="py-2.5 px-3 font-mono text-[0.74rem] text-[#8c8385]">{(d.ts || '').replace('T', ' ').slice(0, 19)}</td>
                    <td className="py-2.5 px-3 text-[var(--torii-vermilion)] font-mono font-extrabold">#{d.incident_id}</td>
                    <td className="py-2.5 px-3 font-mono font-bold text-white">{d.rule_id}</td>
                    <td className="py-2.5 px-3 uppercase text-[0.72rem] font-mono font-bold text-[var(--torii-amber)]">{d.mode}</td>
                    <td className="py-2.5 px-3 font-mono text-white">{d.status}</td>
                    <td className="py-2.5 px-3 font-mono text-[0.74rem] text-[#c5bebe]">{d.playbook_id || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
};
