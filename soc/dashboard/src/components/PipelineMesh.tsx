import React, { useEffect, useRef, useState } from 'react';

/**
 * Live Pipeline Mesh — a real-time diagram of the actual lab architecture,
 * driven by the backend SSE feed (GET /api/events/stream). Nodes pulse as real
 * packets move through capture → ML + rate-rule → decision → playbook → audit.
 *
 * Not a canned animation: every pulse is a real {stage,payload} event emitted by
 * process_flow / the capture loop. Driven by plain EventSource + CSS transitions
 * (no animation library).
 */

interface Props {
  apiBase: string;
}

type Tone = 'accent' | 'danger';

// stage name (from the backend bus) -> node id to light up
const STAGE_TO_NODE: Record<string, string> = {
  capture: 'capture',
  detect_ml: 'ml',
  detect_rate_rule: 'rate',
  score: 'threat',
  correlate: 'threat',
  alert: 'threat',
  policy: 'decision',
  decision: 'decision',
  playbook: 'playbook',
  audit: 'audit',
};

const PULSE_MS = 850;

function summarize(stage: string, p: any): string {
  switch (stage) {
    case 'capture': return `${p.src_ip} → ${p.dst_ip} ${p.proto} ·${p.packets}pkt`;
    case 'detect_ml': return `ML: ${p.label} ${Math.round((p.confidence <= 1 ? p.confidence * 100 : p.confidence))}%`;
    case 'detect_rate_rule': return `rate-rule ${p.rule?.replace('rate-rule:', '')} · ${p.src_ip}`;
    case 'score': return `risk ${Number(p.risk).toFixed(0)} (${p.tier})`;
    case 'correlate': return `incident #${p.incident_id} · ${p.family}`;
    case 'alert': return `alert #${p.alert_id} · ${p.label}`;
    case 'policy': return `${p.rule_id} → ${p.mode}`;
    case 'decision': return `decision #${p.decision_id} · ${p.status}`;
    case 'playbook': return `playbook · ${(p.actions || []).map((a: any) => a.action || a).slice(0, 3).join(', ') || 'none'}`;
    case 'audit': return `audit chained · incident #${p.incident_id}`;
    default: return stage;
  }
}

function toneFor(stage: string, p: any): Tone {
  // benign capture / benign ML verdict = calm accent; everything that reaches
  // the decision pipeline (or a flagged verdict) = danger.
  if (stage === 'capture') return 'accent';
  if (stage === 'detect_ml') return p?.is_threat ? 'danger' : 'accent';
  return 'danger';
}

function isContainment(actions: any): boolean {
  if (!Array.isArray(actions)) return false;
  return actions.some((a: any) => {
    const name = typeof a === 'string' ? a : a?.action;
    return name === 'block_ip' || name === 'isolate_host';
  });
}

const Node: React.FC<{ id: string; title: string; sub?: string; pulse?: Tone; className?: string }> = ({ title, sub, pulse, className }) => (
  <div className={`mesh-node ${pulse ? `mesh-active mesh-${pulse}` : ''} ${className || ''}`}>
    <div className="mesh-node-title">{title}</div>
    {sub && <div className="mesh-node-sub">{sub}</div>}
  </div>
);

