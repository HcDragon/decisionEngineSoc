/* 28px trend line: accent stroke, no end dot, stretched to the tile width. */
export function Sparkline({ values, label }: { values: number[]; label: string }) {
  const w = 100, h = 28, pad = 2;
  if (values.length < 2) {
    return <svg className="soc-spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" role="img" aria-label={label} />;
  }
  const min = Math.min(...values), max = Math.max(...values);
  const span = max - min || 1;
  const points = values
    .map((v, i) => `${((i / (values.length - 1)) * w).toFixed(2)},${(h - pad - ((v - min) / span) * (h - pad * 2)).toFixed(2)}`)
    .join(' ');
  return (
    <svg className="soc-spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" role="img" aria-label={label}>
      <polyline points={points} fill="none" stroke="var(--accent)" strokeWidth={2} vectorEffect="non-scaling-stroke"
        strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}
