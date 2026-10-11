import React from 'react';
import { Cpu, ShieldCheck, Zap, Network, Terminal, Sliders, ArrowUpRight } from 'lucide-react';

interface PlatformBentoProps {
  onOpenConsole: () => void;
}

export const PlatformBento: React.FC<PlatformBentoProps> = ({ onOpenConsole }) => {
  return (
    <section id="platform" className="relative w-full py-24 px-6 md:px-12 bg-transparent border-t border-white/10">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-16 gap-6">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-black/40 border border-white/10 backdrop-blur-xl text-xs text-neutral-300 font-mono tracking-wide uppercase mb-4">
              <Zap className="h-3.5 w-3.5 text-cyan-400" />
              platform architecture
            </div>
            <h2 className="text-3xl md:text-5xl font-medium tracking-tight text-white max-w-2xl">
              autonomous decision engine powered by live nfstream + ml
            </h2>
          </div>
          <p className="text-neutral-400 text-sm md:text-base max-w-md">
            continuous hardware-level flow metering, multi-class model inference, and instant automated response.
          </p>
        </div>

        {/* Bento Grid Layout (Tailwind Pattern) */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-12 gap-6">
          {/* Card 1: 57-Feature NFStream DPI (Large Bento item: 7 cols) */}
          <div className="lg:col-span-7 bg-black/40 backdrop-blur-2xl border border-white/10 rounded-3xl p-8 flex flex-col justify-between hover:border-cyan-400/50 hover:bg-black/50 transition-all group relative overflow-hidden shadow-[0_8px_32px_0_rgba(0,0,0,0.45)]">
            <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity">
              <Network className="w-48 h-48 text-white" />
            </div>

            <div>
              <div className="h-10 w-10 rounded-2xl bg-white/[0.08] border border-white/10 backdrop-blur-xl flex items-center justify-center text-cyan-400 mb-6">
                <Network className="h-5 w-5" />
              </div>
              <span className="text-xs font-mono uppercase tracking-wider text-cyan-400 font-medium">
                telemetry ingestion
              </span>
              <h3 className="text-2xl font-medium text-white tracking-tight mt-2">
                57-feature nfstream deep flow metering
              </h3>
              <p className="text-neutral-300/80 text-sm mt-3 leading-relaxed max-w-xl">
                bypasses synthetic tap blindspots by extracting bidirectional packet timings, inter-arrival distributions (PIAT), and TCP window variations live from raw sockets.
              </p>
            </div>

            <div className="mt-8 pt-6 border-t border-white/10 grid grid-cols-3 gap-4">
              <div>
                <div className="text-xs text-neutral-400 font-mono uppercase">features</div>
                <div className="text-lg font-semibold text-white mt-1">57 observable</div>
              </div>
              <div>
                <div className="text-xs text-neutral-400 font-mono uppercase">capture mode</div>
                <div className="text-lg font-semibold text-white mt-1">live socket tap</div>
              </div>
              <div>
                <div className="text-xs text-neutral-400 font-mono uppercase">latency</div>
                <div className="text-lg font-semibold text-white mt-1">&lt; 0.8 ms</div>
              </div>
            </div>
          </div>

          {/* Card 2: Multi-Class ML Inference (5 cols) */}
          <div className="lg:col-span-5 bg-black/40 backdrop-blur-2xl border border-white/10 rounded-3xl p-8 flex flex-col justify-between hover:border-emerald-400/50 hover:bg-black/50 transition-all group shadow-[0_8px_32px_0_rgba(0,0,0,0.45)]">
            <div>
              <div className="h-10 w-10 rounded-2xl bg-white/[0.08] border border-white/10 backdrop-blur-xl flex items-center justify-center text-emerald-400 mb-6">
                <Cpu className="h-5 w-5" />
              </div>
              <span className="text-xs font-mono uppercase tracking-wider text-emerald-400 font-medium">
                supervised learning
              </span>
              <h3 className="text-2xl font-medium text-white tracking-tight mt-2">
                99.8% precision attack classifier
              </h3>
              <p className="text-neutral-300/80 text-sm mt-3 leading-relaxed">
                trained on modern real attack distributions with probability outputs, confidence margins, and zero-day heuristic fallbacks.
              </p>
            </div>

            <div className="mt-6 space-y-2.5">
              {[
                { name: 'SYN Flood', acc: '99.9%' },
                { name: 'Brute Force', acc: '99.7%' },
                { name: 'Recon Scan', acc: '99.8%' },
              ].map((item) => (
                <div key={item.name} className="flex items-center justify-between text-xs bg-white/[0.05] rounded-xl px-4 py-2.5 border border-white/10 backdrop-blur-md">
                  <span className="text-neutral-200 font-medium">{item.name}</span>
                  <span className="text-emerald-400 font-mono">{item.acc} macro-f1</span>
                </div>
              ))}
            </div>
          </div>

          {/* Card 3: Autonomous Decision Pipeline (4 cols) */}
          <div className="lg:col-span-4 bg-black/40 backdrop-blur-2xl border border-white/10 rounded-3xl p-8 flex flex-col justify-between hover:border-purple-400/50 hover:bg-black/50 transition-all shadow-[0_8px_32px_0_rgba(0,0,0,0.45)]">
            <div>
              <div className="h-10 w-10 rounded-2xl bg-white/[0.08] border border-white/10 backdrop-blur-xl flex items-center justify-center text-purple-400 mb-6">
                <Sliders className="h-5 w-5" />
              </div>
              <span className="text-xs font-mono uppercase tracking-wider text-purple-400 font-medium">
                decision engine
              </span>
              <h3 className="text-xl font-medium text-white tracking-tight mt-2">
                policy guardrails &amp; risk scoring
              </h3>
              <p className="text-neutral-300/80 text-sm mt-3 leading-relaxed">
                every alert traverses a 7-stage gate (classify → gate → score → correlate → rule → persist → apply) with strict safety bounds.
              </p>
            </div>

            <div className="mt-6 flex flex-wrap gap-2">
              <span className="text-[11px] px-2.5 py-1 rounded-full bg-white/[0.05] border border-white/10 text-neutral-300 backdrop-blur-md">
                min_margin 0.35
              </span>
              <span className="text-[11px] px-2.5 py-1 rounded-full bg-white/[0.05] border border-white/10 text-neutral-300 backdrop-blur-md">
                rate-limit tiering
              </span>
              <span className="text-[11px] px-2.5 py-1 rounded-full bg-white/[0.05] border border-white/10 text-neutral-300 backdrop-blur-md">
                crypto audit-chain
              </span>
            </div>
          </div>

          {/* Card 4: Kernel nft Containment (4 cols) */}
          <div className="lg:col-span-4 bg-black/40 backdrop-blur-2xl border border-white/10 rounded-3xl p-8 flex flex-col justify-between hover:border-rose-400/50 hover:bg-black/50 transition-all shadow-[0_8px_32px_0_rgba(0,0,0,0.45)]">
            <div>
              <div className="h-10 w-10 rounded-2xl bg-white/[0.08] border border-white/10 backdrop-blur-xl flex items-center justify-center text-rose-400 mb-6">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <span className="text-xs font-mono uppercase tracking-wider text-rose-400 font-medium">
                firewall execution
              </span>
              <h3 className="text-xl font-medium text-white tracking-tight mt-2">
                kernel-level nft drop &amp; auto-reaper
              </h3>
              <p className="text-neutral-300/80 text-sm mt-3 leading-relaxed">
                executes real kernel-space drops or virtual firewall simulations with automated TTL recovery to prevent self-lockouts.
              </p>
            </div>

            <div className="mt-6 pt-4 border-t border-white/10 flex items-center justify-between">
              <span className="text-xs text-neutral-400">automated ttl expiry</span>
              <span className="text-xs font-mono text-rose-400 bg-rose-500/15 px-2.5 py-1 rounded-full border border-rose-500/30 backdrop-blur-md">
                120s auto-reap
              </span>
            </div>
          </div>

          {/* Card 5: Direct Interactive Console Launcher (4 cols) */}
          <div className="lg:col-span-4 bg-gradient-to-br from-white/10 via-black/40 to-black/60 backdrop-blur-2xl border border-white/20 rounded-3xl p-8 flex flex-col justify-between hover:border-white/50 transition-all cursor-pointer group shadow-[0_8px_32px_0_rgba(0,0,0,0.45)]" onClick={onOpenConsole}>
            <div>
              <div className="h-10 w-10 rounded-2xl bg-white text-black flex items-center justify-center mb-6 shadow-md">
                <Terminal className="h-5 w-5" />
              </div>
              <span className="text-xs font-mono uppercase tracking-wider text-neutral-300 font-medium">
                live operations
              </span>
              <h3 className="text-xl font-medium text-white tracking-tight mt-2 flex items-center gap-2">
                enter smart soc console
                <ArrowUpRight className="h-4 w-4 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
              </h3>
              <p className="text-neutral-300/80 text-sm mt-3 leading-relaxed">
                inspect active threat incidents, drill down into ML probability vectors, and toggle automatic vs manual defense mode.
              </p>
            </div>

            <div className="mt-6">
              <button
                type="button"
                className="w-full bg-white text-black text-xs font-medium py-3 rounded-full hover:bg-neutral-200 transition-colors shadow-lg"
              >
                launch operational console
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