export const PipelineMesh: React.FC<Props> = ({ apiBase }) => {
  const [pulses, setPulses] = useState<Record<string, Tone>>({});
  const [log, setLog] = useState<Array<{ id: number; stage: string; text: string; tone: Tone }>>([]);
  const [blocked, setBlocked] = useState(false);
  const [connected, setConnected] = useState(false);
  const seq = useRef(0);
  const timers = useRef<Record<string, number>>({});

  useEffect(() => {
    const es = new EventSource(`${apiBase}/api/events/stream`);
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false); // browser auto-reconnects
    es.onmessage = (e) => {
      let evt: any;
      try { evt = JSON.parse(e.data); } catch { return; }
      const { stage, payload } = evt;
      const node = STAGE_TO_NODE[stage];
      const tone = toneFor(stage, payload);

      if (node) {
        setPulses((prev) => ({ ...prev, [node]: tone }));
        window.clearTimeout(timers.current[node]);
        timers.current[node] = window.setTimeout(
          () => setPulses((prev) => { const n = { ...prev }; delete n[node]; return n; }),
          PULSE_MS,
        );
      }
      if (stage === 'playbook' && isContainment(payload?.actions)) {
        setBlocked(true);
        window.clearTimeout(timers.current.__block);
        timers.current.__block = window.setTimeout(() => setBlocked(false), 4000);
      }
      setLog((prev) => [{ id: seq.current++, stage, text: summarize(stage, payload), tone }, ...prev].slice(0, 15));
    };
    return () => {
      es.close();
      Object.values(timers.current).forEach((t) => window.clearTimeout(t));
    };
  }, [apiBase]);

  const p = (id: string): Tone | undefined => pulses[id];

  return (
    <section className="backdrop-blur-2xl bg-black/40 border border-white/10 rounded-3xl p-6 shadow-[0_8px_32px_0_rgba(0,0,0,0.45)]">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-sm font-semibold tracking-wide text-white/90 flex items-center gap-2">
          <span className="mesh-dot" /> Live Pipeline Mesh
        </h2>
        <span className="text-[11px] font-mono text-white/40">
          {connected ? 'SSE connected · live' : 'connecting…'}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.6fr_1fr] gap-6">
        {/* diagram */}
        <div className="mesh-diagram">
          {/* attacker ↔ defender link */}
          <div className="mesh-row mesh-row-top">
            <Node id="attacker" title="Attacker Namespace" sub="hydra · hping3 · nmap  (10.66.0.20)" className="mesh-attacker" />
            <div className={`mesh-link ${blocked ? 'mesh-link-blocked' : ''} ${p('capture') ? 'mesh-link-live' : ''}`}>
              <span className="mesh-link-label">{blocked ? 'BLOCKED' : 'veth · 10.66.0.20 → 10.66.0.10'}</span>
            </div>
            <Node id="defender" title="Defender / Host" sub="veth-def  (10.66.0.10)" className="mesh-defender" pulse={p('capture')} />
          </div>

          <div className="mesh-edge-v" />
          <Node id="capture" title="NFStream Capture" sub="BPF tap · flow stats" pulse={p('capture')} />

          <div className="mesh-edge-v" />
          {/* parallel detectors */}
          <div className="mesh-row mesh-row-split">
            <Node id="ml" title="ML Random Forest" sub="57-feature · 5-class" pulse={p('ml')} />
            <Node id="rate" title="Rate-Rule Engine" sub="flood · brute force" pulse={p('rate')} />
          </div>

          <div className="mesh-edge-v" />
          <Node id="threat" title="Threat Event" sub="score · correlate · alert" pulse={p('threat')} />
          <div className="mesh-edge-v" />
          <Node id="decision" title="Decision Engine" sub="risk → policy → decision" pulse={p('decision')} />
          <div className="mesh-edge-v" />
          <Node id="playbook" title="Playbook" sub="dry-run / simulated / lab" pulse={p('playbook')} />
          <div className="mesh-edge-v" />
          <Node id="audit" title="Verification + Audit" sub="hash-chained" pulse={p('audit')} />
          <div className="mesh-edge-v" />
          <Node id="incident" title="Incident / Dashboard" sub="contained & logged" pulse={p('audit')} />
        </div>

        {/* companion event trace */}
        <div className="mesh-log">
          <div className="mesh-log-head">Event trace</div>
          {log.length === 0 ? (
            <div className="mesh-log-empty">waiting for live pipeline events…<br />run an attack scenario to see the mesh light up.</div>
          ) : (
            log.map((e) => (
              <div key={e.id} className={`mesh-log-row mesh-log-${e.tone}`}>
                <span className="mesh-log-stage">{e.stage}</span>
                <span className="mesh-log-text">{e.text}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  );
};
