import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';

export function VocabPage() {
  const queryClient = useQueryClient();
  const [tagFilter, setTagFilter] = useState('');
  const [creatorFilter, setCreatorFilter] = useState('');
  const [showCreate, setShowCreate] = useState(false);

  const params: Record<string, string> = {};
  if (tagFilter) params.tag = tagFilter;
  if (creatorFilter) params.creator = creatorFilter;

  const vocab = useQuery({
    queryKey: ['vocab', params],
    queryFn: () => api.getVocab(Object.keys(params).length ? params : undefined),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Vocabulary Pool</h1>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 rounded-lg bg-wk-vocab text-white font-bold hover:opacity-90 transition-opacity"
        >
          {showCreate ? 'Cancel' : '+ Add Vocab'}
        </button>
      </div>

      {showCreate && (
        <CreateVocabForm
          onCreated={() => {
            setShowCreate(false);
            queryClient.invalidateQueries({ queryKey: ['vocab'] });
          }}
        />
      )}

      {/* Filters */}
      <div className="flex gap-3">
        <input
          type="text"
          placeholder="Filter by tag..."
          value={tagFilter}
          onChange={(e) => setTagFilter(e.target.value)}
          className="px-3 py-2 rounded-lg border border-border bg-surface text-sm focus:outline-none focus:ring-2 focus:ring-wk-vocab"
        />
        <input
          type="text"
          placeholder="Filter by creator..."
          value={creatorFilter}
          onChange={(e) => setCreatorFilter(e.target.value)}
          className="px-3 py-2 rounded-lg border border-border bg-surface text-sm focus:outline-none focus:ring-2 focus:ring-wk-vocab"
        />
      </div>

      {/* Vocab list */}
      {vocab.isLoading ? (
        <div className="text-text-muted animate-pulse">Loading...</div>
      ) : (
        <div className="grid gap-3">
          {(vocab.data || []).length === 0 ? (
            <div className="bg-surface rounded-xl p-8 text-center text-text-muted">
              No vocabulary yet. Be the first to add some!
            </div>
          ) : (
            vocab.data?.map((item) => (
              <div
                key={item.id}
                className="bg-surface rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow flex items-center gap-4"
              >
                <div className="bg-wk-vocab w-14 h-14 rounded-lg flex items-center justify-center text-white font-bold text-xl shrink-0">
                  {item.word}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline gap-2">
                    <span className="font-bold text-lg">{item.word}</span>
                    <span className="text-text-muted">{item.reading}</span>
                  </div>
                  <div className="text-sm text-text-muted">{item.meanings.join(', ')}</div>
                  <div className="flex gap-2 mt-1">
                    {item.tags?.map((tag) => (
                      <span
                        key={tag.id}
                        className="text-xs bg-wk-vocab/10 text-wk-vocab px-2 py-0.5 rounded-full font-medium"
                      >
                        {tag.name}
                      </span>
                    ))}
                  </div>
                </div>
                {item.creator_username && (
                  <span className="text-xs text-text-muted shrink-0">
                    by {item.creator_username}
                  </span>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

function CreateVocabForm({ onCreated }: { onCreated: () => void }) {
  const [word, setWord] = useState('');
  const [reading, setReading] = useState('');
  const [meanings, setMeanings] = useState('');
  const [tags, setTags] = useState('');
  const [comment, setComment] = useState('');
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: api.createVocab,
    onSuccess: onCreated,
    onError: (err: Error) => setError(err.message),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!word.trim() || !reading.trim() || !meanings.trim()) return;
    mutation.mutate({
      word: word.trim(),
      reading: reading.trim(),
      meanings: meanings.split(',').map((m) => m.trim()).filter(Boolean),
      tags: tags ? tags.split(',').map((t) => t.trim()).filter(Boolean) : undefined,
      creator_comment: comment.trim() || undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="bg-surface rounded-xl p-5 shadow-sm space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <input
          type="text"
          placeholder="Word (e.g. &#26085;&#26412;&#35486;)"
          value={word}
          onChange={(e) => setWord(e.target.value)}
          className="px-3 py-2 rounded-lg border border-border bg-surface-alt text-sm focus:outline-none focus:ring-2 focus:ring-wk-vocab"
          required
        />
        <input
          type="text"
          placeholder="Reading (e.g. &#12395;&#12411;&#12435;&#12372;)"
          value={reading}
          onChange={(e) => setReading(e.target.value)}
          className="px-3 py-2 rounded-lg border border-border bg-surface-alt text-sm focus:outline-none focus:ring-2 focus:ring-wk-vocab"
          required
        />
      </div>
      <input
        type="text"
        placeholder="Meanings (comma-separated)"
        value={meanings}
        onChange={(e) => setMeanings(e.target.value)}
        className="w-full px-3 py-2 rounded-lg border border-border bg-surface-alt text-sm focus:outline-none focus:ring-2 focus:ring-wk-vocab"
        required
      />
      <input
        type="text"
        placeholder="Tags (comma-separated, optional)"
        value={tags}
        onChange={(e) => setTags(e.target.value)}
        className="w-full px-3 py-2 rounded-lg border border-border bg-surface-alt text-sm focus:outline-none focus:ring-2 focus:ring-wk-vocab"
      />
      <input
        type="text"
        placeholder="Comment (optional)"
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        className="w-full px-3 py-2 rounded-lg border border-border bg-surface-alt text-sm focus:outline-none focus:ring-2 focus:ring-wk-vocab"
      />
      {error && <p className="text-error text-sm">{error}</p>}
      <button
        type="submit"
        disabled={mutation.isPending}
        className="px-4 py-2 rounded-lg bg-wk-vocab text-white font-bold hover:opacity-90 transition-opacity disabled:opacity-50"
      >
        {mutation.isPending ? 'Creating...' : 'Create Vocabulary'}
      </button>
    </form>
  );
}
