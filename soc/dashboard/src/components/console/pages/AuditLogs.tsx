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
    <div className="flex flex-col gap-5">
      <Panel title="Hash-Chained Audit Integrity">
        {verify.loading ? <Loading /> : verify.error ? <ErrorState /> : (
          <div className="flex items-center gap-4">
            <Badge tone={v?.valid ? 'success' : 'danger'}>
              {v?.valid ? <ShieldCheck size={13} /> : <ShieldAlert size={13} />} {v?.valid ? 'chain verified' : 'chain BROKEN'}
            </Badge>
            <span className="text-[0.78rem] text-[var(--text-dim)]">{v?.count ?? 0} entries</span>
            <span className="text-[0.7rem] font-mono text-[var(--text-muted)] truncate">head: {String(v?.head || '').slice(0, 24)}…</span>
          </div>
        )}
        <div className="text-[0.68rem] text-[var(--text-muted)] mt-3">
          The backend exposes chain verification (`/api/audit/verify`) but not a per-entry list endpoint. The decision/action trail below is the auditable record of what the engine did, reconstructed from `/api/decisions`.
        </div>
      </Panel>

      <Panel title="Decision & Action Trail">
        {decisions.loading ? <Loading /> : decisions.error ? <ErrorState /> : rows.length === 0 ? <EmptyState>no audit activity yet.</EmptyState> : (
          <div className="overflow-x-auto">
            <table className="w-full text-[0.76rem]">
              <thead><tr className="text-[var(--text-muted)] text-left border-b border-[var(--border)]">
                {['Timestamp', 'Incident', 'Rule', 'Decision (mode)', 'Status', 'Playbook'].map(h => <th key={h} className="pb-2 px-2 font-medium">{h}</th>)}
              </tr></thead>
              <tbody className="divide-y divide-[var(--border)]">
                {rows.map((d) => (
                  <tr key={d.id} onClick={() => d.incident_id && openIncident(d.incident_id)} className="hover:bg-[var(--bg-hover)] cursor-pointer">
                    <td className="py-2 px-2 font-mono text-[0.72rem] text-[var(--text-muted)]">{(d.ts || '').replace('T', ' ').slice(0, 19)}</td>
                    <td className="py-2 px-2 text-[var(--accent)]">#{d.incident_id}</td>
                    <td className="py-2 px-2 font-mono text-[var(--text-dim)]">{d.rule_id}</td>
                    <td className="py-2 px-2 uppercase text-[0.7rem] text-[var(--text-dim)]">{d.mode}</td>
                    <td className="py-2 px-2 text-[var(--text-dim)]">{d.status}</td>
                    <td className="py-2 px-2 font-mono text-[0.72rem] text-[var(--text-muted)]">{d.playbook_id || '—'}</td>
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
