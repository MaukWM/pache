import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type KanjiItem, type VocabItem } from '../lib/api';
import { SRS_STAGE_COLORS, SRS_STAGE_NAMES } from '../lib/srs';

// Extract kanji characters from a string
function extractKanji(text: string): string[] {
  return [...text].filter((ch) => ch.charCodeAt(0) >= 0x4e00 && ch.charCodeAt(0) <= 0x9faf);
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

  const [selected, setSelected] = useState<VocabItem | null>(null);
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

      {/* Detail panel — sticky */}
      {selected && (
        <div className="sticky top-2 z-10">
          <VocabDetail
            item={selected}
            onClose={() => setSelected(null)}
            queryClient={queryClient}
          />
        </div>
      )}

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
              onClick={() => setSelected(item)}
              className={`bg-wk-vocab rounded-full px-5 py-2.5 text-white text-lg font-bold hover:scale-105 transition-all cursor-pointer whitespace-nowrap ${
                selected?.id === item.id ? 'ring-2 ring-wk-vocab ring-offset-2' : ''
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

  const progressMap = useQuery({
    queryKey: ['progressMap'],
    queryFn: api.getProgressMap,
  });
  const currentStage = progressMap.data?.[`vocab-${item.id}`];
  const alreadyLearned = currentStage != null;

  const learnMutation = useMutation({
    mutationFn: () =>
      api.completeLessons({ item_ids: [{ item_type: 'vocab', item_id: item.id }] }),
    onSuccess: () => {
      setActionMsg('Learned! First review in 4 hours.');
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
      queryClient.invalidateQueries({ queryKey: ['progress'] });
      queryClient.invalidateQueries({ queryKey: ['progressMap'] });
    },
    onError: (err: Error) => setActionMsg(err.message),
  });

  const queueMutation = useMutation({
    mutationFn: () => api.addToQueue('vocab', item.id),
    onSuccess: () => {
      setActionMsg('Added to lesson queue!');
      queryClient.invalidateQueries({ queryKey: ['queue'] });
    },
    onError: (err: Error) => setActionMsg(err.message),
  });

  return (
    <div className="bg-surface rounded-xl p-5 shadow-md relative">
      <button
        onClick={onClose}
        className="absolute top-3 right-3 text-text-muted hover:text-text text-xl leading-none"
      >
        &times;
      </button>

      <div className="flex items-start gap-5">
        <div className="space-y-2 flex-1">
          <div>
            <span className="text-xl font-bold">{item.word}</span>
            <span className="text-text-muted text-sm ml-2">{item.readings.join('、')}</span>
            <p className="text-sm">{item.meanings.join(', ')}</p>
          </div>

          {item.tags && item.tags.length > 0 && (
            <div className="flex gap-1.5">
              {item.tags.map((tag) => (
                <span
                  key={tag.id}
                  className="text-xs bg-wk-vocab/10 text-wk-vocab px-2 py-0.5 rounded-full"
                >
                  {tag.name}
                </span>
              ))}
            </div>
          )}

          {item.creator_comment && (
            <p className="text-xs text-text-muted italic">"{item.creator_comment}"</p>
          )}

          {item.creator_username && (
            <p className="text-xs text-text-muted">by {item.creator_username}</p>
          )}

          {alreadyLearned ? (
            <div className="pt-1">
              <span
                className="inline-block text-xs font-bold px-3 py-1.5 rounded-full text-white"
                style={{ backgroundColor: SRS_STAGE_COLORS[currentStage] }}
              >
                {SRS_STAGE_NAMES[currentStage]}
              </span>
            </div>
          ) : (
            <div className="flex gap-2 pt-1">
              <button
                onClick={() => learnMutation.mutate()}
                disabled={learnMutation.isPending}
                className="px-4 py-2 rounded-lg bg-wk-vocab text-white font-bold text-sm hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {learnMutation.isPending ? 'Learning...' : 'Learn Now'}
              </button>
              <button
                onClick={() => queueMutation.mutate()}
                disabled={queueMutation.isPending}
                className="px-4 py-2 rounded-lg bg-surface border border-border text-sm font-bold hover:bg-border transition-colors disabled:opacity-50"
              >
                {queueMutation.isPending ? 'Adding...' : 'Add to Queue'}
              </button>
            </div>
          )}

          {actionMsg && (
            <p className={`text-sm ${actionMsg.includes('!') ? 'text-success' : 'text-error'}`}>
              {actionMsg}
            </p>
          )}
        </div>
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

function CreateVocabForm({ onCreated }: { onCreated: () => void }) {
  const [word, setWord] = useState('');
  const [readings, setReadings] = useState('');
  const [meanings, setMeanings] = useState('');
  const [tags, setTags] = useState('');
  const [comment, setComment] = useState('');
  const [error, setError] = useState('');

  // Load all kanji so we can auto-detect IDs
  const allKanji = useQuery({
    queryKey: ['kanji', 'all'],
    queryFn: () => api.getKanji({ include_inactive: 'true' }),
  });

  // Auto-detect kanji from word
  const detectedKanji = useMemo(() => {
    if (!word || !allKanji.data) return [];
    const chars = extractKanji(word);
    const kanjiMap = new Map<string, KanjiItem>();
    for (const k of allKanji.data) {
      kanjiMap.set(k.character, k);
    }
    const found: KanjiItem[] = [];
    const seen = new Set<string>();
    for (const ch of chars) {
      if (!seen.has(ch)) {
        seen.add(ch);
        const k = kanjiMap.get(ch);
        if (k) found.push(k);
      }
    }
    return found;
  }, [word, allKanji.data]);

  const mutation = useMutation({
    mutationFn: api.createVocab,
    onSuccess: onCreated,
    onError: (err: Error) => setError(err.message),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!word.trim() || !readings.trim() || !meanings.trim()) return;
    setError('');
    mutation.mutate({
      word: word.trim(),
      readings: readings.split(',').map((r) => r.trim()).filter(Boolean),
      meanings: meanings.split(',').map((m) => m.trim()).filter(Boolean),
      kanji_ids: detectedKanji.map((k) => k.id),
      tags: tags ? tags.split(',').map((t) => t.trim()).filter(Boolean) : undefined,
      creator_comment: comment.trim() || undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="bg-surface rounded-xl p-5 shadow-sm space-y-3">
      <h2 className="font-bold text-lg">Add Vocabulary</h2>

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
          <label className="text-xs text-text-muted block mb-1">Tags — comma-separated (optional)</label>
          <input
            type="text"
            placeholder="e.g. food, N4"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-border bg-surface-alt text-sm focus:outline-none focus:ring-2 focus:ring-wk-vocab"
          />
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

      {error && <p className="text-error text-sm">{error}</p>}

      <button
        type="submit"
        disabled={mutation.isPending || !word.trim() || !readings.trim() || !meanings.trim()}
        className="px-5 py-2 rounded-lg bg-wk-vocab text-white font-bold hover:opacity-90 transition-opacity disabled:opacity-50"
      >
        {mutation.isPending ? 'Creating...' : 'Create'}
      </button>
    </form>
  );
}
