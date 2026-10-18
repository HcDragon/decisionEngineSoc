import type { Kpi } from '../data/types';
import { formatKpiValue } from '../data/derive';
import { Sparkline } from './Sparkline';

export function KpiTile({ kpi }: { kpi: Kpi }) {
  return (
    <section className="soc-kpi" aria-label={kpi.label}>
      <p className="soc-kpi-label">{kpi.label}</p>
      <p className={`soc-kpi-value ${kpi.emphasize ? `soc-tone-${kpi.delta.tone}` : ''}`}>{formatKpiValue(kpi)}</p>
      {kpi.sub && <p className="soc-kpi-sub">{kpi.sub}</p>}
      <p className={`soc-kpi-delta soc-tone-${kpi.delta.tone}`}>{kpi.delta.text}</p>
      <Sparkline values={kpi.series} label={kpi.seriesLabel} />
    </section>
  );
}
