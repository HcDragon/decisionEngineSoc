import { useState } from 'react';
import { useSocData } from '../hooks/useSocData';
import { useSocSource } from '../data/context';
import { Empty, ErrorState, Panel, QueryBody, Skeleton } from '../components/Panel';
import { BarList } from '../components/BarList';
import { matchesQuery } from '../data/derive';
import { useConsole } from '../shell/ConsoleContext';

const fmtBytes = (b: number) => (b >= 1e9 ? `${(b / 1e9).toFixed(2)} GB` : b >= 1e6 ? `${(b / 1e6).toFixed(1)} MB` : b >= 1e3 ? `${(b / 1e3).toFixed(1)} KB` : `${b} B`);

export function NetworkTrafficPage() {
  const source = useSocSource();
  const { notify, query } = useConsole();
  const traffic = useSocData('traffic', (s) => s.getTraffic(), { pollMs: 2_000 });
  const [threatOnly, setThreatOnly] = useState(false);
  const flows = useSocData(`flows-${threatOnly}`, (s) => s.getFlows(200, threatOnly), { pollMs: 2_000 });
  const [port, setPort] = useState('');
  const [busy, setBusy] = useState(false);

  const run = async (fn: () => Promise<{ ok: boolean; message: string }>) => {
    setBusy(true);
    const r = await fn();
    setBusy(false);
    notify(r.message);
    traffic.retry();
    flows.retry();
  };
  const submitPort = (p: number) => {
    if (!Number.isInteger(p) || p < 1 || p > 65535) { notify('Enter a port between 1 and 65535'); return; }
    run(() => source.setMonitoredPort(p));
  };

  const t = traffic.status === 'ready' ? traffic.data : null;
  const shownFlows = flows.status === 'ready' ? flows.data.filter((f) => matchesQuery(query, [f.srcIp, f.dstIp, f.label, f.app])) : [];

  return (
    <>
      {traffic.status === 'loading' && <Skeleton rows={2} />}
      {traffic.status === 'error' && !t && <ErrorState error={traffic.error} onRetry={traffic.retry} />}
      {t && (
        <div className="soc-kpis">
          {[
            ['Packets / s', Math.round(t.packetsPerSec).toLocaleString('en-US'), `port ${t.monitoredPort}`],
            ['Throughput', `${Math.round(t.kbPerSec).toLocaleString('en-US')} KB/s`, `${fmtBytes(t.totalBytes)} total`],
            ['Flows captured', t.totalFlows.toLocaleString('en-US'), `${t.threatFlows.toLocaleString('en-US')} flagged as threats`],
            ['Capture', t.running ? 'Running' : 'Stopped', t.engineMode === 'native_nfstream' ? 'Native NFStream' : 'Emulated stream'],
          ].map(([label, value, sub]) => (
            <section className="soc-kpi" key={label} aria-label={label}>
              <p className="soc-kpi-label">{label}</p>
              <p className="soc-kpi-value">{value}</p>
              <p className="soc-kpi-sub">{sub}</p>
            </section>
          ))}
        </div>
      )}

      <Panel title="Capture controls" note={t ? `Monitoring port ${t.monitoredPort}` : null}>
        <div className="soc-controls">
          <form className="soc-controls" onSubmit={(e) => { e.preventDefault(); submitPort(Number(port)); }}>
            <label htmlFor="soc-port" className="soc-field">Monitored port</label>
            <input id="soc-port" className="soc-input" inputMode="numeric" placeholder={t ? String(t.monitoredPort) : 'port'} value={port} onChange={(e) => setPort(e.target.value)} />
            <button type="submit" className="soc-btn" disabled={busy || !port}>Set port</button>
          </form>
          <span style={{ flex: '1 1 auto' }} />
          <button type="button" className="soc-btn" disabled={busy || !t} onClick={() => run(() => source.setCapture(!t?.running, t?.monitoredPort))}>
            {t?.running ? 'Stop capture' : 'Start capture'}
          </button>
          <button type="button" className="soc-btn" disabled={busy} onClick={() => run(() => source.clearFlows())}>Clear flow buffer</button>
        </div>
      </Panel>

      <div className="soc-row">
        <Panel title="Protocol mix" note="Flows since capture start" className="soc-w-narrow">
          {t ? <BarList items={Object.entries(t.protocols).map(([name, count]) => ({ name, count }))} empty="No flows yet." /> : <Skeleton rows={3} />}
        </Panel>
        <Panel title="Top sources" note="By packets" className="soc-w-narrow">
          {t ? <BarList mono items={t.topSources.slice(0, 6).map((s) => ({ name: s.ip, count: s.packets }))} empty="No sources yet." /> : <Skeleton rows={3} />}
        </Panel>
      </div>

      <Panel title="Flow buffer" note={
        <>
          {flows.status === 'ready' && <span>{shownFlows.length} flows</span>}
          <button type="button" className="soc-btn soc-btn--sm" aria-pressed={threatOnly} onClick={() => setThreatOnly((v) => !v)}>
            {threatOnly ? 'Showing threats only' : 'Showing all flows'}
          </button>
        </>
      }>
        <QueryBody query={flows} rows={8}>
          {() => shownFlows.length === 0 ? <Empty>No flows in the buffer. Generate traffic to the monitored port.</Empty> : (
            <div className="soc-flows-scroll">
              <div className="soc-table soc-t-flows" role="table" aria-label="Recent flows">
                <div className="soc-thead" role="rowgroup">
                  <div className="soc-tr" role="row">
                    {['Time', 'Source', 'Destination', 'Proto', 'Packets', 'Bytes', 'Verdict', 'Conf.'].map((h) => <span key={h} role="columnheader">{h}</span>)}
                  </div>
                </div>
                <div className="soc-tbody" role="rowgroup">
                  {shownFlows.map((f) => (
                    <div className="soc-tr" role="row" key={f.id}>
                      <span role="cell" className="soc-td soc-mono">{f.time.slice(0, 8)}</span>
                      <span role="cell" className="soc-td soc-mono">{f.srcIp}:{f.srcPort}</span>
                      <span role="cell" className="soc-td soc-mono">{f.dstIp}:{f.dstPort}</span>
                      <span role="cell" className="soc-td">{f.protocol}</span>
                      <span role="cell" className="soc-td soc-num">{f.packets.toLocaleString('en-US')}</span>
                      <span role="cell" className="soc-td soc-num">{fmtBytes(f.bytes)}</span>
                      <span role="cell" className={`soc-td ${f.isThreat ? 'soc-tone-bad' : ''}`}>{f.isThreat ? `Threat · ${f.label}` : f.label}</span>
                      <span role="cell" className="soc-td soc-num">{Math.round(f.confidence * 100)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </QueryBody>
      </Panel>
    </>
  );
}
