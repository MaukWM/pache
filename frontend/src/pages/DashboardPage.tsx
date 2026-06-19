import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ExternalLink } from 'lucide-react';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import { cn } from '@/lib/utils';
import { Card } from '@/components/ui/card';

export function DashboardPage() {
  const { user } = useAuth();

  const reviews = useQuery({
    queryKey: ['reviews'],
    queryFn: api.getReviews,
  });

  const queue = useQuery({
    queryKey: ['queue'],
    queryFn: api.getQueue,
  });

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
      <h1 className="text-2xl font-bold">Welcome back, {user?.username}!</h1>

      <div className="grid grid-cols-2 gap-4">
        <Link
          to="/lessons"
          className={cn(
            'rounded-xl p-8 text-center text-white shadow-md transition-all hover:scale-[1.02] hover:shadow-lg',
            lessonCount > 0 ? 'bg-wk-kanji' : 'bg-muted-foreground',
          )}
        >
          <div className="text-5xl font-black">{lessonCount}</div>
          <div className="mt-2 text-sm font-medium opacity-90">Lessons</div>
        </Link>

        <Link
          to="/reviews"
          className={cn(
            'rounded-xl p-8 text-center text-white shadow-md transition-all hover:scale-[1.02] hover:shadow-lg',
            reviewCount > 0 ? 'bg-wk-radical' : 'bg-muted-foreground',
          )}
        >
          <div className="text-5xl font-black">{reviewCount}</div>
          <div className="mt-2 text-sm font-medium opacity-90">Reviews</div>
        </Link>
      </div>

      {wkConfigured && (
        <Card className="p-0 transition-all hover:scale-[1.01] hover:shadow-md">
          <a
            href="https://www.wanikani.com/subjects/review"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between p-5"
          >
            <div className="flex items-baseline gap-3">
              <span className="text-3xl font-black text-wk-kanji">{wkDue}</span>
              <span className="text-sm font-medium text-muted-foreground">
                {wkDue === 1 ? 'review' : 'reviews'} due on WaniKani
              </span>
            </div>
            <span className="flex items-center gap-1 text-sm font-semibold text-wk-kanji">
              Open WaniKani
              <ExternalLink className="size-4" />
            </span>
          </a>
        </Card>
      )}
    </div>
  );
}
