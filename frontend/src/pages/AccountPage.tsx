import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import { cn } from '@/lib/utils';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';

export function AccountPage() {
  const { user, logout } = useAuth();
  const queryClient = useQueryClient();

  return (
    <div className="space-y-8 max-w-xl">
      <h1 className="text-2xl font-bold">アカウント</h1>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">プロフィール</CardTitle>
          <CardDescription>
            <span className="font-bold text-foreground">{user?.username}</span> でログイン中
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="destructive" onClick={logout}>
            ログアウト
          </Button>
        </CardContent>
      </Card>

      <PasswordSettings queryClient={queryClient} />

      <ReviewSettings queryClient={queryClient} />

      {user?.is_admin && <AdminUsers queryClient={queryClient} />}

      <WaniKaniSettings queryClient={queryClient} />
    </div>
  );
}

function AdminUsers({ queryClient }: { queryClient: ReturnType<typeof useQueryClient> }) {
  const { user: currentUser } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [makeAdmin, setMakeAdmin] = useState(false);
  const [msg, setMsg] = useState('');

  const users = useQuery({ queryKey: ['users'], queryFn: api.listUsers });

  const createMutation = useMutation({
    mutationFn: () => api.createUser(username.trim(), password || undefined, makeAdmin),
    onSuccess: (created) => {
      setMsg(`「${created.username}」を作成しました — パスワード: ${created.password}`);
      setUsername('');
      setPassword('');
      setMakeAdmin(false);
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (err: Error) => setMsg(`⚠ ${err.message}`),
  });

  const resetMutation = useMutation({
    mutationFn: (userId: number) => api.resetUserPassword(userId),
    onSuccess: (updated) => {
      setMsg(`「${updated.username}」をリセットしました — 新しいパスワード: ${updated.password}`);
    },
    onError: (err: Error) => setMsg(`⚠ ${err.message}`),
  });

  const adminMutation = useMutation({
    mutationFn: ({ userId, isAdmin }: { userId: number; isAdmin: boolean }) =>
      api.setUserAdmin(userId, isAdmin),
    onSuccess: (updated) => {
      setMsg(`「${updated.username}」は${updated.is_admin ? '管理者' : '一般ユーザー'}になりました。`);
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (err: Error) => setMsg(`⚠ ${err.message}`),
  });

  const sentencesMutation = useMutation({
    mutationFn: ({ userId, enabled }: { userId: number; enabled: boolean }) =>
      api.setUserSentences(userId, enabled),
    onSuccess: (updated) => {
      setMsg(`「${updated.username}」の作文アクセスを${updated.sentences_enabled ? '有効' : '無効'}にしました。`);
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (err: Error) => setMsg(`⚠ ${err.message}`),
  });

  const adminCount = (users.data ?? []).filter((u) => u.is_admin).length;
  const isOnlyAdmin = (u: { id: number; is_admin?: boolean }) =>
    u.id === currentUser?.id && !!u.is_admin && adminCount <= 1;

  const handleToggleAdmin = (u: { id: number; username: string; is_admin?: boolean }) => {
    const revokingSelf = u.id === currentUser?.id && u.is_admin;
    if (revokingSelf) {
      if (adminCount <= 1) {
        setMsg('⚠ あなたは唯一の管理者です。自分の権限を取り消す前に、別のユーザーを管理者に昇格させてください。');
        return;
      }
      if (
        !window.confirm(
          '自分自身の管理者権限を取り消しますか？ ただちにユーザー管理ができなくなり、' +
            '自分では復元できません。別の管理者に依頼する必要があります。',
        )
      ) {
        return;
      }
    }
    setMsg('');
    adminMutation.mutate({ userId: u.id, isAdmin: !u.is_admin });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">管理者 · ユーザー</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Create user */}
        <div className="space-y-2">
          <div className="flex gap-2">
            <Input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="新しいユーザー名"
            />
            <Input
              type="text"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="パスワード（既定: changeme）"
            />
            <Button
              onClick={() => { setMsg(''); createMutation.mutate(); }}
              disabled={!username.trim() || createMutation.isPending}
            >
              {createMutation.isPending ? '作成中...' : '作成'}
            </Button>
          </div>
          <Label className="text-muted-foreground font-normal">
            <input type="checkbox" checked={makeAdmin} onChange={(e) => setMakeAdmin(e.target.checked)} />
            このユーザーを管理者にする
          </Label>
        </div>

        {/* User list */}
        <div className="divide-y divide-border border border-border rounded-lg overflow-hidden">
          {users.isLoading ? (
            <p className="px-3 py-2 text-sm text-muted-foreground animate-pulse">ユーザーを読み込み中...</p>
          ) : (
            users.data?.map((u) => (
              <div key={u.id} className="px-3 py-2 flex items-center gap-2 text-sm">
                <span className="font-medium">{u.username}</span>
                {u.is_admin && (
                  <Badge className="bg-wk-kanji/15 text-wk-kanji text-[10px]">管理者</Badge>
                )}
                {(u.is_admin || u.sentences_enabled) && (
                  <Badge className="bg-wk-sentence/15 text-wk-sentence text-[10px]">作文</Badge>
                )}
                <button
                  onClick={() =>
                    !u.is_admin &&
                    (setMsg(''), sentencesMutation.mutate({ userId: u.id, enabled: !u.sentences_enabled }))
                  }
                  disabled={sentencesMutation.isPending || u.is_admin}
                  title={u.is_admin ? '管理者は作文に常にアクセスできます' : undefined}
                  className="ml-auto text-xs text-muted-foreground hover:text-wk-sentence font-bold disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {u.sentences_enabled ? '作文を無効' : '作文を有効'}
                </button>
                <button
                  onClick={() => handleToggleAdmin(u)}
                  disabled={adminMutation.isPending || isOnlyAdmin(u)}
                  title={isOnlyAdmin(u) ? 'あなたは唯一の管理者です。先に別のユーザーを昇格させてください' : undefined}
                  className="text-xs text-muted-foreground hover:text-wk-kanji font-bold disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {u.is_admin ? '管理者を解除' : '管理者にする'}
                </button>
                <button
                  onClick={() => { setMsg(''); resetMutation.mutate(u.id); }}
                  disabled={resetMutation.isPending}
                  className="text-xs text-muted-foreground hover:text-destructive font-bold disabled:opacity-50"
                >
                  パスワードをリセット
                </button>
              </div>
            ))
          )}
        </div>

        {msg && (
          <p className={cn('text-sm', msg.startsWith('⚠') ? 'text-destructive' : 'text-success')}>{msg}</p>
        )}
      </CardContent>
    </Card>
  );
}

function PasswordSettings({ queryClient }: { queryClient: ReturnType<typeof useQueryClient> }) {
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [msg, setMsg] = useState('');

  const settings = useQuery({ queryKey: ['settings'], queryFn: api.getSettings });
  const hasPassword = settings.data?.password_set ?? false;

  const saveMutation = useMutation({
    mutationFn: (newPassword: string) => api.setPassword(newPassword),
    onSuccess: () => {
      setMsg('パスワードを更新しました！');
      setPassword('');
      setConfirm('');
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
    onError: (err: Error) => setMsg(`⚠ ${err.message}`),
  });

  const canSave = password.length >= 4 && password === confirm;

  const handleSave = () => {
    if (password !== confirm) {
      setMsg('⚠ パスワードが一致しません。');
      return;
    }
    setMsg('');
    saveMutation.mutate(password);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">パスワード</CardTitle>
        <CardDescription>
          {hasPassword
            ? 'パスワードは設定済みです。変更するには新しいパスワードを入力してください。古いパスワードの入力は不要です。'
            : 'パスワードが未設定です。設定するまで、ユーザー名を知っている人なら誰でもログインできます。'}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        <Input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="新しいパスワード（4文字以上）"
        />
        <Input
          type="password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          placeholder="新しいパスワードを再入力"
        />
        <Button onClick={handleSave} disabled={!canSave || saveMutation.isPending}>
          {saveMutation.isPending ? '保存中...' : hasPassword ? 'パスワードを変更' : 'パスワードを設定'}
        </Button>

        {msg && (
          <p className={cn('text-sm', msg.startsWith('⚠') ? 'text-destructive' : 'text-success')}>{msg}</p>
        )}
      </CardContent>
    </Card>
  );
}

function ReviewSettings({ queryClient }: { queryClient: ReturnType<typeof useQueryClient> }) {
  const settings = useQuery({ queryKey: ['settings'], queryFn: api.getSettings });
  const mode = settings.data?.review_mode ?? 'paired';

  const saveMutation = useMutation({
    mutationFn: api.setReviewMode,
    onSuccess: (data) => {
      queryClient.setQueryData(['settings'], data);
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
  });

  const OPTIONS: { value: 'paired' | 'scrambled'; label: string; desc: string }[] = [
    { value: 'paired', label: 'ペア', desc: '各項目の読みと意味を続けて出題します。' },
    { value: 'scrambled', label: 'シャッフル', desc: 'すべてのカードをシャッフルして出題します。' },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">復習の出題順</CardTitle>
        <CardDescription>復習を開始したときの既定の出題方法です。</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-3">
          {OPTIONS.map((opt) => (
            <Button
              key={opt.value}
              variant={mode === opt.value ? 'default' : 'outline'}
              disabled={saveMutation.isPending || settings.isLoading}
              onClick={() => saveMutation.mutate(opt.value)}
            >
              {opt.label}
            </Button>
          ))}
        </div>
        <p className="text-sm text-muted-foreground">
          {OPTIONS.find((o) => o.value === mode)?.desc}
        </p>
      </CardContent>
    </Card>
  );
}

function WaniKaniSettings({ queryClient }: { queryClient: ReturnType<typeof useQueryClient> }) {
  const [apiKey, setApiKey] = useState('');
  const [msg, setMsg] = useState('');

  const settings = useQuery({
    queryKey: ['settings'],
    queryFn: api.getSettings,
  });

  const saveMutation = useMutation({
    mutationFn: (key: string) => api.updateSettings(key),
    onSuccess: () => {
      setMsg('APIキーを保存しました！');
      setApiKey('');
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
    onError: (err: Error) => setMsg(`⚠ ${err.message}`),
  });

  const removeMutation = useMutation({
    mutationFn: () => api.removeSettings(),
    onSuccess: () => {
      setMsg('APIキーを削除しました。');
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
    onError: (err: Error) => setMsg(`⚠ ${err.message}`),
  });

  const importMutation = useMutation({
    mutationFn: api.importWanikani,
    onSuccess: (data) => {
      setMsg(`${data.total_fetched}件のGuru+項目から${data.imported_count}件を新規インポート、${data.updated_count}件を更新しました！（${data.skipped_count}件スキップ、${data.already_existed}件は変更なし）`);
      queryClient.invalidateQueries({ queryKey: ['kanji'] });
      queryClient.invalidateQueries({ queryKey: ['progress'] });
      queryClient.invalidateQueries({ queryKey: ['wanikani'] });
    },
    onError: (err: Error) => setMsg(`⚠ ${err.message}`),
  });

  const hasKey = settings.data?.wk_api_key_configured ?? false;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">WaniKani連携</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {settings.isLoading ? (
          <p className="text-muted-foreground animate-pulse">読み込み中...</p>
        ) : (
          <>
            <p className="text-sm text-muted-foreground">
              {hasKey
                ? 'APIキーは設定済みです。Guru+の漢字をインポートできます（再インポートでWaniKaniの進捗に合わせて更新）。'
                : 'WaniKaniのAPIキーを追加して、Guru+の漢字をインポートしましょう。'}
            </p>

            {/* Masked indicator that a key is stored (server never returns the key). */}
            {hasKey && (
              <div className="flex items-center gap-2">
                <span
                  aria-hidden
                  className="flex-1 select-none border border-border bg-muted px-3 py-2 font-mono text-sm tracking-[0.3em] text-muted-foreground"
                >
                  ••••••••••••••••
                </span>
                <Badge variant="secondary">設定済み</Badge>
              </div>
            )}

            {/* Save API key */}
            <div className="flex gap-2">
              <Input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={hasKey ? 'APIキーを置き換える...' : 'WaniKaniのAPIキーを貼り付け...'}
              />
              <Button
                onClick={() => saveMutation.mutate(apiKey)}
                disabled={!apiKey.trim() || saveMutation.isPending}
              >
                {saveMutation.isPending ? '保存中...' : '保存'}
              </Button>
            </div>

            {/* Actions when key is configured */}
            {hasKey && (
              <>
                <Separator />
                <div className="flex gap-2">
                  <Button
                    onClick={() => importMutation.mutate()}
                    disabled={importMutation.isPending}
                  >
                    {importMutation.isPending ? 'インポート中...' : 'Guru+の漢字をインポート'}
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={() => removeMutation.mutate()}
                    disabled={removeMutation.isPending}
                  >
                    キーを削除
                  </Button>
                </div>
              </>
            )}

            {importMutation.isPending && (
              <p className="text-sm text-muted-foreground animate-pulse">
                WaniKani APIから取得中... アカウントが大きい場合は1分ほどかかることがあります。
              </p>
            )}

            {msg && (
              <p className={cn('text-sm', msg.startsWith('⚠') ? 'text-destructive' : 'text-success')}>
                {msg}
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
