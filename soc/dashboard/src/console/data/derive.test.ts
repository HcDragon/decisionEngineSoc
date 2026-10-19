import { describe, expect, it } from 'vitest';
import {
  alertTotals, bucketAlerts, countBy, filterIncidents, formatAge, formatDuration, formatKpiValue, gridSteps, HOUR_MS,
  incidentRef, median, normalizeTier, parseUtc, perHour, queueState, responseTimes, severityCounts, shareOfMax, shareOfTarget, pct,
  tierForRisk,
} from './derive';
import { LatencyTracker } from './live';
import { buildKpis, buildSourceHealth } from './kpis';
import { chartScale } from '../components/AlertVolumeChart';
import type { DecisionRecord, Incident, PipelineEvent, Tiers } from './types';

const TIERS: Tiers = { low: 0, medium: 30, high: 60, critical: 80 };
const NOW = Date.UTC(2026, 9, 18, 12, 0, 0);

const decision = (over: Partial<DecisionRecord>): DecisionRecord => ({
  id: 1, incidentId: 1, ts: NOW, riskScore: 50, tier: 'medium', ruleId: 'R-DOS', mode: 'recommend',
  status: 'monitored', playbookId: 'pb_dos_mitigate', policyHash: 'h', ...over,
});
const incident = (over: Partial<Incident>): Incident => ({
  id: 1, srcIp: '10.66.0.20', family: 'dos_flood', firstSeen: NOW - HOUR_MS, lastSeen: NOW, alertCount: 3,
  maxRisk: 50, severity: 'medium', status: 'open', latestDecision: null, ...over,
});

describe('backend timestamps', () => {
  it('reads zone-less SQLite timestamps as UTC', () => {
    const utc = Date.UTC(2026, 9, 11, 18, 18, 53, 550);
    expect(parseUtc('2026-10-11T18:18:53.550400')).toBe(utc);
    expect(parseUtc('2026-10-11T18:18:53.550400Z')).toBe(utc);
    expect(parseUtc('2026-10-11T20:18:53.550+02:00')).toBe(utc);
  });
});

describe('severity tiers (policies.yaml)', () => {
  it('maps risk scores onto the configured thresholds', () => {
    expect([0, 29.9, 30, 59, 60, 79.9, 80, 100].map((r) => tierForRisk(r, TIERS)))
      .toEqual(['low', 'low', 'medium', 'medium', 'high', 'high', 'critical', 'critical']);
  });
  it('normalises backend tier strings', () => {
    expect(normalizeTier('CRITICAL')).toBe('critical');
    expect(normalizeTier('weird')).toBeNull();
  });
});

describe('incident counts and filters', () => {
  const incidents = [
    incident({ id: 1, severity: 'critical', srcIp: '10.66.0.20', family: 'dos_flood' }),
    incident({ id: 2, severity: 'high', srcIp: '10.66.0.44', family: 'mitm' }),
    incident({ id: 3, severity: 'high', srcIp: '10.66.0.20', family: 'brute_force', latestDecision: decision({ ruleId: 'R-BRUTE' }) }),
    incident({ id: 4, severity: 'low', srcIp: '10.66.0.61', family: 'recon' }),
  ];

  it('counts per severity', () => {
    expect(severityCounts(incidents)).toEqual({ all: 4, critical: 1, high: 2, medium: 0, low: 1 });
  });
  it('filters by severity', () => {
    expect(filterIncidents(incidents, 'high').map((i) => i.id)).toEqual([2, 3]);
  });
  it('searches by incident ID, IP and rule ID', () => {
    expect(filterIncidents(incidents, 'all', incidentRef(4)).map((i) => i.id)).toEqual([4]);
    expect(filterIncidents(incidents, 'all', '10.66.0.20').map((i) => i.id)).toEqual([1, 3]);
    expect(filterIncidents(incidents, 'all', 'r-brute').map((i) => i.id)).toEqual([3]);
    expect(filterIncidents(incidents, 'critical', '10.66.0.44')).toEqual([]);
  });
});

