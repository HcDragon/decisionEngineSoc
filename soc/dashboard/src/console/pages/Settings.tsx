import { useState } from 'react';
import { useSocData } from '../hooks/useSocData';
import { useSocSource } from '../data/context';
import { Panel, QueryBody } from '../components/Panel';
import type { AutomationMode } from '../data/types';
import { executorLabel } from '../data/derive';
import { useConsole } from '../shell/ConsoleContext';
import type { Theme } from '../hooks/useTheme';

const MODES: { id: AutomationMode; title: string; text: string }[] = [
  { id: 'auto', title: 'Automatic', text: 'Rules marked auto execute their playbook without waiting for an analyst.' },
  { id: 'recommend_only', title: 'Recommend only', text: 'Auto rules are downgraded to recommendations; actions stay proposed until approved.' },
  { id: 'off', title: 'Monitor only', text: 'Kill switch: decisions are recorded but no response action is taken.' },
];

export function SettingsPage({ theme, onToggleTheme }: { theme: Theme; onToggleTheme: () => void }) {
  const source = useSocSource();
  const { notify } = useConsole();
  const status = useSocData('status', (s) => s.getStatus(), { pollMs: 5_000 });
  const [busy, setBusy] = useState(false);

  const choose = async (mode: AutomationMode) => {
    setBusy(true);
    const r = await source.setAutomationMode(mode);
    setBusy(false);
    notify(r.message);
    status.retry();
  };

  return (
    <>
      <Panel title="Automation mode" note="POST /system/mode · global policy gate">
        <QueryBody query={status} rows={3}>
          {(s) => (
            <div className="soc-choices" role="group" aria-label="Automation mode">
              {MODES.map((m) => (
                <button key={m.id} type="button" className="soc-choice" aria-pressed={s.automationMode === m.id}
                  disabled={busy || !s.connected} onClick={() => choose(m.id)}>
                  <strong>{m.title}{s.automationMode === m.id ? ' · active' : ''}</strong>
                  <span>{m.text}</span>
                </button>
              ))}
            </div>
          )}
        </QueryBody>
      </Panel>

      <div className="soc-row">
        <Panel title="Appearance" className="soc-w-narrow">
          <div className="soc-controls">
            <span className="soc-field">Theme: {theme === 'dark' ? 'Dark' : 'Light'}</span>
            <button type="button" className="soc-btn" onClick={onToggleTheme}>Switch to {theme === 'dark' ? 'light' : 'dark'}</button>
          </div>
          <p className="soc-caption">Saved in this browser. With no saved choice the console follows the system setting.</p>
        </Panel>
        <Panel title="Response executor" className="soc-w-narrow" note="Read-only">
          <QueryBody query={status} rows={2}>
            {(s) => (
              <dl className="soc-kv">
                <div><dt>Executor</dt><dd>{s.connected ? executorLabel(s.executor) : '—'}</dd></div>
                <div><dt>Lab mode</dt><dd>{s.connected ? (s.labMode ? 'On' : 'Off') : '—'}</dd></div>
              </dl>
            )}
          </QueryBody>
          <p className="soc-caption">Set at backend launch (SOC_EXECUTOR / SOC_LAB_MODE).</p>
        </Panel>
      </div>
    </>
  );
}
