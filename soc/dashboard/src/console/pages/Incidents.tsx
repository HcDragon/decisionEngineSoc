import { useState } from 'react';
import { useSocData } from '../hooks/useSocData';
import { useSocSource } from '../data/context';
import { Panel, QueryBody } from '../components/Panel';
import { IncidentTable } from '../components/IncidentTable';
import type { Incident } from '../data/types';
import { useConsole } from '../shell/ConsoleContext';

export function IncidentsPage() {
  const source = useSocSource();
  const { notify } = useConsole();
  const q = useSocData('incidents-all', (s) => s.getIncidents(), { pollMs: 10_000, refreshOn: ['alert', 'decision', 'playbook'] });
  const [busy, setBusy] = useState<number | null>(null);

  const act = async (i: Incident) => {
    setBusy(i.id);
    const r = i.status === 'contained' ? await source.release(i.id) : await source.respond(i.id);
    setBusy(null);
    notify(r.message);
    if (r.ok) q.retry();
  };

  const note = q.status === 'ready'
    ? `${q.data.filter((i) => i.status === 'open').length} open · ${q.data.filter((i) => i.status === 'contained').length} contained · ${q.data.length} total`
    : null;

  return (
    <Panel title="All incidents" note={note}>
      <QueryBody query={q} rows={8}>
        {(incidents) => (
          <IncidentTable
            incidents={incidents}
            actions={(i) => (i.status === 'open' || i.status === 'contained') ? (
              <button type="button" className={`soc-btn soc-btn--sm ${i.status === 'open' ? 'soc-btn--primary' : ''}`}
                disabled={busy === i.id} onClick={() => act(i)}
                aria-label={`${i.status === 'contained' ? 'Release' : 'Contain'} source ${i.srcIp}`}>
                {i.status === 'contained' ? 'Release' : 'Contain'}
              </button>
            ) : <span className="soc-muted">{i.status.replace('_', ' ')}</span>}
          />
        )}
      </QueryBody>
    </Panel>
  );
}
