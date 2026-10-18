import { useEffect, useRef } from 'react';
import { useSocData } from '../hooks/useSocData';
import { alertTotals, formatClock, formatDuration, formatPercent, incidentRef, isActive, pct, shareOfMax, shareOfTarget } from '../data/derive';
import { FETCH_LIMITS } from '../data/limits';
import { AlertVolumeChart } from './AlertVolumeChart';
import { BarList } from './BarList';
import { Empty, Panel, QueryBody } from './Panel';
import { SeverityBadge } from './Badges';
import { IncidentTable } from './IncidentTable';
import { useConsole } from '../shell/ConsoleContext';

const LIVE = { pollMs: 15_000, refreshOn: ['alert', 'decision'] };

export function AlertVolumePanel() {
  const q = useSocData('series-24', (s) => s.getAlertSeries(24), LIVE);
  const note = q.status === 'ready' ? (() => {
    const t = alertTotals(q.data);
    return `${t.total.toLocaleString('en-US')} alerts · ${t.bySeverity.critical} critical`;
  })() : null;
  return (
    <Panel title="Alert volume by severity" note={note} className="soc-w-wide">
      <QueryBody query={q} rows={7}>
        {(series) => (
          <>
            <AlertVolumeChart series={series} />
            <p className="soc-caption">Each alert takes the tier of the decision persisted with it. Reads the latest {FETCH_LIMITS.alerts} alerts.</p>
          </>
        )}
      </QueryBody>
    </Panel>
  );
}

export function FamilyPanel() {
  const q = useSocData('families', (s) => s.getFamilyBreakdown(), LIVE);
  const note = q.status === 'ready' ? `${q.data.reduce((n, f) => n + f.count, 0)} alerts, 24h` : null;
  return (
    <Panel title="Alerts by attack family" note={note} className="soc-w-narrow">
      <QueryBody query={q} rows={5}>{(items) => <BarList items={items} />}</QueryBody>
    </Panel>
  );
}

export function IncidentQueuePanel() {
  const q = useSocData('incidents', (s) => s.getIncidents(), LIVE);
  const active = q.status === 'ready' ? q.data.filter(isActive) : [];
  const open = active.filter((i) => i.status === 'open').length;
  return (
    <Panel title="Incident queue" note={q.status === 'ready' ? `${open} open · ${active.length - open} contained` : null}>
      <QueryBody query={q} rows={6}>{() => <IncidentTable incidents={active} />}</QueryBody>
    </Panel>
  );
}

export function TopAssetsPanel() {
  const q = useSocData('assets', (s) => s.getTopAssets(), LIVE);
  return (
    <Panel title="Most targeted assets" note="Alerts by destination, 24h">
      <QueryBody query={q} rows={5}>{(items) => <BarList items={items} mono />}</QueryBody>
    </Panel>
  );
}

export function SourceHealthPanel() {
  const q = useSocData('sources', (s) => s.getDetectionSourceHealth(), { pollMs: 10_000 });
  const note = q.status === 'ready' ? `${q.data.reduce((n, s) => n + s.up, 0)} / ${q.data.reduce((n, s) => n + s.total, 0)} online` : null;
  return (
    <Panel title="Detection source health" note={note}>
      <QueryBody query={q} rows={5}>
        {(rows) => (
          <ul className="soc-list">
            {rows.map((r) => (
              <li key={r.name}>
                <span className="soc-grow">{r.name}<br /><span className="soc-muted" style={{ fontSize: 12 }}>{r.detail}</span></span>
                <span className={`soc-state ${r.up === r.total ? 'soc-tone-good' : 'soc-tone-bad'}`}>{r.up === r.total ? 'Online' : 'Offline'}</span>
              </li>
            ))}
          </ul>
        )}
      </QueryBody>
    </Panel>
  );
}

