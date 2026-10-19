import type { NamedCount } from '../data/types';
import { pct, shareOfMax } from '../data/derive';
import { Empty } from './Panel';

/* Label left, count right, 6px track with an accent fill scaled to the list maximum. */
export function BarList({ items, mono = false, empty = 'Nothing in the last 24 hours.' }: { items: NamedCount[]; mono?: boolean; empty?: string }) {
  if (!items.length) return <Empty>{empty}</Empty>;
  const counts = items.map((i) => i.count);
  return (
    <ul className="soc-bars">
      {items.map((item) => (
        <li key={item.name}>
          <div className="soc-bar-top">
            <span className={mono ? 'soc-mono' : undefined} title={item.name}>{item.name}</span>
            <span className="soc-bar-count">{item.count.toLocaleString('en-US')}</span>
          </div>
          <div className="soc-track" aria-hidden="true">
            <div className="soc-fill" style={{ width: pct(shareOfMax(item.count, counts)) }} />
          </div>
        </li>
      ))}
    </ul>
  );
}
