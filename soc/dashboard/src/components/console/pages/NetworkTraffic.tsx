import React, { useState } from 'react';
import { Play, Square, RefreshCw, Filter } from 'lucide-react';
import { Panel, Badge, MetricCard, EmptyState } from '../ui';

const PRESETS = [80, 443, 8000, 22, 53];

export const NetworkTrafficPage: React.FC<{ ctx: any }> = ({ ctx }) => {
  const { flows, trafficStats, portInput, setPortInput, handlePortChange, toggleTrafficMonitor, handleClearFlows, fmtConf } = ctx;
  const t = trafficStats || {};
  const live = t.engine_mode === 'native_nfstream';
  const [threatsOnly, setThreatsOnly] = useState(false);
  const [page, setPage] = useState(0);

  const all: any[] = (flows || []).filter((f: any) =>
    !threatsOnly || f.is_threat || (f.threat_label && !String(f.threat_label).toLowerCase().includes('benign')));
  const PER = 20;
  const pageRows = all.slice(page * PER, page * PER + PER);
  const pages = Math.max(1, Math.ceil(all.length / PER));

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label={`Port ${t.monitored_port} pkts/s`} value={t.current_packets_per_sec ?? 0} />
        <MetricCard label="Throughput" value={`${t.current_kb_per_sec ?? 0}`} sub="KB/s" />
        <MetricCard label="Flows seen" value={(t.total_flows ?? 0).toLocaleString()} />
        <MetricCard label="Capture mode" value={<span className="text-[1rem]">{live ? 'native' : 'emulated'}</span>} accent={live ? 'var(--success)' : 'var(--warning)'} />
      </div>

      <Panel title="Capture Controls"
        right={<Badge tone={live ? 'success' : 'warning'}>{live ? 'LIVE — observed network traffic' : 'TEST / REPLAY — emulated stream'}</Badge>}>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[0.76rem] text-[var(--text-dim)]">Target port:</span>
          {PRESETS.map(p => (
            <button key={p} onClick={() => { setPortInput(String(p)); setTimeout(() => handlePortChange(), 0); }}
              className={`px-2.5 py-1 rounded-md text-[0.74rem] border ${t.monitored_port === p ? 'bg-[var(--accent-soft)] border-[var(--accent)] text-[var(--accent)]' : 'bg-[var(--bg-inset)] border-[var(--border)] text-[var(--text-dim)] hover:text-[var(--text-main)]'}`}>{p}</button>
          ))}
          <form onSubmit={handlePortChange} className="flex items-center gap-2 ml-1">
            <input type="number" value={portInput} onChange={e => setPortInput(e.target.value)} min={1} max={65535}
              className="w-24 bg-[var(--bg-inset)] border border-[var(--border)] rounded-md px-2 py-1 text-[0.76rem] font-mono text-[var(--text-main)]" />
            <button type="submit" className="px-2.5 py-1 rounded-md text-[0.74rem] border border-[var(--border)] text-[var(--text-dim)] hover:text-[var(--text-main)]">Set</button>
          </form>
          <div className="ml-auto flex items-center gap-2">
            <button onClick={toggleTrafficMonitor} className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-[0.74rem] border border-[var(--border)] text-[var(--text-dim)] hover:text-[var(--text-main)]">
              {t.status === 'running' ? <><Square size={13} /> Pause</> : <><Play size={13} /> Start</>}
            </button>
            <button onClick={handleClearFlows} className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-[0.74rem] border border-[var(--border)] text-[var(--text-dim)] hover:text-[var(--text-main)]"><RefreshCw size={13} /> Flush</button>
          </div>
        </div>
      </Panel>

      <Panel title={`Flow Buffer (${all.length})`}
        right={<button onClick={() => { setThreatsOnly(v => !v); setPage(0); }}
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[0.72rem] border ${threatsOnly ? 'bg-[var(--danger-soft)] border-[var(--danger)]/40 text-[#ff8085]' : 'bg-[var(--bg-inset)] border-[var(--border)] text-[var(--text-dim)]'}`}><Filter size={12} />{threatsOnly ? 'threats only' : 'all flows'}</button>}>
        {all.length === 0 ? <EmptyState>no flows in buffer — generate traffic to the monitored port.</EmptyState> : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-[0.74rem] font-mono">
                <thead><tr className="text-[var(--text-muted)] text-left border-b border-[var(--border)]">
                  {['Source', 'Destination', 'Proto', 'Packets', 'Bytes', 'Dur(ms)', 'Classification', 'Conf'].map(h => <th key={h} className="pb-2 px-2 font-medium font-sans">{h}</th>)}
                </tr></thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {pageRows.map((f: any, idx: number) => {
                    const label = f.threat_label || 'Benign Traffic';
                    const threat = f.is_threat || (!String(label).toLowerCase().includes('benign'));
                    return (
                      <tr key={idx} className={`hover:bg-[var(--bg-hover)] ${threat ? 'bg-[var(--danger-soft)]' : ''}`}>
                        <td className="py-2 px-2 text-[var(--text-main)]">{f.src_ip}:{f.src_port}</td>
                        <td className="py-2 px-2 text-[var(--text-dim)]">{f.dst_ip}:{f.dst_port}</td>
                        <td className="py-2 px-2">{f.protocol}</td>
                        <td className="py-2 px-2 tabular-nums">{f.bidirectional_packets}</td>
                        <td className="py-2 px-2 tabular-nums">{((f.bidirectional_bytes || 0) / 1024).toFixed(1)}K</td>
                        <td className="py-2 px-2 tabular-nums">{f.duration_ms}</td>
                        <td className="py-2 px-2"><Badge tone={threat ? 'danger' : 'success'}>{label}</Badge></td>
                        <td className="py-2 px-2 tabular-nums text-[var(--text-dim)]">{fmtConf(f.confidence)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {pages > 1 && (
              <div className="flex items-center justify-end gap-2 mt-3 text-[0.74rem]">
                <button disabled={page === 0} onClick={() => setPage(p => p - 1)} className="px-2 py-1 rounded border border-[var(--border)] text-[var(--text-dim)] disabled:opacity-40">prev</button>
                <span className="text-[var(--text-muted)]">{page + 1}/{pages}</span>
                <button disabled={page >= pages - 1} onClick={() => setPage(p => p + 1)} className="px-2 py-1 rounded border border-[var(--border)] text-[var(--text-dim)] disabled:opacity-40">next</button>
              </div>
            )}
          </>
        )}
      </Panel>
    </div>
  );
};
