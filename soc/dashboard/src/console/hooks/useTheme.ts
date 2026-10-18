import { useCallback, useEffect, useState } from 'react';

export type Theme = 'dark' | 'light';
export const THEME_KEY = 'rashomon-console-theme';

export function readStoredTheme(): Theme | null {
  try {
    const v = localStorage.getItem(THEME_KEY);
    return v === 'dark' || v === 'light' ? v : null;
  } catch {
    return null;   // storage blocked: follow the OS preference
  }
}

const systemTheme = (): Theme =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';

/**
 * Explicit choice: localStorage + <html data-theme>. No stored choice: the
 * attribute is removed and the console's CSS follows prefers-color-scheme.
 * The attribute is cleared again when the console unmounts (landing page).
 */
export function useTheme() {
  const [stored, setStored] = useState<Theme | null>(readStoredTheme);
  const [system, setSystem] = useState<Theme>(systemTheme);

  useEffect(() => {
    const mq = window.matchMedia?.('(prefers-color-scheme: light)');
    if (!mq) return;
    const onChange = () => setSystem(mq.matches ? 'light' : 'dark');
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (stored) root.dataset.theme = stored;
    else delete root.dataset.theme;
    return () => { delete root.dataset.theme; };
  }, [stored]);

  const theme: Theme = stored ?? system;
  const toggle = useCallback(() => {
    const next: Theme = theme === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem(THEME_KEY, next); } catch { /* choice lasts this session only */ }
    setStored(next);
  }, [theme]);

  return { theme, toggle };
}
