import { useEffect, useRef, useState } from 'react';
import { useSocData } from '../hooks/useSocData';
import { useSocSource } from '../data/context';
import type { DecisionDetail, IncidentDetail } from '../data/types';
import { familyLabel, formatClock, formatPercent, incidentRef, queueState } from '../data/derive';
import { Icon } from '../components/Icon';
import { Panel, QueryBody } from '../components/Panel';
import { SeverityBadge, StatusText } from '../components/Badges';
import { useConsole } from './ConsoleContext';

const fmtDate = (ms: number) => new Date(ms).toLocaleString('en-GB', { hour12: false });

function guardrailChips(g: Record<string, unknown> | null) {
  if (!g) return null;
  return (
    <ul className="soc-chips" aria-label="Guardrails">
      {Object.entries(g).map(([k, v]) => {
        const obj = v && typeof v === 'object' ? (v as Record<string, unknown>) : null;
        const passed = obj && 'passed' in obj ? !!obj.passed : null;
        const text = obj ? (obj.actual !== undefined ? `${k}: ${Number(obj.actual).toFixed(2)}` : k) : `${k}: ${String(v)}`;
        return (
          <li key={k} className={`soc-chip ${passed === true ? 'soc-chip--ok' : passed === false ? 'soc-chip--fail' : ''}`}>
            {passed === true ? 'Passed · ' : passed === false ? 'Failed · ' : ''}{text}
          </li>
        );
      })}
    </ul>
  );
}

function DecisionBlock({ d }: { d: DecisionDetail }) {
  return (
    <Panel title="Latest decision" note={<span className="soc-mono">{fmtDate(d.ts)}</span>}>
      <dl className="soc-kv">
        <div><dt>Rule</dt><dd className="soc-mono">{d.ruleId}</dd></div>
        <div><dt>Tier</dt><dd><SeverityBadge severity={d.tier} /></dd></div>
        <div><dt>Risk score</dt><dd className="soc-num">{d.riskScore.toFixed(1)} / 100</dd></div>
        <div><dt>Mode</dt><dd>{d.mode}</dd></div>
        <div><dt>Status</dt><dd>{d.status.replace(/_/g, ' ')}</dd></div>
        <div><dt>Playbook</dt><dd className="soc-mono">{d.playbookId ?? '—'}</dd></div>
      </dl>
      {d.guardrails && <div style={{ marginTop: 14 }}>{guardrailChips(d.guardrails)}</div>}
      {d.actions.length > 0 && (
        <ul className="soc-list" style={{ marginTop: 14 }} aria-label="Response actions">
          {d.actions.map((a) => (
            <li key={a.id}>
              <span className="soc-grow soc-mono">{a.action}</span>
              <span className="soc-muted">{a.executor}{a.dryRun ? ' · dry-run' : ''}</span>
              <span className={`soc-state ${a.status === 'applied' || a.status === 'executed' ? 'soc-tone-good' : 'soc-tone-neutral'}`}>{a.status}</span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

function Detail({ d, onChanged }: { d: IncidentDetail; onChanged: () => void }) {
  const source = useSocSource();
  const { notify } = useConsole();
  const [busy, setBusy] = useState(false);
  const st = queueState(d);
  const act = async (kind: 'respond' | 'release') => {
    setBusy(true);
    const r = kind === 'respond' ? await source.respond(d.id) : await source.release(d.id);
    setBusy(false);
    notify(r.message);
    if (r.ok) onChanged();
  };
  return (
    <>
      <div className="soc-controls">
        <SeverityBadge severity={d.severity} />
        <StatusText {...st} />
        <span style={{ marginLeft: 'auto' }} />
        {d.status === 'contained'
          ? <button type="button" className="soc-btn" disabled={busy} onClick={() => act('release')}>Release source</button>
          : <button type="button" className="soc-btn soc-btn--primary" disabled={busy} onClick={() => act('respond')}>Contain source</button>}
      </div>
      <Panel title="Summary">
        <dl className="soc-kv">
          <div><dt>Source</dt><dd className="soc-mono">{d.srcIp}</dd></div>
          <div><dt>Family</dt><dd>{familyLabel(d.family)}</dd></div>
          <div><dt>Alerts</dt><dd className="soc-num">{d.alertCount}</dd></div>
          <div><dt>Max risk</dt><dd className="soc-num">{d.maxRisk.toFixed(1)}</dd></div>
          <div><dt>First seen</dt><dd className="soc-mono">{fmtDate(d.firstSeen)}</dd></div>
          <div><dt>Last seen</dt><dd className="soc-mono">{fmtDate(d.lastSeen)}</dd></div>
        </dl>
      </Panel>
      {d.decisions[0] && <DecisionBlock d={d.decisions[0]} />}
      <Panel title="Detections" note={`${d.alerts.length} alerts`}>
        <ul className="soc-list">
          {d.alerts.slice(0, 12).map((a) => {
            const probs = Object.entries(a.probabilities).sort((x, y) => y[1] - x[1]).slice(0, 3);
            return (
              <li key={a.id} style={{ flexDirection: 'column', alignItems: 'stretch', gap: 6 }}>
                <div className="soc-controls" style={{ gap: 8 }}>
                  <span className="soc-mono soc-muted">{formatClock(a.ts)}</span>
                  <SeverityBadge severity={a.severity} short />
                  <strong style={{ fontWeight: 500 }}>{a.label}</strong>
                  <span className="soc-muted soc-num">{formatPercent(a.confidence)} · margin {a.margin.toFixed(2)} · {a.detector === 'rate-rule' ? 'rate rule' : 'ML model'}</span>
                </div>
                {probs.length > 0 && (
                  <ul className="soc-bars" style={{ gap: 6, maxWidth: 420 }} aria-label="Class probabilities">
                    {probs.map(([cls, p]) => (
                      <li key={cls}>
                        <div className="soc-bar-top" style={{ marginBottom: 3 }}><span>{cls}</span><span className="soc-bar-count">{formatPercent(p)}</span></div>
                        <div className="soc-track" aria-hidden="true"><div className="soc-fill" style={{ width: `${(p * 100).toFixed(1)}%` }} /></div>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
      </Panel>
    </>
  );
}

export function IncidentDrawer({ id, onClose }: { id: number; onClose: () => void }) {
  const q = useSocData(`incident-${id}`, (s) => s.getIncidentDetail(id), { refreshOn: ['decision', 'playbook'] });
  const closeRef = useRef<HTMLButtonElement>(null);

  // focus moves into the dialog; the shell restores it to the opener on close
  useEffect(() => { closeRef.current?.focus(); }, []);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="soc-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="soc-drawer" role="dialog" aria-modal="true" aria-labelledby="soc-drawer-title">
        <div className="soc-drawer-head">
          <h2 id="soc-drawer-title" className="soc-mono">{incidentRef(id)}</h2>
          <button type="button" className="soc-btn soc-btn--sm" ref={closeRef} onClick={onClose} aria-label="Close incident details">
            <Icon name="close" size={16} /> Close
          </button>
        </div>
        <QueryBody query={q} rows={10}>{(d) => <Detail d={d} onChanged={q.retry} />}</QueryBody>
      </div>
    </div>
  );
}
