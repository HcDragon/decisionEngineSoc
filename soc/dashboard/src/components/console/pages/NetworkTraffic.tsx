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
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label={`Port ${t.monitored_port} pkts/s`} value={t.current_packets_per_sec ?? 0} />
        <MetricCard label="Throughput" value={`${t.current_kb_per_sec ?? 0}`} sub="KB/s" accent="var(--torii-amber)" />
        <MetricCard label="Flows seen" value={(t.total_flows ?? 0).toLocaleString()} accent="var(--torii-sage)" />
        <MetricCard label="Capture mode" value={<span className="text-[1.2rem] font-bold font-mono">{live ? 'NATIVE' : 'EMULATED'}</span>} accent={live ? 'var(--torii-sage)' : 'var(--torii-amber)'} />
      </div>

      <Panel title="Capture Controls"
        right={<Badge tone={live ? 'success' : 'warning'}>{live ? 'LIVE • OBSERVED TRAFFIC' : 'TEST / REPLAY • EMULATED'}</Badge>}>
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-[0.76rem] font-mono font-bold uppercase text-[#c5bebe]">Target Port:</span>
          {PRESETS.map(p => (
            <button
              key={p}
              onClick={() => { setPortInput(String(p)); setTimeout(() => handlePortChange(), 0); }}
              className={`px-3 py-1 rounded-md text-[0.74rem] font-mono font-bold border-[1.5px] border-[#0d0d11] shadow-[1.5px_1.5px_0px_#0d0d11] active:translate-x-[1px] active:translate-y-[1px] cursor-pointer transition-all ${
                t.monitored_port === p
                  ? 'bg-[var(--torii-vermilion)] text-white'
                  : 'bg-[#faf6f0] text-[#0d0d11] hover:bg-white'
              }`}
            >
              {p}
            </button>
          ))}
          <form onSubmit={handlePortChange} className="flex items-center gap-2 ml-1">
            <input
              type="number"
              value={portInput}
              onChange={e => setPortInput(e.target.value)}
              min={1}
              max={65535}
              className="w-24 bg-[#faf6f0] text-[#0d0d11] border-[2px] border-[#0d0d11] shadow-[2px_2px_0px_#0d0d11] rounded-md px-2.5 py-1 text-[0.76rem] font-mono font-bold"
            />
            <button
              type="submit"
              className="px-3 py-1 rounded-md text-[0.74rem] font-mono font-bold uppercase bg-[var(--torii-vermilion)] text-white border-[1.5px] border-[#0d0d11] shadow-[1.5px_1.5px_0px_#0d0d11] active:translate-x-[1px] active:translate-y-[1px] cursor-pointer"
            >
              Set
            </button>
          </form>
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={toggleTrafficMonitor}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-[0.74rem] font-mono font-bold uppercase bg-[#faf6f0] text-[#0d0d11] border-[2px] border-[#0d0d11] shadow-[2px_2px_0px_#0d0d11] active:translate-x-[1px] active:translate-y-[1px] hover:bg-white cursor-pointer transition-all"
            >
              {t.status === 'running' ? <><Square size={13} className="text-[var(--torii-vermilion)]" /> Pause Tap</> : <><Play size={13} className="text-[var(--torii-sage)]" /> Start Tap</>}
            </button>
            <button
              onClick={handleClearFlows}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-[0.74rem] font-mono font-bold uppercase bg-[#faf6f0] text-[#0d0d11] border-[2px] border-[#0d0d11] shadow-[2px_2px_0px_#0d0d11] active:translate-x-[1px] active:translate-y-[1px] hover:bg-white cursor-pointer transition-all"
            >
              <RefreshCw size={13} /> Flush Buffer
            </button>
          </div>
        </div>
      </Panel>

      <Panel title={`Flow Buffer (${all.length})`}
        right={
          <button
            onClick={() => { setThreatsOnly(v => !v); setPage(0); }}
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-[0.72rem] font-mono font-bold uppercase border-[1.5px] border-[#0d0d11] shadow-[2px_2px_0px_#0d0d11] active:translate-x-[1px] active:translate-y-[1px] cursor-pointer transition-all ${
              threatsOnly
                ? 'bg-[var(--torii-vermilion)] text-white'
                : 'bg-[#faf6f0] text-[#0d0d11]'
            }`}
          >
            <Filter size={12} /> {threatsOnly ? 'Threats Only' : 'All Flows'}
          </button>
        }>
        {all.length === 0 ? <EmptyState>No flows in buffer — generate traffic to the monitored port.</EmptyState> : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-[0.76rem] font-mono">
                <thead>
                  <tr className="text-white text-left border-b-[2px] border-[#0d0d11]">
                    {['Source IP', 'Destination IP', 'Proto', 'Packets', 'Bytes', 'Dur (ms)', 'Classification', 'Confidence'].map(h => (
                      <th key={h} className="pb-2.5 px-3 font-extrabold uppercase font-mono text-[0.72rem] text-[#c5bebe]">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y-[1.5px] divide-[#1d171b]">
                  {pageRows.map((f: any, idx: number) => {
                    const label = f.threat_label || 'Benign Traffic';
                    const threat = f.is_threat || (!String(label).toLowerCase().includes('benign'));
                    return (
                      <tr key={idx} className={`hover:bg-[rgba(226,74,43,0.08)] transition-colors ${threat ? 'bg-[rgba(226,74,43,0.12)]' : ''}`}>
                        <td className="py-2.5 px-3 font-bold text-white">{f.src_ip}:{f.src_port}</td>
                        <td className="py-2.5 px-3 text-[#c5bebe]">{f.dst_ip}:{f.dst_port}</td>
                        <td className="py-2.5 px-3 font-bold">{f.protocol}</td>
                        <td className="py-2.5 px-3 tabular-nums font-bold text-white">{f.bidirectional_packets}</td>
                        <td className="py-2.5 px-3 tabular-nums text-[#c5bebe]">{((f.bidirectional_bytes || 0) / 1024).toFixed(1)}K</td>
                        <td className="py-2.5 px-3 tabular-nums text-[#c5bebe]">{f.duration_ms}</td>
                        <td className="py-2.5 px-3"><Badge tone={threat ? 'danger' : 'success'}>{label}</Badge></td>
                        <td className="py-2.5 px-3 tabular-nums text-white font-bold">{fmtConf(f.confidence)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {pages > 1 && (
              <div className="flex items-center justify-end gap-2 mt-4 text-[0.74rem] font-mono">
                <button
                  disabled={page === 0}
                  onClick={() => setPage(p => p - 1)}
                  className="px-3 py-1 rounded-md border-[1.5px] border-[#0d0d11] shadow-[1.5px_1.5px_0px_#0d0d11] bg-[#faf6f0] text-[#0d0d11] font-bold uppercase disabled:opacity-40 cursor-pointer"
                >
                  Prev
                </button>
                <span className="text-white font-bold px-2">{page + 1} / {pages}</span>
                <button
                  disabled={page >= pages - 1}
                  onClick={() => setPage(p => p + 1)}
                  className="px-3 py-1 rounded-md border-[1.5px] border-[#0d0d11] shadow-[1.5px_1.5px_0px_#0d0d11] bg-[#faf6f0] text-[#0d0d11] font-bold uppercase disabled:opacity-40 cursor-pointer"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </Panel>
    </div>
  );
};
