import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import { getSrsGroup } from '../lib/srs';
import { SrsStageBar } from '../components/SrsStageBar';

export function DashboardPage() {
  const { user } = useAuth();

  const reviews = useQuery({
    queryKey: ['reviews'],
    queryFn: api.getReviews,
  });

  const progress = useQuery({
    queryKey: ['progress'],
    queryFn: () => api.getProgress(),
  });

  const queue = useQuery({
    queryKey: ['queue'],
    queryFn: api.getQueue,
  });

  const reviewCount = reviews.data?.length ?? 0;
  const lessonCount = queue.data?.length ?? 0;

  // Compute SRS group counts
  const srsCounts: Record<string, number> = {};
  if (progress.data) {
    for (const item of progress.data) {
      const group = getSrsGroup(item.srs_stage);
      srsCounts[group] = (srsCounts[group] || 0) + 1;
    }
  }

  return (
    <div className="space-y-6">
      {/* Greeting */}
      <div>
        <h1 className="text-2xl font-bold">
          Welcome back, {user?.username}!
        </h1>
        <p className="text-text-muted mt-1">
          {reviewCount > 0
            ? `You have ${reviewCount} review${reviewCount !== 1 ? 's' : ''} waiting.`
            : 'No reviews due right now. Nice work!'}
        </p>
      </div>

      {/* Action cards */}
      <div className="grid grid-cols-2 gap-4">
        <Link
          to="/reviews"
          className={`rounded-xl p-6 text-white text-center shadow-md hover:shadow-lg transition-all hover:scale-[1.02] ${
            reviewCount > 0 ? 'bg-wk-kanji' : 'bg-text-muted'
          }`}
        >
          <div className="text-4xl font-black">{reviewCount}</div>
          <div className="text-sm font-medium mt-1 opacity-90">Reviews</div>
        </Link>

        <Link
          to="/lessons"
          className={`rounded-xl p-6 text-white text-center shadow-md hover:shadow-lg transition-all hover:scale-[1.02] ${
            lessonCount > 0 ? 'bg-wk-radical' : 'bg-text-muted'
          }`}
        >
          <div className="text-4xl font-black">{lessonCount}</div>
          <div className="text-sm font-medium mt-1 opacity-90">Lessons</div>
        </Link>
      </div>

      {/* SRS Progress bar */}
      <div>
        <h2 className="text-lg font-bold mb-3">SRS Progress</h2>
        {progress.isLoading ? (
          <div className="bg-surface rounded-xl p-6 text-center text-text-muted animate-pulse">
            Loading progress...
          </div>
        ) : (
          <SrsStageBar counts={srsCounts} />
        )}
      </div>

      {/* Recent items due */}
      {reviewCount > 0 && reviews.data && (
        <div>
          <h2 className="text-lg font-bold mb-3">Up Next for Review</h2>
          <div className="flex gap-3 flex-wrap">
            {reviews.data.slice(0, 10).map((item) => {
              const isKanji = item.item_type === 'kanji';
              const display = item.item_details.character || item.item_details.word || '?';
              return (
                <div
                  key={`${item.item_type}-${item.item_id}`}
                  className={`${isKanji ? 'bg-wk-kanji' : 'bg-wk-vocab'} w-14 h-14 rounded-lg flex items-center justify-center text-white font-bold text-xl shadow-sm`}
                  title={item.item_details.meanings?.join(', ')}
                >
                  {display}
                </div>
              );
            })}
            {reviewCount > 10 && (
              <div className="w-14 h-14 rounded-lg flex items-center justify-center bg-border text-text-muted font-bold text-sm">
                +{reviewCount - 10}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
