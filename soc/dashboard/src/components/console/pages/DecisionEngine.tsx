import React from 'react';
import { Panel, Badge, usePoll, Loading, ErrorState, EmptyState, severityTone } from '../ui';
import { PipelineMesh } from '../../PipelineMesh';

const STAGES = ['NFStream', 'Feature Mapping', 'ML IDS', 'Rate Rules', 'Threat Event', 'Risk Engine', 'Policy Engine', 'Decision', 'Playbook', 'Audit & Verification'];

export const DecisionEnginePage: React.FC<{ ctx: any }> = ({ ctx }) => {
  const { apiBase, openIncident } = ctx;
  const { data, loading, error } = usePoll<any>(`${apiBase}/api/decisions?limit=50`, 3500);
  const decisions: any[] = data?.decisions || [];

  return (
    <div className="flex flex-col gap-6">
      <Panel title="Processing Pipeline" right={<Badge tone="neutral">LIVE GATES</Badge>}>
        <div className="flex flex-wrap items-center gap-2 mb-6">
          {STAGES.map((s, i) => (
            <React.Fragment key={s}>
              <span className="px-3 py-1 rounded-md text-[0.7rem] font-mono font-bold uppercase bg-[#faf6f0] text-[#0d0d11] border-[1.5px] border-[#0d0d11] shadow-[1.5px_1.5px_0px_#0d0d11]">
                {s}
              </span>
              {i < STAGES.length - 1 && <span className="text-[var(--torii-vermilion)] font-bold text-xs">→</span>}
            </React.Fragment>
          ))}
        </div>
        <PipelineMesh apiBase={apiBase} />
      </Panel>

      <Panel title="Recent Decisions" right={<span className="text-[0.72rem] font-mono font-bold uppercase text-[var(--torii-amber)]">Click a row for full rationale</span>}>
        {loading ? <Loading /> : error ? <ErrorState /> : decisions.length === 0 ? <EmptyState>No decisions executed yet.</EmptyState> : (
          <div className="overflow-x-auto">
            <table className="w-full text-[0.78rem]">
              <thead>
                <tr className="text-white text-left border-b-[2px] border-[#0d0d11]">
                  {['Time', 'Incident', 'Rule ID', 'Severity Tier', 'Risk Score', 'Mode', 'Playbook ID', 'Status'].map(h => (
                    <th key={h} className="pb-2.5 px-3 font-extrabold uppercase font-mono text-[0.72rem] text-[#c5bebe]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y-[1.5px] divide-[#1d171b]">
                {decisions.map((d) => (
                  <tr key={d.id} onClick={() => d.incident_id && openIncident(d.incident_id)} className="hover:bg-[rgba(226,74,43,0.08)] transition-colors cursor-pointer">
                    <td className="py-2.5 px-3 font-mono text-[0.74rem] text-[#8c8385]">{(d.ts || '').replace('T', ' ').slice(11, 19)}</td>
                    <td className="py-2.5 px-3 text-[var(--torii-vermilion)] font-mono font-extrabold">#{d.incident_id}</td>
                    <td className="py-2.5 px-3 font-mono font-bold text-white">{d.rule_id}</td>
                    <td className="py-2.5 px-3"><Badge tone={severityTone(d.tier)}>{d.tier}</Badge></td>
                    <td className="py-2.5 px-3 tabular-nums font-mono font-bold text-white">{Number(d.risk_score).toFixed(1)}</td>
                    <td className="py-2.5 px-3 uppercase text-[0.72rem] font-bold text-[var(--torii-amber)]">{d.mode}</td>
                    <td className="py-2.5 px-3 font-mono text-[0.74rem] text-[#c5bebe]">{d.playbook_id || '—'}</td>
                    <td className="py-2.5 px-3"><Badge tone={severityTone(d.status)}>{d.status}</Badge></td>
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
