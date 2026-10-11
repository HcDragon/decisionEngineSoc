import React from 'react';
import { Panel, Badge, usePoll, Loading, ErrorState, EmptyState, severityTone } from '../ui';
import { PipelineMesh } from '../../PipelineMesh';

const STAGES = ['NFStream', 'Feature Mapping', 'ML IDS', 'Rate Rules', 'Threat Event', 'Risk Engine', 'Policy Engine', 'Decision', 'Playbook', 'Verification / Audit'];

export const DecisionEnginePage: React.FC<{ ctx: any }> = ({ ctx }) => {
  const { apiBase, openIncident } = ctx;
  const { data, loading, error } = usePoll<any>(`${apiBase}/api/decisions?limit=50`, 3500);
  const decisions: any[] = data?.decisions || [];

  return (
    <div className="flex flex-col gap-5">
      <Panel title="Processing Pipeline" right={<Badge tone="neutral">live</Badge>}>
        <div className="flex flex-wrap items-center gap-1.5 mb-4">
          {STAGES.map((s, i) => (
            <React.Fragment key={s}>
              <span className="px-2 py-1 rounded-md text-[0.68rem] bg-[var(--bg-inset)] border border-[var(--border)] text-[var(--text-dim)]">{s}</span>
              {i < STAGES.length - 1 && <span className="text-[var(--text-muted)]">›</span>}
            </React.Fragment>
          ))}
        </div>
        <PipelineMesh apiBase={apiBase} />
      </Panel>

      <Panel title="Recent Decisions" right={<span className="text-[0.7rem] text-[var(--text-muted)]">click a row for full rationale</span>}>
        {loading ? <Loading /> : error ? <ErrorState /> : decisions.length === 0 ? <EmptyState>no decisions yet.</EmptyState> : (
          <div className="overflow-x-auto">
            <table className="w-full text-[0.76rem]">
              <thead><tr className="text-[var(--text-muted)] text-left border-b border-[var(--border)]">
                {['Time', 'Incident', 'Rule', 'Tier', 'Risk', 'Mode', 'Playbook', 'Status'].map(h => <th key={h} className="pb-2 px-2 font-medium">{h}</th>)}
              </tr></thead>
              <tbody className="divide-y divide-[var(--border)]">
                {decisions.map((d) => (
                  <tr key={d.id} onClick={() => d.incident_id && openIncident(d.incident_id)} className="hover:bg-[var(--bg-hover)] cursor-pointer">
                    <td className="py-2 px-2 font-mono text-[0.72rem] text-[var(--text-muted)]">{(d.ts || '').replace('T', ' ').slice(11, 19)}</td>
                    <td className="py-2 px-2 text-[var(--accent)]">#{d.incident_id}</td>
                    <td className="py-2 px-2 font-mono text-[var(--text-dim)]">{d.rule_id}</td>
                    <td className="py-2 px-2"><Badge tone={severityTone(d.tier)}>{d.tier}</Badge></td>
                    <td className="py-2 px-2 tabular-nums">{Number(d.risk_score).toFixed(1)}</td>
                    <td className="py-2 px-2 uppercase text-[0.7rem] text-[var(--text-dim)]">{d.mode}</td>
                    <td className="py-2 px-2 font-mono text-[0.72rem] text-[var(--text-muted)]">{d.playbook_id || '—'}</td>
                    <td className="py-2 px-2"><Badge tone={severityTone(d.status)}>{d.status}</Badge></td>
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
