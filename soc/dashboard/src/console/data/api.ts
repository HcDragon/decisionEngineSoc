import type { SocDataSource } from './source';
import type {
  ActionResult, AlertRecord, AuditVerify, AutomationMode, DecisionDetail, DecisionRecord, FlowRecord, Incident,
  IncidentDetail, Kpi, PipelineEvent, PolicySummary, SourceHealth, SystemSnapshot, Tiers, TrafficStats,
} from './types';
import { SEVERITIES } from './types';
import { bucketAlerts, countBy, familyLabel, normalizeTier, parseUtc, tierForRisk, withinHours } from './derive';
import { buildKpis, buildSourceHealth } from './kpis';
import { LatencyTracker } from './live';
import { FETCH_LIMITS } from './limits';

/* Raw backend shapes (soc/backend/app/api/*.py). Only the fields the console reads. */
type Json = Record<string, any>;


const conf01 = (c: number) => (c > 1 ? c / 100 : c);

function mapDecision(d: Json): DecisionRecord {
  return {
    id: d.id,
    incidentId: d.incident_id,
    ts: parseUtc(d.ts),
    riskScore: Number(d.risk_score),
    tier: normalizeTier(d.tier) ?? 'low',
    ruleId: d.rule_id,
    mode: d.mode,
    status: d.status,
    playbookId: d.playbook_id ?? null,
    policyHash: d.policy_hash,
  };
}

/** Alert and Decision rows written by one pipeline run share incident_id + ts. */
const joinKey = (incidentId: unknown, ts: string) => `${incidentId}|${ts}`;

function mapAlert(a: Json, decisionsByKey: Map<string, Json>): AlertRecord {
  const d = decisionsByKey.get(joinKey(a.incident_id, a.ts));
  return {
    id: a.id,
    ts: parseUtc(a.ts),
    srcIp: a.src_ip,
    dstIp: a.dst_ip,
    srcPort: a.src_port ?? null,
    dstPort: a.dst_port ?? null,
    label: a.label,
    family: a.family,
    confidence: conf01(Number(a.confidence)),
    margin: Number(a.margin ?? 0),
    detector: String(a.model_version ?? '').startsWith('rate-rule') ? 'rate-rule' : 'ml',
    modelVersion: a.model_version ?? '',
    incidentId: a.incident_id ?? null,
    severity: d ? normalizeTier(d.tier) : null,
    riskScore: d ? Number(d.risk_score) : null,
    probabilities: a.probabilities ?? {},
    featureCount: Object.keys(a.raw_features?.model_features ?? {}).length,
  };
}

function mapIncident(i: Json, tiers: Tiers): Incident {
  return {
    id: i.id,
    srcIp: i.src_ip,
    family: i.family,
    firstSeen: parseUtc(i.first_seen),
    lastSeen: parseUtc(i.last_seen),
    alertCount: i.alert_count,
    maxRisk: Number(i.max_risk),
    severity: tierForRisk(Number(i.max_risk), tiers),
    status: i.status,
    latestDecision: i.latest_decision ? mapDecision(i.latest_decision) : null,
  };
}

export class ApiSocDataSource implements SocDataSource {
  private cache = new Map<string, { at: number; promise: Promise<unknown> }>();
  private tracker = new LatencyTracker();
  private listeners = new Set<{ onEvent: (e: PipelineEvent) => void; onConnection?: (c: boolean) => void }>();
  private stream: EventSource | null = null;
  private streamUp = false;
  private sourcesHistory: number[] = [];

  constructor(private base: string) {}

  /* ---------------- transport ---------------- */

