import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';

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

  const reviewCount = reviews.data?.length ?? 0;
  const lessonCount = queue.data?.length ?? 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Welcome back, {user?.username}!</h1>

      <div className="grid grid-cols-2 gap-4">
        <Link
          to="/reviews"
          className={`rounded-xl p-8 text-white text-center shadow-md hover:shadow-lg transition-all hover:scale-[1.02] ${
            reviewCount > 0 ? 'bg-wk-kanji' : 'bg-text-muted'
          }`}
        >
          <div className="text-5xl font-black">{reviewCount}</div>
          <div className="text-sm font-medium mt-2 opacity-90">Reviews</div>
        </Link>

        <Link
          to="/lessons"
          className={`rounded-xl p-8 text-white text-center shadow-md hover:shadow-lg transition-all hover:scale-[1.02] ${
            lessonCount > 0 ? 'bg-wk-radical' : 'bg-text-muted'
          }`}
        >
          <div className="text-5xl font-black">{lessonCount}</div>
          <div className="text-sm font-medium mt-2 opacity-90">Lessons</div>
        </Link>
      </div>
    </div>
  );
}
