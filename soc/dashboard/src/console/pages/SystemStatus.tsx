import { useSocData } from '../hooks/useSocData';
import { Panel, QueryBody } from '../components/Panel';
import { executorLabel } from '../data/derive';

const yesNo = (v: boolean, yes = 'Yes', no = 'No') => <span className={v ? 'soc-tone-good' : 'soc-tone-bad'}>{v ? yes : no}</span>;

export function SystemStatusPage() {
  const sources = useSocData('sources', (s) => s.getDetectionSourceHealth(), { pollMs: 5_000 });
  const status = useSocData('status', (s) => s.getStatus(), { pollMs: 5_000 });
  const policy = useSocData('policy', (s) => s.getPolicy());

  return (
    <>
      <Panel title="Detection sources" note={sources.status === 'ready' ? `${sources.data.reduce((n, r) => n + r.up, 0)} / ${sources.data.length} online` : null}>
        <QueryBody query={sources} rows={5}>
          {(rows) => (
            <ul className="soc-list">
              {rows.map((r) => (
                <li key={r.name}>
                  <span className="soc-grow">{r.name}</span>
                  <span className="soc-muted">{r.detail}</span>
                  <span className={`soc-state ${r.up === r.total ? 'soc-tone-good' : 'soc-tone-bad'}`}>{r.up === r.total ? 'Online' : 'Offline'}</span>
                </li>
              ))}
            </ul>
          )}
        </QueryBody>
      </Panel>

      <div className="soc-row">
        <Panel title="Runtime" className="soc-w-wide">
          <QueryBody query={status} rows={4}>
            {(s) => !s.connected ? <p className="soc-tone-bad">Backend unreachable.</p> : (
              <dl className="soc-kv">
                <div><dt>Environment</dt><dd>{s.environment}</dd></div>
                <div><dt>Automation</dt><dd>{s.automationMode.replace('_', ' ')}</dd></div>
                <div><dt>Executor</dt><dd>{executorLabel(s.executor)}</dd></div>
                <div><dt>Lab mode</dt><dd>{yesNo(s.labMode, 'On', 'Off')}</dd></div>
                <div><dt>Capture engine</dt><dd>{s.engineMode === 'native_nfstream' ? 'Native NFStream' : 'Emulated stream'}</dd></div>
                <div><dt>Monitored port</dt><dd className="soc-num">{s.monitoredPort}</dd></div>
                <div><dt>Model artifacts</dt><dd>{yesNo(s.modelLoaded, 'Present', 'Missing')}</dd></div>
                <div><dt>Config directory</dt><dd>{yesNo(s.configLoaded, 'Present', 'Missing')}</dd></div>
                <div><dt>Database</dt><dd>{yesNo(s.databaseConnected, 'Connected', 'Down')}</dd></div>
                <div><dt>Active blocks</dt><dd className="soc-num">{s.activeBlocks}</dd></div>
              </dl>
            )}
          </QueryBody>
        </Panel>
        <Panel title="Policy" className="soc-w-narrow" note={policy.status === 'ready' ? <span className="soc-mono">{policy.data.policyHash.slice(0, 12)}</span> : null}>
          <QueryBody query={policy} rows={4}>
            {(p) => (
              <>
                <dl className="soc-kv" style={{ marginBottom: 14 }}>
                  <div><dt>Version</dt><dd>{p.version}</dd></div>
                  <div><dt>Tiers (risk ≥)</dt><dd className="soc-num">C {p.tiers.critical} · H {p.tiers.high} · M {p.tiers.medium}</dd></div>
                  <div><dt>Min alert confidence</dt><dd className="soc-num">{p.minAlertConfidence}</dd></div>
                </dl>
                <ul className="soc-list">
                  {p.rules.map((r) => (
                    <li key={r.id}><span className="soc-grow soc-mono">{r.id}</span><span className="soc-muted">{r.mode}</span><span className="soc-mono soc-soft">{r.playbook ?? '—'}</span></li>
                  ))}
                </ul>
              </>
            )}
          </QueryBody>
        </Panel>
      </div>
    </>
  );
}
