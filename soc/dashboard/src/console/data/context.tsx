import { createContext, useContext, type ReactNode } from 'react';
import type { SocDataSource } from './source';

const SocDataContext = createContext<SocDataSource | null>(null);

export function SocDataProvider({ source, children }: { source: SocDataSource; children: ReactNode }) {
  return <SocDataContext.Provider value={source}>{children}</SocDataContext.Provider>;
}

/** The active data source. Components depend on the interface only. */
export function useSocSource(): SocDataSource {
  const source = useContext(SocDataContext);
  if (!source) throw new Error('useSocSource must be used inside <SocDataProvider>');
  return source;
}
