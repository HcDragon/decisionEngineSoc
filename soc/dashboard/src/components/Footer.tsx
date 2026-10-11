import React from 'react';

interface FooterProps {
  onOpenConsole: () => void;
}

export const Footer: React.FC<FooterProps> = ({ onOpenConsole }) => {
  return (
    <footer className="w-full bg-black/60 backdrop-blur-2xl border-t border-white/10 py-16 px-6 md:px-12 text-neutral-400 text-xs shadow-[0_8px_32px_0_rgba(0,0,0,0.37)]">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-8">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-white/[0.08] border border-white/10 rounded-full px-4 py-2 backdrop-blur-md">
            <svg
              className="h-4 w-4"
              viewBox="0 0 256 256"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path
                d="M 128 192 L 128 256 L 64.5 256 L 32 223 L 0 192 L 0 128 L 64 128 Z M 256 192 L 256 256 L 192.5 256 L 160 223 L 128 192 L 128 128 L 192 128 Z M 128 64 L 128 128 L 64.5 128 L 32 95 L 0 64 L 0 0 L 64 0 Z M 256 64 L 256 128 L 192.5 128 L 160 95 L 128 64 L 128 0 L 192 0 Z"
                fill="#ffffff"
              />
            </svg>
            <span className="text-white text-xs font-medium tracking-tight">roshomon</span>
          </div>
          <span>autonomous data-security &amp; smart soc manager</span>
        </div>

        <div className="flex items-center gap-6">
          <a href="#platform" className="hover:text-white transition-colors">
            platform
          </a>
          <a href="#solutions" className="hover:text-white transition-colors">
            solutions
          </a>
          <button
            type="button"
            onClick={onOpenConsole}
            className="hover:text-white transition-colors cursor-pointer"
          >
            soc console
          </button>
          <a
            href="https://github.com"
            target="_blank"
            rel="noreferrer"
            className="hover:text-white transition-colors"
          >
            docs &amp; lab guide
          </a>
        </div>

        <div className="text-neutral-500">
          © 2026 roshomon. all rights reserved.
        </div>
      </div>
    </footer>
  );
};
