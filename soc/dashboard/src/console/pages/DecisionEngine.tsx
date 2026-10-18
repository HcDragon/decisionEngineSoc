import { useState } from 'react';
import { useSocData } from '../hooks/useSocData';
import { useLiveEvents, useStreamConnected } from '../hooks/useLive';
import { Empty, Panel, QueryBody } from '../components/Panel';
import { PipelineMesh } from '../components/PipelineMesh';
import { SeverityBadge } from '../components/Badges';
import type { PipelineEvent } from '../data/types';
import { formatClock, formatDateTime, incidentRef } from '../data/derive';
import { useConsole } from '../shell/ConsoleContext';

/* Pipeline stages in the order the backend emits them (monitor/streamer.py, decision/pipeline.py). */
const STAGES: { stage: string; label: string }[] = [
  { stage: 'capture', label: 'NFStream capture' },
  { stage: 'detect_ml', label: 'ML classification' },
  { stage: 'detect_rate_rule', label: 'Rate-rule match' },
  { stage: 'score', label: 'Risk scoring' },
  { stage: 'correlate', label: 'Correlation' },
  { stage: 'alert', label: 'Alert persisted' },
  { stage: 'policy', label: 'Policy rule' },
  { stage: 'decision', label: 'Decision' },
  { stage: 'playbook', label: 'Playbook' },
  { stage: 'audit', label: 'Audit chain' },
];

const s = (v: unknown) => (v == null ? '' : String(v));

export function describeEvent(e: PipelineEvent): string {
  const p = e.payload;
  switch (e.stage) {
    case 'capture': return `${s(p.src_ip)} → ${s(p.dst_ip)} ${s(p.proto)} · ${s(p.packets)} pkts`;
    case 'detect_ml': return `${s(p.label)} (${Number(p.confidence ?? 0) > 1 ? Number(p.confidence).toFixed(0) : (Number(p.confidence ?? 0) * 100).toFixed(0)}%)${p.is_threat ? ' · threat' : ''}`;
    case 'detect_rate_rule': return `${s(p.rule).replace('rate-rule:', '')} · ${s(p.src_ip)}`;
    case 'score': return `risk ${Number(p.risk ?? 0).toFixed(0)} · ${s(p.tier)} · ${s(p.incident_hint)}`;
    case 'correlate': return `${incidentRef(Number(p.incident_id))} · ${s(p.family)}`;
    case 'alert': return `alert #${s(p.alert_id)} · ${s(p.label)}`;
    case 'policy': return `${s(p.rule_id)} → ${s(p.mode)}${p.playbook ? ` · ${s(p.playbook)}` : ''}`;
    case 'decision': return `decision #${s(p.decision_id)} · ${s(p.status).replace(/_/g, ' ')}`;
    case 'playbook': {
      const actions = Array.isArray(p.actions) ? p.actions.map((a) => (typeof a === 'string' ? a : (a as { action?: string })?.action)).filter(Boolean) : [];
      return actions.length ? actions.join(', ') : 'no actions';
    }
    case 'audit': return `entry chained · ${incidentRef(Number(p.incident_id))}`;
    default: return e.stage;
  }
}

function EventTrace() {
  const connected = useStreamConnected();
  const [trace, setTrace] = useState<PipelineEvent[]>([]);
  const [paused, setPaused] = useState(false);
  const [buffered, setBuffered] = useState(0);
  const [stage, setStage] = useState<string | null>(null);

  useLiveEvents((e) => {
    if (paused) { setBuffered((n) => n + 1); return; }
    setTrace((t) => [e, ...t].slice(0, 300));
  });

  const shown = stage ? trace.filter((e) => e.stage === stage) : trace;

  return (
    <Panel title="Event trace" className="soc-w-narrow" note={
      <>
        <button type="button" className="soc-btn soc-btn--sm" aria-pressed={paused}
          onClick={() => { setPaused((p) => !p); setBuffered(0); }}>{paused ? 'Resume' : 'Pause'}</button>
        <button type="button" className="soc-btn soc-btn--sm" onClick={() => { setTrace([]); setBuffered(0); }}>Clear</button>
      </>
    }>
      <div className="soc-filters" role="group" aria-label="Filter trace by stage" style={{ gap: 6 }}>
        <button type="button" className="soc-btn soc-btn--sm" aria-pressed={stage === null} onClick={() => setStage(null)}>All</button>
        {STAGES.map((x) => (
          <button key={x.stage} type="button" className="soc-btn soc-btn--sm" aria-pressed={stage === x.stage}
            onClick={() => setStage(stage === x.stage ? null : x.stage)}>{x.label}</button>
        ))}
      </div>
      {shown.length === 0 ? (
        <Empty>{connected ? 'Waiting for pipeline events. Run a lab scenario (docs/DEMO.md §4) to see flows move through the engine.' : 'Event stream reconnecting…'}</Empty>
      ) : (
        <ul className="soc-trace soc-trace--tall" aria-label="Pipeline events, newest first">
          {shown.map((e, i) => (
            <li key={`${e.receivedAt}-${i}`}>
              <span className="soc-muted">{formatClock(e.receivedAt)}</span>
              <span>{STAGES.find((x) => x.stage === e.stage)?.label ?? e.stage}</span>
              <span className="soc-soft" style={{ overflow: 'hidden', textOverflow: 'ellipsis' }} title={describeEvent(e)}>{describeEvent(e)}</span>
            </li>
          ))}
        </ul>
      )}
      <p className="soc-caption">{paused ? `Paused · ${buffered} new event${buffered === 1 ? '' : 's'} not shown` : `${trace.length} events this session`}</p>
    </Panel>
  );
}

function RecentDecisions() {
  const { openIncident } = useConsole();
  const q = useSocData('decisions', (src) => src.getDecisions(100), { pollMs: 10_000, refreshOn: ['decision'] });
  return (
    <Panel title="Recent decisions" note={q.status === 'ready' ? `${q.data.length} latest` : null}>
      <QueryBody query={q} rows={6}>
        {(rows) => rows.length === 0 ? <Empty>No decisions yet.</Empty> : (
          <div className="soc-flows-scroll">
            <div className="soc-table soc-t-decisions" role="table" aria-label="Recent decisions">
              <div className="soc-thead" role="rowgroup">
                <div className="soc-tr" role="row">
                  {['Time', 'Incident', 'Rule', 'Tier', 'Risk', 'Mode', 'Playbook', 'Status'].map((h) => <span key={h} role="columnheader">{h}</span>)}
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
                    <span role="cell" className="soc-td soc-mono">{d.playbookId ?? '—'}</span>
                    <span role="cell" className="soc-td">{d.status.replace(/_/g, ' ')}</span>
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

export function DecisionEnginePage() {
  return (
    <>
      <div className="soc-row">
        <PipelineMesh />
        <EventTrace />
      </div>
      <RecentDecisions />
    </>
  );
}
