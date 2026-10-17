import React from 'react';
import { Shield, Lock, FileSearch, AlertOctagon } from 'lucide-react';

interface SolutionsSectionProps {
  onOpenConsole: () => void;
}

export const SolutionsSection: React.FC<SolutionsSectionProps> = ({ onOpenConsole }) => {
  const solutions = [
    {
      icon: AlertOctagon,
      title: 'SYN Flood & DDoS Defense',
      desc: 'Detects asymmetric packet ratios, half-open TCP socket flooding, and automated hping3 volumetric spikes before service degradation occurs.',
      tags: ['asymmetric ratio', 'pcap rate-rules', 'nft instant-drop'],
      badge: 'Critical Tier',
      badgeTone: 'bg-[var(--torii-vermilion)] text-white',
    },
    {
      icon: Lock,
      title: 'Brute-Force Credential Protection',
      desc: 'Correlates burst login failures, dictionary sweeps, and automated hydra attacks across HTTP/SSH endpoints with automatic source IP containment.',
      tags: ['frequency burst', 'fail2ban parity', 'virtual firewall'],
      badge: 'High Tier',
      badgeTone: 'bg-[var(--torii-amber)] text-[#0d0d11]',
    },
    {
      icon: FileSearch,
      title: 'Reconnaissance & Port Scan Evasion',
      desc: 'Identifies horizontal network sweeps, SYN stealth probes, and Nmap host discovery before attackers can map internal service topologies.',
      tags: ['flow fan-out', 'port entropy', 'stealth detection'],
      badge: 'Medium Tier',
      badgeTone: 'bg-[#faf6f0] text-[#0d0d11]',
    },
    {
      icon: Shield,
      title: 'Cryptographic Audit & Governance',
      desc: 'Every automated decision, risk score, and firewall action is cryptographically hash-chained (SHA-256) for auditability and compliance verification.',
      tags: ['tamper-proof', 'sha-256 chain', 'verifiable ledger'],
      badge: 'Compliance Ready',
      badgeTone: 'bg-[var(--torii-sage)] text-white',
    },
  ];

  return (
    <section id="solutions" className="relative w-full py-24 px-6 md:px-12 bg-transparent border-t-[3px] border-[#0d0d11]">
      <div className="max-w-7xl mx-auto">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[var(--torii-amber)] border-[2px] border-[#0d0d11] shadow-[2.5px_2.5px_0px_#0d0d11] text-xs text-[#0d0d11] font-mono font-bold tracking-wider uppercase mb-4">
            Threat Prevention Solutions
          </div>
          <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight uppercase text-white drop-shadow-[2px_2px_0px_#0d0d11]">
            Protecting Modern Cloud Workloads Against Active Attack Scenarios
          </h2>
          <p className="text-[#c5bebe] text-sm md:text-base mt-4 font-medium">
            Battle-tested in isolated network namespaces with realistic attack scenarios and zero-friction analyst control.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {solutions.map((s) => {
            const Icon = s.icon;
            return (
              <div
                key={s.title}
                className="bg-[rgba(26,21,24,0.94)] border-[2.5px] border-[#0d0d11] shadow-[5px_5px_0px_#0d0d11] rounded-3xl p-8 hover:-translate-y-1 hover:shadow-[7px_7px_0px_#0d0d11] transition-all group"
              >
                <div className="flex items-center justify-between mb-6">
                  <div className="h-12 w-12 rounded-2xl bg-[#faf6f0] border-[2px] border-[#0d0d11] shadow-[2.5px_2.5px_0px_#0d0d11] flex items-center justify-center text-[#0d0d11] group-hover:scale-105 transition-transform">
                    <Icon className="h-6 w-6 text-[var(--torii-vermilion)]" />
                  </div>
                  <span className={`text-[11px] font-mono font-bold uppercase tracking-wider px-3 py-1 rounded-md border-[1.5px] border-[#0d0d11] shadow-[2px_2px_0px_#0d0d11] ${s.badgeTone}`}>
                    {s.badge}
                  </span>
                </div>

                <h3 className="text-xl font-bold text-white tracking-tight uppercase">
                  {s.title}
                </h3>
                <p className="text-[#c5bebe] text-sm mt-3 leading-relaxed font-medium">
                  {s.desc}
                </p>

                <div className="mt-6 pt-6 border-t-[2px] border-[#0d0d11] flex flex-wrap gap-2">
                  {s.tags.map((t) => (
                    <span
                      key={t}
                      className="text-[11px] font-mono font-bold uppercase tracking-wider px-3 py-1 rounded-md bg-[#faf6f0] border-[1.5px] border-[#0d0d11] shadow-[1.5px_1.5px_0px_#0d0d11] text-[#0d0d11]"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
