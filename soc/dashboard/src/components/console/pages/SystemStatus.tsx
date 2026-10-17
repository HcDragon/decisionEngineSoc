import React from 'react';
import { Panel, Badge, usePoll, Loading, ErrorState } from '../ui';

export const SystemStatusPage: React.FC<{ ctx: any }> = ({ ctx }) => {
  const { apiBase, systemHealth, trafficStats } = ctx;
  const { data, loading, error } = usePoll<any>(`${apiBase}/system/status`, 5000);
  const t = trafficStats || {};

  const reachable = !error && !!data;
  const comp = (ok: boolean | undefined, okNote: string, badNote: string, degraded = false) => {
    if (loading) return { tone: 'neutral' as const, state: 'Checking', note: 'Querying telemetry...' };
    if (ok === undefined) return { tone: 'neutral' as const, state: 'Unknown', note: 'Not reported' };
    if (ok) return degraded ? { tone: 'warning' as const, state: 'Degraded', note: okNote } : { tone: 'success' as const, state: 'Healthy', note: okNote };
    return { tone: 'danger' as const, state: 'Offline', note: badNote };
  };

  const components = [
    { name: 'Decision Engine API', ...comp(systemHealth?.status === 'healthy', 'Responding', 'Unreachable') },
    { name: 'Database', ...comp(reachable ? data?.database_connected : undefined, 'Connected', 'Disconnected') },
    { name: 'AI/ML IDS Model', ...comp(reachable ? data?.model_dir_exists : undefined, 'Artifacts present', 'Model directory missing') },
    { name: 'Policy / Config Store', ...comp(reachable ? data?.config_dir_exists : undefined, 'Loaded', 'Config directory missing') },
    { name: 'NFStream Sensor', ...comp(t.engine_mode === 'native_nfstream' ? true : t.engine_mode === 'emulated_stream', t.engine_mode === 'native_nfstream' ? 'Native capture' : 'Emulated fallback', 'Not running', t.engine_mode !== 'native_nfstream') },
    { name: 'Event Pipeline', ...comp(t.status === 'running', 'Processing flows', 'Stopped') },
  ];

  return (
    <div className="flex flex-col gap-6">
      {error && <ErrorState>Decision Engine API unreachable — component states below are Unknown, not Offline.</ErrorState>}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {components.map((c) => (
          <div key={c.name} className="rounded-xl border-[2.5px] border-[#0d0d11] bg-[#faf6f0] text-[#0d0d11] shadow-[3.5px_3.5px_0px_#0d0d11] p-4 transition-transform hover:-translate-y-0.5">
            <div className="flex items-center justify-between">
              <span className="text-[0.88rem] font-bold text-[#0d0d11] uppercase tracking-wide">{c.name}</span>
              <Badge tone={c.tone}>
                <span className="h-2 w-2 rounded-full border border-[#0d0d11]" style={{ background: c.tone === 'success' ? 'var(--torii-sage)' : c.tone === 'warning' ? 'var(--torii-amber)' : c.tone === 'danger' ? 'var(--torii-vermilion)' : '#8c857b' }} />
                {c.state}
              </Badge>
            </div>
            <div className="text-[0.75rem] font-mono font-medium text-[#544d49] mt-2">{c.note}</div>
          </div>
        ))}
      </div>
      {data && (
        <Panel title="Runtime Diagnostics">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-[0.78rem]">
            {[['environment', data.environment], ['automation', data.automation_mode], ['executor', data.executor], ['lab mode', String(data.lab_mode)]].map(([k, v]) => (
              <div key={k} className="bg-[#faf6f0] p-3 rounded-lg border-[1.5px] border-[#0d0d11] shadow-[1.5px_1.5px_0px_#0d0d11]">
                <div className="text-[0.66rem] uppercase tracking-wider font-mono font-bold text-[#544d49]">{k}</div>
                <div className="text-[#0d0d11] font-mono font-extrabold mt-1 text-[0.85rem]">{v}</div>
              </div>
            ))}
          </div>
          <div className="text-[0.7rem] font-mono text-[var(--torii-amber)] font-bold mt-4">
            Last health verification: {(data.timestamp || '').replace('T', ' ').slice(0, 19)}
          </div>
        </Panel>
      )}
    </div>
  );
};
