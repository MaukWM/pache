import { getSrsGroupColor } from '../lib/srs';
import { Card } from '@/components/ui/card';

interface SrsStageBarProps {
  counts: Record<string, number>;
}

export function SrsStageBar({ counts }: SrsStageBarProps) {
  const groups = ['アプレンティス', 'グル', 'マスター', 'エンライテンド', 'バーンド'];
  const total = groups.reduce((sum, g) => sum + (counts[g] || 0), 0);

  if (total === 0) {
    return (
      <Card className="items-center p-6 text-center text-sm text-muted-foreground">
        まだSRSに項目がありません。レッスンを完了して始めましょう！
      </Card>
    );
  }

  return (
    <Card className="gap-4 p-5">
      <div className="mb-1 flex h-8 overflow-hidden rounded-lg">
        {groups.map((group) => {
          const count = counts[group] || 0;
          if (count === 0) return null;
          const pct = (count / total) * 100;
          return (
            <div
              key={group}
              className="flex items-center justify-center text-xs font-bold text-white transition-all"
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
              className="text-xs font-bold tracking-wide uppercase"
              style={{ color: getSrsGroupColor(group) }}
            >
              {group}
            </div>
            <div className="text-lg font-bold">{counts[group] || 0}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}
