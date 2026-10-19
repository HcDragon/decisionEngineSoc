import { useEffect, useRef, useState } from 'react';
import { useSocSource } from '../data/context';
import type { PipelineEvent } from '../data/types';

/** Subscribe to live pipeline events; the handler may change between renders. */
export function useLiveEvents(handler: (e: PipelineEvent) => void, enabled = true) {
  const source = useSocSource();
  const ref = useRef(handler);
  ref.current = handler;
  useEffect(() => {
    if (!enabled) return;
    return source.subscribe((e) => ref.current(e));
  }, [source, enabled]);
}

/** Whether the live event stream is currently connected. */
export function useStreamConnected() {
  const source = useSocSource();
  const [connected, setConnected] = useState(false);
  useEffect(() => source.subscribe(() => setConnected(true), setConnected), [source]);
  return connected;
}