describe('queue status mapping', () => {
  it('turns incident + latest decision into the four console states', () => {
    expect(queueState(incident({ status: 'contained' })).state).toBe('contained');
    expect(queueState(incident({ latestDecision: decision({ status: 'pending_approval' }) }))).toEqual({ state: 'pending', label: 'Pending approval' });
    expect(queueState(incident({ latestDecision: decision({ status: 'executed', mode: 'auto' }) }))).toEqual({ state: 'escalated', label: 'Auto-executed' });
    expect(queueState(incident({ latestDecision: decision({ status: 'monitored', mode: 'recommend' }) })).state).toBe('investigating');
    expect(queueState(incident({ latestDecision: null })).label).toBe('New');
  });
});

describe('MTTR: first alert → executed playbook', () => {
  it('uses the first executed or approved decision per incident', () => {
    const incidents = [incident({ id: 1, firstSeen: NOW - 10 * 60_000 }), incident({ id: 2, firstSeen: NOW - 30 * 60_000 }), incident({ id: 3 })];
    const decisions = [
      decision({ incidentId: 1, ts: NOW - 9 * 60_000, status: 'monitored' }),
      decision({ incidentId: 1, ts: NOW - 8 * 60_000, status: 'executed' }),   // 2 min after first alert
      decision({ incidentId: 1, ts: NOW - 1 * 60_000, status: 'executed' }),   // later, ignored
      decision({ incidentId: 2, ts: NOW - 26 * 60_000, status: 'approved' }),  // 4 min
      decision({ incidentId: 3, ts: NOW, status: 'pending_approval' }),        // never acted on
    ];
    const r = responseTimes(incidents, decisions);
    expect(r.map((x) => [x.incidentId, x.ms])).toEqual([[2, 4 * 60_000], [1, 2 * 60_000]]);   // oldest incident first
    expect(median(r.map((x) => x.ms))).toBe(3 * 60_000);
  });
  it('median handles odd, even and empty inputs', () => {
    expect(median([5, 1, 3])).toBe(3);
    expect(median([4, 1, 3, 2])).toBe(2.5);
    expect(median([])).toBeNull();
  });
});

describe('MTTD and decision latency from the live stream', () => {
  const ev = (stage: string, receivedAt: number, payload: Record<string, unknown> = {}): PipelineEvent => ({ stage, payload, receivedAt });

  it('pairs capture → alert and capture → decision by source IP', () => {
    const t = new LatencyTracker();
    t.feed(ev('capture', 1000, { src_ip: '10.66.0.20' }));
    t.feed(ev('capture', 1100, { src_ip: '10.66.0.99' }));          // unrelated benign flow
    t.feed(ev('detect_ml', 1150));
    t.feed(ev('score', 1200, { incident_hint: '10.66.0.20', tier: 'critical' }));
    t.feed(ev('alert', 1300));
    t.feed(ev('decision', 1450));
    expect(t.detection.map((d) => d.ms)).toEqual([300]);
    expect(t.decisionByTier('critical')).toEqual({ medianMs: 450, samples: 1 });
    expect(t.decisionByTier('low')).toEqual({ medianMs: null, samples: 0 });
  });

  it('ignores alerts and decisions that have no captured flow to pair with', () => {
    const t = new LatencyTracker();
    t.feed(ev('score', 100, { incident_hint: '10.66.0.20', tier: 'high' }));
    t.feed(ev('alert', 200));
    t.feed(ev('decision', 300));
    expect(t.detection).toHaveLength(0);
    expect(t.decision).toHaveLength(0);
  });
});

