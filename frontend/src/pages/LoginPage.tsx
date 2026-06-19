import { useState } from 'react';
import { useAuth } from '../lib/auth';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

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
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="items-center text-center">
          <div className="mx-auto mb-2 flex size-16 items-center justify-center rounded-full bg-wk-kanji">
            <span lang="ja" className="text-3xl font-bold text-white">
              漢
            </span>
          </div>
          <CardTitle className="text-2xl">iwkisgwitnwk2</CardTitle>
          <CardDescription>Social kanji learning for friends</CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your username"
                autoFocus
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
              />
            </div>

            <Button
              type="submit"
              disabled={loading || !username.trim() || !password}
              className="w-full"
            >
              {loading ? 'Logging in...' : 'Log In'}
            </Button>

            {error && <p className="text-sm text-destructive">{error}</p>}
          </form>

          <p className="mt-6 text-center text-xs text-muted-foreground">
            No account? Ask an admin to create one for you.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
