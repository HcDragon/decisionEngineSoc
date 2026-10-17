import React from 'react';
import { ShieldCheck, Hand, Power } from 'lucide-react';
import { Panel, Badge, usePoll } from '../ui';

export const SettingsPage: React.FC<{ ctx: any }> = ({ ctx }) => {
  const { apiBase, automationMode, handleModeChange, executorMode } = ctx;
  const sys = usePoll<any>(`${apiBase}/system/status`, 8000);

  const modes = [
    { id: 'auto', label: 'Automatic', icon: ShieldCheck, desc: 'Engine evaluates and executes containment rules autonomously.' },
    { id: 'recommend_only', label: 'Manual Approval', icon: Hand, desc: 'Engine generates recommendations; analyst manually approves.' },
    { id: 'off', label: 'Passive Only', icon: Power, desc: 'Passive monitoring only — automated mitigation is disabled.' },
  ];

  return (
    <div className="flex flex-col gap-6 max-w-4xl">
      <Panel title="Defense Automation Mode">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {modes.map((m) => {
            const Icon = m.icon;
            const active = automationMode === m.id;
            return (
              <button
                key={m.id}
                onClick={() => handleModeChange(m.id)}
                className={`text-left rounded-xl border-[2.5px] border-[#0d0d11] p-4 transition-all cursor-pointer ${
                  active
                    ? 'bg-[var(--torii-vermilion)] text-white shadow-[4px_4px_0px_#0d0d11] -translate-y-0.5'
                    : 'bg-[#faf6f0] text-[#0d0d11] shadow-[2.5px_2.5px_0px_#0d0d11] hover:bg-white active:translate-x-[1px] active:translate-y-[1px]'
                }`}
              >
                <div className="flex items-center gap-2 text-[0.88rem] font-bold uppercase tracking-wide">
                  <Icon size={16} /> {m.label}
                  {active && (
                    <Badge tone="neutral" className="ml-auto bg-white text-[#0d0d11] border-[#0d0d11]">
                      ACTIVE
                    </Badge>
                  )}
                </div>
                <div className={`text-[0.74rem] font-mono mt-2 leading-relaxed ${active ? 'text-[#f5efe6]' : 'text-[#544d49]'}`}>
                  {m.desc}
                </div>
              </button>
            );
          })}
        </div>
        <div className="text-[0.72rem] font-mono text-[#c5bebe] mt-4">
          Writes to <code className="bg-[#181417] px-2 py-0.5 rounded border border-[#0d0d11] text-[var(--torii-amber)]">POST /system/mode</code> — the global autonomous policy gate.
        </div>
      </Panel>

      <Panel title="Executor &amp; Runtime Environment (Read-Only)">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-[0.78rem]">
          <div className="bg-[#faf6f0] p-3.5 rounded-xl border-[1.5px] border-[#0d0d11] shadow-[2px_2px_0px_#0d0d11]">
            <div className="text-[0.66rem] uppercase tracking-wider font-mono font-bold text-[#544d49]">Executor</div>
            <div className="text-[#0d0d11] font-mono font-extrabold mt-1 text-[0.85rem]">{executorMode}</div>
          </div>
          <div className="bg-[#faf6f0] p-3.5 rounded-xl border-[1.5px] border-[#0d0d11] shadow-[2px_2px_0px_#0d0d11]">
            <div className="text-[0.66rem] uppercase tracking-wider font-mono font-bold text-[#544d49]">Lab Mode</div>
            <div className="text-[#0d0d11] font-mono font-extrabold mt-1 text-[0.85rem]">{String(sys.data?.lab_mode ?? '—')}</div>
          </div>
          <div className="bg-[#faf6f0] p-3.5 rounded-xl border-[1.5px] border-[#0d0d11] shadow-[2px_2px_0px_#0d0d11]">
            <div className="text-[0.66rem] uppercase tracking-wider font-mono font-bold text-[#544d49]">Environment</div>
            <div className="text-[#0d0d11] font-mono font-extrabold mt-1 text-[0.85rem]">{sys.data?.environment ?? '—'}</div>
          </div>
          <div className="bg-[#faf6f0] p-3.5 rounded-xl border-[1.5px] border-[#0d0d11] shadow-[2px_2px_0px_#0d0d11]">
            <div className="text-[0.66rem] uppercase tracking-wider font-mono font-bold text-[#544d49]">Database</div>
            <div className="text-[#0d0d11] font-mono font-extrabold mt-1 text-[0.85rem]">
              {sys.data ? (sys.data.database_connected ? 'Connected' : 'Offline') : '—'}
            </div>
          </div>
        </div>
        <div className="text-[0.72rem] font-mono text-[#8c8385] mt-4 leading-relaxed">
          Executor mode and driver settings are initialized at daemon launch (e.g. nftables vs virtual firewall dry-run).
        </div>
      </Panel>
    </div>
  );
};
