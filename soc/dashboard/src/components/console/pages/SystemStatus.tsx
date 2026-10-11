import React from 'react';
import { Panel, Badge, usePoll, Loading, ErrorState } from '../ui';

export const SystemStatusPage: React.FC<{ ctx: any }> = ({ ctx }) => {
  const { apiBase, systemHealth, trafficStats } = ctx;
  const { data, loading, error } = usePoll<any>(`${apiBase}/system/status`, 5000);
  const t = trafficStats || {};

  // Each component resolves to Healthy / Degraded / Offline / Unknown from real signals.
  const reachable = !error && !!data;
  const comp = (ok: boolean | undefined, okNote: string, badNote: string, degraded = false) => {
    if (loading) return { tone: 'neutral' as const, state: 'Unknown', note: 'checking…' };
    if (ok === undefined) return { tone: 'neutral' as const, state: 'Unknown', note: 'not reported' };
    if (ok) return degraded ? { tone: 'warning' as const, state: 'Degraded', note: okNote } : { tone: 'success' as const, state: 'Healthy', note: okNote };
    return { tone: 'danger' as const, state: 'Offline', note: badNote };
  };

  const components = [
    { name: 'Decision Engine API', ...comp(systemHealth?.status === 'healthy', 'responding', 'unreachable') },
    { name: 'Database', ...comp(reachable ? data?.database_connected : undefined, 'connected', 'disconnected') },
    { name: 'AI/ML IDS model', ...comp(reachable ? data?.model_dir_exists : undefined, 'artifacts present', 'model dir missing') },
    { name: 'Policy / config store', ...comp(reachable ? data?.config_dir_exists : undefined, 'loaded', 'config dir missing') },
    { name: 'NFStream sensor', ...comp(t.engine_mode === 'native_nfstream' ? true : t.engine_mode === 'emulated_stream', t.engine_mode === 'native_nfstream' ? 'native capture' : 'emulated fallback', 'not running', t.engine_mode !== 'native_nfstream') },
    { name: 'Event-processing pipeline', ...comp(t.status === 'running', 'processing flows', 'stopped') },
  ];

  return (
    <div className="flex flex-col gap-5">
      {error && <ErrorState>Decision Engine API unreachable — component states below are Unknown, not Offline.</ErrorState>}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {components.map((c) => (
          <div key={c.name} className="rounded-lg border border-[var(--border)] bg-[rgba(16,21,30,0.72)] backdrop-blur-xl p-4">
            <div className="flex items-center justify-between">
              <span className="text-[0.82rem] font-medium text-[var(--text-main)]">{c.name}</span>
              <Badge tone={c.tone}><span className="h-1.5 w-1.5 rounded-full" style={{ background: c.tone === 'success' ? 'var(--success)' : c.tone === 'warning' ? 'var(--warning)' : c.tone === 'danger' ? 'var(--danger)' : 'var(--text-muted)' }} />{c.state}</Badge>
            </div>
            <div className="text-[0.74rem] text-[var(--text-muted)] mt-1.5">{c.note}</div>
          </div>
        ))}
      </div>
      {data && (
        <Panel title="Runtime">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-[0.78rem]">
            {[['environment', data.environment], ['automation', data.automation_mode], ['executor', data.executor], ['lab mode', String(data.lab_mode)]].map(([k, v]) => (
              <div key={k}><div className="text-[0.66rem] uppercase tracking-wide text-[var(--text-muted)]">{k}</div><div className="text-[var(--text-main)] font-medium mt-0.5">{v}</div></div>
            ))}
          </div>
          <div className="text-[0.68rem] text-[var(--text-muted)] mt-3">last health check: {(data.timestamp || '').replace('T', ' ').slice(0, 19)}</div>
        </Panel>
      )}
    </div>
  );
};
