import type {
  ActionResult, AlertBucket, AlertRecord, AuditVerify, AutomationMode, DecisionLatency, DecisionRecord,
  FeedItem, FlowRecord, Incident, IncidentDetail, Kpi, NamedCount, PipelineEvent, PolicySummary,
  SourceHealth, SystemSnapshot, TrafficStats,
} from './types';

/**
 * Everything the console reads or does. Components and pages only ever talk to
 * this interface (via useSocData / useSocSource); ApiSocDataSource binds it to
 * the FastAPI backend.
 */
export interface SocDataSource {
  /* --- overview dashboard --- */
  getKpis(): Promise<Kpi[]>;
  getAlertSeries(hours: number): Promise<AlertBucket[]>;
  getFamilyBreakdown(): Promise<NamedCount[]>;
  getIncidents(): Promise<Incident[]>;
  getTopAssets(): Promise<NamedCount[]>;
  getDetectionSourceHealth(): Promise<SourceHealth[]>;
  getFeed(): Promise<FeedItem[]>;
  getDecisionLatency(): Promise<DecisionLatency[]>;

  /* --- shared status (breadcrumb pill, sidebar footer, footnote) --- */
  getStatus(): Promise<SystemSnapshot>;

  /* --- supporting pages --- */
  getAlerts(limit: number): Promise<AlertRecord[]>;
  getDecisions(limit: number): Promise<DecisionRecord[]>;
  getIncidentDetail(id: number): Promise<IncidentDetail>;
  verifyAudit(): Promise<AuditVerify>;
  getTraffic(): Promise<TrafficStats>;
  getFlows(limit: number, threatOnly: boolean): Promise<FlowRecord[]>;
  getPolicy(): Promise<PolicySummary>;

  /* --- analyst actions --- */
  respond(incidentId: number): Promise<ActionResult>;
  release(incidentId: number): Promise<ActionResult>;
  setAutomationMode(mode: AutomationMode): Promise<ActionResult>;
  setMonitoredPort(port: number): Promise<ActionResult>;
  setCapture(running: boolean, port?: number): Promise<ActionResult>;
  clearFlows(): Promise<ActionResult>;

  /**
   * Live pipeline events (SSE). Returns an unsubscribe function. `onConnection`
   * reports stream state so the UI can show the live pulse honestly.
   */
  subscribe(onEvent: (e: PipelineEvent) => void, onConnection?: (connected: boolean) => void): () => void;
}
