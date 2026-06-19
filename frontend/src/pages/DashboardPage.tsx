import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ExternalLink } from 'lucide-react';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import { cn } from '@/lib/utils';

// A genkō-style stat slab: big mincho numeral, mono label, sharp bordered card.
// "Ready" marker (not a loud color fill) signals there's something to do.
function StatTile({ to, count, label }: { to: string; count: number; label: string }) {
  const active = count > 0;
  return (
    <Link
      to={to}
      className={cn(
        'group relative flex flex-col items-center justify-center border-2 bg-card p-10 transition-colors hover:bg-accent',
        active ? 'border-foreground/40' : 'border-border',
      )}
    >
      {active && (
        <span className="absolute top-3 right-3 font-mono text-[10px] tracking-wider text-muted-foreground uppercase">
          準備完了
        </span>
      )}
      <span
        className={cn(
          'font-[family-name:var(--font-mincho)] text-6xl leading-none tabular-nums',
          active ? 'text-foreground' : 'text-muted-foreground/60',
        )}
      >
        {count}
      </span>
      <span className="mt-3 font-mono text-xs tracking-[0.2em] text-muted-foreground uppercase">
        {label}
      </span>
    </Link>
  );
}

export function DashboardPage() {
  const { user } = useAuth();

  const reviews = useQuery({ queryKey: ['reviews'], queryFn: api.getReviews });
  const queue = useQuery({ queryKey: ['queue'], queryFn: api.getQueue });
  const wanikani = useQuery({
    queryKey: ['wanikani-status'],
    queryFn: api.getWanikaniStatus,
    retry: false,
  });

  const reviewCount = reviews.data?.length ?? 0;
  const lessonCount = queue.data?.filter((i) => !i.locked).length ?? 0;
  const wkConfigured = wanikani.data?.configured ?? false;
  const wkDue = wanikani.data?.reviews_due ?? 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">おかえりなさい、{user?.username}！</h1>

      <div className="grid grid-cols-2 gap-4">
        <StatTile to="/lessons" count={lessonCount} label="レッスン" />
        <StatTile to="/reviews" count={reviewCount} label="復習" />
      </div>

      {wkConfigured && (
        <a
          href="https://www.wanikani.com/subjects/review"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-between border border-border bg-card p-5 transition-colors hover:bg-accent"
        >
          <div className="flex items-baseline gap-3">
            <span className="font-[family-name:var(--font-mincho)] text-3xl tabular-nums">{wkDue}</span>
            <span className="text-sm text-muted-foreground">
              WaniKaniの復習
            </span>
          </div>
          <span className="flex items-center gap-1.5 font-mono text-xs tracking-wider text-muted-foreground uppercase">
            WaniKaniを開く
            <ExternalLink className="size-3.5" />
          </span>
        </a>
      )}
    </div>
  );
}
