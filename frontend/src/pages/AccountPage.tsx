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

      <WaniKaniSettings queryClient={queryClient} />
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
    onError: (err: Error) => setMsg(err.message),
  });

  const removeMutation = useMutation({
    mutationFn: () => api.removeSettings(),
    onSuccess: () => {
      setMsg('API key removed.');
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
    onError: (err: Error) => setMsg(err.message),
  });

  const importMutation = useMutation({
    mutationFn: api.importWanikani,
    onSuccess: (data) => {
      setMsg(`Imported ${data.imported_count} kanji from ${data.total_fetched} Guru+ items! (${data.skipped_count} skipped, ${data.already_existed} already existed)`);
      queryClient.invalidateQueries({ queryKey: ['kanji'] });
      queryClient.invalidateQueries({ queryKey: ['progress'] });
    },
    onError: (err: Error) => setMsg(err.message),
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
