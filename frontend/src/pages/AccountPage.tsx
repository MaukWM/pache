import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';

export function AccountPage() {
  const { user, logout } = useAuth();
  const queryClient = useQueryClient();

  return (
    <div className="space-y-8 max-w-xl">
      <h1 className="text-2xl font-bold">Account</h1>

      <div className="bg-surface rounded-xl p-5 shadow-sm space-y-2">
        <h2 className="font-bold text-lg">Profile</h2>
        <p className="text-text-muted">Logged in as <span className="font-bold text-text">{user?.username}</span></p>
        <button
          onClick={logout}
          className="px-4 py-2 rounded-lg bg-border text-text-muted text-sm font-bold hover:bg-error hover:text-white transition-colors"
        >
          Logout
        </button>
      </div>

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
    <div className="bg-surface rounded-xl p-5 shadow-sm space-y-4">
      <h2 className="font-bold text-lg">Admin · Users</h2>

      {/* Create user */}
      <div className="space-y-2">
        <div className="flex gap-2">
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="New username"
            className="flex-1 px-3 py-2 rounded-lg border border-border bg-surface-alt text-sm focus:outline-none focus:ring-2 focus:ring-wk-kanji"
          />
          <input
            type="text"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password (default: changeme)"
            className="flex-1 px-3 py-2 rounded-lg border border-border bg-surface-alt text-sm focus:outline-none focus:ring-2 focus:ring-wk-kanji"
          />
          <button
            onClick={() => { setMsg(''); createMutation.mutate(); }}
            disabled={!username.trim() || createMutation.isPending}
            className="px-4 py-2 rounded-lg bg-wk-kanji text-white font-bold text-sm hover:bg-accent-hover transition-colors disabled:opacity-50"
          >
            {createMutation.isPending ? 'Creating...' : 'Create'}
          </button>
        </div>
        <label className="flex items-center gap-2 text-sm text-text-muted">
          <input type="checkbox" checked={makeAdmin} onChange={(e) => setMakeAdmin(e.target.checked)} />
          Make this user an admin
        </label>
      </div>

      {/* User list */}
      <div className="divide-y divide-border border border-border rounded-lg overflow-hidden">
        {users.isLoading ? (
          <p className="px-3 py-2 text-sm text-text-muted animate-pulse">Loading users...</p>
        ) : (
          users.data?.map((u) => (
            <div key={u.id} className="px-3 py-2 flex items-center gap-2 text-sm">
              <span className="font-medium">{u.username}</span>
              {u.is_admin && (
                <span className="text-[10px] font-bold bg-wk-kanji/15 text-wk-kanji px-2 py-0.5 rounded-full">
                  admin
                </span>
              )}
              <button
                onClick={() => handleToggleAdmin(u)}
                disabled={adminMutation.isPending || isOnlyAdmin(u)}
                title={isOnlyAdmin(u) ? 'You are the only admin — promote someone else first' : undefined}
                className="ml-auto text-xs text-text-muted hover:text-wk-kanji font-bold disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {u.is_admin ? 'Revoke admin' : 'Make admin'}
              </button>
              <button
                onClick={() => { setMsg(''); resetMutation.mutate(u.id); }}
                disabled={resetMutation.isPending}
                className="text-xs text-text-muted hover:text-error font-bold disabled:opacity-50"
              >
                Reset password
              </button>
            </div>
          ))
        )}
      </div>

      {msg && (
        <p className={`text-sm ${msg.startsWith('⚠') ? 'text-error' : 'text-success'}`}>{msg}</p>
      )}
    </div>
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
    <div className="bg-surface rounded-xl p-5 shadow-sm space-y-4">
      <h2 className="font-bold text-lg">Password</h2>
      <p className="text-sm text-text-muted">
        {hasPassword
          ? 'A password is set. Enter a new one to change it — no need to type the old one.'
          : 'No password set. Anyone who knows your username can log in until you set one.'}
      </p>

      <div className="space-y-2">
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="New password (min 4 chars)"
          className="w-full px-3 py-2 rounded-lg border border-border bg-surface-alt text-sm focus:outline-none focus:ring-2 focus:ring-wk-kanji"
        />
        <input
          type="password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          placeholder="Confirm new password"
          className="w-full px-3 py-2 rounded-lg border border-border bg-surface-alt text-sm focus:outline-none focus:ring-2 focus:ring-wk-kanji"
        />
        <button
          onClick={handleSave}
          disabled={!canSave || saveMutation.isPending}
          className="px-4 py-2 rounded-lg bg-wk-kanji text-white font-bold text-sm hover:bg-accent-hover transition-colors disabled:opacity-50"
        >
          {saveMutation.isPending ? 'Saving...' : hasPassword ? 'Change Password' : 'Set Password'}
        </button>
      </div>

      {msg && (
        <p className={`text-sm ${msg.includes('!') ? 'text-success' : 'text-error'}`}>{msg}</p>
      )}
    </div>
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
    <div className="bg-surface rounded-xl p-5 shadow-sm space-y-4">
      <h2 className="font-bold text-lg">WaniKani Integration</h2>

      {settings.isLoading ? (
        <p className="text-text-muted animate-pulse">Loading...</p>
      ) : (
        <>
          <p className="text-sm text-text-muted">
            {hasKey
              ? 'API key configured. You can import your burned kanji.'
              : 'Add your WaniKani API key to import Guru+ kanji.'}
          </p>

          {/* Save API key */}
          <div className="flex gap-2">
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={hasKey ? 'Replace API key...' : 'Paste your WK API key...'}
              className="flex-1 px-3 py-2 rounded-lg border border-border bg-surface-alt text-sm focus:outline-none focus:ring-2 focus:ring-wk-kanji"
            />
            <button
              onClick={() => saveMutation.mutate(apiKey)}
              disabled={!apiKey.trim() || saveMutation.isPending}
              className="px-4 py-2 rounded-lg bg-wk-kanji text-white font-bold text-sm hover:bg-accent-hover transition-colors disabled:opacity-50"
            >
              {saveMutation.isPending ? 'Saving...' : 'Save'}
            </button>
          </div>

          {/* Actions when key is configured */}
          {hasKey && (
            <div className="flex gap-2">
              <button
                onClick={() => importMutation.mutate()}
                disabled={importMutation.isPending}
                className="px-4 py-2 rounded-lg bg-wk-radical text-white font-bold text-sm hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {importMutation.isPending ? 'Importing...' : 'Import Guru+ Kanji'}
              </button>
              <button
                onClick={() => removeMutation.mutate()}
                disabled={removeMutation.isPending}
                className="px-4 py-2 rounded-lg bg-border text-text-muted text-sm font-bold hover:bg-error hover:text-white transition-colors disabled:opacity-50"
              >
                Remove Key
              </button>
            </div>
          )}

          {importMutation.isPending && (
            <p className="text-sm text-text-muted animate-pulse">
              Fetching from WaniKani API... this can take a minute for large accounts.
            </p>
          )}

          {msg && (
            <p className={`text-sm ${msg.includes('!') ? 'text-success' : 'text-error'}`}>
              {msg}
            </p>
          )}
        </>
      )}
    </div>
  );
}
