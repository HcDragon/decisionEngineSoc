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
    <div className="w-full bg-white/[0.07] border-y border-white/15 backdrop-blur-2xl px-4 sm:px-8 py-5 shadow-[0_4px_24px_0_rgba(0,0,0,0.22)]">
      <div className="max-w-7xl mx-auto flex flex-col lg:flex-row items-center justify-between gap-6">
        {/* Status & Engine Info */}
        <div className="flex items-center gap-3">
          <div className="relative flex h-3 w-3">
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                isHealthy ? 'bg-emerald-400' : 'bg-amber-400'
              }`}
            />
            <span
              className={`relative inline-flex rounded-full h-3 w-3 ${
                isHealthy ? 'bg-emerald-500' : 'bg-amber-500'
              }`}
            />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-white text-sm font-semibold tracking-tight">
                autonomous soc telemetry
              </span>
              <span
                className={`text-[11px] px-2 py-0.5 rounded-full uppercase font-medium tracking-wide border backdrop-blur-md ${
                  isHealthy
                    ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300'
                    : 'bg-amber-500/20 border-amber-500/40 text-amber-300'
                }`}
              >
                {isHealthy ? 'live & active' : 'standby'}
              </span>
            </div>
            <p className="text-xs text-neutral-400 mt-0.5">
              nfstream hardware tap · port {trafficStats.monitored_port} · mode:{' '}
              <span className="text-neutral-200 uppercase">{automationMode}</span>
            </p>
          </div>
        </div>

        {/* Live Metrics Quick Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-6 w-full lg:w-auto">
          <div className="bg-white/[0.04] border border-white/10 backdrop-blur-xl rounded-xl px-3.5 py-2.5">
            <div className="text-[11px] text-neutral-400 flex items-center gap-1.5">
              <Activity className="h-3 w-3 text-cyan-400" /> throughput
            </div>
            <div className="text-white text-lg font-medium mt-0.5 tracking-tight">
              {trafficStats.current_packets_per_sec}{' '}
              <span className="text-xs text-neutral-400 font-normal ml-1">pkts/s</span>
            </div>
          </div>

          <div className="bg-white/[0.04] border border-white/10 backdrop-blur-xl rounded-xl px-3.5 py-2.5">
            <div className="text-[11px] text-neutral-400 flex items-center gap-1.5">
              <Radio className="h-3 w-3 text-emerald-400" /> total flows
            </div>
            <div className="text-white text-lg font-medium mt-0.5 tracking-tight">
              {trafficStats.total_flows.toLocaleString()}
            </div>
          </div>

          <div className="bg-white/[0.04] border border-white/10 backdrop-blur-xl rounded-xl px-3.5 py-2.5">
            <div className="text-[11px] text-neutral-400 flex items-center gap-1.5">
              <AlertTriangle className="h-3 w-3 text-rose-400" /> anomaly rate
            </div>
            <div className="text-white text-lg font-medium mt-0.5 tracking-tight">
              {threatPct}%
            </div>
          </div>

          <div className="bg-white/[0.04] border border-white/10 backdrop-blur-xl rounded-xl px-3.5 py-2.5">
            <div className="text-[11px] text-neutral-400 flex items-center gap-1.5">
              <ShieldCheck className="h-3 w-3 text-purple-400" /> active blocks
            </div>
            <div className="text-white text-lg font-medium mt-0.5 tracking-tight">
              {overview?.stats?.active_blocks ?? 0}
            </div>
          </div>
        </div>

        {/* CTA Launch into Console */}
        <button
          type="button"
          onClick={onOpenConsole}
          className="w-full lg:w-auto inline-flex items-center justify-center gap-2 bg-white text-black hover:bg-neutral-200 transition-colors text-xs font-semibold px-5 py-2.5 rounded-full cursor-pointer shadow-lg shadow-white/5 whitespace-nowrap"
        >
          <span>open live soc console</span>
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
};