describe('alert volume', () => {
  it('buckets scored alerts by hour and skips unscored or out-of-range ones', () => {
    const alerts = [
      { ts: NOW - 5 * 60_000, severity: 'critical' as const },
      { ts: NOW - 30 * 60_000, severity: 'low' as const },
      { ts: NOW - 90 * 60_000, severity: 'high' as const },
      { ts: NOW - 2 * 60_000, severity: null },
      { ts: NOW - 25 * HOUR_MS, severity: 'medium' as const },
    ];
    const series = bucketAlerts(alerts, 24, NOW);
    expect(series).toHaveLength(24);
    expect(series[23]).toMatchObject({ critical: 1, low: 1 });
    expect(series[22]).toMatchObject({ high: 1 });
    expect(alertTotals(series).total).toBe(3);
  });

  it('keeps 2.8px/alert under 60 per hour and rescales above it', () => {
    const flat = Array.from({ length: 24 }, (_, hour) => ({ hour, low: 10, medium: 10, high: 5, critical: 1 }));
    expect(chartScale(flat)).toEqual({ grid: [0, 20, 40, 60], px: 2.8 });
    const spike = flat.map((b) => (b.hour === 12 ? { ...b, low: 100 } : b));
    const s = chartScale(spike);
    expect(s.grid[s.grid.length - 1]).toBe(120);
    expect(120 * s.px).toBeLessThanOrEqual(208 - 24);
    expect(gridSteps(0)).toEqual([0, 20, 40, 60]);
  });

  it('counts per hour for sparklines', () => {
    expect(perHour([NOW - 1, NOW - 1, NOW - HOUR_MS - 1], 3, NOW)).toEqual([0, 1, 2]);
  });
});

describe('KPI tiles', () => {
  const sources = buildSourceHealth({
    captureRunning: true, nativeCapture: false, monitoredPort: 22, modelLoaded: true,
    apiHealthy: true, apiDetail: 'ok', databaseConnected: true,
  });

  it('detection sources: emulated capture counts the sensor as down', () => {
    expect(sources.map((s) => s.up)).toEqual([0, 1, 1, 1, 1]);
  });

  it('builds the five tiles from real inputs', () => {
    const kpis = buildKpis({
      now: NOW, openIncidents: 3, containedIncidents: 2,
      incidents: [incident({ id: 1, firstSeen: NOW - 10 * 60_000 })],
      decisions: [
        decision({ riskScore: 91, status: 'pending_approval', ts: NOW - 5 * 60_000 }),
        decision({ riskScore: 85, status: 'executed', ts: NOW - 3 * HOUR_MS }),
        decision({ riskScore: 70, ts: NOW - 60_000 }),
      ],
      tiers: TIERS, detectionMs: [120, 80, 100], sources, sourcesHistory: [5, 4],
    });
    const byId = Object.fromEntries(kpis.map((k) => [k.id, k]));
    expect(kpis.map((k) => k.id)).toEqual(['incidents', 'critical', 'mttd', 'mttr', 'sources']);
    expect(byId.incidents.value).toBe(3);
    expect(byId.incidents.delta).toEqual({ text: '+1 new in the last hour', tone: 'bad' });
    expect(byId.critical.value).toBe(2);
    expect(byId.critical.sub).toBe('1 awaiting approval · risk ≥ 80');
    expect(formatKpiValue(byId.mttd)).toBe('100 ms');
    expect(byId.mttr.value).toBeNull();                        // nothing executed after incident 1's first alert
    expect(formatKpiValue(byId.mttr)).toBe('—');
    expect(formatKpiValue(byId.sources)).toBe('4 / 5');
    expect(byId.sources.delta).toEqual({ text: 'NFStream sensor down', tone: 'bad' });
  });
});

describe('bars and formatting', () => {
  it('scales bars to the list maximum and to the target', () => {
    expect(pct(shareOfMax(34, [68, 34, 9]))).toBe('50.0%');
    expect(shareOfMax(3, [0])).toBe(0);
    expect(pct(shareOfTarget(450, 1000))).toBe('45.0%');
    expect(shareOfTarget(3000, 1000)).toBe(1);
  });
  it('counts by key, largest first', () => {
    expect(countBy(['a', 'b', 'a', 'c', 'a', 'b'], (x) => x, 2)).toEqual([{ name: 'a', count: 3 }, { name: 'b', count: 2 }]);
  });
  it('formats ages and durations', () => {
    expect([14, 72, 123, 60 * 27].map((m) => formatAge(m * 60_000))).toEqual(['14m', '1h 12m', '2h 03m', '1d 03h']);
    expect([320, 1400, 12_000, 252_000, 7_500_000].map(formatDuration)).toEqual(['320 ms', '1.4 s', '12 s', '4m 12s', '2h 05m']);
  });
});
