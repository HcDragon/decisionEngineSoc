import React from 'react';
import { ShieldCheck, Hand, Power } from 'lucide-react';
import { Panel, Badge, usePoll } from '../ui';

export const SettingsPage: React.FC<{ ctx: any }> = ({ ctx }) => {
  const { apiBase, automationMode, handleModeChange, executorMode } = ctx;
  const sys = usePoll<any>(`${apiBase}/system/status`, 8000);

  const modes = [
    { id: 'auto', label: 'Automatic', icon: ShieldCheck, desc: 'Engine contains threats on its own.' },
    { id: 'recommend_only', label: 'Manual', icon: Hand, desc: 'Analyst approves each containment.' },
    { id: 'off', label: 'Off', icon: Power, desc: 'Monitor only, no containment.' },
  ];

  return (
    <div className="flex flex-col gap-5 max-w-3xl">
      <Panel title="Defence Automation Mode">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {modes.map((m) => {
            const Icon = m.icon; const active = automationMode === m.id;
            return (
              <button key={m.id} onClick={() => handleModeChange(m.id)}
                className={`text-left rounded-lg border p-3 transition-colors ${active ? 'border-[var(--accent)] bg-[var(--accent-soft)]' : 'border-[var(--border)] bg-[var(--bg-inset)] hover:border-[var(--border-strong)]'}`}>
                <div className="flex items-center gap-2 text-[0.82rem] font-semibold text-[var(--text-main)]"><Icon size={15} /> {m.label} {active && <Badge tone="accent" className="ml-auto">active</Badge>}</div>
                <div className="text-[0.72rem] text-[var(--text-muted)] mt-1.5">{m.desc}</div>
              </button>
            );
          })}
        </div>
        <div className="text-[0.68rem] text-[var(--text-muted)] mt-3">Writes to <code>POST /system/mode</code> — the global automation kill-switch.</div>
      </Panel>

      <Panel title="Executor & Runtime (read-only)">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-[0.78rem]">
          <div><div className="text-[0.66rem] uppercase tracking-wide text-[var(--text-muted)]">executor</div><div className="text-[var(--text-main)] font-medium mt-0.5">{executorMode}</div></div>
          <div><div className="text-[0.66rem] uppercase tracking-wide text-[var(--text-muted)]">lab mode</div><div className="text-[var(--text-main)] font-medium mt-0.5">{String(sys.data?.lab_mode ?? '—')}</div></div>
          <div><div className="text-[0.66rem] uppercase tracking-wide text-[var(--text-muted)]">environment</div><div className="text-[var(--text-main)] font-medium mt-0.5">{sys.data?.environment ?? '—'}</div></div>
          <div><div className="text-[0.66rem] uppercase tracking-wide text-[var(--text-muted)]">database</div><div className="text-[var(--text-main)] font-medium mt-0.5">{sys.data ? (sys.data.database_connected ? 'connected' : 'down') : '—'}</div></div>
        </div>
        <div className="text-[0.68rem] text-[var(--text-muted)] mt-3">Executor tier and lab mode are backend-configured (env / <code>defend/start.sh</code>); changing them from the UI is intentionally not supported.</div>
      </Panel>
    </div>
  );
};
