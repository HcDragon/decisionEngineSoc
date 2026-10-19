import { useCallback, useEffect, useRef, useState } from 'react';
import { useSocSource } from '../data/context';
import type { SocDataSource } from '../data/source';
import { useLiveEvents } from './useLive';

export type Query<T> =
  | { status: 'loading'; data?: undefined; error?: undefined; retry: () => void; updatedAt: number | null }
  | { status: 'error'; data?: T; error: Error; retry: () => void; updatedAt: number | null }
  | { status: 'ready'; data: T; error?: undefined; retry: () => void; updatedAt: number | null };

interface Options {
  /** Re-fetch on an interval (ms). */
  pollMs?: number;
  /** Re-fetch when one of these pipeline stages arrives on the live stream. */
  refreshOn?: string[];
}

/**
 * Read one slice of console data through the SocDataSource interface.
 * `key` identifies the request; the loader itself may be an inline arrow.
 * Background refreshes keep showing the last good data; only the first load
 * (or a failure with nothing to show) renders skeletons / the error state.
 */
export function useSocData<T>(key: string, load: (source: SocDataSource) => Promise<T>, opts: Options = {}): Query<T> {
  const source = useSocSource();
  const loadRef = useRef(load);
  loadRef.current = load;
  const [nonce, setNonce] = useState(0);
  const [state, setState] = useState<{ data?: T; error?: Error; loading: boolean; updatedAt: number | null }>({ loading: true, updatedAt: null });

  useEffect(() => {
    let alive = true;
    loadRef.current(source).then(
      (data) => alive && setState({ data, loading: false, updatedAt: Date.now() }),
      (err: unknown) => alive && setState((s) => ({ ...s, loading: false, error: err instanceof Error ? err : new Error(String(err)) })),
    );
    return () => { alive = false; };
  }, [source, key, nonce]);

  // reset to a fresh load when the request identity changes
  useEffect(() => { setState({ loading: true, updatedAt: null }); }, [key]);

  const refresh = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    if (!opts.pollMs) return;
    const id = setInterval(refresh, opts.pollMs);
    return () => clearInterval(id);
  }, [opts.pollMs, refresh]);

  const stages = opts.refreshOn;
  const lastRefresh = useRef(0);
  useLiveEvents((e) => {
    if (!stages?.includes(e.stage)) return;
    // throttle: a flood can emit hundreds of events per second
    if (Date.now() - lastRefresh.current < 1000) return;
    lastRefresh.current = Date.now();
    refresh();
  }, !!stages?.length);

  const retry = useCallback(() => {
    setState((s) => ({ ...s, loading: s.data === undefined, error: undefined }));
    refresh();
  }, [refresh]);

  if (state.data !== undefined && !state.error) return { status: 'ready', data: state.data, retry, updatedAt: state.updatedAt };
  if (state.error) return { status: 'error', error: state.error, data: state.data, retry, updatedAt: state.updatedAt };
  return { status: 'loading', retry, updatedAt: state.updatedAt };
}
