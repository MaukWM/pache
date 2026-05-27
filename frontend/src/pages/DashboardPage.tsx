import { useAuth } from '../lib/auth';

export function DashboardPage() {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Welcome back, {user?.username}!</h1>
      <p className="text-text-muted">
        Head to the Kanji page to start browsing and learning.
      </p>
    </div>
  );
}
