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
      <h1 className="text-2xl font-bold">Account</h1>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Profile</CardTitle>
          <CardDescription>
            Logged in as <span className="font-bold text-foreground">{user?.username}</span>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="destructive" onClick={logout}>
            Logout
          </Button>
        </CardContent>
      </Card>

      <PasswordSettings queryClient={queryClient} />

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
      setMsg(`Created "${created.username}" — password: ${created.password}`);
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
      setMsg(`Reset "${updated.username}" — new password: ${updated.password}`);
    },
    onError: (err: Error) => setMsg(`⚠ ${err.message}`),
  });

  const adminMutation = useMutation({
    mutationFn: ({ userId, isAdmin }: { userId: number; isAdmin: boolean }) =>
      api.setUserAdmin(userId, isAdmin),
    onSuccess: (updated) => {
      setMsg(`"${updated.username}" is now ${updated.is_admin ? 'an admin' : 'a regular user'}.`);
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
        setMsg('⚠ You are the only admin — promote someone else before revoking your own access.');
        return;
      }
      if (
        !window.confirm(
          'Revoke your OWN admin access? You will immediately lose user management ' +
            'and cannot restore it yourself — another admin would have to.',
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
        <CardTitle className="text-lg">Admin · Users</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Create user */}
        <div className="space-y-2">
          <div className="flex gap-2">
            <Input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="New username"
            />
            <Input
              type="text"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password (default: changeme)"
            />
            <Button
              onClick={() => { setMsg(''); createMutation.mutate(); }}
              disabled={!username.trim() || createMutation.isPending}
            >
              {createMutation.isPending ? 'Creating...' : 'Create'}
            </Button>
          </div>
          <Label className="text-muted-foreground font-normal">
            <input type="checkbox" checked={makeAdmin} onChange={(e) => setMakeAdmin(e.target.checked)} />
            Make this user an admin
          </Label>
        </div>

        {/* User list */}
        <div className="divide-y divide-border border border-border rounded-lg overflow-hidden">
          {users.isLoading ? (
            <p className="px-3 py-2 text-sm text-muted-foreground animate-pulse">Loading users...</p>
          ) : (
            users.data?.map((u) => (
              <div key={u.id} className="px-3 py-2 flex items-center gap-2 text-sm">
                <span className="font-medium">{u.username}</span>
                {u.is_admin && (
                  <Badge className="bg-wk-kanji/15 text-wk-kanji text-[10px]">admin</Badge>
                )}
                <button
                  onClick={() => handleToggleAdmin(u)}
                  disabled={adminMutation.isPending || isOnlyAdmin(u)}
                  title={isOnlyAdmin(u) ? 'You are the only admin — promote someone else first' : undefined}
                  className="ml-auto text-xs text-muted-foreground hover:text-wk-kanji font-bold disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {u.is_admin ? 'Revoke admin' : 'Make admin'}
                </button>
                <button
                  onClick={() => { setMsg(''); resetMutation.mutate(u.id); }}
                  disabled={resetMutation.isPending}
                  className="text-xs text-muted-foreground hover:text-destructive font-bold disabled:opacity-50"
                >
                  Reset password
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
      setMsg('Password updated!');
      setPassword('');
      setConfirm('');
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
    onError: (err: Error) => setMsg(`⚠ ${err.message}`),
  });

  const canSave = password.length >= 4 && password === confirm;

  const handleSave = () => {
    if (password !== confirm) {
      setMsg('Passwords do not match.');
      return;
    }
    setMsg('');
    saveMutation.mutate(password);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Password</CardTitle>
        <CardDescription>
          {hasPassword
            ? 'A password is set. Enter a new one to change it — no need to type the old one.'
            : 'No password set. Anyone who knows your username can log in until you set one.'}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        <Input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="New password (min 4 chars)"
        />
        <Input
          type="password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          placeholder="Confirm new password"
        />
        <Button onClick={handleSave} disabled={!canSave || saveMutation.isPending}>
          {saveMutation.isPending ? 'Saving...' : hasPassword ? 'Change Password' : 'Set Password'}
        </Button>

        {msg && (
          <p className={cn('text-sm', msg.includes('!') ? 'text-success' : 'text-destructive')}>{msg}</p>
        )}
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
      setMsg('API key saved!');
      setApiKey('');
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
    onError: (err: Error) => setMsg(`⚠ ${err.message}`),
  });

  const removeMutation = useMutation({
    mutationFn: () => api.removeSettings(),
    onSuccess: () => {
      setMsg('API key removed.');
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
    onError: (err: Error) => setMsg(`⚠ ${err.message}`),
  });

  const importMutation = useMutation({
    mutationFn: api.importWanikani,
    onSuccess: (data) => {
      setMsg(`Imported ${data.imported_count} kanji from ${data.total_fetched} Guru+ items! (${data.skipped_count} skipped, ${data.already_existed} already existed)`);
      queryClient.invalidateQueries({ queryKey: ['kanji'] });
      queryClient.invalidateQueries({ queryKey: ['progress'] });
    },
    onError: (err: Error) => setMsg(`⚠ ${err.message}`),
  });

  const hasKey = settings.data?.wk_api_key_configured ?? false;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">WaniKani Integration</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {settings.isLoading ? (
          <p className="text-muted-foreground animate-pulse">Loading...</p>
        ) : (
          <>
            <p className="text-sm text-muted-foreground">
              {hasKey
                ? 'API key configured. You can import your burned kanji.'
                : 'Add your WaniKani API key to import Guru+ kanji.'}
            </p>

            {/* Save API key */}
            <div className="flex gap-2">
              <Input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={hasKey ? 'Replace API key...' : 'Paste your WK API key...'}
              />
              <Button
                onClick={() => saveMutation.mutate(apiKey)}
                disabled={!apiKey.trim() || saveMutation.isPending}
              >
                {saveMutation.isPending ? 'Saving...' : 'Save'}
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
                    {importMutation.isPending ? 'Importing...' : 'Import Guru+ Kanji'}
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={() => removeMutation.mutate()}
                    disabled={removeMutation.isPending}
                  >
                    Remove Key
                  </Button>
                </div>
              </>
            )}

            {importMutation.isPending && (
              <p className="text-sm text-muted-foreground animate-pulse">
                Fetching from WaniKani API... this can take a minute for large accounts.
              </p>
            )}

            {msg && (
              <p className={cn('text-sm', msg.includes('!') ? 'text-success' : 'text-destructive')}>
                {msg}
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
