import { useState } from 'react';
import { useAuth } from '../lib/auth';

export function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) return;
    setLoading(true);
    setError('');
    try {
      await login(username.trim(), password);
    } catch (err) {
      const status = (err as { status?: number }).status;
      setError(
        status === 401
          ? 'Incorrect password for this account.'
          : 'Failed to log in. Is the API running?',
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center">
      <div className="bg-surface rounded-2xl shadow-lg p-10 w-full max-w-sm text-center">
        <div className="mb-6">
          <div className="w-20 h-20 bg-wk-kanji rounded-full mx-auto flex items-center justify-center mb-4">
            <span className="text-white text-3xl font-bold">漢</span>
          </div>
          <h1 className="text-2xl font-bold text-text">iwkisgwitnwk2</h1>
          <p className="text-text-muted text-sm mt-1">
            Social kanji learning for friends
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter your username"
            autoFocus
            className="w-full px-4 py-3 rounded-lg border border-border bg-surface-alt text-text text-center text-lg focus:outline-none focus:ring-2 focus:ring-wk-kanji focus:border-transparent placeholder:text-text-muted/50"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            className="w-full px-4 py-3 rounded-lg border border-border bg-surface-alt text-text text-center text-lg focus:outline-none focus:ring-2 focus:ring-wk-kanji focus:border-transparent placeholder:text-text-muted/50"
          />
          <button
            type="submit"
            disabled={loading || !username.trim() || !password}
            className="w-full py-3 rounded-lg bg-wk-kanji text-white font-bold text-lg hover:bg-accent-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Logging in...' : 'Log In'}
          </button>
          {error && (
            <p className="text-error text-sm">{error}</p>
          )}
        </form>

        <p className="text-text-muted text-xs mt-6">
          No account? Ask an admin to create one for you.
        </p>
      </div>
    </div>
  );
}
