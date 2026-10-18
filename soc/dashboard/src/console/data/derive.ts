/* Pure functions for every derived figure in the console (unit-tested). */
import type {
  AlertBucket, AlertRecord, DecisionRecord, Incident, Kpi, NamedCount, QueueState, Severity, Tiers,
} from './types';
import { SEVERITIES } from './types';

export const HOUR_MS = 3_600_000;

/**
 * Backend timestamps are UTC, but SQLite returns them without a zone designator
 * ("2026-10-11T18:18:53.550400"), which JavaScript would read as local time.
 */
export function parseUtc(iso: string): number {
  return Date.parse(/(Z|[+-]\d{2}:?\d{2})$/.test(iso) ? iso : `${iso}Z`);
}

/* ---------- severity ---------- */

/** Highest tier whose threshold the risk score reaches (policy.yaml `tiers`). */
export function tierForRisk(risk: number, tiers: Tiers): Severity {
  if (risk >= tiers.critical) return 'critical';
  if (risk >= tiers.high) return 'high';
  if (risk >= tiers.medium) return 'medium';
  return 'low';
}

export function normalizeTier(tier: string | null | undefined): Severity | null {
  const t = String(tier ?? '').toLowerCase();
  return (SEVERITIES as string[]).includes(t) ? (t as Severity) : null;
}

/* ---------- alert volume ---------- */

export const bucketTotal = (b: AlertBucket) => b.low + b.medium + b.high + b.critical;

/**
 * Hourly buckets ending at `now`: bucket hours-1 covers the last hour.
 * Alerts without a tier (no matching decision) are not counted.
 */
export function bucketAlerts(alerts: Pick<AlertRecord, 'ts' | 'severity'>[], hours: number, now: number): AlertBucket[] {
  const buckets: AlertBucket[] = Array.from({ length: hours }, (_, hour) => ({ hour, low: 0, medium: 0, high: 0, critical: 0 }));
  for (const a of alerts) {
    if (!a.severity) continue;
    const age = now - a.ts;
    if (age < 0 || age >= hours * HOUR_MS) continue;
    buckets[hours - 1 - Math.floor(age / HOUR_MS)][a.severity]++;
  }
  return buckets;
}

export function alertTotals(series: AlertBucket[]) {
  const bySeverity = Object.fromEntries(
    SEVERITIES.map((s) => [s, series.reduce((sum, b) => sum + b[s], 0)]),
  ) as Record<Severity, number>;
  const total = SEVERITIES.reduce((sum, s) => sum + bySeverity[s], 0);
  const peak = series.reduce<AlertBucket | null>((best, b) => (!best || bucketTotal(b) > bucketTotal(best) ? b : best), null);
  return { total, bySeverity, peak };
}

/** Gridlines every 20 alerts up to the real maximum (at least 0/20/40/60). */
export function gridSteps(maxPerHour: number) {
  const top = Math.max(60, Math.ceil(maxPerHour / 20) * 20);
  return Array.from({ length: top / 20 + 1 }, (_, i) => i * 20);
}

/** Count items by key, largest first (ties alphabetical). */
export function countBy<T>(items: T[], key: (t: T) => string, limit = Infinity): NamedCount[] {
  const m = new Map<string, number>();
  items.forEach((it) => m.set(key(it), (m.get(key(it)) ?? 0) + 1));
  return [...m.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))
    .slice(0, limit);
}

export const withinHours = <T extends { ts: number }>(items: T[], hours: number, now: number) =>
  items.filter((i) => now - i.ts >= 0 && now - i.ts < hours * HOUR_MS);

/** Count timestamps per hour for the last `hours` hours (oldest first). */
export function perHour(timestamps: number[], hours: number, now: number): number[] {
  const out = new Array(hours).fill(0);
  for (const t of timestamps) {
    const age = now - t;
    if (age < 0 || age >= hours * HOUR_MS) continue;
    out[hours - 1 - Math.floor(age / HOUR_MS)]++;
  }
  return out;
}

/* ---------- bars ---------- */

export const shareOfMax = (value: number, values: number[]) => {
  const max = Math.max(0, ...values);
  return max > 0 ? value / max : 0;
};
export const shareOfTarget = (median: number, target: number) => (target > 0 ? Math.min(1, median / target) : 0);
export const pct = (fraction: number) => `${(fraction * 100).toFixed(1)}%`;

/* ---------- incidents ---------- */

export function severityCounts(incidents: Pick<Incident, 'severity'>[]) {
  const counts = Object.fromEntries(SEVERITIES.map((s) => [s, 0])) as Record<Severity, number>;
  incidents.forEach((i) => counts[i.severity]++);
  return { all: incidents.length, ...counts };
}

export const incidentRef = (id: number) => `INC-${id}`;

export function matchesQuery(query: string, fields: (string | number | null | undefined)[]) {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return fields.some((f) => f != null && String(f).toLowerCase().includes(q));
}

