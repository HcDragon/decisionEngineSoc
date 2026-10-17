import React from 'react';
import { Activity, ShieldCheck, AlertTriangle, Radio, ArrowRight } from 'lucide-react';

interface LiveTelemetryBannerProps {
  systemHealth: { status?: string } | null;
  trafficStats: {
    status?: string;
    total_flows: number;
    current_packets_per_sec: number;
    current_kb_per_sec: number;
    threat_flows_count: number;
    monitored_port: number;
  };
  overview: {
    stats?: {
      active_blocks?: number;
      total_incidents?: number;
    };
  } | null;
  automationMode: string;
  onOpenConsole: () => void;
}

export const LiveTelemetryBanner: React.FC<LiveTelemetryBannerProps> = ({
  systemHealth,
  trafficStats,
  overview,
  automationMode,
  onOpenConsole,
}) => {
  const isHealthy = systemHealth?.status === 'healthy';
  const threatPct =
    trafficStats.total_flows > 0
      ? ((trafficStats.threat_flows_count / trafficStats.total_flows) * 100).toFixed(1)
      : '0.0';

  return (
    <div className="w-full bg-[rgba(26,21,24,0.96)] border-y-[3px] border-[#0d0d11] shadow-[0_4px_0px_#0d0d11] px-4 sm:px-8 py-5">
      <div className="max-w-7xl mx-auto flex flex-col lg:flex-row items-center justify-between gap-6">
        {/* Status & Engine Info */}
        <div className="flex items-center gap-3.5">
          <div className="relative flex h-3.5 w-3.5">
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                isHealthy ? 'bg-[var(--torii-sage)]' : 'bg-[var(--torii-amber)]'
              }`}
            />
            <span
              className={`relative inline-flex rounded-full h-3.5 w-3.5 border border-[#0d0d11] ${
                isHealthy ? 'bg-[var(--torii-sage)]' : 'bg-[var(--torii-amber)]'
              }`}
            />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <span className="text-white text-sm font-bold uppercase tracking-wider font-mono">
                Autonomous SOC Telemetry
              </span>
              <span
                className={`text-[10px] px-2.5 py-0.5 rounded-md uppercase font-extrabold tracking-wider border-[1.5px] border-[#0d0d11] shadow-[1.5px_1.5px_0px_#0d0d11] ${
                  isHealthy
                    ? 'bg-[var(--torii-sage)] text-white'
                    : 'bg-[var(--torii-amber)] text-[#0d0d11]'
                }`}
              >
                {isHealthy ? 'LIVE & ACTIVE' : 'STANDBY'}
              </span>
            </div>
            <p className="text-xs text-[#c5bebe] font-mono mt-1">
              NFSTREAM TAP • PORT <span className="font-bold text-white">{trafficStats.monitored_port}</span> • MODE:{' '}
              <span className="text-[var(--torii-amber)] uppercase font-bold">{automationMode}</span>
            </p>
          </div>
        </div>

        {/* Live Metrics Quick Strip — Tactile Neobrutalist Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 w-full lg:w-auto">
          <div className="bg-[#faf6f0] text-[#0d0d11] border-[2.5px] border-[#0d0d11] shadow-[3.5px_3.5px_0px_#0d0d11] rounded-xl px-3.5 py-2.5 hover:-translate-y-0.5 transition-transform">
            <div className="text-[10.5px] text-[#544d49] font-bold uppercase tracking-wider flex items-center gap-1.5 font-mono">
              <Activity className="h-3.5 w-3.5 text-[var(--torii-vermilion)]" /> Throughput
            </div>
            <div className="text-[#0d0d11] text-lg font-extrabold mt-0.5 font-mono">
              {trafficStats.current_packets_per_sec}{' '}
              <span className="text-xs text-[#706764] font-bold font-sans">pkts/s</span>
            </div>
          </div>

          <div className="bg-[#faf6f0] text-[#0d0d11] border-[2.5px] border-[#0d0d11] shadow-[3.5px_3.5px_0px_#0d0d11] rounded-xl px-3.5 py-2.5 hover:-translate-y-0.5 transition-transform">
            <div className="text-[10.5px] text-[#544d49] font-bold uppercase tracking-wider flex items-center gap-1.5 font-mono">
              <Radio className="h-3.5 w-3.5 text-[var(--torii-sage)]" /> Total Flows
            </div>
            <div className="text-[#0d0d11] text-lg font-extrabold mt-0.5 font-mono">
              {trafficStats.total_flows.toLocaleString()}
            </div>
          </div>

          <div className="bg-[#faf6f0] text-[#0d0d11] border-[2.5px] border-[#0d0d11] shadow-[3.5px_3.5px_0px_#0d0d11] rounded-xl px-3.5 py-2.5 hover:-translate-y-0.5 transition-transform">
            <div className="text-[10.5px] text-[#544d49] font-bold uppercase tracking-wider flex items-center gap-1.5 font-mono">
              <AlertTriangle className="h-3.5 w-3.5 text-[var(--torii-amber)]" /> Anomaly Rate
            </div>
            <div className="text-[#0d0d11] text-lg font-extrabold mt-0.5 font-mono">
              {threatPct}%
            </div>
          </div>

          <div className="bg-[#faf6f0] text-[#0d0d11] border-[2.5px] border-[#0d0d11] shadow-[3.5px_3.5px_0px_#0d0d11] rounded-xl px-3.5 py-2.5 hover:-translate-y-0.5 transition-transform">
            <div className="text-[10.5px] text-[#544d49] font-bold uppercase tracking-wider flex items-center gap-1.5 font-mono">
              <ShieldCheck className="h-3.5 w-3.5 text-[var(--torii-crimson)]" /> Active Blocks
            </div>
            <div className="text-[#0d0d11] text-lg font-extrabold mt-0.5 font-mono">
              {overview?.stats?.active_blocks ?? 0}
            </div>
          </div>
        </div>

        {/* CTA Launch into Console */}
        <button
          type="button"
          onClick={onOpenConsole}
          className="w-full lg:w-auto inline-flex items-center justify-center gap-2 bg-[var(--torii-vermilion)] text-white hover:bg-[var(--torii-vermilion-hover)] text-xs font-extrabold uppercase tracking-wider px-6 py-3 rounded-full border-[2.5px] border-[#0d0d11] shadow-[3.5px_3.5px_0px_#0d0d11] active:translate-x-[2px] active:translate-y-[2px] active:shadow-[1px_1px_0px_#0d0d11] cursor-pointer transition-all whitespace-nowrap"
        >
          <span>Open Live SOC Console</span>
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
};
