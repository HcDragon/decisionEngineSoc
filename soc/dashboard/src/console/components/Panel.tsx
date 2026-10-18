import { useId, type ReactNode } from 'react';
import type { Query } from '../hooks/useSocData';

interface PanelProps {
  title: ReactNode;
  note?: ReactNode;
  className?: string;
  flush?: boolean;
  children: ReactNode;
}

/* The one panel used everywhere: bordered card, header strip, padded body. No shadows. */
export function Panel({ title, note, className, flush, children }: PanelProps) {
  const id = useId();
  return (
    <section className={`soc-panel ${className ?? ''}`} aria-labelledby={id}>
      <header className="soc-panel-head">
        <h2 id={id}>{title}</h2>
        {note != null && note !== false && <div className="soc-panel-note">{note}</div>}
      </header>
      <div className={`soc-panel-body ${flush ? 'soc-panel-body--flush' : ''}`}>{children}</div>
    </section>
  );
}

export function Skeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="soc-skeleton" role="status" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => <span key={i} />)}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error?: Error; onRetry: () => void }) {
  return (
    <div className="soc-error" role="alert">
      <span><strong>Couldn’t reach the SOC API.</strong> {error?.message ? `(${error.message})` : 'Is the backend running on port 8000?'}</span>
      <button type="button" className="soc-btn" onClick={onRetry}>Retry</button>
    </div>
  );
}

/** Ready data, or the standard skeleton / error states (stale data stays visible on refresh errors). */
export function QueryBody<T>({ query, rows, children }: { query: Query<T>; rows?: number; children: (data: T) => ReactNode }) {
  if (query.status === 'ready') return <>{children(query.data)}</>;
  if (query.status === 'error') {
    return (
      <>
        <ErrorState error={query.error} onRetry={query.retry} />
        {query.data !== undefined && <div style={{ marginTop: 14 }}>{children(query.data)}</div>}
      </>
    );
  }
  return <Skeleton rows={rows} />;
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="soc-empty">{children}</p>;
}
