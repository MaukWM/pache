import { useState, useMemo, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type KanjiItem, type VocabItem, type VocabSearchResult, type Sentence } from '../lib/api';
import { SRS_STAGE_COLORS, SRS_STAGE_NAMES } from '../lib/srs';

// Extract kanji characters from a string
function extractKanji(text: string): string[] {
  return [...text].filter((ch) => ch.charCodeAt(0) >= 0x4e00 && ch.charCodeAt(0) <= 0x9faf);
}

// Resolve the kanji items contained in a word, deduped, for auto-linking.
function useDetectedKanji(word: string): KanjiItem[] {
  const allKanji = useQuery({
    queryKey: ['kanji', 'all'],
    queryFn: () => api.getKanji({ include_inactive: 'true' }),
  });
  return useMemo(() => {
    if (!word || !allKanji.data) return [];
    const map = new Map(allKanji.data.map((k) => [k.character, k]));
    const found: KanjiItem[] = [];
    const seen = new Set<string>();
    for (const ch of extractKanji(word)) {
      if (!seen.has(ch)) {
        seen.add(ch);
        const k = map.get(ch);
        if (k) found.push(k);
      }
    }
    return found;
  }, [word, allKanji.data]);
}

export function VocabPage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [tagFilter, setTagFilter] = useState('');
  const [creatorFilter, setCreatorFilter] = useState('');
  const [hideKnown, setHideKnown] = useState(false);

  const params: Record<string, string> = {};
  if (tagFilter) params.tag = tagFilter;
  if (creatorFilter) params.creator = creatorFilter;

  const vocab = useQuery({
    queryKey: ['vocab', params],
    queryFn: () => api.getVocab(Object.keys(params).length ? params : undefined),
  });

  // Fetch all vocab (unfiltered) to extract tag/creator options
  const allVocab = useQuery({
    queryKey: ['vocab'],
    queryFn: () => api.getVocab(),
  });

  const allTags = useMemo(() => {
    const tags = new Set<string>();
    for (const v of allVocab.data || []) {
      for (const t of v.tags || []) tags.add(t.name);
    }
    return [...tags].sort();
  }, [allVocab.data]);

  const allCreators = useMemo(() => {
    const creators = new Set<string>();
    for (const v of allVocab.data || []) {
      if (v.creator_username) creators.add(v.creator_username);
    }
    return [...creators].sort();
  }, [allVocab.data]);

  const progressMap = useQuery({
    queryKey: ['progressMap'],
    queryFn: api.getProgressMap,
  });

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const items = useMemo(() => {
    let list = vocab.data || [];
    if (hideKnown && progressMap.data) {
      list = list.filter((v) => progressMap.data![`vocab-${v.id}`] == null);
    }
    return list;
  }, [vocab.data, hideKnown, progressMap.data]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Vocabulary</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-text-muted">
            {items.length} item{items.length !== 1 ? 's' : ''}
          </span>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="px-4 py-2 rounded-lg bg-wk-vocab text-white font-bold text-sm hover:opacity-90 transition-opacity"
          >
            {showCreate ? 'Cancel' : '+ New Vocab'}
          </button>
        </div>
      </div>

      {showCreate && (
        <CreateVocabForm
          onCreated={() => {
            setShowCreate(false);
            queryClient.invalidateQueries({ queryKey: ['vocab'] });
          }}
        />
      )}

      {/* Detail panel — sticky, always reads fresh data from query cache */}
      {selectedId != null && (() => {
        const freshItem = (vocab.data || []).find((v) => v.id === selectedId);
        if (!freshItem) return null;
        return (
          <div className="sticky top-2 z-10">
            <VocabDetail
              item={freshItem}
              onClose={() => setSelectedId(null)}
              queryClient={queryClient}
            />
          </div>
        );
      })()}

      {/* Filters */}
      <div className="flex gap-3">
        <FilterDropdown
          placeholder="Filter by tag..."
          value={tagFilter}
          onChange={setTagFilter}
          options={allTags}
        />
        <FilterDropdown
          placeholder="Filter by creator..."
          value={creatorFilter}
          onChange={setCreatorFilter}
          options={allCreators}
        />
        <button
          onClick={() => setHideKnown(!hideKnown)}
          className={`px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
            hideKnown ? 'bg-wk-vocab text-white' : 'border border-border bg-surface hover:bg-border'
          }`}
        >
          Hide Known
        </button>
      </div>

      {/* Vocab grid — compact blocks */}
      {vocab.isLoading ? (
        <div className="text-text-muted animate-pulse">Loading...</div>
      ) : items.length === 0 ? (
        <div className="bg-surface rounded-xl p-10 text-center text-text-muted">
          No vocabulary yet. Be the first to add some!
        </div>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {items.map((item) => (
            <button
              key={item.id}
              onClick={() => setSelectedId(item.id)}
              className={`bg-wk-vocab rounded-full px-5 py-2.5 text-white text-lg font-bold hover:scale-105 transition-all cursor-pointer whitespace-nowrap ${
                selectedId === item.id ? 'ring-2 ring-wk-vocab ring-offset-2' : ''
              }`}
              title={`${item.word} — ${item.meanings.join(', ')}`}
            >
              {item.word}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function VocabDetail({
  item,
  onClose,
  queryClient,
}: {
  item: VocabItem;
  onClose: () => void;
  queryClient: ReturnType<typeof useQueryClient>;
}) {
  const [actionMsg, setActionMsg] = useState('');
  const [showAddSentence, setShowAddSentence] = useState(false);
  const [showSuggest, setShowSuggest] = useState(false);
  const [newJa, setNewJa] = useState('');
  const [newEn, setNewEn] = useState('');
  const [editing, setEditing] = useState(false);
  const [editingSentenceId, setEditingSentenceId] = useState<number | null>(null);
  const [editJa, setEditJa] = useState('');
  const [editEn, setEditEn] = useState('');

  // Reset state when item changes
  const prevItemId = useRef(item.id);
  if (item.id !== prevItemId.current) {
    prevItemId.current = item.id;
    setShowAddSentence(false);
    setShowSuggest(false);
    setNewJa('');
    setNewEn('');
    setActionMsg('');
    setEditing(false);
    setEditingSentenceId(null);
  }

  const deleteMut = useMutation({
    mutationFn: () => api.deleteVocab(item.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vocab'] });
      queryClient.invalidateQueries({ queryKey: ['queue'] });
      queryClient.invalidateQueries({ queryKey: ['progressMap'] });
      onClose();
    },
    onError: (err: Error) => setActionMsg(err.message),
  });

  const updateSentenceMut = useMutation({
    mutationFn: ({ id, ja, en }: { id: number; ja: string; en: string }) =>
      api.updateSentence(item.id, id, ja, en),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vocab'] });
      setEditingSentenceId(null);
    },
    onError: (err: Error) => setActionMsg(err.message),
  });

  const handleDelete = () => {
    if (
      window.confirm(
        `Delete "${item.word}" permanently?\n\nThis removes it from the shared pool for everyone, ` +
          `along with its lesson-queue entries and all users' review progress for it. ` +
          `Linked example sentences are kept. This cannot be undone.`,
      )
    ) {
      deleteMut.mutate();
    }
  };

  const startEditSentence = (id: number, ja: string, en: string) => {
    setEditingSentenceId(id);
    setEditJa(ja);
    setEditEn(en);
  };

  const createSentenceMut = useMutation({
    mutationFn: () => api.createSentence(item.id, newJa.trim(), newEn.trim()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vocab'] });
      setShowAddSentence(false);
      setNewJa('');
      setNewEn('');
    },
    onError: (err: Error) => setActionMsg(err.message),
  });

  const linkMut = useMutation({
    mutationFn: (sentenceId: number) => api.linkSentence(item.id, sentenceId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['vocab'] }),
    onError: (err: Error) => setActionMsg(err.message),
  });

  const unlinkMut = useMutation({
    mutationFn: (sentenceId: number) => api.unlinkSentence(item.id, sentenceId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['vocab'] }),
    onError: (err: Error) => setActionMsg(err.message),
  });

  const suggestions = useQuery({
    queryKey: ['vocab', item.id, 'suggest'],
    queryFn: () => api.suggestSentences(item.id),
    enabled: showSuggest,
  });

  const progressMap = useQuery({
    queryKey: ['progressMap'],
    queryFn: api.getProgressMap,
  });
  const currentStage = progressMap.data?.[`vocab-${item.id}`];
  const alreadyLearned = currentStage != null;
  const isBurned = currentStage === 9;
  const [confirmUnlearn, setConfirmUnlearn] = useState(false);
  const [confirmResurrect, setConfirmResurrect] = useState(false);

  const queueMutation = useMutation({
    mutationFn: () => api.addToQueue('vocab', item.id),
    onSuccess: () => {
      setActionMsg('Added to lesson queue!');
      queryClient.invalidateQueries({ queryKey: ['queue'] });
    },
    onError: (err: Error) => setActionMsg(err.message),
  });

  const unlearnMutation = useMutation({
    mutationFn: () => api.unlearnItem('vocab', item.id),
    onSuccess: () => {
      setActionMsg('Unlearned! Removed from your reviews.');
      setConfirmUnlearn(false);
      queryClient.invalidateQueries({ queryKey: ['progressMap'] });
      queryClient.invalidateQueries({ queryKey: ['progress'] });
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
      queryClient.invalidateQueries({ queryKey: ['queue'] });
    },
    onError: (err: Error) => setActionMsg(err.message),
  });

  const resurrectMutation = useMutation({
    mutationFn: () => api.resurrectItem('vocab', item.id),
    onSuccess: () => {
      setActionMsg('Resurrected to Apprentice I! First review in 4 hours.');
      setConfirmResurrect(false);
      queryClient.invalidateQueries({ queryKey: ['progressMap'] });
      queryClient.invalidateQueries({ queryKey: ['progress'] });
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
    },
    onError: (err: Error) => setActionMsg(err.message),
  });

  return (
    <div className="bg-surface rounded-xl shadow-md overflow-hidden relative">
      <button
        onClick={onClose}
        className="absolute top-3 right-3 text-text-muted hover:text-text text-xl leading-none z-10"
      >
        &times;
      </button>

      {/* Header — word + reading + SRS badge */}
      <div className="bg-wk-vocab px-5 py-4 text-white flex items-center gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold">{item.word}</span>
            <span className="text-sm opacity-80">{item.readings.join('、')}</span>
          </div>
          <p className="text-sm opacity-90">{item.meanings.join(', ')}</p>
        </div>
        {alreadyLearned && (
          <span
            className="text-[10px] font-bold px-2 py-1 rounded-full shrink-0"
            style={{ backgroundColor: SRS_STAGE_COLORS[currentStage], color: '#fff' }}
          >
            {SRS_STAGE_NAMES[currentStage]}
          </span>
        )}
      </div>

      {/* Body */}
      {editing ? (
        <EditVocabForm
          item={item}
          queryClient={queryClient}
          onDone={() => setEditing(false)}
        />
      ) : (
      <div className="px-5 py-3 space-y-3">
        {/* Meta row — tags, creator, comment */}
        <div className="flex items-center gap-2 flex-wrap text-xs">
          {item.tags?.map((tag) => (
            <span key={tag.id} className="bg-wk-vocab/10 text-wk-vocab px-2 py-0.5 rounded-full font-medium">
              {tag.name}
            </span>
          ))}
          {item.creator_comment && (
            <span className="text-text-muted italic">"{item.creator_comment}"</span>
          )}
          {item.creator_username && (
            <span className="text-text-muted">by {item.creator_username}</span>
          )}
        </div>

        {/* Sentences */}
        {(item.sentences.length > 0 || showAddSentence || showSuggest) && (
          <div className="space-y-1.5">
            {item.sentences.map((s) =>
              editingSentenceId === s.id ? (
                <div key={s.id} className="flex gap-2">
                  <div className="flex-1 space-y-1">
                    <input type="text" value={editJa} onChange={(e) => setEditJa(e.target.value)} lang="ja"
                      className="w-full px-2.5 py-1.5 rounded border border-border bg-surface-alt text-sm focus:outline-none focus:ring-1 focus:ring-wk-vocab" />
                    <input type="text" value={editEn} onChange={(e) => setEditEn(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded border border-border bg-surface-alt text-sm focus:outline-none focus:ring-1 focus:ring-wk-vocab" />
                  </div>
                  <div className="flex flex-col gap-1 self-end">
                    <button
                      onClick={() => updateSentenceMut.mutate({ id: s.id, ja: editJa.trim(), en: editEn.trim() })}
                      disabled={!editJa.trim() || !editEn.trim() || updateSentenceMut.isPending}
                      className="px-3 rounded bg-wk-vocab text-white text-xs font-bold py-1.5 disabled:opacity-50">
                      Save
                    </button>
                    <button onClick={() => setEditingSentenceId(null)}
                      className="px-3 rounded border border-border text-xs font-bold py-1 hover:bg-border">
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div key={s.id} className="bg-surface-alt rounded-lg px-3 py-2 text-sm group relative">
                  <p lang="ja">{s.ja}</p>
                  <p className="text-text-muted text-xs">{s.en}</p>
                  <div className="absolute top-1 right-2 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => startEditSentence(s.id, s.ja, s.en)}
                      className="text-text-muted hover:text-wk-vocab text-xs"
                      title="Edit sentence"
                    >
                      &#9998;
                    </button>
                    <button
                      onClick={() => unlinkMut.mutate(s.id)}
                      className="text-text-muted hover:text-error text-xs"
                      title="Unlink sentence"
                    >
                      &times;
                    </button>
                  </div>
                </div>
              ),
            )}

            {showAddSentence && (
              <div className="flex gap-2">
                <div className="flex-1 space-y-1">
                  <input type="text" value={newJa} onChange={(e) => setNewJa(e.target.value)} placeholder="Japanese..." lang="ja"
                    className="w-full px-2.5 py-1.5 rounded border border-border bg-surface-alt text-sm focus:outline-none focus:ring-1 focus:ring-wk-vocab" />
                  <input type="text" value={newEn} onChange={(e) => setNewEn(e.target.value)} placeholder="English..."
                    className="w-full px-2.5 py-1.5 rounded border border-border bg-surface-alt text-sm focus:outline-none focus:ring-1 focus:ring-wk-vocab" />
                </div>
                <button onClick={() => createSentenceMut.mutate()} disabled={!newJa.trim() || !newEn.trim() || createSentenceMut.isPending}
                  className="px-3 self-end rounded bg-wk-vocab text-white text-xs font-bold py-1.5 disabled:opacity-50">
                  Add
                </button>
              </div>
            )}

            {showSuggest && (
              <div className="space-y-1">
                {suggestions.isLoading && <p className="text-xs text-text-muted animate-pulse">Searching...</p>}
                {suggestions.data?.length === 0 && <p className="text-xs text-text-muted">No matches found.</p>}
                {suggestions.data?.map((s) => (
                  <div key={s.id} className="bg-surface-alt rounded-lg px-3 py-1.5 text-sm flex items-center gap-2">
                    <div className="flex-1 min-w-0">
                      <span lang="ja">{s.ja}</span>
                      <span className="text-text-muted text-xs ml-2">{s.en}</span>
                    </div>
                    <button onClick={() => linkMut.mutate(s.id)} className="text-xs text-wk-vocab font-bold hover:underline shrink-0">Link</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2">
          {!alreadyLearned && (
            <button onClick={() => queueMutation.mutate()} disabled={queueMutation.isPending}
              className="px-3 py-1.5 rounded-lg bg-wk-vocab text-white font-bold text-xs hover:opacity-90 disabled:opacity-50">
              {queueMutation.isPending ? 'Adding...' : 'Add to Queue'}
            </button>
          )}
          {alreadyLearned && isBurned && !confirmResurrect && (
            <button onClick={() => setConfirmResurrect(true)}
              className="px-3 py-1.5 rounded-lg bg-wk-radical text-white font-bold text-xs hover:opacity-90">
              Resurrect
            </button>
          )}
          {alreadyLearned && !confirmUnlearn && (
            <button onClick={() => setConfirmUnlearn(true)}
              className="px-3 py-1.5 rounded-lg bg-surface border border-border text-xs font-bold hover:bg-border">
              Unlearn
            </button>
          )}
          <button onClick={() => { setShowAddSentence(!showAddSentence); setShowSuggest(false); }}
            className="px-3 py-1.5 rounded-lg bg-surface border border-border text-xs font-bold hover:bg-border">
            {showAddSentence ? 'Cancel' : '+ Sentence'}
          </button>
          <button onClick={() => { setShowSuggest(!showSuggest); setShowAddSentence(false); }}
            className="px-3 py-1.5 rounded-lg bg-surface border border-border text-xs font-bold hover:bg-border">
            {showSuggest ? 'Cancel' : 'Find Links'}
          </button>
          <div className="ml-auto flex items-center gap-2">
            <button onClick={() => setEditing(true)}
              className="px-3 py-1.5 rounded-lg bg-surface border border-border text-xs font-bold hover:bg-border">
              Edit
            </button>
            <button onClick={handleDelete} disabled={deleteMut.isPending}
              className="px-3 py-1.5 rounded-lg border border-error/40 text-error text-xs font-bold hover:bg-error/10 disabled:opacity-50">
              {deleteMut.isPending ? 'Deleting...' : 'Delete'}
            </button>
          </div>
        </div>

        {confirmResurrect && (
          <div className="flex items-center gap-2 flex-wrap text-xs">
            <span className="text-text-muted font-medium">
              Resurrect {item.word} back to Apprentice I? It re-enters your reviews.
            </span>
            <button onClick={() => resurrectMutation.mutate()} disabled={resurrectMutation.isPending}
              className="px-3 py-1.5 rounded-lg bg-wk-radical text-white font-bold hover:opacity-90 disabled:opacity-50">
              {resurrectMutation.isPending ? 'Resurrecting…' : 'Yes, resurrect'}
            </button>
            <button onClick={() => setConfirmResurrect(false)}
              className="px-3 py-1.5 rounded-lg bg-surface border border-border font-bold hover:bg-border">
              Cancel
            </button>
          </div>
        )}

        {confirmUnlearn && (
          <div className="flex items-center gap-2 flex-wrap text-xs">
            <span className="text-error font-medium">
              Unlearn {item.word}? This deletes its progress and upcoming reviews.
            </span>
            <button onClick={() => unlearnMutation.mutate()} disabled={unlearnMutation.isPending}
              className="px-3 py-1.5 rounded-lg bg-error text-white font-bold hover:opacity-90 disabled:opacity-50">
              {unlearnMutation.isPending ? 'Unlearning…' : 'Yes, unlearn'}
            </button>
            <button onClick={() => setConfirmUnlearn(false)}
              className="px-3 py-1.5 rounded-lg bg-surface border border-border font-bold hover:bg-border">
              Cancel
            </button>
          </div>
        )}

        {actionMsg && (
          <p className={`text-xs ${actionMsg.includes('!') ? 'text-success' : 'text-error'}`}>{actionMsg}</p>
        )}
      </div>
      )}
    </div>
  );
}

function EditVocabForm({
  item,
  queryClient,
  onDone,
}: {
  item: VocabItem;
  queryClient: ReturnType<typeof useQueryClient>;
  onDone: () => void;
}) {
  const [word, setWord] = useState(item.word);
  const [readings, setReadings] = useState(item.readings.join(', '));
  const [meanings, setMeanings] = useState(item.meanings.join(', '));
  const [tags, setTags] = useState<string[]>((item.tags ?? []).map((t) => t.name));
  const [comment, setComment] = useState(item.creator_comment ?? '');
  const [error, setError] = useState('');

  const allTags = useAllTags();
  const detectedKanji = useDetectedKanji(word);

  const mutation = useMutation({
    mutationFn: () =>
      api.updateVocab(item.id, {
        word: word.trim(),
        readings: readings.split(',').map((r) => r.trim()).filter(Boolean),
        meanings: meanings.split(',').map((m) => m.trim()).filter(Boolean),
        kanji_ids: detectedKanji.map((k) => k.id),
        tags: tags,
        creator_comment: comment.trim() || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vocab'] });
      queryClient.invalidateQueries({ queryKey: ['progressMap'] });
      onDone();
    },
    onError: (err: Error) => setError(err.message),
  });

  const canSave = !!(word.trim() && readings.trim() && meanings.trim());

  return (
    <div className="px-5 py-4 space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-text-muted block mb-1">Word</label>
          <input type="text" value={word} onChange={(e) => setWord(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-border bg-surface-alt text-lg focus:outline-none focus:ring-2 focus:ring-wk-vocab" />
        </div>
        <div>
          <label className="text-xs text-text-muted block mb-1">Reading(s) — comma-separated</label>
          <input type="text" value={readings} onChange={(e) => setReadings(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-border bg-surface-alt focus:outline-none focus:ring-2 focus:ring-wk-vocab" />
        </div>
      </div>

      <div>
        <label className="text-xs text-text-muted block mb-1">Meanings — comma-separated</label>
        <input type="text" value={meanings} onChange={(e) => setMeanings(e.target.value)}
          className="w-full px-3 py-2 rounded-lg border border-border bg-surface-alt focus:outline-none focus:ring-2 focus:ring-wk-vocab" />
      </div>

      {detectedKanji.length > 0 && (
        <div>
          <label className="text-xs text-text-muted block mb-1">Linked Kanji (auto-detected)</label>
          <div className="flex gap-1.5">
            {detectedKanji.map((k) => (
              <div key={k.id} className="bg-wk-kanji w-9 h-9 rounded-lg flex items-center justify-center text-white font-bold"
                title={k.meanings.join(', ')}>
                {k.character}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-text-muted block mb-1">Tags</label>
          <TagInput value={tags} onChange={setTags} options={allTags} />
        </div>
        <div>
          <label className="text-xs text-text-muted block mb-1">Comment</label>
          <input type="text" value={comment} onChange={(e) => setComment(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-border bg-surface-alt text-sm focus:outline-none focus:ring-2 focus:ring-wk-vocab" />
        </div>
      </div>

      {error && <p className="text-error text-sm">{error}</p>}

      <div className="flex gap-2">
        <button
          onClick={() => { if (canSave) { setError(''); mutation.mutate(); } }}
          disabled={!canSave || mutation.isPending}
          className="px-5 py-2 rounded-lg bg-wk-vocab text-white font-bold hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {mutation.isPending ? 'Saving...' : 'Save Changes'}
        </button>
        <button
          onClick={onDone}
          className="px-5 py-2 rounded-lg bg-surface border border-border font-bold hover:bg-border transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

function FilterDropdown({
  placeholder,
  value,
  onChange,
  options,
}: {
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState(value);

  const filtered = options.filter((o) =>
    o.toLowerCase().includes(input.toLowerCase()),
  );

  return (
    <div className="relative">
      <input
        type="text"
        placeholder={placeholder}
        value={input}
        onChange={(e) => {
          setInput(e.target.value);
          setOpen(true);
          if (!e.target.value) onChange('');
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        className="px-3 py-2 rounded-lg border border-border bg-surface text-sm focus:outline-none focus:ring-2 focus:ring-wk-vocab w-48"
      />
      {value && (
        <button
          onClick={() => { setInput(''); onChange(''); }}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-text-muted hover:text-text text-sm"
        >
          &times;
        </button>
      )}
      {open && filtered.length > 0 && (
        <div className="absolute top-full left-0 mt-1 w-full bg-surface border border-border rounded-lg shadow-lg z-20 max-h-48 overflow-y-auto">
          {filtered.map((opt) => (
            <button
              key={opt}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => {
                setInput(opt);
                onChange(opt);
                setOpen(false);
              }}
              className="w-full text-left px-3 py-1.5 text-sm hover:bg-border transition-colors"
            >
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// Existing tag names across the vocab pool, for tag suggestions. Reuses the
// cached ['vocab'] query so it's a cache hit on the Vocab page.
function useAllTags(): string[] {
  const allVocab = useQuery({
    queryKey: ['vocab'],
    queryFn: () => api.getVocab(),
  });
  return useMemo(() => {
    const tags = new Set<string>();
    for (const v of allVocab.data || []) {
      for (const t of v.tags || []) tags.add(t.name);
    }
    return [...tags].sort();
  }, [allVocab.data]);
}

// Multi-select tag editor: existing tags shown as a filtered dropdown, plus
// free entry of new tags (Enter / comma). Selected tags render as removable chips.
function TagInput({
  value,
  onChange,
  options,
}: {
  value: string[];
  onChange: (tags: string[]) => void;
  options: string[];
}) {
  const [input, setInput] = useState('');
  const [open, setOpen] = useState(false);

  const available = options.filter(
    (o) => !value.includes(o) && o.toLowerCase().includes(input.toLowerCase()),
  );

  const addTag = (tag: string) => {
    const t = tag.trim();
    if (t && !value.includes(t)) onChange([...value, t]);
    setInput('');
  };
  const removeTag = (tag: string) => onChange(value.filter((t) => t !== tag));

  return (
    <div className="relative">
      <div className="flex flex-wrap items-center gap-1.5 px-2 py-1.5 rounded-lg border border-border bg-surface-alt focus-within:ring-2 focus-within:ring-wk-vocab">
        {value.map((tag) => (
          <span
            key={tag}
            className="flex items-center gap-1 bg-wk-vocab/10 text-wk-vocab px-2 py-0.5 rounded-full text-sm font-medium"
          >
            {tag}
            <button
              type="button"
              onClick={() => removeTag(tag)}
              className="hover:text-wk-vocab/60 leading-none"
            >
              &times;
            </button>
          </span>
        ))}
        <input
          type="text"
          value={input}
          placeholder={value.length ? '' : 'Add tags...'}
          onChange={(e) => {
            const v = e.target.value;
            if (v.endsWith(',')) addTag(v.slice(0, -1));
            else setInput(v);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              if (input.trim()) addTag(input);
            } else if (e.key === 'Backspace' && !input && value.length) {
              removeTag(value[value.length - 1]);
            }
          }}
          className="flex-1 min-w-[80px] bg-transparent text-sm py-0.5 focus:outline-none"
        />
      </div>
      {open && available.length > 0 && (
        <div className="absolute top-full left-0 mt-1 w-full bg-surface border border-border rounded-lg shadow-lg z-20 max-h-48 overflow-y-auto">
          {available.map((opt) => (
            <button
              key={opt}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => addTag(opt)}
              className="w-full text-left px-3 py-1.5 text-sm hover:bg-border transition-colors"
            >
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function CreateVocabForm({ onCreated }: { onCreated: () => void }) {
  const queryClient = useQueryClient();
  const [word, setWord] = useState('');
  const [readings, setReadings] = useState('');
  const [meanings, setMeanings] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [comment, setComment] = useState('');
  const allTags = useAllTags();
  const [sentences, setSentences] = useState<{ ja: string; en: string }[]>([]);
  const [showLinks, setShowLinks] = useState(false);
  const [linkIds, setLinkIds] = useState<Set<number>>(new Set());
  const [error, setError] = useState('');

  const toggleLink = (id: number) =>
    setLinkIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const addSentence = () => setSentences((prev) => [...prev, { ja: '', en: '' }]);
  const removeSentence = (i: number) =>
    setSentences((prev) => prev.filter((_, idx) => idx !== i));
  const updateSentence = (i: number, field: 'ja' | 'en', value: string) =>
    setSentences((prev) => prev.map((s, idx) => (idx === i ? { ...s, [field]: value } : s)));

  // Dictionary search (offline JMdict via backend) — prefills the fields below.
  const [dictQuery, setDictQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(dictQuery.trim()), 300);
    return () => clearTimeout(t);
  }, [dictQuery]);

  const dictResults = useQuery({
    queryKey: ['vocabSearch', debouncedQuery],
    queryFn: () => api.searchVocab(debouncedQuery),
    enabled: debouncedQuery.length > 0,
  });

  const applyResult = (r: VocabSearchResult) => {
    setWord(r.word);
    setReadings(r.readings.join(', '));
    setMeanings(r.meanings.join(', '));
    setDictQuery('');
    setDebouncedQuery('');
  };

  // Auto-detect kanji from word
  const detectedKanji = useDetectedKanji(word);

  // Existing pool sentences containing the word — for linking during creation.
  const linkSuggestions = useQuery({
    queryKey: ['sentenceSearch', word.trim()],
    queryFn: () => api.searchSentences(word.trim()),
    enabled: showLinks && word.trim().length > 0,
  });

  const mutation = useMutation({
    mutationFn: async ({ queue }: { queue: boolean }) => {
      const vocab = await api.createVocab({
        word: word.trim(),
        readings: readings.split(',').map((r) => r.trim()).filter(Boolean),
        meanings: meanings.split(',').map((m) => m.trim()).filter(Boolean),
        kanji_ids: detectedKanji.map((k) => k.id),
        tags: tags.length ? tags : undefined,
        creator_comment: comment.trim() || undefined,
      });
      for (const s of sentences) {
        if (s.ja.trim() && s.en.trim()) {
          await api.createSentence(vocab.id, s.ja.trim(), s.en.trim());
        }
      }
      for (const id of linkIds) {
        await api.linkSentence(vocab.id, id);
      }
      if (queue) await api.addToQueue('vocab', vocab.id);
      return vocab;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queue'] });
      onCreated();
    },
    onError: (err: Error) => setError(err.message),
  });

  const submit = (queue: boolean) => {
    if (!word.trim() || !readings.trim() || !meanings.trim()) return;
    setError('');
    mutation.mutate({ queue });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submit(true);
  };

  return (
    <form onSubmit={handleSubmit} className="bg-surface rounded-xl p-5 shadow-sm space-y-3">
      <h2 className="font-bold text-lg">Add Vocabulary</h2>

      {/* Dictionary search — pick a result to prefill the fields below */}
      <div>
        <label className="text-xs text-text-muted block mb-1">Search dictionary (Japanese or English)</label>
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted">🔍</span>
          <input
            type="text"
            placeholder="e.g. 食べ, たべる, or eat"
            value={dictQuery}
            onChange={(e) => setDictQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-border bg-surface-alt focus:outline-none focus:ring-2 focus:ring-wk-vocab"
          />
        </div>

        {debouncedQuery.length > 0 && (
          <div className="mt-1 border border-border rounded-lg bg-surface max-h-64 overflow-y-auto divide-y divide-border">
            {dictResults.isLoading && (
              <p className="px-3 py-2 text-sm text-text-muted animate-pulse">Searching...</p>
            )}
            {dictResults.data?.length === 0 && (
              <p className="px-3 py-2 text-sm text-text-muted">No dictionary matches.</p>
            )}
            {dictResults.data?.map((r, i) => (
              <button
                key={`${r.word}-${i}`}
                type="button"
                disabled={r.already_exists}
                onClick={() => applyResult(r)}
                className={`w-full text-left px-3 py-2 flex items-center gap-3 transition-colors ${
                  r.already_exists ? 'opacity-50 cursor-not-allowed' : 'hover:bg-border/50 cursor-pointer'
                }`}
              >
                <span className="text-lg font-bold shrink-0" lang="ja">{r.word}</span>
                <span className="text-sm text-text-muted shrink-0" lang="ja">{r.readings.slice(0, 2).join('、')}</span>
                <span className="text-sm flex-1 min-w-0 truncate">{r.meanings.slice(0, 4).join(', ')}</span>
                {r.is_common && !r.already_exists && (
                  <span className="text-[10px] font-bold text-success shrink-0">● common</span>
                )}
                {r.already_exists && (
                  <span className="text-[10px] font-bold text-text-muted shrink-0">✓ in pool</span>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-text-muted block mb-1">Word</label>
          <input
            type="text"
            placeholder="e.g. 食べ物"
            value={word}
            onChange={(e) => setWord(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-border bg-surface-alt text-lg focus:outline-none focus:ring-2 focus:ring-wk-vocab"
            required
          />
        </div>
        <div>
          <label className="text-xs text-text-muted block mb-1">Reading(s) — comma-separated</label>
          <input
            type="text"
            placeholder="e.g. たべもの"
            value={readings}
            onChange={(e) => setReadings(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-border bg-surface-alt focus:outline-none focus:ring-2 focus:ring-wk-vocab"
            required
          />
        </div>
      </div>

      <div>
        <label className="text-xs text-text-muted block mb-1">Meanings — comma-separated</label>
        <input
          type="text"
          placeholder="e.g. food, provisions"
          value={meanings}
          onChange={(e) => setMeanings(e.target.value)}
          className="w-full px-3 py-2 rounded-lg border border-border bg-surface-alt focus:outline-none focus:ring-2 focus:ring-wk-vocab"
          required
        />
      </div>

      {/* Auto-detected kanji */}
      {detectedKanji.length > 0 && (
        <div>
          <label className="text-xs text-text-muted block mb-1">Linked Kanji (auto-detected)</label>
          <div className="flex gap-1.5">
            {detectedKanji.map((k) => (
              <div
                key={k.id}
                className="bg-wk-kanji w-9 h-9 rounded-lg flex items-center justify-center text-white font-bold"
                title={k.meanings.join(', ')}
              >
                {k.character}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-text-muted block mb-1">Tags (optional)</label>
          <TagInput value={tags} onChange={setTags} options={allTags} />
        </div>
        <div>
          <label className="text-xs text-text-muted block mb-1">Comment (optional)</label>
          <input
            type="text"
            placeholder="Where did you find this word?"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-border bg-surface-alt text-sm focus:outline-none focus:ring-2 focus:ring-wk-vocab"
          />
        </div>
      </div>

      {/* Example sentences (optional) */}
      <div>
        <label className="text-xs text-text-muted block mb-1">Example sentences (optional)</label>
        <div className="space-y-2">
          {sentences.map((s, i) => (
            <div key={i} className="flex gap-2">
              <div className="flex-1 space-y-1">
                <input
                  type="text"
                  value={s.ja}
                  onChange={(e) => updateSentence(i, 'ja', e.target.value)}
                  placeholder="Japanese..."
                  lang="ja"
                  className="w-full px-2.5 py-1.5 rounded border border-border bg-surface-alt text-sm focus:outline-none focus:ring-1 focus:ring-wk-vocab"
                />
                <input
                  type="text"
                  value={s.en}
                  onChange={(e) => updateSentence(i, 'en', e.target.value)}
                  placeholder="English..."
                  className="w-full px-2.5 py-1.5 rounded border border-border bg-surface-alt text-sm focus:outline-none focus:ring-1 focus:ring-wk-vocab"
                />
              </div>
              <button
                type="button"
                onClick={() => removeSentence(i)}
                className="self-start text-text-muted hover:text-error text-lg leading-none px-1"
                title="Remove sentence"
              >
                &times;
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={addSentence}
            className="text-sm text-wk-vocab font-bold hover:underline"
          >
            + Add sentence
          </button>
        </div>
      </div>

      {/* Find & link existing pool sentences containing this word */}
      <div>
        <div className="flex items-center gap-3 mb-1">
          <label className="text-xs text-text-muted">Link existing sentences (optional)</label>
          <button
            type="button"
            onClick={() => setShowLinks((v) => !v)}
            disabled={!word.trim()}
            className="text-sm text-wk-vocab font-bold hover:underline disabled:opacity-40 disabled:no-underline"
          >
            {showLinks ? 'Hide' : 'Find links'}
          </button>
          {linkIds.size > 0 && (
            <span className="text-xs text-text-muted">{linkIds.size} selected</span>
          )}
        </div>

        {showLinks && word.trim() && (
          <div className="space-y-1">
            {linkSuggestions.isLoading && (
              <p className="text-xs text-text-muted animate-pulse">Searching…</p>
            )}
            {linkSuggestions.data?.length === 0 && (
              <p className="text-xs text-text-muted">No existing sentences contain "{word.trim()}".</p>
            )}
            {linkSuggestions.data?.map((s: Sentence) => {
              const selected = linkIds.has(s.id);
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => toggleLink(s.id)}
                  className={`w-full text-left rounded-lg px-3 py-1.5 text-sm flex items-center gap-2 transition-colors ${
                    selected ? 'bg-wk-vocab/15 ring-1 ring-wk-vocab' : 'bg-surface-alt hover:bg-border/50'
                  }`}
                >
                  <span className={`shrink-0 ${selected ? 'text-wk-vocab' : 'text-text-muted'}`}>
                    {selected ? '☑' : '☐'}
                  </span>
                  <span className="flex-1 min-w-0">
                    <span lang="ja">{s.ja}</span>
                    <span className="text-text-muted text-xs ml-2">{s.en}</span>
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {error && <p className="text-error text-sm">{error}</p>}

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={mutation.isPending || !word.trim() || !readings.trim() || !meanings.trim()}
          className="px-5 py-2 rounded-lg bg-wk-vocab text-white font-bold hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {mutation.isPending ? 'Saving...' : 'Create & Add to Queue'}
        </button>
        <button
          type="button"
          onClick={() => submit(false)}
          disabled={mutation.isPending || !word.trim() || !readings.trim() || !meanings.trim()}
          className="px-5 py-2 rounded-lg bg-surface border border-border font-bold hover:bg-border transition-colors disabled:opacity-50"
        >
          Create only
        </button>
      </div>
    </form>
  );
}
