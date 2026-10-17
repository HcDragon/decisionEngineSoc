import React, { useEffect, useRef, useState } from 'react';

/* Shared, Japanese Torii-Gate Neobrutalism SOC console primitives */

/* Poll a backend endpoint with proper loading/error/cleanup. */
export function usePoll<T = any>(url: string, intervalMs = 4000): { data: T | null; loading: boolean; error: boolean } {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    const fetchOnce = async () => {
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(String(res.status));
        const json = await res.json();
        if (alive.current) { setData(json); setError(false); }
      } catch {
        if (alive.current) setError(true);
      } finally {
        if (alive.current) setLoading(false);
      }
    };
    fetchOnce();
    const id = setInterval(fetchOnce, intervalMs);
    return () => { alive.current = false; clearInterval(id); };
  }, [url, intervalMs]);
  return { data, loading, error };
}

export const Loading: React.FC = () => (
  <div className="py-10 text-center text-[0.82rem] font-mono font-bold uppercase tracking-wider text-[var(--torii-amber)]">
    <span className="inline-block animate-spin mr-2">✦</span> loading telemetry...
  </div>
);

export const ErrorState: React.FC<{ children?: React.ReactNode }> = ({ children }) => (
  <div className="py-8 px-4 my-2 text-center text-[0.82rem] font-bold text-white bg-[var(--torii-vermilion)] border-[2.5px] border-[#0d0d11] shadow-[3px_3px_0px_#0d0d11] rounded-xl">
    {children || 'Backend unreachable — ensure FastAPI server is running on port 8000.'}
  </div>
);

export const Panel: React.FC<{ title?: string; right?: React.ReactNode; className?: string; children: React.ReactNode }> = ({ title, right, className, children }) => (
  <section className={`rounded-xl border-[2.5px] border-[#0d0d11] bg-[rgba(26,21,24,0.94)] shadow-[4px_4px_0px_#0d0d11] overflow-hidden ${className || ''}`}>
    {(title || right) && (
      <header className="flex items-center justify-between gap-3 px-4 py-3 border-b-[2px] border-[#0d0d11] bg-[#1d171b]">
        {title && <h3 className="text-[0.84rem] font-bold text-white uppercase tracking-wider flex items-center gap-2">{title}</h3>}
        {right}
      </header>
    )}
    <div className="p-4">{children}</div>
  </section>
);

export const MetricCard: React.FC<{ label: string; value: React.ReactNode; sub?: string; accent?: string; unavailable?: boolean }> = ({ label, value, sub, accent = 'var(--torii-vermilion)', unavailable }) => (
  <div className="relative rounded-xl border-[2.5px] border-[#0d0d11] bg-[#faf6f0] text-[#0d0d11] shadow-[3.5px_3.5px_0px_#0d0d11] px-4 py-3 overflow-hidden transition-transform hover:-translate-y-0.5">
    <span className="absolute left-0 top-0 bottom-0 w-[5px] border-r border-[#0d0d11]" style={{ background: unavailable ? '#8c857b' : accent }} />
    <div className="text-[0.68rem] font-bold uppercase tracking-wider text-[#544d49] pl-1">{label}</div>
    {unavailable ? (
      <div className="text-[1.1rem] font-bold text-[#8c857b] mt-1.5 pl-1 font-mono">unavailable</div>
    ) : (
      <div className="text-[1.75rem] font-extrabold leading-none mt-1.5 text-[#0d0d11] tabular-nums pl-1 font-mono">{value}</div>
    )}
    {sub && <div className="text-[0.72rem] font-medium text-[#706764] mt-2 pl-1">{sub}</div>}
  </div>
);

type Tone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger';
const TONE: Record<Tone, string> = {
  neutral: 'bg-[#faf6f0] border-[#0d0d11] text-[#0d0d11]',
  accent: 'bg-[var(--torii-vermilion)] border-[#0d0d11] text-white',
  success: 'bg-[var(--torii-sage)] border-[#0d0d11] text-white',
  warning: 'bg-[var(--torii-amber)] border-[#0d0d11] text-[#0d0d11]',
  danger: 'bg-[var(--torii-vermilion)] border-[#0d0d11] text-white',
};

export const Badge: React.FC<{ tone?: Tone; children: React.ReactNode; className?: string }> = ({ tone = 'neutral', children, className }) => (
  <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[0.72rem] font-bold font-mono uppercase tracking-wide border-[1.5px] shadow-[2px_2px_0px_#0d0d11] ${TONE[tone]} ${className || ''}`}>{children}</span>
);

export function severityTone(sev?: string | number): Tone {
  if (typeof sev === 'number') return sev >= 75 ? 'danger' : sev >= 50 ? 'warning' : sev >= 25 ? 'accent' : 'neutral';
  const s = String(sev || '').toLowerCase();
  if (['critical', 'high', 'contained', 'blocked'].includes(s)) return s === 'contained' || s === 'blocked' ? 'success' : 'danger';
  if (['medium', 'open', 'pending_approval'].includes(s)) return 'warning';
  if (['low', 'monitored', 'benign'].includes(s)) return 'neutral';
  return 'neutral';
}

export const EmptyState: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="py-10 text-center text-[0.82rem] font-mono text-[var(--text-muted)]">{children}</div>
);

