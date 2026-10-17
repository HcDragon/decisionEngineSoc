import React, { useEffect, useState } from 'react';
import DecryptedText from './components/DecryptedText';
import SlingButton from './components/SlingButton';
import { Sun, Moon, Home } from 'lucide-react';

interface SecurifyHeroProps {
  onGetStarted?: () => void;
  onOpenConsole?: () => void;
  theme?: string;
  onToggleTheme?: () => void;
}

export const SecurifyHero: React.FC<SecurifyHeroProps> = ({
  onGetStarted,
  onOpenConsole,
  theme = 'dark',
  onToggleTheme,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const handleHomeClick = () => {
    if ((window as any).__gsapScrollTo) {
      (window as any).__gsapScrollTo(0);
    } else {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  return (
    <section
      className="relative min-h-[96vh] w-full flex flex-col justify-between items-center px-4 sm:px-8 py-6 select-none font-sans overflow-hidden"
      style={{ color: '#f0ede8' }}
    >
      {/* 1) Neobrutalist Navigation Header: Exactly 2 Core Buttons ("Home" and "Open Console") + Theme Toggle */}
      <header
        className="relative z-20 w-full max-w-[820px] flex items-center justify-between gap-3 sm:gap-6 shrink-0 transition-all duration-300"
        style={{ animation: 'slideDown 0.6s cubic-bezier(0.22,1,0.36,1) both' }}
      >
        {/* Logo */}
        <button
          type="button"
          onClick={handleHomeClick}
          className="w-11 h-11 md:w-12 md:h-12 rounded-full bg-[#faf6f0] border-[2.5px] border-[#0d0d11] shadow-[3px_3px_0px_#0d0d11] flex items-center justify-center shrink-0 cursor-pointer hover:-translate-y-0.5 active:translate-x-[1px] active:translate-y-[1px] active:shadow-[1px_1px_0px_#0d0d11] transition-all"
          aria-label="RASHOMON Home"
        >
          <img src="/assets/logo.webp" alt="RASHOMON" width="44" height="44" className="w-[72%] h-[72%] object-contain" />
        </button>

        {/* Desktop Nav: Just 2 Buttons (Home & Open Console) + Theme Switch */}
        <div className="hidden md:flex items-center gap-3">
          {/* 1. Home Button with rich hover animation */}
          <button
            type="button"
            onClick={handleHomeClick}
            className="group relative flex items-center gap-2 h-11 px-5 rounded-full font-bold text-[13.5px] bg-[#faf6f0] text-[#0d0d11] border-[2.5px] border-[#0d0d11] shadow-[3px_3px_0px_#0d0d11] hover:-translate-y-0.5 hover:shadow-[4.5px_4.5px_0px_#0d0d11] active:translate-x-[1px] active:translate-y-[1px] active:shadow-[1px_1px_0px_#0d0d11] cursor-pointer transition-all duration-200"
          >
            <Home className="w-4 h-4 text-[var(--torii-vermilion)] transition-transform duration-200 group-hover:scale-110" />
            <span>Home</span>
            <span className="absolute bottom-[6px] left-1/2 -translate-x-1/2 w-0 h-[2.5px] rounded-full bg-[var(--torii-vermilion)] transition-all duration-300 group-hover:w-8" />
          </button>

          {/* Theme Switch Button (Dark / Light Mode) */}
          <button
            type="button"
            onClick={onToggleTheme}
            className="w-11 h-11 rounded-full bg-[#faf6f0] text-[#0d0d11] border-[2.5px] border-[#0d0d11] shadow-[3px_3px_0px_#0d0d11] flex items-center justify-center cursor-pointer hover:-translate-y-0.5 hover:shadow-[4.5px_4.5px_0px_#0d0d11] active:translate-x-[1px] active:translate-y-[1px] active:shadow-[1px_1px_0px_#0d0d11] transition-all duration-200"
            aria-label={theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode'}
            title={theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode'}
          >
            {theme === 'light' ? (
              <Moon className="w-5 h-5 text-[var(--torii-crimson)] transition-transform duration-300 hover:-rotate-12" />
            ) : (
              <Sun className="w-5 h-5 text-[var(--torii-amber)] transition-transform duration-300 hover:rotate-45" />
            )}
          </button>

          {/* 2. Open Console Button with React Bits <SlingButton /> animation */}
          <div className="flex items-center">
            <button
              type="button"
              onClick={onOpenConsole}
              className="group flex items-center gap-2.5 h-11 pl-5 pr-1.5 rounded-full font-extrabold uppercase tracking-wider text-[13px] bg-[var(--torii-vermilion)] text-white border-[2.5px] border-[#0d0d11] shadow-[3.5px_3.5px_0px_#0d0d11] hover:bg-[var(--torii-vermilion-hover)] hover:-translate-y-0.5 hover:shadow-[5px_5px_0px_#0d0d11] active:translate-x-[2px] active:translate-y-[2px] active:shadow-[1px_1px_0px_#0d0d11] cursor-pointer transition-all duration-200"
            >
              <span className="transition-transform duration-200 group-hover:scale-105">Open Console</span>
              <span
                className="scale-[0.74] origin-center -my-2 -mr-1.5 inline-flex"
                onClick={(e) => {
                  e.stopPropagation();
                }}
              >
                <SlingButton
                  onSend={onOpenConsole}
                  size={38}
                  strokeWidth={2.5}
                  armAt={28}
                  maxPull={80}
                  launchSpeed={2400}
                  padColor="#faf6f0"
                  iconColor="#0d0d11"
                  accentColor="#eaa838"
                  wellColor="#0d0d11"
                  bandColor="#8c857b"
                  flight={95}
                  particles={12}
                  tapSends={true}
                  ariaLabel="Launch SOC Console"
                />
              </span>
            </button>
          </div>
        </div>

        {/* Mobile controls */}
        <div className="flex items-center gap-2 md:hidden">
          <button
            type="button"
            onClick={onToggleTheme}
            className="w-11 h-11 rounded-full bg-[#faf6f0] text-[#0d0d11] border-[2.5px] border-[#0d0d11] shadow-[3px_3px_0px_#0d0d11] flex items-center justify-center cursor-pointer active:translate-x-[1px] active:translate-y-[1px]"
            aria-label="Toggle Theme"
          >
            {theme === 'light' ? (
              <Moon className="w-5 h-5 text-[var(--torii-crimson)]" />
            ) : (
              <Sun className="w-5 h-5 text-[var(--torii-amber)]" />
            )}
          </button>

          <button
            type="button"
            onClick={() => setMobileMenuOpen((o) => !o)}
            className="w-11 h-11 rounded-full bg-[#faf6f0] border-[2.5px] border-[#0d0d11] shadow-[3px_3px_0px_#0d0d11] flex flex-col items-center justify-center gap-1.5 cursor-pointer z-40 transition-transform active:translate-x-[1px] active:translate-y-[1px]"
            aria-expanded={mobileMenuOpen}
            aria-label="Toggle navigation menu"
          >
            <span className={`w-5 h-[2px] bg-[#0d0d11] rounded-full transition-transform ${mobileMenuOpen ? 'translate-y-[8px] rotate-45' : ''}`} />
            <span className={`w-5 h-[2px] bg-[#0d0d11] rounded-full transition-opacity ${mobileMenuOpen ? 'opacity-0' : ''}`} />
            <span className={`w-5 h-[2px] bg-[#0d0d11] rounded-full transition-transform ${mobileMenuOpen ? '-translate-y-[8px] -rotate-45' : ''}`} />
          </button>
        </div>
      </header>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <>
          <div
            className="fixed inset-0 z-30 md:hidden bg-black/60 backdrop-blur-sm"
            onClick={() => setMobileMenuOpen(false)}
          />
          <div
            className="fixed top-20 left-1/2 -translate-x-1/2 w-[calc(100%-32px)] max-w-[360px] rounded-2xl p-6 z-35 flex flex-col items-center gap-3 md:hidden bg-[#faf6f0] text-[#0d0d11] border-[3px] border-[#0d0d11] shadow-[6px_6px_0px_#0d0d11]"
            style={{ animation: 'menuIn 0.3s cubic-bezier(0.22,1,0.36,1) both' }}
          >
            <button
              type="button"
              onClick={() => {
                setMobileMenuOpen(false);
                handleHomeClick();
              }}
              className="w-full py-2.5 font-bold text-[16px] text-[#0d0d11] flex items-center justify-center gap-2 bg-transparent border-none cursor-pointer"
            >
              <Home className="w-4 h-4 text-[var(--torii-vermilion)]" />
              Home
            </button>
            <button
              type="button"
              onClick={() => {
                setMobileMenuOpen(false);
                onOpenConsole?.();
              }}
              className="w-full mt-2 py-3.5 rounded-xl font-bold uppercase tracking-wider text-[14px] cursor-pointer bg-[var(--torii-vermilion)] text-white border-[2.5px] border-[#0d0d11] shadow-[3px_3px_0px_#0d0d11]"
            >
              Open Console
            </button>
          </div>
        </>
      )}

      {/* 2) Upper Brand Badge - above the Torii gate */}
      <div className="relative z-10 flex flex-col items-center justify-start text-center max-w-[860px] w-full pt-4">
        <div
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-[12px] font-mono font-bold tracking-widest uppercase bg-[var(--torii-amber)] text-[#0d0d11] border-[2px] border-[#0d0d11] shadow-[2.5px_2.5px_0px_#0d0d11]"
          style={{ animation: 'reveal 0.85s cubic-bezier(0.22,1,0.36,1) both' }}
        >
          <span className="h-2 w-2 rounded-full bg-[var(--torii-vermilion)] animate-pulse" />
          Autonomous SOC   AI Decision Engine
        </div>
      </div>

      {/* 3) Lower Water Region: Title as RASHOMON with <DecryptedText /> and clean lake reflection area */}
      {/* (Notice the red dash inside the Torii gate is completely removed!) */}
      <div className="relative z-10 w-full flex flex-col items-center justify-center text-center mt-auto pt-16 sm:pt-24 pb-6">
        <h1 className="m-0 select-none leading-none">
          <DecryptedText
            text="RASHOMON"
            animateOn="inViewHover"
            effect="scramble"
            sequential={true}
            revealDirection="start"
            speed={55}
            maxIterations={12}
            hoverRadius={110}
            scrambleColor="#e24a2b"
            loop={false}
            loopDelay={2500}
            useOriginalCharsOnly={false}
            characters="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+"
            className="font-['Readex_Pro',sans-serif] font-black text-[54px] sm:text-[76px] md:text-[98px] lg:text-[116px] tracking-[0.02em] uppercase text-white drop-shadow-[0_4px_24px_rgba(0,0,0,0.95)]"
            encryptedClassName="font-['Readex_Pro',sans-serif] font-black text-[54px] sm:text-[76px] md:text-[98px] lg:text-[116px] tracking-[0.02em] uppercase text-[var(--torii-vermilion)] opacity-90 drop-shadow-[0_4px_24px_rgba(0,0,0,0.95)]"
            parentClassName="inline-block cursor-pointer"
          />
        </h1>
        <p className="mt-3 text-[13px] sm:text-[15px] md:text-[17px] font-bold tracking-[0.2em] uppercase text-[var(--torii-washi)] drop-shadow-[0_2px_10px_rgba(0,0,0,0.95)] opacity-95">
          Intelligence Designed To Evolve
        </p>

        {/* Dual CTA buttons below title */}
        <div className="flex items-center gap-4 flex-wrap justify-center mt-6">
          <button
            type="button"
            onClick={onGetStarted || onOpenConsole}
            className="inline-flex items-center justify-center px-7 py-3 rounded-full font-extrabold uppercase tracking-wider text-[13.5px] cursor-pointer bg-[var(--torii-vermilion)] text-white border-[2.5px] border-[#0d0d11] shadow-[3.5px_3.5px_0px_#0d0d11] hover:bg-[var(--torii-vermilion-hover)] hover:-translate-y-0.5 active:translate-x-[2px] active:translate-y-[2px] active:shadow-[1px_1px_0px_#0d0d11] transition-all"
          >
            Launch Decision Engine
          </button>
          <a
            href="#platform"
            className="inline-flex items-center justify-center px-7 py-3 rounded-full font-bold text-[13.5px] bg-[#faf6f0] text-[#0d0d11] border-[2.5px] border-[#0d0d11] shadow-[3.5px_3.5px_0px_#0d0d11] hover:bg-white hover:-translate-y-0.5 active:translate-x-[2px] active:translate-y-[2px] active:shadow-[1px_1px_0px_#0d0d11] transition-all"
          >
            Explore Platform
          </a>
        </div>
      </div>
    </section>
  );
};

export default SecurifyHero;
