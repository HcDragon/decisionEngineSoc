import type { IconName } from '../components/Icon';

export type PageId = 'dashboard' | 'threats' | 'incidents' | 'decision' | 'traffic' | 'audit' | 'system' | 'settings';

export interface PageMeta { id: PageId; label: string; icon: IconName; title: string; subtitle: string }

export const NAV: { group: string; pages: PageMeta[] }[] = [
  {
    group: 'Monitor',
    pages: [
      { id: 'dashboard', label: 'Dashboard', icon: 'dashboard', title: 'Security Operations Overview', subtitle: 'Alerts, incidents and detection health for the last 24 hours' },
      { id: 'threats', label: 'Threat Events', icon: 'threats', title: 'Threat Events', subtitle: 'Every alert persisted by the ML model and the rate-rule engine, newest first' },
      { id: 'incidents', label: 'Incidents', icon: 'incidents', title: 'Incidents', subtitle: 'Correlated incidents with their latest decision and containment controls' },
    ],
  },
  {
    group: 'Investigate',
    pages: [
      { id: 'decision', label: 'Decision Engine', icon: 'decision', title: 'Decision Engine', subtitle: 'Live pipeline mesh: every stage from capture to audit as it happens' },
      { id: 'traffic', label: 'Network Traffic', icon: 'traffic', title: 'Network Traffic', subtitle: 'NFStream capture on the monitored port and the recent flow buffer' },
      { id: 'audit', label: 'Audit Logs', icon: 'audit', title: 'Audit Logs', subtitle: 'Hash-chained decision trail and its integrity check' },
    ],
  },
  {
    group: 'Manage',
    pages: [
      { id: 'system', label: 'System Status', icon: 'system', title: 'System Status', subtitle: 'Detection sources, runtime configuration and backend health' },
      { id: 'settings', label: 'Settings', icon: 'settings', title: 'Settings', subtitle: 'Automation mode and console preferences' },
    ],
  },
];

export const PAGES: PageMeta[] = NAV.flatMap((g) => g.pages);
export const pageMeta = (id: PageId) => PAGES.find((p) => p.id === id) ?? PAGES[0];