  private async request<T = Json>(path: string, init?: RequestInit): Promise<T> {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 8000);
    try {
      const res = await fetch(`${this.base}${path}`, { ...init, signal: ctrl.signal });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error((body as Json).detail || `${path} → HTTP ${res.status}`);
      return body as T;
    } finally {
      clearTimeout(timer);
    }
  }

  private post(path: string, body?: unknown) {
    return this.request(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  }

  /** De-duplicate identical reads issued by several panels in one refresh. */
  private memo<T>(key: string, ttlMs: number, load: () => Promise<T>): Promise<T> {
    const hit = this.cache.get(key);
    if (hit && Date.now() - hit.at < ttlMs) return hit.promise as Promise<T>;
    const promise = load().catch((err) => { this.cache.delete(key); throw err; });
    this.cache.set(key, { at: Date.now(), promise });
    return promise;
  }

  private policyRaw = () => this.memo('policy', 60_000, () => this.request('/api/policy'));
  /** Risk tiers come only from the live policy; there is no client-side fallback. */
  private tiers = async (): Promise<Tiers> => {
    const t = (await this.policyRaw()).tiers ?? {};
    const missing = SEVERITIES.filter((s) => typeof t[s] !== 'number');
    if (missing.length) throw new Error(`/api/policy is missing tiers: ${missing.join(', ')}`);
    return { low: t.low, medium: t.medium, high: t.high, critical: t.critical };
  };
  private decisionsRaw = () => this.memo('decisions', 1500, () =>
    this.request<{ decisions: Json[] }>(`/api/decisions?limit=${FETCH_LIMITS.decisions}`).then((r) => r.decisions));
  private alertsRaw = () => this.memo('alerts', 1500, () =>
    this.request<{ alerts: Json[] }>(`/api/alerts?limit=${FETCH_LIMITS.alerts}`).then((r) => r.alerts));
  private incidentsRaw = () => this.memo('incidents', 1500, () =>
    this.request<{ incidents: Json[] }>(`/api/incidents?limit=${FETCH_LIMITS.incidents}`).then((r) => r.incidents));
  private overview = () => this.memo('overview', 1500, () => this.request('/api/dashboard/overview'));
  private health = () => this.memo('health', 1500, () => this.request('/health'));
  private system = () => this.memo('system', 1500, () => this.request('/system/status'));

  private async scoredAlerts(): Promise<AlertRecord[]> {
    const [alerts, decisions] = await Promise.all([this.alertsRaw(), this.decisionsRaw()]);
    const byKey = new Map(decisions.map((d) => [joinKey(d.incident_id, d.ts), d]));
    return alerts.map((a) => mapAlert(a, byKey));
  }

  /* ---------------- overview ---------------- */

  async getIncidents(): Promise<Incident[]> {
    const [raw, tiers] = await Promise.all([this.incidentsRaw(), this.tiers()]);
    return raw.map((i) => mapIncident(i, tiers));
  }

  async getAlertSeries(hours: number) {
    return bucketAlerts(await this.scoredAlerts(), hours, Date.now());
  }

  async getFamilyBreakdown() {
    return countBy(withinHours(await this.scoredAlerts(), 24, Date.now()), (a) => familyLabel(a.family));
  }

  async getTopAssets() {
    return countBy(withinHours(await this.scoredAlerts(), 24, Date.now()), (a) => a.dstIp, 5);
  }

  async getFeed() {
    const alerts = (await this.scoredAlerts()).sort((a, b) => b.ts - a.ts).slice(0, 30);
    return alerts.map((a) => ({
      id: a.id, ts: a.ts, severity: a.severity, label: a.label, confidence: a.confidence,
      detector: a.detector, srcIp: a.srcIp, incidentId: a.incidentId,
    }));
  }

  async getDecisionLatency() {
    this.ensureStream();
    const targets = (await this.policyRaw()).decision_latency_targets_ms ?? {};
    return SEVERITIES.map((severity) => ({
      severity,
      targetMs: typeof targets[severity] === 'number' ? targets[severity] : null,
      ...this.tracker.decisionByTier(severity),
    }));
  }

  async getDetectionSourceHealth(): Promise<SourceHealth[]> {
    const [health, system, overview] = await Promise.all([this.health(), this.system(), this.overview()]);
    const t = overview.traffic ?? {};
    return buildSourceHealth({
      captureRunning: t.status === 'running', nativeCapture: t.engine_mode === 'native_nfstream',
      monitoredPort: t.monitored_port, modelLoaded: !!system.model_dir_exists,
      apiHealthy: health.status === 'healthy', apiDetail: `API ${health.status} · v${health.version}`,
      databaseConnected: health.database === 'connected',
    });
  }

  async getKpis(): Promise<Kpi[]> {
    this.ensureStream();
    const [overview, incidents, decisions, tiers, sources] = await Promise.all([
      this.overview(), this.getIncidents(), this.decisionsRaw().then((ds) => ds.map(mapDecision)), this.tiers(),
      this.getDetectionSourceHealth(),
    ]);
    const stats = overview.stats ?? {};
    this.sourcesHistory = [...this.sourcesHistory, sources.reduce((n, s) => n + s.up, 0)].slice(-12);
    return buildKpis({
      now: Date.now(),
      openIncidents: stats.open_incidents ?? incidents.filter((i) => i.status === 'open').length,
      containedIncidents: stats.contained_incidents ?? 0,
      incidents, decisions, tiers,
      detectionMs: this.tracker.detection.map((d) => d.ms),
      sources, sourcesHistory: this.sourcesHistory,
    });
  }

  async getStatus(): Promise<SystemSnapshot> {
    const checkedAt = Date.now();
    try {
      const [health, system, overview] = await Promise.all([this.health(), this.system(), this.overview()]);
      const t = overview.traffic ?? {};
      const s = overview.stats ?? {};
      return {
        connected: true, checkedAt,
        executor: system.executor, automationMode: system.automation_mode, labMode: !!system.lab_mode,
        environment: system.environment, engineMode: t.engine_mode ?? 'unknown', captureRunning: t.status === 'running',
        monitoredPort: t.monitored_port ?? 0, flowsCaptured: t.total_flows ?? 0,
        activeIncidents: s.open_incidents ?? 0, containedIncidents: s.contained_incidents ?? 0,
        activeBlocks: s.active_blocks ?? 0, totalAlerts: s.total_alerts ?? 0,
        modelLoaded: !!system.model_dir_exists, databaseConnected: health.database === 'connected',
        configLoaded: !!system.config_dir_exists,
        dataMode: t.engine_mode === 'native_nfstream' ? 'live' : 'emulated',
      };
    } catch {
      return {
        connected: false, checkedAt, executor: 'unknown', automationMode: 'off', labMode: false, environment: 'unknown',
        engineMode: 'unknown', captureRunning: false, monitoredPort: 0, flowsCaptured: 0, activeIncidents: 0,
        containedIncidents: 0, activeBlocks: 0, totalAlerts: 0, modelLoaded: false, databaseConnected: false,
        configLoaded: false, dataMode: 'live',
      };
    }
  }

  /* ---------------- supporting pages ---------------- */

  async getAlerts(limit: number) {
    return (await this.scoredAlerts()).sort((a, b) => b.ts - a.ts).slice(0, limit);
  }

  async getDecisions(limit: number) {
    return (await this.decisionsRaw()).map(mapDecision).sort((a, b) => b.ts - a.ts).slice(0, limit);
  }

  async getIncidentDetail(id: number): Promise<IncidentDetail> {
    const [raw, tiers] = await Promise.all([this.request(`/api/incidents/${id}`), this.tiers()]);
    const byKey = new Map<string, Json>((raw.decisions ?? []).map((d: Json) => [joinKey(raw.id, d.ts), { ...d, incident_id: raw.id }]));
    const decisions: DecisionDetail[] = (raw.decisions ?? []).map((d: Json) => ({
      ...mapDecision({ ...d, incident_id: raw.id }),
      ruleTrace: d.rule_trace, guardrails: d.guardrail_results ?? null, explanation: d.explanation,
      actions: (d.actions ?? []).map((a: Json) => ({ id: a.id, action: a.action, executor: a.executor, dryRun: !!a.dry_run, status: a.status })),
    }));
    return {
      ...mapIncident({ ...raw, latest_decision: raw.decisions?.[0] ? { ...raw.decisions[0], incident_id: raw.id } : null }, tiers),
      alerts: (raw.alerts ?? []).map((a: Json) => mapAlert(a, byKey)),
      decisions,
    };
  }

  async verifyAudit(): Promise<AuditVerify> {
    const v = await this.request('/api/audit/verify');
    return { valid: !!v.valid, count: v.count ?? null, head: v.head ?? null, brokenAtId: v.broken_at_id ?? null, reason: v.reason ?? null };
  }

  async getTraffic(): Promise<TrafficStats> {
    const t = await this.request('/api/traffic/status');
    return {
      monitoredPort: t.monitored_port, engineMode: t.engine_mode, running: t.status === 'running',
      totalFlows: t.total_flows, totalPackets: t.total_packets, totalBytes: t.total_bytes,
      packetsPerSec: t.current_packets_per_sec, kbPerSec: t.current_kb_per_sec, threatFlows: t.threat_flows_count,
      activeConnections: t.active_connections, protocols: t.protocol_distribution ?? {},
      topSources: (t.top_sources ?? []).map((s: Json) => ({ ip: s.ip, packets: Number(s.packets) })),
    };
  }

  async getFlows(limit: number, threatOnly: boolean): Promise<FlowRecord[]> {
    const flows = await this.request<Json[]>(`/api/traffic/flows?limit=${limit}&threat_only=${threatOnly}`);
    return flows.map((f) => ({
      id: f.id, time: f.timestamp, srcIp: f.src_ip, srcPort: f.src_port, dstIp: f.dst_ip, dstPort: f.dst_port,
      protocol: f.protocol, app: f.application_name, packets: f.bidirectional_packets, bytes: f.bidirectional_bytes,
      durationMs: f.duration_ms, label: f.threat_label, isThreat: !!f.is_threat, confidence: conf01(Number(f.confidence)),
      detector: f.detector ?? '',
    }));
  }

  async getPolicy(): Promise<PolicySummary> {
    const p = await this.policyRaw();
    return {
      version: String(p.version), policyHash: p.policy_hash, tiers: await this.tiers(),
      minAlertConfidence: p.min_alert_confidence,
      rules: (p.rules ?? []).map((r: Json) => ({ id: r.id, priority: r.priority, mode: r.mode, playbook: r.playbook ?? null })),
      latencyTargetsMs: p.decision_latency_targets_ms ?? {},
    };
  }

  /* ---------------- actions ---------------- */

  private invalidate() { this.cache.clear(); }

  private async act(run: () => Promise<string>): Promise<ActionResult> {
    try {
      const message = await run();
      this.invalidate();
      return { ok: true, message };
    } catch (err) {
      return { ok: false, message: err instanceof Error ? err.message : String(err) };
    }
  }

  respond(id: number) {
    return this.act(async () => {
      const r = await this.post(`/api/incidents/${id}/respond`, { action: 'block_ip' });
      return r.status === 'already_blocked' ? `Source ${r.target} is already contained` : `Blocked ${r.target} (${r.enforcement})`;
    });
  }

  release(id: number) {
    return this.act(async () => {
      const r = await this.post(`/api/incidents/${id}/release`);
      return `Released ${r.target} (${r.released} rule(s) lifted)`;
    });
  }

  setAutomationMode(mode: AutomationMode) {
    return this.act(async () => (await this.post('/system/mode', { automation: mode })).message);
  }

  setMonitoredPort(port: number) {
    return this.act(async () => { await this.post('/api/traffic/port', { port }); return `Monitoring port ${port}`; });
  }

  setCapture(running: boolean, port?: number) {
    return this.act(async () => {
      await this.post(running ? '/api/traffic/start' : '/api/traffic/stop', running && port ? { port } : undefined);
      return running ? 'Capture started' : 'Capture stopped';
    });
  }

  clearFlows() {
    return this.act(async () => { await this.post('/api/traffic/clear'); return 'Flow buffer cleared'; });
  }

  /* ---------------- live stream ---------------- */

  private ensureStream() {
    if (this.stream || typeof EventSource === 'undefined') return;
    const es = new EventSource(`${this.base}/api/events/stream`);
    this.stream = es;
    const setUp = (up: boolean) => {
      if (up === this.streamUp) return;
      this.streamUp = up;
      this.listeners.forEach((l) => l.onConnection?.(up));
    };
    es.onopen = () => setUp(true);
    es.onerror = () => setUp(false);           // EventSource reconnects on its own
    es.onmessage = (msg) => {
      let parsed: Json;
      try { parsed = JSON.parse(msg.data); } catch { return; }
      if (!parsed?.stage) return;
      setUp(true);
      const event: PipelineEvent = { stage: parsed.stage, payload: parsed.payload ?? {}, receivedAt: Date.now() };
      this.tracker.feed(event);
      if (event.stage === 'alert' || event.stage === 'decision' || event.stage === 'playbook') this.invalidate();
      this.listeners.forEach((l) => l.onEvent(event));
    };
  }

  subscribe(onEvent: (e: PipelineEvent) => void, onConnection?: (connected: boolean) => void) {
    this.ensureStream();
    const listener = { onEvent, onConnection };
    this.listeners.add(listener);
    onConnection?.(this.streamUp);
    return () => { this.listeners.delete(listener); };
  }

}
