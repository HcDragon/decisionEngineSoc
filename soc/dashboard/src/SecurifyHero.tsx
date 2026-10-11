import React, { useEffect, useState } from 'react';

interface SecurifyHeroProps {
  onGetStarted?: () => void;
  onOpenConsole?: () => void;
}

export const SecurifyHero: React.FC<SecurifyHeroProps> = ({
  onGetStarted,
  onOpenConsole,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [counts, setCounts] = useState({
    inference: 0,
    uptime: 0,
    runtime: 0,
    context: 0,
  });
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);
    const startCount = (target: number, duration: number, delay: number, callback: (val: number) => void) => {
      setTimeout(() => {
        let startTime: number | null = null;
        function step(time: number) {
          if (!startTime) startTime = time;
          const elapsed = time - startTime;
          const progress = Math.min(elapsed / duration, 1);
          const current = easeOutCubic(progress) * target;
          callback(current);
          if (progress < 1) requestAnimationFrame(step);
          else callback(target);
        }
        requestAnimationFrame(step);
      }, delay);
    };

    startCount(120, 1500, 480, (v) => setCounts((c) => ({ ...c, inference: Math.round(v) })));
    startCount(99.99, 1580, 570, (v) => setCounts((c) => ({ ...c, uptime: parseFloat(v.toFixed(2)) })));
    startCount(24, 1660, 660, (v) => setCounts((c) => ({ ...c, runtime: Math.round(v) })));
    startCount(2.4, 1740, 750, (v) => setCounts((c) => ({ ...c, context: parseFloat(v.toFixed(1)) })));
  }, []);

  return (
    <section
      className="relative h-screen w-full flex flex-col justify-between items-center px-4 sm:px-8 py-5 select-none font-sans overflow-hidden"
      style={{ color: '#f0ede8' }}
    >
      {/* No local bg — the global fixed image in App.jsx shows through */}

      {/* ── 1) Navigation Header ── */}
      <header
        className={`relative z-20 w-full max-w-[740px] flex items-center justify-between md:justify-center gap-5 sm:gap-7 shrink-0 transition-all duration-500`}
        style={{ animation: 'slideDown 0.7s cubic-bezier(0.22,1,0.36,1) both' }}
      >
        {/* Logo */}
        <button
          type="button"
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          className="w-10 h-10 md:w-11 md:h-11 rounded-full flex items-center justify-center shrink-0 cursor-pointer border-none hover:scale-[1.04] transition-transform"
          style={{
            background: 'rgba(255,255,255,0.15)',
            backdropFilter: 'blur(12px)',
            border: '1px solid rgba(255,255,255,0.25)',
            boxShadow: '0 4px 20px rgba(0,0,0,0.25)',
          }}
          aria-label="Roshomon Home"
        >
          <img src="/assets/logo.webp" alt="" width="44" height="44" className="w-[68%] h-[68%] object-contain" />
        </button>

        {/* Desktop Nav pill — frosted glass, warm tone */}
        <nav
          className="hidden md:flex items-center justify-around h-11 md:h-12 max-w-[460px] flex-1 px-2 rounded-full"
          style={{
            background: 'rgba(255,255,255,0.12)',
            backdropFilter: 'blur(18px)',
            border: '1px solid rgba(255,255,255,0.22)',
            boxShadow: '0 4px 20px rgba(0,0,0,0.22)',
          }}
        >
          <a
            href="#"
            className="relative font-medium text-[14px] px-3.5 h-full flex items-center justify-center transition-colors"
            style={{ color: '#f0ede8' }}
          >
            Home
            <span
              className="absolute bottom-[6px] left-1/2 -translate-x-1/2 w-[18px] h-[2px] rounded-full"
              style={{ background: '#e8a07a' }}
            />
          </a>
          <button
            type="button"
            onClick={onOpenConsole}
            className="font-medium text-[14px] px-3.5 h-full flex items-center justify-center cursor-pointer border-none bg-transparent transition-opacity hover:opacity-100"
            style={{ color: 'rgba(240,237,232,0.6)' }}
          >
            Console
          </button>
          <a
            href="#platform"
            className="font-medium text-[14px] px-3.5 h-full flex items-center justify-center transition-opacity hover:opacity-100"
            style={{ color: 'rgba(240,237,232,0.6)' }}
          >
            Platform
          </a>
          <a
            href="#solutions"
            className="font-medium text-[14px] px-3.5 h-full flex items-center justify-center transition-opacity hover:opacity-100"
            style={{ color: 'rgba(240,237,232,0.6)' }}
          >
            Solutions
          </a>
        </nav>

        {/* Desktop CTA button */}
        <button
          type="button"
          onClick={onOpenConsole}
          className="hidden md:inline-flex items-center justify-center h-11 md:h-12 px-5 rounded-full text-[14px] font-medium transition-all hover:-translate-y-0.5 cursor-pointer shrink-0 border-none"
          style={{
            background: 'rgba(232,160,122,0.9)',
            color: '#1a1819',
            boxShadow: '0 4px 20px rgba(232,160,122,0.4)',
          }}
        >
          Open Console
        </button>

        {/* Mobile burger */}
        <button
          type="button"
          onClick={() => setMobileMenuOpen((o) => !o)}
          className="md:hidden w-12 h-12 rounded-full flex flex-col items-center justify-center gap-1.5 cursor-pointer z-40 transition-colors border-none"
          style={{
            background: 'rgba(255,255,255,0.12)',
            backdropFilter: 'blur(12px)',
            border: '1px solid rgba(255,255,255,0.2)',
          }}
          aria-expanded={mobileMenuOpen}
          aria-label="Toggle navigation menu"
        >
          <span className={`w-[18px] h-[1.5px] rounded-full transition-transform ${mobileMenuOpen ? 'translate-y-[7.5px] rotate-45' : ''}`} style={{ background: '#f0ede8' }} />
          <span className={`w-[18px] h-[1.5px] rounded-full transition-opacity ${mobileMenuOpen ? 'opacity-0' : ''}`} style={{ background: '#f0ede8' }} />
          <span className={`w-[18px] h-[1.5px] rounded-full transition-transform ${mobileMenuOpen ? '-translate-y-[7.5px] -rotate-45' : ''}`} style={{ background: '#f0ede8' }} />
        </button>
      </header>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <>
          <div
            className="fixed inset-0 z-30 md:hidden"
            style={{ background: 'rgba(20,18,22,0.6)', backdropFilter: 'blur(4px)' }}
            onClick={() => setMobileMenuOpen(false)}
          />
          <div
            className="fixed top-20 left-1/2 -translate-x-1/2 w-[calc(100%-32px)] max-w-[420px] rounded-[28px] p-6 shadow-2xl z-35 flex flex-col items-center gap-3 md:hidden"
            style={{
              background: 'rgba(240,237,232,0.95)',
              backdropFilter: 'blur(20px)',
              color: '#2e2e2e',
              animation: 'menuIn 0.38s cubic-bezier(0.22,1,0.36,1) both',
            }}
          >
            <a href="#" onClick={() => setMobileMenuOpen(false)} className="w-full text-center py-2.5 font-medium text-[16px]" style={{ color: '#2e2e2e' }}>
              Home
            </a>
            <button type="button" onClick={() => { setMobileMenuOpen(false); onOpenConsole?.(); }} className="w-full text-center py-2.5 font-medium text-[16px] bg-transparent border-none cursor-pointer" style={{ color: '#2e2e2e' }}>
              Console
            </button>
            <a href="#platform" onClick={() => setMobileMenuOpen(false)} className="w-full text-center py-2.5 font-medium text-[16px]" style={{ color: '#2e2e2e' }}>
              Platform
            </a>
            <a href="#solutions" onClick={() => setMobileMenuOpen(false)} className="w-full text-center py-2.5 font-medium text-[16px]" style={{ color: '#2e2e2e' }}>
              Solutions
            </a>
            <button type="button" onClick={() => { setMobileMenuOpen(false); onOpenConsole?.(); }} className="w-full mt-2 py-3.5 rounded-full font-medium text-[15px] cursor-pointer border-none" style={{ background: '#1a1819', color: '#f0ede8' }}>
              Open Console
            </button>
          </div>
        </>
      )}

      {/* ── 2) Hero Center ── */}
      <div className="relative z-10 flex flex-col items-center justify-center text-center max-w-[860px] w-full my-auto">

        {/* Brand badge */}
        <div
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full mb-6 text-[12px] font-mono tracking-widest uppercase"
          style={{
            background: 'rgba(255,255,255,0.1)',
            backdropFilter: 'blur(12px)',
            border: '1px solid rgba(232,160,122,0.45)',
            color: '#e8a07a',
            animation: 'reveal 0.85s cubic-bezier(0.22,1,0.36,1) both',
            animationDelay: '0.05s',
          }}
        >
          <span
            className="h-1.5 w-1.5 rounded-full animate-pulse"
            style={{ background: '#e8a07a' }}
          />
          Autonomous SOC · AI Decision Engine
        </div>

        {/* Main headline */}
        <h1
          className="font-['Readex_Pro',sans-serif] font-bold text-[44px] sm:text-[62px] md:text-[80px] lg:text-[88px] leading-[1.0] sm:leading-[1.05] tracking-[-0.05em] uppercase m-0"
          style={{ color: '#f5f0eb' }}
        >
          <span
            className="block opacity-0 translate-y-4"
            style={{ animation: 'headlineFade 0.9s cubic-bezier(0.22,1,0.36,1) forwards', animationDelay: '0.12s' }}
          >
            Roshomon
          </span>
          <span
            className="block text-[28px] sm:text-[36px] md:text-[42px] lg:text-[46px] opacity-0 translate-y-4 tracking-[-0.02em]"
            style={{
              animation: 'headlineFade 0.9s cubic-bezier(0.22,1,0.36,1) forwards',
              animationDelay: '0.3s',
              fontFamily: 'Inter, system-ui, sans-serif',
              fontWeight: 300,
              letterSpacing: '-0.02em',
              color: 'rgba(240,237,232,0.75)',
            }}
          >
            Intelligence Designed To Evolve
          </span>
        </h1>

        {/* Divider line */}
        <div
          className="w-16 h-px my-6"
          style={{
            background: 'linear-gradient(to right, transparent, #e8a07a, transparent)',
            opacity: 0.8,
            animation: 'reveal 1s cubic-bezier(0.22,1,0.36,1) both',
            animationDelay: '0.42s',
          }}
        />

        {/* Subhead */}
        <p
          className="max-w-[480px] w-[92%] text-[15px] sm:text-[17px] leading-[1.65] font-light opacity-0"
          style={{
            color: 'rgba(240,237,232,0.78)',
            animation: 'reveal 0.85s cubic-bezier(0.22,1,0.36,1) forwards',
            animationDelay: '0.38s',
            marginBottom: '2rem',
          }}
        >
          Live NFStream telemetry, multi-class ML inference, and autonomous containment — all in a single decision loop.
        </p>

        {/* CTA buttons */}
        <div
          className="flex items-center gap-3 flex-wrap justify-center opacity-0"
          style={{ animation: 'reveal 0.85s cubic-bezier(0.22,1,0.36,1) forwards', animationDelay: '0.5s' }}
        >
          <button
            type="button"
            onClick={onGetStarted || onOpenConsole}
            className="inline-flex items-center justify-center px-7 py-3.5 rounded-full font-semibold text-[14.5px] cursor-pointer border-none transition-all hover:-translate-y-0.5 hover:scale-[1.02]"
            style={{
              background: '#e8a07a',
              color: '#1a1819',
              boxShadow: '0 0 0 1px rgba(232,160,122,0.5), 0 8px 32px rgba(232,160,122,0.35)',
            }}
          >
            Open SOC Console
          </button>
          <a
            href="#platform"
            className="inline-flex items-center justify-center px-7 py-3.5 rounded-full font-medium text-[14.5px] transition-all hover:-translate-y-0.5"
            style={{
              background: 'rgba(255,255,255,0.1)',
              backdropFilter: 'blur(12px)',
              border: '1px solid rgba(255,255,255,0.25)',
              color: '#f0ede8',
            }}
          >
            Explore Platform
          </a>
        </div>
      </div>

      {/* ── 3) Stats Footer ── */}
      <footer
        className="relative z-10 w-full max-w-[900px] grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6 shrink-0 text-center"
        style={{
          borderTop: '1px solid rgba(255,255,255,0.12)',
          paddingTop: '1.25rem',
          background: 'rgba(20,18,22,0.18)',
          backdropFilter: 'blur(8px)',
          borderRadius: '16px',
          padding: '1.25rem 1.5rem',
          animation: 'reveal 0.85s cubic-bezier(0.22,1,0.36,1) both',
          animationDelay: '0.55s',
        }}
      >
        {/* Stat 1 */}
        <div className="flex flex-col items-center">
          <div className="flex items-baseline justify-center gap-1">
            <span
              className="font-['JetBrains_Mono',monospace] text-[22px] sm:text-[28px] leading-none"
              style={{ color: '#e8a07a' }}
            >
              &lt;
            </span>
            <span className="font-mono font-medium text-[18px] sm:text-[22px] tracking-[-0.02em] leading-none" style={{ color: '#f0ede8' }}>
              {counts.inference}ms
            </span>
          </div>
          <span className="text-[11px] sm:text-[12px] mt-1.5" style={{ color: 'rgba(240,237,232,0.5)' }}>
            Inference Time
          </span>
        </div>

        {/* Stat 2 */}
        <div className="flex flex-col items-center">
          <div className="flex items-baseline justify-center gap-1">
            <span className="font-mono font-medium text-[18px] sm:text-[22px] tracking-[-0.02em] leading-none" style={{ color: '#f0ede8' }}>
              {counts.uptime.toFixed(2)}%
            </span>
          </div>
          <span className="text-[11px] sm:text-[12px] mt-1.5" style={{ color: 'rgba(240,237,232,0.5)' }}>
            Platform Uptime
          </span>
        </div>

        {/* Stat 3 */}
        <div className="flex flex-col items-center">
          <div className="flex items-baseline justify-center gap-1">
            <span
              className="font-['JetBrains_Mono',monospace] text-[22px] sm:text-[28px] leading-none"
              style={{ color: '#e8a07a' }}
            >
              *
            </span>
            <span className="font-mono font-medium text-[18px] sm:text-[22px] tracking-[-0.02em] leading-none" style={{ color: '#f0ede8' }}>
              {counts.runtime}/7
            </span>
          </div>
          <span className="text-[11px] sm:text-[12px] mt-1.5" style={{ color: 'rgba(240,237,232,0.5)' }}>
            Autonomous Runtime
          </span>
        </div>

        {/* Stat 4 */}
        <div className="flex flex-col items-center">
          <div className="flex items-baseline justify-center gap-1">
            <span className="font-mono font-medium text-[18px] sm:text-[22px] tracking-[-0.02em] leading-none" style={{ color: '#f0ede8' }}>
              {counts.context.toFixed(1)}M
            </span>
            <span
              className="font-['JetBrains_Mono',monospace] text-[22px] sm:text-[28px] leading-none"
              style={{ color: '#e8a07a' }}
            >
              #
            </span>
          </div>
          <span className="text-[11px] sm:text-[12px] mt-1.5" style={{ color: 'rgba(240,237,232,0.5)' }}>
            Context Windows
          </span>
        </div>
      </footer>
    </section>
  );
};

export default SecurifyHero;
