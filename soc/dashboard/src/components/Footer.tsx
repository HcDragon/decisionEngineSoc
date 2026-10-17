import React from 'react';

interface FooterProps {
  onOpenConsole: () => void;
}

export const Footer: React.FC<FooterProps> = ({ onOpenConsole }) => {
  return (
    <footer className="w-full bg-[rgba(20,16,19,0.96)] border-t-[3px] border-[#0d0d11] py-14 px-6 md:px-12 text-[#c5bebe] text-xs">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-8">
        <div className="flex items-center gap-3.5">
          <div className="flex items-center gap-2.5 bg-[#faf6f0] text-[#0d0d11] border-[2px] border-[#0d0d11] shadow-[2.5px_2.5px_0px_#0d0d11] rounded-full px-4 py-1.5 font-bold">
            <svg
              className="h-4 w-4"
              viewBox="0 0 256 256"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path
                d="M 128 192 L 128 256 L 64.5 256 L 32 223 L 0 192 L 0 128 L 64 128 Z M 256 192 L 256 256 L 192.5 256 L 160 223 L 128 192 L 128 128 L 192 128 Z M 128 64 L 128 128 L 64.5 128 L 32 95 L 0 64 L 0 0 L 64 0 Z M 256 64 L 256 128 L 192.5 128 L 160 95 L 128 64 L 128 0 L 192 0 Z"
                fill="#0d0d11"
              />
            </svg>
            <span className="text-[#0d0d11] text-xs font-mono font-extrabold tracking-wider uppercase">RASHOMON</span>
          </div>
          <span className="font-medium text-[#c5bebe]">Autonomous Data-Security &amp; Smart SOC Manager</span>
        </div>

        <div className="flex items-center gap-6 font-bold uppercase tracking-wider font-mono text-[11px]">
          <a href="#platform" className="hover:text-white transition-colors">
            Platform
          </a>
          <a href="#solutions" className="hover:text-white transition-colors">
            Solutions
          </a>
          <button
            type="button"
            onClick={onOpenConsole}
            className="hover:text-white transition-colors cursor-pointer border-none bg-transparent font-bold uppercase tracking-wider font-mono text-[11px] text-[#c5bebe]"
          >
            SOC Console
          </button>
          <a
            href="https://github.com"
            target="_blank"
            rel="noreferrer"
            className="hover:text-white transition-colors"
          >
            Docs &amp; Guide
          </a>
        </div>

        <div className="text-[#8c8385] font-mono text-[11px]">
          &copy; 2026 RASHOMON. All Rights Reserved.
        </div>
      </div>
    </footer>
  );
};
