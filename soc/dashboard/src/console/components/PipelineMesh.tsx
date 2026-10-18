import { useEffect, useRef, useState } from 'react';
import { useSocData } from '../hooks/useSocData';
import { useLiveEvents, useStreamConnected } from '../hooks/useLive';
import type { PipelineEvent } from '../data/types';
import { executorLabel, familyLabel } from '../data/derive';
import { Icon, type IconName } from './Icon';
import { Panel } from './Panel';

/*
 * Live Pipeline Mesh. Every figure comes from the backend: polled endpoints for
 * persistent state (traffic, audit chain, policy, incidents, latest alerts) and
 * the SSE stream for per-stage activity. Session counters start when the page opens.
 */

type NodeId = 'capture' | 'features' | 'ml' | 'rate' | 'threat' | 'decision' | 'playbook' | 'audit' | 'incident';
type NodeStatus = 'running' | 'idle' | 'error' | 'offline';

// which mesh nodes each backend stage lights up
const STAGE_NODES: Record<string, NodeId[]> = {
  capture: ['capture', 'features'],
  detect_ml: ['ml'],
  detect_rate_rule: ['rate'],
  correlate: ['threat'],
  alert: ['threat'],
  score: ['decision'],
  policy: ['decision'],
  decision: ['decision'],
  playbook: ['playbook'],
  audit: ['audit', 'incident'],
};

const PULSE_MS = 900;
const RUNNING_WINDOW_MS = 60_000;
const BLOCK_FLASH_MS = 4_000;
const STATUS_LABEL: Record<NodeStatus, string> = { running: 'Running', idle: 'Idle', error: 'Error', offline: 'Offline' };

const str = (v: unknown) => (v == null ? '' : String(v));
const actionNames = (actions: unknown) =>
  (Array.isArray(actions) ? actions : []).map((a) => (typeof a === 'string' ? a : (a as { action?: string })?.action)).filter(Boolean) as string[];
const isContainment = (actions: unknown) => actionNames(actions).some((n) => n === 'block_ip' || n === 'isolate_host');

interface Session {
  counts: Record<string, number>;
  last: Record<string, PipelineEvent>;
  lastAt: Partial<Record<NodeId, number>>;
  threats: number;           // detect_ml with is_threat
  contained: number;         // playbooks with block/isolate
  captureDst: Map<string, string>;
  liveThreat: { src: string; dst: string; at: number } | null;
  blockedAt: number;
}

const emptySession = (): Session => ({
  counts: {}, last: {}, lastAt: {}, threats: 0, contained: 0, captureDst: new Map(), liveThreat: null, blockedAt: 0,
});

function useMeshSession() {
  const ref = useRef<Session>(emptySession());
  const [, force] = useState(0);
  useLiveEvents((e) => {
    const s = ref.current;
    s.counts[e.stage] = (s.counts[e.stage] ?? 0) + 1;
    s.last[e.stage] = e;
    (STAGE_NODES[e.stage] ?? []).forEach((n) => { s.lastAt[n] = e.receivedAt; });
    const p = e.payload;
    if (e.stage === 'capture' && typeof p.src_ip === 'string') s.captureDst.set(p.src_ip, str(p.dst_ip));
    if (e.stage === 'detect_ml' && p.is_threat) s.threats++;
    if (e.stage === 'score' && typeof p.incident_hint === 'string') {
      s.liveThreat = { src: p.incident_hint, dst: s.captureDst.get(p.incident_hint) ?? '', at: e.receivedAt };
    }
    if (e.stage === 'playbook' && isContainment(p.actions)) { s.contained++; s.blockedAt = e.receivedAt; }
    force((n) => n + 1);
  });
  return ref.current;
}

/* ---------------- pieces ---------------- */

interface NodeProps {
  icon: IconName;
  title: string;
  sub: string;
  stats: [string, string][];
  status: NodeStatus;
  active: boolean;
}

function MeshNode({ icon, title, sub, stats, status, active }: NodeProps) {
  return (
    <li className="soc-mesh-node" data-active={active} data-status={status}>
      <div className="soc-mesh-id">
        <span className="soc-mesh-icon"><Icon name={icon} /></span>
        <div className="soc-mesh-names">
          <span className="soc-mesh-title">{title}</span>
          <span className="soc-mesh-sub" title={sub}>{sub}</span>
        </div>
      </div>
      <dl className="soc-mesh-stats">
        {stats.map(([k, v]) => (
          <div key={k}><dt>{k}</dt><dd>{v}</dd></div>
        ))}
      </dl>
      <span className={`soc-mesh-state soc-mesh-state--${status}`}>{STATUS_LABEL[status]}</span>
    </li>
  );
}

