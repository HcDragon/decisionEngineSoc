import type { QueueState, Severity } from '../data/types';

export const SEVERITY_LABEL: Record<Severity, string> = { critical: 'Critical', high: 'High', medium: 'Medium', low: 'Low' };
const SHORT: Record<Severity, string> = { critical: 'Crit', high: 'High', medium: 'Med', low: 'Low' };

/** Severity is always spelled out; colour is never the only signal. */
export function SeverityBadge({ severity, short = false }: { severity: Severity | null; short?: boolean }) {
  if (!severity) return <span className="soc-badge soc-sev-none">Unscored</span>;
  return (
    <span className={`soc-badge soc-sev-${severity}`} title={short ? SEVERITY_LABEL[severity] : undefined}>
      {short ? SHORT[severity] : SEVERITY_LABEL[severity]}
    </span>
  );
}

export function StatusText({ state, label }: { state: QueueState; label: string }) {
  return <span className={`soc-status soc-st-${state}`}>{label}</span>;
}
