import { createContext, useContext } from 'react';

export interface ConsoleApi {
  /** Global search text from the title row (incident ID, IP, threat/rule ID). */
  query: string;
  openIncident: (id: number) => void;
  notify: (message: string) => void;
}

export const ConsoleContext = createContext<ConsoleApi>({ query: '', openIncident: () => {}, notify: () => {} });
export const useConsole = () => useContext(ConsoleContext);
