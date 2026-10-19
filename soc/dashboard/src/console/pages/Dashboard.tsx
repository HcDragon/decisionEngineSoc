import { useSocData } from '../hooks/useSocData';
import { KpiTile } from '../components/KpiTile';
import { ErrorState, Skeleton } from '../components/Panel';
import {
  AlertVolumePanel, DecisionLatencyPanel, FamilyPanel, IncidentQueuePanel, LiveFeedPanel, SourceHealthPanel, TopAssetsPanel,
} from '../components/OverviewPanels';

function KpiRow() {
  const q = useSocData('kpis', (s) => s.getKpis(), { pollMs: 10_000, refreshOn: ['alert', 'decision'] });
  if (q.status === 'ready') return <div className="soc-kpis">{q.data.map((k) => <KpiTile key={k.id} kpi={k} />)}</div>;
  return (
    <div className="soc-kpis">
      <div className="soc-kpi" style={{ flexBasis: '100%' }}>
        {q.status === 'loading' ? <Skeleton rows={3} /> : <ErrorState error={q.error} onRetry={q.retry} />}
      </div>
    </div>
  );
}

export function DashboardPage() {
  return (
    <>
      <KpiRow />
      <div className="soc-row">
        <AlertVolumePanel />
        <FamilyPanel />
      </div>
      <div className="soc-row">
        <div className="soc-w-queue"><IncidentQueuePanel /></div>
        <div className="soc-stack">
          <TopAssetsPanel />
          <SourceHealthPanel />
        </div>
      </div>
      <div className="soc-row">
        <LiveFeedPanel />
        <DecisionLatencyPanel />
      </div>
    </>
  );
}