export function LiveFeedPanel() {
  const { openIncident } = useConsole();
  const q = useSocData('feed', (s) => s.getFeed(), { pollMs: 20_000, refreshOn: ['alert'] });
  const scroller = useRef<HTMLDivElement>(null);
  const newest = q.status === 'ready' ? q.data[0]?.id : undefined;
  // newest first: keep the view pinned to the top as events arrive, unless the analyst scrolled down
  useEffect(() => {
    const el = scroller.current;
    if (el && el.scrollTop < 40) el.scrollTop = 0;
  }, [newest]);

  return (
    <Panel title="Live threat event feed" note="Newest first" className="soc-w-queue">
      <QueryBody query={q} rows={6}>
        {(items) => items.length === 0 ? <Empty>No alerts yet. Detections appear here as they are persisted.</Empty> : (
          <div className="soc-scroll-x soc-feed-scroll" ref={scroller}>
            <div className="soc-table soc-t-feed" role="table" aria-label="Live threat events, newest first">
              <div className="soc-thead" role="rowgroup">
                <div className="soc-tr" role="row">{['Time', 'Severity', 'Event', 'Source'].map((h) => <span key={h} role="columnheader">{h}</span>)}</div>
              </div>
              <div className="soc-tbody" role="rowgroup">
                {items.map((f) => (
                  <div className="soc-tr" role="row" key={f.id}>
                    <span role="cell" className="soc-td soc-mono">{formatClock(f.ts)}</span>
                    <span role="cell"><SeverityBadge severity={f.severity} short /></span>
                    <span role="cell" className="soc-td" title={f.incidentId ? incidentRef(f.incidentId) : undefined}>
                      {f.incidentId ? (
                        <button type="button" className="soc-link" style={{ color: 'inherit' }} onClick={() => openIncident(f.incidentId!)}>{f.label}</button>
                      ) : f.label}
                      <span className="soc-muted"> · {formatPercent(f.confidence)} · {f.detector === 'rate-rule' ? 'rate rule' : 'ML model'}</span>
                    </span>
                    <span role="cell" className="soc-td soc-mono">{f.srcIp}</span>
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

export function DecisionLatencyPanel() {
  const q = useSocData('latency', (s) => s.getDecisionLatency(), { pollMs: 5_000, refreshOn: ['decision'] });
  const rows = q.status === 'ready' ? q.data : [];
  const measured = rows.filter((r) => r.medianMs != null);
  const withTarget = measured.filter((r) => r.targetMs != null);
  const hasTargets = rows.some((r) => r.targetMs != null);
  const note = q.status !== 'ready' ? null
    : withTarget.length ? `${withTarget.filter((r) => r.medianMs! <= r.targetMs!).length} of ${withTarget.length} tiers within target`
    : measured.length ? `${measured.reduce((n, r) => n + r.samples, 0)} decisions measured` : 'Live, this session';
  const medians = measured.map((r) => r.medianMs!);

  return (
    <Panel title={hasTargets ? 'Decision latency vs target' : 'Decision latency'} note={note} className="soc-w-narrow">
      <QueryBody query={q} rows={4}>
        {(data) => (
          <>
            <ul className="soc-resp">
              {data.map((r) => {
                const width = r.medianMs == null ? 0
                  : r.targetMs != null ? shareOfTarget(r.medianMs, r.targetMs) : shareOfMax(r.medianMs, medians);
                return (
                  <li key={r.severity}>
                    <div className="soc-resp-top">
                      <SeverityBadge severity={r.severity} />
                      <span className="soc-num">
                        {r.medianMs == null
                          ? <span className="soc-muted">No decisions yet{r.targetMs != null ? ` · target ${formatDuration(r.targetMs)}` : ''}</span>
                          : <>{formatDuration(r.medianMs)}{r.targetMs != null ? ` of ${formatDuration(r.targetMs)}` : ''} <span className="soc-muted">· n={r.samples}</span></>}
                      </span>
                    </div>
                    <div className="soc-track" aria-hidden="true"><div className="soc-fill" style={{ width: pct(width) }} /></div>
                  </li>
                );
              })}
            </ul>
            <p className="soc-caption">
              Median time from flow capture to decision persisted, measured from the live event stream this session.{' '}
              {hasTargets ? 'Bar length is the median as a share of the target.'
                : 'Bars compare tiers with each other. Set decision_latency_targets_ms in config/policies.yaml to draw them against a target.'}
            </p>
          </>
        )}
      </QueryBody>
    </Panel>
  );
}
