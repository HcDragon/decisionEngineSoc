import React from 'react';
import { Shield, Lock, FileSearch, AlertOctagon, Terminal } from 'lucide-react';

interface SolutionsSectionProps {
  onOpenConsole: () => void;
}

export const SolutionsSection: React.FC<SolutionsSectionProps> = ({ onOpenConsole }) => {
  const solutions = [
    {
      icon: AlertOctagon,
      title: 'syn flood & ddos defense',
      desc: 'detects asymmetric packet ratios, half-open tcp socket flooding, and automated hping3 volumetric spikes before service degradation occurs.',
      tags: ['asymmetric ratio', 'pcap rate-rules', 'nft instant-drop'],
      badge: 'critical tier'
    },
    {
      icon: Lock,
      title: 'brute-force credential protection',
      desc: 'correlates burst login failures, dictionary sweeps, and automated hydra attacks across http/ssh endpoints with automatic source ip containment.',
      tags: ['frequency burst', 'fail2ban parity', 'virtual firewall'],
      badge: 'high tier'
    },
    {
      icon: FileSearch,
      title: 'reconnaissance & port scan evasion',
      desc: 'identifies horizontal network sweeps, syn stealth probes, and nmap host discovery before attackers can map internal service topologies.',
      tags: ['flow fan-out', 'port entropy', 'stealth detection'],
      badge: 'medium tier'
    },
    {
      icon: Shield,
      title: 'cryptographic audit & governance',
      desc: 'every automated decision, risk score, and firewall action is cryptographically hash-chained (sha-256) for auditability and compliance verification.',
      tags: ['tamper-proof', 'sha-256 chain', 'verifiable ledger'],
      badge: 'compliance ready'
    }
  ];

  return (
    <section id="solutions" className="relative w-full py-24 px-6 md:px-12 bg-transparent border-t border-white/10">
      <div className="max-w-7xl mx-auto">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-black/40 border border-white/10 backdrop-blur-xl text-xs text-neutral-300 font-mono tracking-wide uppercase mb-4">
            threat prevention solutions
          </div>
          <h2 className="text-3xl md:text-5xl font-medium tracking-tight text-white">
            protecting modern cloud workloads against active attack scenarios
          </h2>
          <p className="text-neutral-300/80 text-sm md:text-base mt-4">
            battle-tested in isolated network namespaces with realistic attack scenarios and zero-friction analyst control.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {solutions.map((s) => {
            const Icon = s.icon;
            return (
              <div
                key={s.title}
                className="bg-black/40 border border-white/10 backdrop-blur-2xl rounded-3xl p-8 hover:border-white/25 transition-all hover:bg-black/50 group shadow-[0_8px_32px_0_rgba(0,0,0,0.45)]"
              >
                <div className="flex items-center justify-between mb-6">
                  <div className="h-12 w-12 rounded-2xl bg-white/[0.08] border border-white/10 backdrop-blur-xl flex items-center justify-center text-white group-hover:scale-105 transition-transform">
                    <Icon className="h-6 w-6 text-neutral-200" />
                  </div>
                  <span className="text-[11px] font-mono uppercase px-3 py-1 rounded-full bg-white/[0.06] border border-white/10 text-neutral-300 backdrop-blur-md">
                    {s.badge}
                  </span>
                </div>

                <h3 className="text-xl font-medium text-white tracking-tight">
                  {s.title}
                </h3>
                <p className="text-neutral-300/80 text-sm mt-3 leading-relaxed">
                  {s.desc}
                </p>

                <div className="mt-6 pt-6 border-t border-white/10 flex flex-wrap gap-2">
                  {s.tags.map((t) => (
                    <span
                      key={t}
                      className="text-xs text-neutral-300 bg-white/[0.05] px-3 py-1 rounded-full border border-white/10 backdrop-blur-sm"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {/* Lab Demonstration Banner */}
        <div className="mt-12 bg-black/50 border border-white/10 backdrop-blur-2xl rounded-3xl p-8 flex flex-col md:flex-row items-center justify-between gap-6 shadow-[0_8px_32px_0_rgba(0,0,0,0.45)]">
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-2xl bg-white/10 border border-white/15 backdrop-blur-xl flex items-center justify-center text-white">
              <Terminal className="h-6 w-6" />
            </div>
            <div>
              <h4 className="text-white text-base font-medium">ready to run attack &amp; defence lab?</h4>
              <p className="text-neutral-300/80 text-xs mt-1">
                execute brute-force, syn-flood, or recon-scan inside isolated netns and verify automatic containment.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onOpenConsole}
            className="bg-white text-black text-xs font-semibold px-6 py-3 rounded-full hover:bg-neutral-200 transition-colors whitespace-nowrap cursor-pointer shadow-lg"
          >
            open soc operations console
          </button>
        </div>
      </div>
    </section>
  );
};
