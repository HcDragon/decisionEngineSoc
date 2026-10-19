import type { AlertBucket, Severity } from '../data/types';
import { alertTotals, bucketTotal, gridSteps } from '../data/derive';
import { SEVERITY_LABEL } from './Badges';

const VIEW_W = 720, VIEW_H = 240;
const X0 = 36, X1 = 712, BASE = 208, PLOT_TOP = 24, PX_PER_ALERT = 2.8, BAR_W = 18;
const STACK: Severity[] = ['low', 'medium', 'high', 'critical'];   // bottom -> top
const FILL: Record<Severity, string> = {
  low: 'var(--chart-low)', medium: 'var(--chart-med)', high: 'var(--chart-high)', critical: 'var(--chart-crit)',
};

export function describeSeries(series: AlertBucket[]) {
  const { total, bySeverity, peak } = alertTotals(series);
  if (!total || !peak) return `Stacked bar chart of alerts per hour over the last ${series.length} hours: no alerts.`;
  const ago = series.length - 1 - peak.hour;
  return `Stacked bar chart of alerts per hour over the last ${series.length} hours by severity: ${total} alerts, ` +
    `${bySeverity.critical} critical, ${bySeverity.high} high, ${bySeverity.medium} medium, ${bySeverity.low} low. ` +
    `The busiest hour had ${bucketTotal(peak)} alerts${ago === 0 ? ', in the current hour' : `, ${ago} hours ago`}.`;
}

/** 2.8px per alert while the busiest hour fits under 60; beyond that the scale shrinks to fit. */
export function chartScale(series: AlertBucket[]) {
  const max = Math.max(0, ...series.map(bucketTotal));
  const grid = gridSteps(max);
  const top = grid[grid.length - 1];
  return { grid, px: Math.min(PX_PER_ALERT, (BASE - PLOT_TOP) / top) };
}

export function AlertVolumeChart({ series }: { series: AlertBucket[] }) {
  const slot = (X1 - X0) / series.length;
  const xOf = (i: number) => X0 + i * slot + (slot - BAR_W) / 2;
  const { grid, px } = chartScale(series);
  const yOf = (alerts: number) => BASE - alerts * px;

  return (
    <>
      <div className="soc-legend" aria-hidden="true">
        {[...STACK].reverse().map((s) => (
          <span className="soc-legend-item" key={s}><span className="soc-swatch" style={{ background: FILL[s] }} />{SEVERITY_LABEL[s]}</span>
        ))}
        <span className="soc-legend-unit">Alerts per hour</span>
      </div>
      <div className="soc-chart-wrap">
        <svg className="soc-chart" viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} role="img" aria-label={describeSeries(series)}>
          {grid.map((g) => (
            <g key={g}>
              <line className="soc-chart-grid" x1={X0} x2={X1} y1={yOf(g)} y2={yOf(g)} />
              <text className="soc-chart-axis" x={X0 - 8} y={yOf(g) + 4} textAnchor="end">{g}</text>
            </g>
          ))}

          {series.map((b, i) => {
            let top = BASE;
            return (
              <g key={b.hour}>
                {STACK.map((s) => {
                  const h = b[s] * px;
                  if (h <= 0) return null;
                  top -= h;
                  return <rect key={s} x={xOf(i)} y={top} width={BAR_W} height={Math.max(0.5, h - 1)} fill={FILL[s]} />;  // 1px gap
                })}
              </g>
            );
          })}

          {series.map((b, i) => (i % 4 === 0 ? (
            <text key={`x${b.hour}`} className="soc-chart-axis" x={xOf(i) + BAR_W / 2} y={VIEW_H - 8} textAnchor="middle">
              -{series.length - i}h
            </text>
          ) : null))}
          <text className="soc-chart-axis" x={X1} y={VIEW_H - 8} textAnchor="end">now</text>
        </svg>
      </div>
    </>
  );
}
