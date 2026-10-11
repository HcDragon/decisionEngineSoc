import React, { useEffect, useRef, useState } from 'react';

/* Shared, professional SOC console primitives — muted tokens from index.css,
   dependency-free SVG charts. No neon, no new libraries. */

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
  <div className="py-10 text-center text-[0.82rem] text-[var(--text-muted)]">loading…</div>
);
export const ErrorState: React.FC<{ children?: React.ReactNode }> = ({ children }) => (
  <div className="py-10 text-center text-[0.82rem] text-[#ff8085]">{children || 'backend unreachable — check the connection.'}</div>
);

export const Panel: React.FC<{ title?: string; right?: React.ReactNode; className?: string; children: React.ReactNode }> = ({ title, right, className, children }) => (
  <section className={`rounded-lg border border-[var(--border)] bg-[rgba(16,21,30,0.72)] backdrop-blur-xl ${className || ''}`}>
    {(title || right) && (
      <header className="flex items-center justify-between gap-3 px-4 py-3 border-b border-[var(--border)]">
        {title && <h3 className="text-[0.82rem] font-semibold text-[var(--text-main)] tracking-tight">{title}</h3>}
        {right}
      </header>
    )}
    <div className="p-4">{children}</div>
  </section>
);

export const MetricCard: React.FC<{ label: string; value: React.ReactNode; sub?: string; accent?: string; unavailable?: boolean }> = ({ label, value, sub, accent = 'var(--accent)', unavailable }) => (
  <div className="relative rounded-lg border border-[var(--border)] bg-[rgba(16,21,30,0.72)] backdrop-blur-xl px-4 py-3 overflow-hidden">
    <span className="absolute left-0 top-0 bottom-0 w-[3px]" style={{ background: unavailable ? 'var(--border-strong)' : accent }} />
    <div className="text-[0.66rem] font-semibold uppercase tracking-[0.06em] text-[var(--text-muted)]">{label}</div>
    {unavailable ? (
      <div className="text-[1.1rem] font-medium text-[var(--text-muted)] mt-1.5">unavailable</div>
    ) : (
      <div className="text-[1.7rem] font-semibold leading-none mt-1.5 text-[var(--text-main)] tabular-nums">{value}</div>
    )}
    {sub && <div className="text-[0.72rem] text-[var(--text-dim)] mt-2">{sub}</div>}
  </div>
);

type Tone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger';
const TONE: Record<Tone, string> = {
  neutral: 'bg-[var(--bg-inset)] border-[var(--border)] text-[var(--text-dim)]',
  accent: 'bg-[var(--accent-soft)] border-[var(--accent)]/40 text-[#7aa7f5]',
  success: 'bg-[var(--success-soft)] border-[var(--success)]/40 text-[#4ade80]',
  warning: 'bg-[var(--warning-soft)] border-[var(--warning)]/40 text-[#e0b64a]',
  danger: 'bg-[var(--danger-soft)] border-[var(--danger)]/40 text-[#ff8085]',
};
export const Badge: React.FC<{ tone?: Tone; children: React.ReactNode; className?: string }> = ({ tone = 'neutral', children, className }) => (
  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[0.7rem] font-semibold border ${TONE[tone]} ${className || ''}`}>{children}</span>
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
  <div className="py-10 text-center text-[0.82rem] text-[var(--text-muted)]">{children}</div>
);

export const Placeholder: React.FC<{ title: string; reason: string }> = ({ title, reason }) => (
  <div className="rounded-lg border border-dashed border-[var(--border-strong)] bg-[rgba(16,21,30,0.72)] backdrop-blur-xl p-10 text-center">
    <div className="text-[1rem] font-semibold text-[var(--text-dim)]">{title}</div>
    <div className="text-[0.8rem] text-[var(--text-muted)] mt-2 max-w-md mx-auto leading-relaxed">{reason}</div>
    <div className="mt-3"><Badge tone="neutral">no backend endpoint</Badge></div>
  </div>
);

/* ---- dependency-free SVG charts ---- */

export const Donut: React.FC<{ data: Array<{ label: string; value: number; color: string }>; size?: number }> = ({ data, size = 130 }) => {
  const total = Math.max(1, data.reduce((s, d) => s + d.value, 0));
  const r = size / 2 - 10, cx = size / 2, cy = size / 2, C = 2 * Math.PI * r;
  let off = 0;
  return (
    <div className="flex items-center gap-4">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="shrink-0">
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--bg-inset)" strokeWidth={12} />
        {data.filter(d => d.value > 0).map((d, i) => {
          const len = (d.value / total) * C;
          const el = <circle key={i} cx={cx} cy={cy} r={r} fill="none" stroke={d.color} strokeWidth={12}
            strokeDasharray={`${len} ${C - len}`} strokeDashoffset={-off} transform={`rotate(-90 ${cx} ${cy})`} />;
          off += len; return el;
        })}
        <text x={cx} y={cy - 2} textAnchor="middle" className="fill-[var(--text-main)]" style={{ fontSize: 20, fontWeight: 700 }}>{total}</text>
        <text x={cx} y={cy + 14} textAnchor="middle" className="fill-[var(--text-muted)]" style={{ fontSize: 9 }}>total</text>
      </svg>
      <div className="flex flex-col gap-1.5 text-[0.76rem] min-w-0">
        {data.map((d, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-sm shrink-0" style={{ background: d.color }} />
            <span className="text-[var(--text-dim)] truncate">{d.label}</span>
            <span className="text-[var(--text-main)] font-semibold ml-auto tabular-nums">{d.value}</span>
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
          <span className="w-28 shrink-0 text-[var(--text-dim)] truncate capitalize">{d.label}</span>
          <div className="flex-1 h-2 rounded-full bg-[var(--bg-inset)] overflow-hidden">
            <div className="h-full rounded-full" style={{ width: `${(d.value / max) * 100}%`, background: d.color || 'var(--accent)' }} />
          </div>
          <span className="w-8 text-right text-[var(--text-main)] font-semibold tabular-nums">{d.value}</span>
        </div>
      ))}
    </div>
  );
};

export const Sparkline: React.FC<{ points: number[]; color?: string; height?: number }> = ({ points, color = 'var(--accent)', height = 40 }) => {
  if (points.length < 2) return <div className="text-[0.72rem] text-[var(--text-muted)] py-3">collecting…</div>;
  const w = 100, max = Math.max(1, ...points), min = Math.min(...points);
  const span = max - min || 1;
  const d = points.map((p, i) => `${(i / (points.length - 1)) * w},${height - ((p - min) / span) * (height - 4) - 2}`).join(' ');
  return (
    <svg width="100%" height={height} viewBox={`0 0 ${w} ${height}`} preserveAspectRatio="none" className="block">
      <polyline points={d} fill="none" stroke={color} strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
    </svg>
  );
};
