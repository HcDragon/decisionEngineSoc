import React, { useEffect, useRef, useState } from 'react';
import { Panel, MetricCard, Badge, Donut, HBars, Sparkline, EmptyState, severityTone, usePoll } from '../ui';

export const DashboardPage: React.FC<{ ctx: any; goto: (p: string) => void }> = ({ ctx, goto }) => {
  const { overview, trafficStats, systemHealth, apiBase, fmtConf } = ctx;
  const stats = overview?.stats || {};
  const t = trafficStats || {};
  const incidents: any[] = overview?.recent_incidents || [];

  // Live session pps trend (backend keeps no history; this is an honest
  // session-local rolling buffer of observed throughput, labelled as such).
  const [pps, setPps] = useState<number[]>([]);
  const last = useRef<number | undefined>(undefined);
  useEffect(() => {
    const v = Number(t.current_packets_per_sec || 0);
    if (v !== last.current) { last.current = v; setPps((p) => [...p, v].slice(-40)); }
  }, [t.current_packets_per_sec]);

  // Recent threat events (real alerts)
  const alerts = usePoll<any>(`${apiBase}/api/alerts?limit=10`, 4000);
  const sys = usePoll<any>(`${apiBase}/system/status`, 6000);

  const proto = t.protocol_distribution || {};
  const protoData = [
    { label: 'TCP', value: proto.TCP || 0, color: 'var(--accent)' },
    { label: 'UDP', value: proto.UDP || 0, color: 'var(--accent-2)' },
    { label: 'ICMP', value: proto.ICMP || 0, color: 'var(--warning)' },
  ];
  const famCount: Record<string, number> = {};
  incidents.forEach((i) => { famCount[i.family] = (famCount[i.family] || 0) + 1; });
  const famData = Object.entries(famCount).map(([label, value]) => ({ label, value }));
  const sevBuckets = { critical: 0, high: 0, medium: 0, low: 0 };
  incidents.forEach((i) => {
    const r = i.max_risk || 0;
    if (r >= 75) sevBuckets.critical++; else if (r >= 50) sevBuckets.high++; else if (r >= 25) sevBuckets.medium++; else sevBuckets.low++;
  });
  const sevData = [
    { label: 'Critical', value: sevBuckets.critical, color: 'var(--danger)' },
    { label: 'High', value: sevBuckets.high, color: 'var(--warning)' },
    { label: 'Medium', value: sevBuckets.medium, color: 'var(--accent)' },
    { label: 'Low', value: sevBuckets.low, color: 'var(--border-strong)' },
  ];

  const components = [
    { name: 'NFStream sensor', ok: t.engine_mode === 'native_nfstream', note: t.engine_mode === 'native_nfstream' ? 'native capture' : 'emulated' },
    { name: 'AI/ML IDS', ok: !!sys.data?.model_dir_exists, note: sys.data?.model_dir_exists ? 'model loaded' : 'model dir missing', unknown: sys.loading },
    { name: 'Decision Engine API', ok: systemHealth?.status === 'healthy', note: systemHealth?.status || 'unknown' },
    { name: 'Database', ok: !!sys.data?.database_connected, note: sys.data?.database_connected ? 'connected' : 'down', unknown: sys.loading },
  ];

  return (
    <div className="flex flex-col gap-5">
      {/* summary metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        <MetricCard label="Network flows" value={(t.total_flows ?? 0).toLocaleString()} />
        <MetricCard label="Suspicious flows" value={(t.threat_flows_count ?? 0).toLocaleString()} accent="var(--danger)" />
        <MetricCard label="Active incidents" value={stats.open_incidents ?? 0} accent="var(--warning)" />
        <MetricCard label="Contained" value={stats.contained_incidents ?? 0} accent="var(--success)" />
        <MetricCard label="Mitigations active" value={stats.active_blocks ?? 0} accent="var(--accent-2)" />
        <MetricCard label="Total alerts" value={stats.total_alerts ?? 0} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* traffic overview */}
        <Panel title="Network Traffic" className="lg:col-span-2"
          right={<Badge tone="neutral">live session</Badge>}>
          <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-5 items-center">
            <div>
              <div className="flex items-baseline gap-4 mb-1">
                <div><span className="text-[1.5rem] font-semibold text-[var(--text-main)] tabular-nums">{t.current_packets_per_sec ?? 0}</span><span className="text-[0.72rem] text-[var(--text-muted)] ml-1">pkts/s</span></div>
                <div><span className="text-[1.1rem] font-semibold text-[var(--text-dim)] tabular-nums">{t.current_kb_per_sec ?? 0}</span><span className="text-[0.72rem] text-[var(--text-muted)] ml-1">KB/s</span></div>
              </div>
              <Sparkline points={pps} />
              <div className="text-[0.68rem] text-[var(--text-muted)] mt-1">throughput over this session (backend keeps no historical store — 1h/24h/7d ranges unavailable)</div>
            </div>
            <Donut data={protoData} />
          </div>
        </Panel>

        {/* system health */}
        <Panel title="System Health">
          <div className="flex flex-col gap-2.5">
            {components.map((c) => (
              <div key={c.name} className="flex items-center justify-between text-[0.78rem]">
                <span className="text-[var(--text-dim)]">{c.name}</span>
                <Badge tone={c.unknown ? 'neutral' : c.ok ? 'success' : 'danger'}>
                  <span className="h-1.5 w-1.5 rounded-full" style={{ background: c.unknown ? 'var(--text-muted)' : c.ok ? 'var(--success)' : 'var(--danger)' }} />
                  {c.unknown ? 'unknown' : c.note}
                </Badge>
              </div>
            ))}
            <div className="text-[0.66rem] text-[var(--text-muted)] mt-1">Event pipeline: {t.status === 'running' ? 'processing' : 'idle'}</div>
          </div>
        </Panel>
      </div>

      {/* threat distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <Panel title="Attack Types (active incidents)">
          {famData.length ? <HBars data={famData} /> : <EmptyState>no active incidents</EmptyState>}
        </Panel>
        <Panel title="Severity Distribution"><Donut data={sevData} /></Panel>
        <Panel title="Incident Status">
          <HBars data={[
            { label: 'open', value: stats.open_incidents ?? 0, color: 'var(--warning)' },
            { label: 'contained', value: stats.contained_incidents ?? 0, color: 'var(--success)' },
          ]} />
        </Panel>
      </div>

      {/* recent threat events */}
      <Panel title="Recent Threat Events" right={<button onClick={() => goto('threats')} className="text-[0.72rem] text-[var(--accent)] hover:underline">view all</button>}>
        {alerts.loading ? <EmptyState>loading…</EmptyState> : !alerts.data?.alerts?.length ? <EmptyState>no threat events recorded</EmptyState> : (
          <div className="overflow-x-auto">
            <table className="w-full text-[0.76rem]">
              <thead><tr className="text-[var(--text-muted)] text-left border-b border-[var(--border)]">
                <th className="pb-2 font-medium">Time</th><th className="pb-2 font-medium">Source</th><th className="pb-2 font-medium">Destination</th>
                <th className="pb-2 font-medium">Attack</th><th className="pb-2 font-medium">Confidence</th><th className="pb-2 font-medium">Family</th>
              </tr></thead>
              <tbody className="divide-y divide-[var(--border)]">
                {alerts.data.alerts.map((a: any) => (
                  <tr key={a.id} className="hover:bg-[var(--bg-hover)]">
                    <td className="py-2 text-[var(--text-muted)] font-mono text-[0.72rem]">{(a.ts || '').replace('T', ' ').slice(11, 19)}</td>
                    <td className="py-2 font-mono text-[var(--text-main)]">{a.src_ip}</td>
                    <td className="py-2 font-mono text-[var(--text-dim)]">{a.dst_ip}:{a.dst_port}</td>
                    <td className="py-2"><Badge tone="danger">{a.label}</Badge></td>
                    <td className="py-2 tabular-nums text-[var(--text-dim)]">{fmtConf(a.confidence)}</td>
                    <td className="py-2 text-[var(--text-dim)] capitalize">{a.family}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
};