function Endpoint({ kind, ip, detail }: { kind: 'attacker' | 'defender'; ip: string | null; detail: string }) {
  return (
    <div className={`soc-mesh-end soc-mesh-end--${kind}`}>
      <span className="soc-mesh-icon"><Icon name={kind} /></span>
      <div className="soc-mesh-names">
        <span className="soc-mesh-title">{kind === 'attacker' ? 'Threat source' : 'Monitored host'}</span>
        <span className="soc-mono soc-mesh-ip">{ip ?? '—'}</span>
        <span className="soc-mesh-sub">{detail}</span>
      </div>
    </div>
  );
}

/* ---------------- mesh ---------------- */

export function PipelineMesh() {
  const connected = useStreamConnected();
  const session = useMeshSession();
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const id = setInterval(() => setNow(Date.now()), 250); return () => clearInterval(id); }, []);

  const traffic = useSocData('traffic', (s) => s.getTraffic(), { pollMs: 2_000 });
  const status = useSocData('status', (s) => s.getStatus(), { pollMs: 5_000 });
  const verify = useSocData('audit-verify', (s) => s.verifyAudit(), { pollMs: 15_000, refreshOn: ['audit'] });
  const policy = useSocData('policy', (s) => s.getPolicy());
  const alerts = useSocData('alerts-recent', (s) => s.getAlerts(50), { pollMs: 20_000, refreshOn: ['alert'] });
  const incidents = useSocData('incidents', (s) => s.getIncidents(), { pollMs: 15_000, refreshOn: ['decision', 'playbook'] });

  const t = traffic.data;
  const sys = status.data;
  const v = verify.data;
  const recent = alerts.data ?? [];
  const latestAlert = recent[0];
  const latestMl = recent.find((a) => a.detector === 'ml');
  const featureAlert = recent.find((a) => a.featureCount > 0);
  const c = (stage: string) => session.counts[stage] ?? 0;
  const last = (stage: string) => session.last[stage]?.payload;

  // endpoints: the live flow that reached scoring, else the most recent persisted alert
  const src = session.liveThreat?.src ?? latestAlert?.srcIp ?? null;
  const dst = session.liveThreat?.dst || latestAlert?.dstIp || null;
  const srcAlerts = src ? recent.filter((a) => a.srcIp === src) : [];
  const srcFamilies = [...new Set(srcAlerts.map((a) => familyLabel(a.family)))];
  const srcIncident = src ? (incidents.data ?? []).find((i) => i.srcIp === src && (i.status === 'open' || i.status === 'contained')) : undefined;
  const blockedNow = now - session.blockedAt < BLOCK_FLASH_MS;
  const contained = srcIncident?.status === 'contained';
  const linkState = blockedNow ? 'blocked' : contained ? 'contained' : session.liveThreat && now - session.liveThreat.at < RUNNING_WINDOW_MS ? 'live' : 'idle';
  const linkText = { blocked: 'Containment executed', contained: 'Source contained', live: 'Threat traffic live', idle: src ? 'Last observed threat path' : 'No threat path observed yet' }[linkState];

  const active = (n: NodeId) => (session.lastAt[n] ?? 0) > now - PULSE_MS;
  const nodeStatus = (n: NodeId): NodeStatus => {
    if (!connected) return 'offline';
    if (n === 'capture' && t && !t.running) return 'error';
    if (n === 'audit' && v && !v.valid) return 'error';
    if ((n === 'audit' || n === 'incident') && (session.lastAt[n] ?? 0) === 0) return v || sys ? 'idle' : 'offline';
    return (session.lastAt[n] ?? 0) > now - RUNNING_WINDOW_MS ? 'running' : 'idle';
  };

  const lastScore = last('score');
  const lastPolicy = last('policy');
  const lastRate = last('detect_rate_rule');
  const lastCorrelate = last('correlate');
  const dash = '—';

  const nodes: (NodeProps & { id: NodeId })[] = [
    {
      id: 'capture', icon: 'capture', title: 'NFStream capture',
      sub: t ? `port ${t.monitoredPort} · ${t.engineMode === 'native_nfstream' ? 'native capture' : 'emulated stream'}` : dash,
      stats: [['Packets/s', t ? Math.round(t.packetsPerSec).toLocaleString('en-US') : dash], ['Flows', t ? t.totalFlows.toLocaleString('en-US') : dash]],
    },
    {
      id: 'features', icon: 'features', title: 'Feature mapping',
      sub: featureAlert ? `${featureAlert.featureCount}-feature model input` : 'model input vector',
      stats: [['Inputs', featureAlert ? String(featureAlert.featureCount) : dash], ['Mapped', c('capture').toLocaleString('en-US')]],
    },
    {
      id: 'ml', icon: 'model', title: 'ML classifier',
      sub: latestMl?.modelVersion || 'no ML verdict persisted yet',
      stats: [['Inferences', c('detect_ml').toLocaleString('en-US')], ['Threats', session.threats.toLocaleString('en-US')]],
    },
    {
      id: 'rate', icon: 'rule', title: 'Rate-rule engine',
      sub: lastRate ? `last: ${str(lastRate.src_ip)}` : 'cross-flow rate detector',
      stats: [['Triggered', c('detect_rate_rule').toLocaleString('en-US')], ['Last rule', lastRate ? str(lastRate.rule).replace('rate-rule:', '') : dash]],
    },
    {
      id: 'threat', icon: 'alert', title: 'Threat event',
      sub: lastCorrelate ? `${familyLabel(str(lastCorrelate.family))} · INC-${str(lastCorrelate.incident_id)}` : 'score · correlate · alert',
      stats: [['Alerts', c('alert').toLocaleString('en-US')], ['Correlated', c('correlate').toLocaleString('en-US')]],
    },
    {
      id: 'decision', icon: 'decision', title: 'Decision engine',
      sub: policy.data ? `policy v${policy.data.version} · ${policy.data.policyHash.slice(0, 8)}` : 'risk · policy · decision',
      stats: [['Risk', lastScore ? `${Number(lastScore.risk).toFixed(0)} ${str(lastScore.tier).toLowerCase()}` : dash], ['Mode', lastPolicy ? str(lastPolicy.mode) : dash]],
    },
    {
      id: 'playbook', icon: 'playbook', title: 'Playbook',
      sub: sys?.connected ? `${executorLabel(sys.executor)} executor` : dash,
      stats: [['Runs', c('playbook').toLocaleString('en-US')], ['Contained', session.contained.toLocaleString('en-US')]],
    },
    {
      id: 'audit', icon: 'audit', title: 'Verification + audit',
      sub: v?.head ? `head ${v.head.slice(0, 12)}` : 'hash-chained trail',
      stats: [['Entries', v?.count != null ? v.count.toLocaleString('en-US') : dash], ['Integrity', v ? (v.valid ? 'Verified' : 'Broken') : dash]],
    },
    {
      id: 'incident', icon: 'incidents', title: 'Incidents',
      sub: sys?.connected ? `${sys.activeBlocks} active block${sys.activeBlocks === 1 ? '' : 's'}` : dash,
      stats: [['Open', sys?.connected ? String(sys.activeIncidents) : dash], ['Contained', sys?.connected ? String(sys.containedIncidents) : dash]],
    },
  ].map((n) => ({ ...n, status: nodeStatus(n.id as NodeId), active: active(n.id as NodeId) })) as (NodeProps & { id: NodeId })[];

  const tally = nodes.reduce((acc, n) => { acc[n.status]++; return acc; }, { running: 0, idle: 0, error: 0, offline: 0 } as Record<NodeStatus, number>);

  return (
    <Panel
      title={<><span className={`soc-dot ${connected ? 'soc-dot--live' : 'soc-dot--off'}`} aria-hidden="true" /> Live pipeline mesh</>}
      note={connected ? 'Event stream connected' : 'Event stream reconnecting…'}
      className="soc-w-wide"
    >
      <div className="soc-mesh">
        <div className="soc-mesh-ends">
          <Endpoint kind="attacker" ip={src}
            detail={src ? `${srcAlerts.length} recent alert${srcAlerts.length === 1 ? '' : 's'}${srcFamilies.length ? ` · ${srcFamilies.join(', ')}` : ''}` : 'waiting for a scored flow'} />
          <Endpoint kind="defender" ip={dst}
            detail={t ? `port ${t.monitoredPort} · capture ${t.running ? 'running' : 'stopped'}` : '—'} />
        </div>
        <p className={`soc-mesh-link soc-mesh-link--${linkState}`} role="status">
          <span className="soc-mono">{src && dst ? `${src} → ${dst}${t ? `:${t.monitoredPort}` : ''}` : '—'}</span>
          <span>{linkText}</span>
        </p>

        <ol className="soc-mesh-nodes" aria-label="Pipeline stages, capture to incident">
          {nodes.map((n) => <MeshNode key={n.id} {...n} />)}
        </ol>

        <ul className="soc-mesh-legend" aria-label="Stage status">
          {(Object.keys(STATUS_LABEL) as NodeStatus[]).map((s) => (
            <li key={s}><span className={`soc-mesh-state soc-mesh-state--${s}`}>{STATUS_LABEL[s]}</span> <span className="soc-num">{tally[s]}</span></li>
          ))}
        </ul>
        <p className="soc-caption">
          Running = handled an event in the last minute. Counters (inferences, alerts, runs) are this session; flows, audit entries and incidents are totals from the backend.
        </p>
      </div>
    </Panel>
  );
}
