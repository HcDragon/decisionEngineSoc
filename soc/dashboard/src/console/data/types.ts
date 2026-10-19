/* Console view-models. The API layer maps backend JSON into these shapes. */

export type Severity = 'critical' | 'high' | 'medium' | 'low';
export const SEVERITIES: Severity[] = ['critical', 'high', 'medium', 'low'];

/** Risk-score thresholds per tier, from GET /api/policy `tiers`. */
export type Tiers = Record<Severity, number>;

export type Tone = 'good' | 'bad' | 'neutral';
export type Detector = 'ml' | 'rate-rule';

/** Backend Incident.status. */
export type IncidentStatus = 'open' | 'contained' | 'closed' | 'false_positive';
/** Backend Decision.status. */
export type DecisionStatus =
  | 'monitored' | 'pending_approval' | 'approved' | 'rejected' | 'executed' | 'failed' | 'expired';
export type DecisionMode = 'monitor' | 'recommend' | 'auto';
export type AutomationMode = 'off' | 'recommend_only' | 'auto';

/** Console status vocabulary (colour + text), derived from incident + latest decision. */
export type QueueState = 'pending' | 'investigating' | 'escalated' | 'contained';

export interface AlertRecord {
  id: number;
  ts: number;               // epoch ms
  srcIp: string;
  dstIp: string;
  srcPort: number | null;
  dstPort: number | null;
  label: string;
  family: string;
  confidence: number;       // 0..1
  margin: number;
  detector: Detector;
  modelVersion: string;
  incidentId: number | null;
  /** Tier of the decision persisted with this alert (same incident + timestamp). */
  severity: Severity | null;
  riskScore: number | null;
  probabilities: Record<string, number>;
  /** Size of the model input vector stored with the alert (raw_features.model_features). */
  featureCount: number;
}

export interface DecisionRecord {
  id: number;
  incidentId: number;
  ts: number;
  riskScore: number;
  tier: Severity;
  ruleId: string;
  mode: DecisionMode;
  status: DecisionStatus;
  playbookId: string | null;
  policyHash: string;
}

export interface Incident {
  id: number;
  srcIp: string;
  family: string;
  firstSeen: number;
  lastSeen: number;
  alertCount: number;
  maxRisk: number;
  severity: Severity;
  status: IncidentStatus;
  latestDecision: DecisionRecord | null;
}

export interface DecisionAction {
  id: number;
  action: string;
  executor: string;
  dryRun: boolean;
  status: string;
}

export interface DecisionDetail extends DecisionRecord {
  ruleTrace: unknown;
  guardrails: Record<string, unknown> | null;
  explanation: unknown;
  actions: DecisionAction[];
}

export interface IncidentDetail extends Incident {
  alerts: AlertRecord[];
  decisions: DecisionDetail[];
}

export type KpiFormat = 'count' | 'ms' | 'seconds' | 'ratio';

export interface Kpi {
  id: string;
  label: string;
  value: number | null;      // null = not measurable yet
  total?: number;            // denominator for ratio KPIs
  format: KpiFormat;
  sub?: string;
  delta: { text: string; tone: Tone };
  emphasize?: boolean;       // colour the value with the delta tone
  series: number[];
  seriesLabel: string;
}

export interface AlertBucket {
  /** 0 = oldest bucket; hours-1 = the current hour. */
  hour: number;
  low: number;
  medium: number;
  high: number;
  critical: number;
}

export interface NamedCount { name: string; count: number }

export interface SourceHealth {
  name: string;
  up: number;
  total: number;
  detail: string;
}

export interface FeedItem {
  id: number;
  ts: number;
  severity: Severity | null;
  label: string;
  confidence: number;
  detector: Detector;
  srcIp: string;
  incidentId: number | null;
}

export interface DecisionLatency {
  severity: Severity;
  medianMs: number | null;   // null = no samples this session
  targetMs: number | null;   // null = no target set in policies.yaml
  samples: number;
}

export type DataMode = 'live' | 'emulated';

export interface SystemSnapshot {
  connected: boolean;
  checkedAt: number;
  executor: string;
  automationMode: AutomationMode;
  labMode: boolean;
  environment: string;
  engineMode: string;        // native_nfstream | emulated_stream
  captureRunning: boolean;
  monitoredPort: number;
  flowsCaptured: number;
  activeIncidents: number;
  containedIncidents: number;
  activeBlocks: number;
  totalAlerts: number;
  modelLoaded: boolean;
  databaseConnected: boolean;
  configLoaded: boolean;
  dataMode: DataMode;
}

export interface TrafficStats {
  monitoredPort: number;
  engineMode: string;
  running: boolean;
  totalFlows: number;
  totalPackets: number;
  totalBytes: number;
  packetsPerSec: number;
  kbPerSec: number;
  threatFlows: number;
  activeConnections: number;
  protocols: Record<string, number>;
  topSources: { ip: string; packets: number }[];
}

export interface FlowRecord {
  id: string;
  time: string;
  srcIp: string;
  srcPort: number;
  dstIp: string;
  dstPort: number;
  protocol: string;
  app: string;
  packets: number;
  bytes: number;
  durationMs: number;
  label: string;
  isThreat: boolean;
  confidence: number;
  detector: string;
}

export interface AuditVerify {
  valid: boolean;
  count: number | null;
  head: string | null;
  brokenAtId: number | null;
  reason: string | null;
}

export interface PolicySummary {
  version: string;
  policyHash: string;
  tiers: Tiers;
  minAlertConfidence: number;
  rules: { id: string; priority: number; mode: string; playbook: string | null }[];
  /** Optional per-tier decision-latency SLA (policies.yaml decision_latency_targets_ms). */
  latencyTargetsMs: Partial<Record<Severity, number>>;
}

/** One pipeline-stage event from GET /api/events/stream. */
export interface PipelineEvent {
  stage: string;
  payload: Record<string, unknown>;
  receivedAt: number;
}

export interface ActionResult { ok: boolean; message: string }
