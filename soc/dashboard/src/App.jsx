import { useEffect, useState } from 'react';
import Landing from './landing/Landing';
import ConsoleApp from './console/ConsoleApp';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const isConsoleHash = () => typeof window !== 'undefined' && window.location.hash === '#console';

/** Two views: the landing page and the SOC console (#console). */
export default function App() {
  const [view, setView] = useState(() => (isConsoleHash() ? 'console' : 'landing'));

  useEffect(() => {
    const onHash = () => setView(isConsoleHash() ? 'console' : 'landing');
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const go = (next) => {
    window.location.hash = next === 'console' ? '#console' : '';
    setView(next);
    window.scrollTo({ top: 0 });
  };

  return view === 'console'
    ? <ConsoleApp apiBase={API_BASE} onExit={() => go('landing')} />
    : <Landing onOpenConsole={() => go('console')} />;
}
