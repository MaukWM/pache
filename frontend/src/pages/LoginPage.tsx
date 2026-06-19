import { useState } from 'react';
import { useAuth } from '../lib/auth';
import { GlyphCell } from '../components/GlyphCell';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
          ? 'このアカウントのパスワードが正しくありません。'
          : 'ログインに失敗しました。APIは起動していますか？',
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="items-center text-center">
          <div className="mb-2">
            <GlyphCell type="kanji" character="漢" size="lg" />
          </div>
          <CardTitle className="text-2xl">iwkisgwitnwk2</CardTitle>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">ユーザー名</Label>
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="ユーザー名を入力"
                autoFocus
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">パスワード</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="パスワード"
              />
            </div>

            <Button
              type="submit"
              disabled={loading || !username.trim() || !password}
              className="w-full"
            >
              {loading ? 'ログイン中...' : 'ログイン'}
            </Button>

            {error && <p className="text-sm text-destructive">{error}</p>}
          </form>

          <p className="mt-6 text-center text-xs text-muted-foreground">
            アカウントがありませんか？管理者に作成を依頼してください。
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