export function filterIncidents(incidents: Incident[], severity: Severity | 'all', query = '') {
  return incidents.filter(
    (i) =>
      (severity === 'all' || i.severity === severity) &&
      matchesQuery(query, [incidentRef(i.id), i.id, i.srcIp, i.family, familyLabel(i.family), i.latestDecision?.ruleId, i.latestDecision?.playbookId]),
  );
}

/** Active queue = everything not closed or marked false positive. */
export const isActive = (i: Pick<Incident, 'status'>) => i.status === 'open' || i.status === 'contained';

/** Map backend incident + decision states onto the console's four status colours. */
export function queueState(i: Pick<Incident, 'status' | 'latestDecision'>): { state: QueueState; label: string } {
  if (i.status === 'contained') return { state: 'contained', label: 'Contained' };
  const d = i.latestDecision;
  if (!d) return { state: 'pending', label: 'New' };
  switch (d.status) {
    case 'pending_approval': return { state: 'pending', label: 'Pending approval' };
    case 'executed':
    case 'approved': return { state: 'escalated', label: d.mode === 'auto' ? 'Auto-executed' : 'Approved' };
    case 'monitored': return { state: 'investigating', label: d.mode === 'recommend' ? 'Recommended' : 'Monitoring' };
    default: return { state: 'investigating', label: d.status.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase()) };
  }
}

/* ---------- timing ---------- */

export function median(values: number[]): number | null {
  if (!values.length) return null;
  const s = [...values].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

/**
 * Time to respond per incident: first alert (incident.first_seen) to the first
 * decision whose playbook was executed or approved. Oldest incident first.
 */
export function responseTimes(incidents: Pick<Incident, 'id' | 'firstSeen'>[], decisions: Pick<DecisionRecord, 'incidentId' | 'ts' | 'status'>[]) {
  const firstSeen = new Map(incidents.map((i) => [i.id, i.firstSeen]));
  const firstActed = new Map<number, number>();
  for (const d of decisions) {
    if (d.status !== 'executed' && d.status !== 'approved') continue;
    const start = firstSeen.get(d.incidentId);
    if (start === undefined || d.ts < start) continue;   // only actions taken after the first alert
    const prev = firstActed.get(d.incidentId);
    if (prev === undefined || d.ts < prev) firstActed.set(d.incidentId, d.ts);
  }
  return incidents
    .filter((i) => firstActed.has(i.id))
    .map((i) => ({ incidentId: i.id, at: i.firstSeen, ms: firstActed.get(i.id)! - i.firstSeen }))
    .sort((a, b) => a.at - b.at);
}

/* ---------- formatting ---------- */

const FAMILY_LABEL: Record<string, string> = {
  dos_flood: 'DoS flood', recon: 'Reconnaissance', brute_force: 'Brute force', mitm: 'MITM / ARP spoofing', benign: 'Benign',
};
export const familyLabel = (family: string) => FAMILY_LABEL[family] ?? family.replace(/_/g, ' ');

const EXECUTOR_LABEL: Record<string, string> = { dry_run: 'Dry-run', simulated: 'Simulated', nft: 'Lab', lab: 'Lab' };
export const executorLabel = (executor: string) => EXECUTOR_LABEL[executor] ?? executor;

/** Age since a timestamp: "14m", "1h 12m", "2h 03m", "3d 04h". */
export function formatAge(ms: number) {
  const minutes = Math.max(0, Math.floor(ms / 60_000));
  if (minutes < 60) return `${minutes}m`;
  const h = Math.floor(minutes / 60);
  if (h < 24) return `${h}h ${String(minutes % 60).padStart(2, '0')}m`;
  return `${Math.floor(h / 24)}d ${String(h % 24).padStart(2, '0')}h`;
}

/** Latencies: "320 ms", "1.4 s", "4m 12s", "2h 05m". */
export function formatDuration(ms: number) {
  if (ms < 1000) return `${Math.round(ms)} ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(ms < 10_000 ? 1 : 0)} s`;
  const totalS = Math.round(ms / 1000);
  const m = Math.floor(totalS / 60);
  if (m < 60) return `${m}m ${String(totalS % 60).padStart(2, '0')}s`;
  return `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, '0')}m`;
}

export const formatClock = (ms: number) =>
  new Date(ms).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });

/** Compact date + time for tables: "11/10 18:20:33". */
export const formatDateTime = (ms: number) => {
  const d = new Date(ms);
  return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')} ${formatClock(ms)}`;
};

export const formatPercent = (fraction: number) => `${Math.round(fraction * 100)}%`;

export function formatKpiValue(kpi: Pick<Kpi, 'value' | 'format' | 'total'>) {
  if (kpi.value == null) return '—';
  switch (kpi.format) {
    case 'ms': return formatDuration(kpi.value);
    case 'seconds': return formatDuration(kpi.value * 1000);
    case 'ratio': return `${kpi.value} / ${kpi.total ?? 0}`;
    default: return kpi.value.toLocaleString('en-US');
  }
}
