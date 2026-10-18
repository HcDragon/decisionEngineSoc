/* KPI tiles and detection-source rows, shared by every SocDataSource (unit-tested). */
import type { DecisionRecord, Incident, Kpi, SourceHealth, Tiers } from './types';
import { median, perHour, responseTimes, withinHours } from './derive';

export interface SourceInputs {
  captureRunning: boolean;
  nativeCapture: boolean;
  monitoredPort: number;
  modelLoaded: boolean;
  apiHealthy: boolean;
  apiDetail: string;
  databaseConnected: boolean;
}

export function buildSourceHealth(s: SourceInputs): SourceHealth[] {
  const row = (name: string, ok: boolean, detail: string): SourceHealth => ({ name, up: ok ? 1 : 0, total: 1, detail });
  return [
    row('NFStream sensor', s.captureRunning && s.nativeCapture,
      !s.captureRunning ? 'Capture stopped' : s.nativeCapture ? `Native capture · port ${s.monitoredPort}` : 'Emulated stream'),
    row('Random Forest model', s.modelLoaded, s.modelLoaded ? 'Model artifacts present' : 'Model directory missing'),
    row('Rate-rule engine', s.captureRunning, s.captureRunning ? 'Runs in the capture loop' : 'Idle while capture is stopped'),
    row('Decision API', s.apiHealthy, s.apiDetail),
    row('Database', s.databaseConnected, s.databaseConnected ? 'Connected' : 'Disconnected'),
  ];
}

export interface KpiInputs {
  now: number;
  openIncidents: number;
  containedIncidents: number;
  incidents: Pick<Incident, 'id' | 'firstSeen'>[];
  decisions: DecisionRecord[];
  tiers: Tiers;
  detectionMs: number[];      // live capture -> alert samples, oldest first
  sources: SourceHealth[];
  sourcesHistory: number[];   // recent "sources up" readings, oldest first
}

export function buildKpis(k: KpiInputs): Kpi[] {
  const newPerHour = perHour(k.incidents.map((i) => i.firstSeen), 12, k.now);
  const newLastHour = newPerHour[newPerHour.length - 1];

  const critical = withinHours(k.decisions.filter((d) => d.riskScore >= k.tiers.critical), 24, k.now);
  const pendingCritical = critical.filter((d) => d.status === 'pending_approval').length;
  const critPerHour = perHour(critical.map((d) => d.ts), 12, k.now);
  const critLastHour = critPerHour[critPerHour.length - 1];

  const responses = responseTimes(k.incidents, k.decisions);

  const up = k.sources.reduce((n, s) => n + s.up, 0);
  const total = k.sources.reduce((n, s) => n + s.total, 0);
  const down = k.sources.filter((s) => s.up < s.total).map((s) => s.name);

  return [
    {
      id: 'incidents', label: 'Active incidents', value: k.openIncidents, format: 'count',
      sub: `${k.containedIncidents} contained`,
      delta: newLastHour > 0 ? { text: `+${newLastHour} new in the last hour`, tone: 'bad' } : { text: 'No new incidents in the last hour', tone: 'good' },
      series: newPerHour, seriesLabel: `New incidents per hour over the last 12 hours: ${newPerHour.join(', ')}`,
    },
    {
      id: 'critical', label: 'Critical alerts', value: critical.length, format: 'count',
      sub: `${pendingCritical} awaiting approval · risk ≥ ${k.tiers.critical}`, emphasize: critical.length > 0,
      delta: critLastHour > 0 ? { text: `+${critLastHour} in the last hour`, tone: 'bad' } : { text: 'None in the last hour', tone: 'good' },
      series: critPerHour, seriesLabel: `Critical alerts per hour over the last 12 hours: ${critPerHour.join(', ')}`,
    },
    {
      id: 'mttd', label: 'Mean time to detect', value: median(k.detectionMs), format: 'ms',
      sub: k.detectionMs.length ? `median of ${k.detectionMs.length} live detection${k.detectionMs.length === 1 ? '' : 's'}` : 'waiting for live detections',
      delta: { text: 'Flow capture → alert, live stream', tone: 'neutral' },
      series: k.detectionMs.slice(-12),
      seriesLabel: k.detectionMs.length ? `Last ${Math.min(12, k.detectionMs.length)} detection latencies in milliseconds` : 'No detection latency samples yet',
    },
    {
      id: 'mttr', label: 'Mean time to respond', value: median(responses.map((r) => r.ms)), format: 'ms',
      sub: responses.length ? `median of ${responses.length} incident${responses.length === 1 ? '' : 's'} acted on` : 'no executed playbooks yet',
      delta: { text: 'First alert → playbook executed', tone: 'neutral' },
      series: responses.slice(-12).map((r) => r.ms),
      seriesLabel: responses.length ? `Response time of the last ${Math.min(12, responses.length)} incidents acted on` : 'No response time samples yet',
    },
    {
      id: 'sources', label: 'Detection sources online', value: up, total, format: 'ratio',
      delta: down.length ? { text: `${down.join(', ')} down`, tone: 'bad' } : { text: 'All sources online', tone: 'good' },
      series: k.sourcesHistory, seriesLabel: `Detection sources online across recent checks: ${k.sourcesHistory.join(', ')}`,
    },
  ];
}
