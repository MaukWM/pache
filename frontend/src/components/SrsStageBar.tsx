import { getSrsGroupColor } from '../lib/srs';

interface SrsStageBarProps {
  counts: Record<string, number>;
}

export function SrsStageBar({ counts }: SrsStageBarProps) {
  const groups = ['Apprentice', 'Guru', 'Master', 'Enlightened', 'Burned'];
  const total = groups.reduce((sum, g) => sum + (counts[g] || 0), 0);

  if (total === 0) {
    return (
      <div className="bg-surface rounded-xl p-6 text-center text-text-muted">
        No items in SRS yet. Complete some lessons to get started!
      </div>
    );
  }

  return (
    <div className="bg-surface rounded-xl p-5 shadow-sm">
      <div className="flex rounded-lg overflow-hidden h-8 mb-4">
        {groups.map((group) => {
          const count = counts[group] || 0;
          if (count === 0) return null;
          const pct = (count / total) * 100;
          return (
            <div
              key={group}
              className="flex items-center justify-center text-white text-xs font-bold transition-all"
              style={{ width: `${pct}%`, backgroundColor: getSrsGroupColor(group) }}
              title={`${group}: ${count}`}
            >
              {pct > 8 ? count : ''}
            </div>
          );
        })}
      </div>
      <div className="flex justify-between">
        {groups.map((group) => (
          <div key={group} className="text-center">
            <div
              className="text-xs font-bold uppercase tracking-wide"
              style={{ color: getSrsGroupColor(group) }}
            >
              {group}
            </div>
            <div className="text-lg font-bold">{counts[group] || 0}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
