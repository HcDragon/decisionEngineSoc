import React from 'react';
import { Cpu, ShieldCheck, Zap, Network, Terminal, Sliders, ArrowUpRight } from 'lucide-react';

interface PlatformBentoProps {
  onOpenConsole: () => void;
}

export const PlatformBento: React.FC<PlatformBentoProps> = ({ onOpenConsole }) => {
  return (
    <section id="platform" className="relative w-full py-24 px-6 md:px-12 bg-transparent border-t-[3px] border-[#0d0d11]">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-16 gap-6">
          <div>
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[var(--torii-amber)] border-[2px] border-[#0d0d11] shadow-[2.5px_2.5px_0px_#0d0d11] text-xs text-[#0d0d11] font-mono font-bold tracking-wider uppercase mb-4">
              <Zap className="h-3.5 w-3.5 text-[#0d0d11]" />
              Platform Architecture
            </div>
            <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight uppercase text-white max-w-2xl drop-shadow-[2px_2px_0px_#0d0d11]">
              Autonomous Decision Engine Powered By Live NFStream + ML
            </h2>
          </div>
          <p className="text-[#c5bebe] text-sm md:text-base max-w-md font-medium leading-relaxed">
            Continuous hardware-level flow metering, multi-class model inference, and instant automated response.
          </p>
        </div>

        {/* Bento Grid Layout (Neobrutalism Pattern) */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-12 gap-6">
          {/* Card 1: 57-Feature NFStream DPI (Large Bento item: 7 cols) */}
          <div className="lg:col-span-7 bg-[rgba(26,21,24,0.94)] border-[2.5px] border-[#0d0d11] shadow-[5px_5px_0px_#0d0d11] rounded-3xl p-8 flex flex-col justify-between hover:-translate-y-1 hover:shadow-[7px_7px_0px_#0d0d11] transition-all group relative overflow-hidden">
            <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-15 transition-opacity pointer-events-none">
              <Network className="w-48 h-48 text-white" />
            </div>

            <div>
              <div className="h-11 w-11 rounded-2xl bg-[#faf6f0] border-[2px] border-[#0d0d11] shadow-[2.5px_2.5px_0px_#0d0d11] flex items-center justify-center text-[#0d0d11] mb-6">
                <Network className="h-5 w-5 text-[var(--torii-vermilion)]" />
              </div>
              <span className="text-xs font-mono uppercase tracking-wider text-[var(--torii-amber)] font-bold">
                Telemetry Ingestion
              </span>
              <h3 className="text-2xl font-bold text-white tracking-tight mt-2 uppercase">
                57-Feature NFStream Deep Flow Metering
              </h3>
              <p className="text-[#c5bebe] text-sm mt-3 leading-relaxed max-w-xl font-medium">
                Bypasses synthetic tap blindspots by extracting bidirectional packet timings, inter-arrival distributions (PIAT), and TCP window variations live from raw sockets.
              </p>
            </div>

            <div className="mt-8 pt-6 border-t-[2px] border-[#0d0d11] grid grid-cols-3 gap-3">
              <div className="bg-[#faf6f0] text-[#0d0d11] border-[2px] border-[#0d0d11] shadow-[2.5px_2.5px_0px_#0d0d11] rounded-xl p-3">
                <div className="text-[10px] text-[#544d49] font-mono font-bold uppercase">Features</div>
                <div className="text-base font-extrabold font-mono text-[#0d0d11] mt-0.5">57 Observable</div>
              </div>
              <div className="bg-[#faf6f0] text-[#0d0d11] border-[2px] border-[#0d0d11] shadow-[2.5px_2.5px_0px_#0d0d11] rounded-xl p-3">
                <div className="text-[10px] text-[#544d49] font-mono font-bold uppercase">Capture Mode</div>
                <div className="text-base font-extrabold font-mono text-[#0d0d11] mt-0.5">Socket Tap</div>
              </div>
              <div className="bg-[#faf6f0] text-[#0d0d11] border-[2px] border-[#0d0d11] shadow-[2.5px_2.5px_0px_#0d0d11] rounded-xl p-3">
                <div className="text-[10px] text-[#544d49] font-mono font-bold uppercase">Latency</div>
                <div className="text-base font-extrabold font-mono text-[var(--torii-vermilion)] mt-0.5">&lt; 0.8 ms</div>
              </div>
            </div>
          </div>

          {/* Card 2: Multi-Class ML Inference (5 cols) */}
          <div className="lg:col-span-5 bg-[rgba(26,21,24,0.94)] border-[2.5px] border-[#0d0d11] shadow-[5px_5px_0px_#0d0d11] rounded-3xl p-8 flex flex-col justify-between hover:-translate-y-1 hover:shadow-[7px_7px_0px_#0d0d11] transition-all group">
            <div>
              <div className="h-11 w-11 rounded-2xl bg-[#faf6f0] border-[2px] border-[#0d0d11] shadow-[2.5px_2.5px_0px_#0d0d11] flex items-center justify-center text-[#0d0d11] mb-6">
                <Cpu className="h-5 w-5 text-[var(--torii-sage)]" />
              </div>
              <span className="text-xs font-mono uppercase tracking-wider text-[var(--torii-sage)] font-bold">
                Supervised Learning
              </span>
              <h3 className="text-2xl font-bold text-white tracking-tight mt-2 uppercase">
                99.8% Precision Attack Classifier
              </h3>
              <p className="text-[#c5bebe] text-sm mt-3 leading-relaxed font-medium">
                Trained on modern real attack distributions with probability outputs, confidence margins, and zero-day heuristic fallbacks.
              </p>
            </div>

            <div className="mt-6 space-y-2.5">
              {[
                { name: 'SYN Flood', acc: '99.9%' },
                { name: 'Brute Force', acc: '99.7%' },
                { name: 'Recon Scan', acc: '99.8%' },
              ].map((item) => (
                <div key={item.name} className="flex items-center justify-between text-xs bg-[#faf6f0] text-[#0d0d11] rounded-xl px-4 py-2.5 border-[2px] border-[#0d0d11] shadow-[2px_2px_0px_#0d0d11]">
                  <span className="font-bold uppercase tracking-wide">{item.name}</span>
                  <span className="text-[var(--torii-sage)] font-mono font-extrabold">{item.acc} Macro-F1</span>
                </div>
              ))}
            </div>
          </div>

          {/* Card 3: Autonomous Decision Pipeline (4 cols) */}
          <div className="lg:col-span-4 bg-[rgba(26,21,24,0.94)] border-[2.5px] border-[#0d0d11] shadow-[5px_5px_0px_#0d0d11] rounded-3xl p-8 flex flex-col justify-between hover:-translate-y-1 hover:shadow-[7px_7px_0px_#0d0d11] transition-all">
            <div>
              <div className="h-11 w-11 rounded-2xl bg-[#faf6f0] border-[2px] border-[#0d0d11] shadow-[2.5px_2.5px_0px_#0d0d11] flex items-center justify-center text-[#0d0d11] mb-6">
                <Sliders className="h-5 w-5 text-[var(--torii-amber)]" />
              </div>
              <span className="text-xs font-mono uppercase tracking-wider text-[var(--torii-amber)] font-bold">
                Decision Engine
              </span>
              <h3 className="text-xl font-bold text-white tracking-tight mt-2 uppercase">
                Policy Guardrails &amp; Risk Scoring
              </h3>
              <p className="text-[#c5bebe] text-sm mt-3 leading-relaxed font-medium">
                Every alert traverses a 7-stage gate (classify → gate → score → correlate → rule → persist → apply) with strict safety bounds.
              </p>
            </div>

            <div className="mt-6 flex flex-wrap gap-2">
              <span className="text-[11px] px-3 py-1 rounded-md bg-[#faf6f0] border-[1.5px] border-[#0d0d11] shadow-[1.5px_1.5px_0px_#0d0d11] text-[#0d0d11] font-mono font-bold uppercase">
                min_margin 0.35
              </span>
              <span className="text-[11px] px-3 py-1 rounded-md bg-[#faf6f0] border-[1.5px] border-[#0d0d11] shadow-[1.5px_1.5px_0px_#0d0d11] text-[#0d0d11] font-mono font-bold uppercase">
                rate-limit tiering
              </span>
              <span className="text-[11px] px-3 py-1 rounded-md bg-[#faf6f0] border-[1.5px] border-[#0d0d11] shadow-[1.5px_1.5px_0px_#0d0d11] text-[#0d0d11] font-mono font-bold uppercase">
                crypto audit-chain
              </span>
            </div>
          </div>

          {/* Card 4: Kernel nft Containment (4 cols) */}
          <div className="lg:col-span-4 bg-[rgba(26,21,24,0.94)] border-[2.5px] border-[#0d0d11] shadow-[5px_5px_0px_#0d0d11] rounded-3xl p-8 flex flex-col justify-between hover:-translate-y-1 hover:shadow-[7px_7px_0px_#0d0d11] transition-all">
            <div>
              <div className="h-11 w-11 rounded-2xl bg-[#faf6f0] border-[2px] border-[#0d0d11] shadow-[2.5px_2.5px_0px_#0d0d11] flex items-center justify-center text-[#0d0d11] mb-6">
                <ShieldCheck className="h-5 w-5 text-[var(--torii-vermilion)]" />
              </div>
              <span className="text-xs font-mono uppercase tracking-wider text-[var(--torii-vermilion)] font-bold">
                Firewall Execution
              </span>
              <h3 className="text-xl font-bold text-white tracking-tight mt-2 uppercase">
                Kernel-Level NFT Drop &amp; Auto-Reaper
              </h3>
              <p className="text-[#c5bebe] text-sm mt-3 leading-relaxed font-medium">
                Executes real kernel-space drops or virtual firewall simulations with automated TTL recovery to prevent self-lockouts.
              </p>
            </div>

            <div className="mt-6 pt-4 border-t-[2px] border-[#0d0d11] flex items-center justify-between">
              <span className="text-xs font-bold text-[#c5bebe] uppercase font-mono">Automated TTL Expiry</span>
              <span className="text-xs font-mono font-bold text-white bg-[var(--torii-vermilion)] px-3 py-1 rounded-md border-[1.5px] border-[#0d0d11] shadow-[2px_2px_0px_#0d0d11]">
                120s Auto-Reap
              </span>
            </div>
          </div>

          {/* Card 5: Direct Interactive Console Launcher (4 cols) */}
          <div
            className="lg:col-span-4 bg-[#faf6f0] text-[#0d0d11] border-[2.5px] border-[#0d0d11] shadow-[5px_5px_0px_#0d0d11] rounded-3xl p-8 flex flex-col justify-between hover:-translate-y-1 hover:shadow-[7px_7px_0px_#0d0d11] transition-all cursor-pointer group"
            onClick={onOpenConsole}
          >
            <div>
              <div className="h-11 w-11 rounded-2xl bg-[var(--torii-vermilion)] text-white border-[2px] border-[#0d0d11] shadow-[2.5px_2.5px_0px_#0d0d11] flex items-center justify-center mb-6">
                <Terminal className="h-5 w-5" />
              </div>
              <span className="text-xs font-mono uppercase tracking-wider text-[#544d49] font-bold">
                Live Operations
              </span>
              <h3 className="text-xl font-extrabold text-[#0d0d11] tracking-tight mt-2 flex items-center gap-2 uppercase">
                Enter Smart SOC Console
                <ArrowUpRight className="h-5 w-5 group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
              </h3>
              <p className="text-[#544d49] text-sm mt-3 leading-relaxed font-medium">
                Inspect active threat incidents, drill down into ML probability vectors, and toggle automatic vs manual defense mode.
              </p>
            </div>

            <div className="mt-6">
              <button
                type="button"
                className="w-full bg-[var(--torii-vermilion)] text-white text-xs font-extrabold uppercase tracking-wider py-3.5 rounded-full border-[2px] border-[#0d0d11] shadow-[3px_3px_0px_#0d0d11] active:translate-x-[2px] active:translate-y-[2px] active:shadow-[1px_1px_0px_#0d0d11] hover:bg-[var(--torii-vermilion-hover)] transition-all cursor-pointer"
              >
                Launch Console View →
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