export const Placeholder: React.FC<{ title: string; reason: string }> = ({ title, reason }) => (
  <div className="rounded-xl border-[2.5px] border-dashed border-[#0d0d11] bg-[rgba(26,21,24,0.94)] shadow-[4px_4px_0px_#0d0d11] p-10 text-center">
    <div className="text-[1.1rem] font-bold text-white uppercase tracking-wider">{title}</div>
    <div className="text-[0.82rem] text-[var(--text-dim)] mt-2 max-w-md mx-auto leading-relaxed">{reason}</div>
    <div className="mt-4"><Badge tone="neutral">no backend endpoint</Badge></div>
  </div>
);

/* ---- dependency-free SVG charts ---- */

export const Donut: React.FC<{ data: Array<{ label: string; value: number; color: string }>; size?: number }> = ({ data, size = 130 }) => {
  const total = Math.max(1, data.reduce((s, d) => s + d.value, 0));
  const r = size / 2 - 12, cx = size / 2, cy = size / 2, C = 2 * Math.PI * r;
  let off = 0;
  return (
    <div className="flex items-center gap-4">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="shrink-0 drop-shadow-[2px_2px_0px_#0d0d11]">
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#131013" strokeWidth={14} />
        {data.filter(d => d.value > 0).map((d, i) => {
          const len = (d.value / total) * C;
          const el = <circle key={i} cx={cx} cy={cy} r={r} fill="none" stroke={d.color} strokeWidth={14}
            strokeDasharray={`${len} ${C - len}`} strokeDashoffset={-off} transform={`rotate(-90 ${cx} ${cy})`} />;
          off += len; return el;
        })}
        <text x={cx} y={cy - 2} textAnchor="middle" className="fill-white" style={{ fontSize: 20, fontWeight: 800 }}>{total}</text>
        <text x={cx} y={cy + 14} textAnchor="middle" className="fill-[var(--text-muted)]" style={{ fontSize: 9, fontWeight: 700 }}>TOTAL</text>
      </svg>
      <div className="flex flex-col gap-1.5 text-[0.76rem] min-w-0">
        {data.map((d, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-sm border border-[#0d0d11] shrink-0 shadow-[1px_1px_0px_#0d0d11]" style={{ background: d.color }} />
            <span className="text-[var(--text-dim)] font-medium truncate">{d.label}</span>
            <span className="text-white font-bold font-mono ml-auto tabular-nums">{d.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export const HBars: React.FC<{ data: Array<{ label: string; value: number; color?: string }> }> = ({ data }) => {
  const max = Math.max(1, ...data.map(d => d.value));
  return (
    <div className="flex flex-col gap-2.5">
      {data.length === 0 && <EmptyState>no data</EmptyState>}
      {data.map((d, i) => (
        <div key={i} className="flex items-center gap-3 text-[0.76rem]">
          <span className="w-28 shrink-0 text-[var(--text-dim)] font-medium truncate capitalize">{d.label}</span>
          <div className="flex-1 h-3 rounded-md bg-[#131013] border border-[#0d0d11] overflow-hidden shadow-[inset_1px_1px_0px_rgba(0,0,0,0.5)]">
            <div className="h-full rounded-sm" style={{ width: `${(d.value / max) * 100}%`, background: d.color || 'var(--torii-vermilion)' }} />
          </div>
          <span className="w-8 text-right text-white font-bold font-mono tabular-nums">{d.value}</span>
        </div>
      ))}
    </div>
  );
};

export const Sparkline: React.FC<{ points: number[]; color?: string; height?: number }> = ({ points, color = 'var(--torii-vermilion)', height = 40 }) => {
  if (points.length < 2) return <div className="text-[0.72rem] font-mono text-[var(--text-muted)] py-3">collecting...</div>;
  const w = 100, max = Math.max(1, ...points), min = Math.min(...points);
  const span = max - min || 1;
  const d = points.map((p, i) => `${(i / (points.length - 1)) * w},${height - ((p - min) / span) * (height - 4) - 2}`).join(' ');
  return (
    <svg width="100%" height={height} viewBox={`0 0 ${w} ${height}`} preserveAspectRatio="none" className="block drop-shadow-[1px_1px_0px_#0d0d11]">
      <polyline points={d} fill="none" stroke={color} strokeWidth={2.2} vectorEffect="non-scaling-stroke" />
    </svg>
  );
};
