import { useState, useMemo, useRef, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type KanjiItem } from '../lib/api';
import { romajiToKana } from '../lib/romaji';

const CHUNK_SIZE = 250;
const INITIAL_LOAD = 250;

type SortMode = 'frequency' | 'grade' | 'jlpt' | 'strokes' | 'default';

const SORT_OPTIONS: { value: SortMode; label: string }[] = [
  { value: 'frequency', label: 'Frequency' },
  { value: 'grade', label: 'School Grade' },
  { value: 'jlpt', label: 'JLPT Level' },
  { value: 'strokes', label: 'Stroke Count' },
  { value: 'default', label: 'Database Order' },
];

function sortKanji(items: KanjiItem[], mode: SortMode): KanjiItem[] {
  if (mode === 'default') return items;
  return [...items].sort((a, b) => {
    if (mode === 'frequency') {
      return (a.frequency ?? 99999) - (b.frequency ?? 99999);
    }
    if (mode === 'grade') {
      return (a.grade ?? 99) - (b.grade ?? 99) || (a.stroke_count ?? 99) - (b.stroke_count ?? 99);
    }
    if (mode === 'jlpt') {
      return (b.jlpt_level ?? 0) - (a.jlpt_level ?? 0) || (a.grade ?? 99) - (b.grade ?? 99);
    }
    if (mode === 'strokes') {
      return (a.stroke_count ?? 99) - (b.stroke_count ?? 99);
    }
    return 0;
  });
}

export function KanjiPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState<SortMode>('frequency');
  const [selected, setSelected] = useState<KanjiItem | null>(null);
  const [visibleCount, setVisibleCount] = useState(INITIAL_LOAD);

  const kanji = useQuery({
    queryKey: ['kanji', 'all'],
    queryFn: () => api.getKanji({ include_inactive: 'true' }),
  });

  const filtered = useMemo(() => {
    let items = kanji.data || [];

    if (search.trim()) {
      const q = search.trim().toLowerCase();
      const kana = romajiToKana(q);

      items = items.filter((k) => {
        if (k.character === q) return true;
        if (k.meanings.some((m) => m.toLowerCase().includes(q))) return true;
        if (k.readings_on.some((r) => r.includes(q))) return true;
        if (k.readings_kun.some((r) => r.includes(q))) return true;
        if (kana) {
          if (k.readings_on.some((r) => r.includes(kana.katakana))) return true;
          if (k.readings_kun.some((r) => r.includes(kana.hiragana))) return true;
        }
        return false;
      });
    }

    return sortKanji(items, sort);
  }, [kanji.data, search, sort]);

  // Reset visible count when filter/sort changes
  const prevFilterLen = useRef(filtered.length);
  if (filtered.length !== prevFilterLen.current) {
    prevFilterLen.current = filtered.length;
    if (visibleCount > INITIAL_LOAD) setVisibleCount(INITIAL_LOAD);
  }

  const visible = filtered.slice(0, visibleCount);
  const hasMore = visibleCount < filtered.length;

  // Intersection observer for infinite scroll
  const observerRef = useRef<IntersectionObserver | null>(null);
  const sentinelRef = useCallback(
    (node: HTMLDivElement | null) => {
      if (observerRef.current) observerRef.current.disconnect();
      if (!node || !hasMore) return;
      observerRef.current = new IntersectionObserver(
        (entries) => {
          if (entries[0].isIntersecting) {
            setVisibleCount((c) => c + CHUNK_SIZE);
          }
        },
        { rootMargin: '400px' },
      );
      observerRef.current.observe(node);
    },
    [hasMore],
  );

  // Split visible items into chunks with dividers
  const chunks: { start: number; items: KanjiItem[] }[] = [];
  for (let i = 0; i < visible.length; i += CHUNK_SIZE) {
    chunks.push({
      start: i,
      items: visible.slice(i, i + CHUNK_SIZE),
    });
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">Kanji</h1>
        <span className="text-sm text-text-muted">
          {filtered.length.toLocaleString()} kanji
        </span>
      </div>

      {/* Search + Sort */}
      <div className="flex gap-3">
        <input
          type="text"
          placeholder="Search by character, meaning, or reading..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setVisibleCount(INITIAL_LOAD); }}
          className="flex-1 px-4 py-2.5 rounded-lg border border-border bg-surface focus:outline-none focus:ring-2 focus:ring-wk-kanji"
        />
        <select
          value={sort}
          onChange={(e) => { setSort(e.target.value as SortMode); setVisibleCount(INITIAL_LOAD); }}
          className="px-3 py-2.5 rounded-lg border border-border bg-surface text-sm focus:outline-none focus:ring-2 focus:ring-wk-kanji"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Detail panel — sticky at top */}
      {selected && (
        <div className="sticky top-2 z-10">
          <KanjiDetail
            kanji={selected}
            onClose={() => setSelected(null)}
            queryClient={queryClient}
          />
        </div>
      )}

      {kanji.isLoading ? (
        <div className="text-text-muted animate-pulse text-center py-10">Loading kanji...</div>
      ) : (
        <div className="space-y-1">
          {chunks.map((chunk) => (
            <div key={chunk.start}>
              {/* Section divider */}
              {chunk.start > 0 && (
                <div className="flex items-center gap-3 py-3">
                  <div className="flex-1 h-px bg-border" />
                  <span className="text-xs text-text-muted font-medium">
                    {chunk.start + 1}–{Math.min(chunk.start + CHUNK_SIZE, filtered.length)}
                  </span>
                  <div className="flex-1 h-px bg-border" />
                </div>
              )}

              {/* Grid */}
              <div className="grid grid-cols-[repeat(auto-fill,minmax(3.2rem,1fr))] gap-1.5">
                {chunk.items.map((k) => (
                  <button
                    key={k.id}
                    onClick={() => setSelected(k)}
                    className={`aspect-square rounded-lg flex items-center justify-center text-white text-2xl kanji-text hover:scale-105 transition-all cursor-pointer ${
                      k.active ? 'bg-wk-kanji' : 'bg-gray-400 hover:bg-wk-kanji'
                    } ${selected?.id === k.id ? 'ring-2 ring-wk-kanji ring-offset-2' : ''}`}
                    title={`${k.character} — ${k.meanings.join(', ')}`}
                  >
                    {k.character}
                  </button>
                ))}
              </div>
            </div>
          ))}

          {/* Infinite scroll sentinel */}
          {hasMore && (
            <div ref={sentinelRef} className="text-center py-4 text-text-muted text-sm">
              Loading more...
            </div>
          )}

          {!hasMore && filtered.length > CHUNK_SIZE && (
            <div className="text-center py-4 text-text-muted text-xs">
              All {filtered.length.toLocaleString()} kanji loaded
            </div>
          )}
        </div>
      )}

    </div>
  );
}

function KanjiDetail({
  kanji,
  onClose,
  queryClient,
}: {
  kanji: KanjiItem;
  onClose: () => void;
  queryClient: ReturnType<typeof useQueryClient>;
}) {
  const [actionMsg, setActionMsg] = useState('');

  const learnMutation = useMutation({
    mutationFn: () =>
      api.completeLessons({ item_ids: [{ item_type: 'kanji', item_id: kanji.id }] }),
    onSuccess: () => {
      setActionMsg('Learned! First review in 4 hours.');
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
      queryClient.invalidateQueries({ queryKey: ['queue'] });
      queryClient.invalidateQueries({ queryKey: ['progress'] });
    },
    onError: (err: Error) => setActionMsg(err.message),
  });

  const queueMutation = useMutation({
    mutationFn: () => api.addToQueue('kanji', kanji.id),
    onSuccess: () => {
      setActionMsg('Added to lesson queue!');
      queryClient.invalidateQueries({ queryKey: ['queue'] });
    },
    onError: (err: Error) => setActionMsg(err.message),
  });

  return (
    <div className="bg-surface rounded-xl p-6 shadow-md relative">
      <button
        onClick={onClose}
        className="absolute top-3 right-3 text-text-muted hover:text-text text-xl leading-none"
      >
        &times;
      </button>

      <div className="flex items-start gap-6">
        <div className="bg-wk-kanji w-20 h-20 rounded-xl flex items-center justify-center text-white text-4xl kanji-text shadow-md shrink-0">
          {kanji.character}
        </div>
        <div className="space-y-3 flex-1">
          <div>
            <p className="text-text-muted text-sm">{kanji.meanings.join(', ')}</p>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-text-muted text-xs block">On'yomi</span>
              <span>{kanji.readings_on.join(', ') || 'None'}</span>
            </div>
            <div>
              <span className="text-text-muted text-xs block">Kun'yomi</span>
              <span>{kanji.readings_kun.join(', ') || 'None'}</span>
            </div>
            <div className="flex gap-4 flex-wrap">
              {kanji.frequency && (
                <span><span className="text-text-muted text-xs">Freq </span>#{kanji.frequency}</span>
              )}
              {kanji.grade && (
                <span><span className="text-text-muted text-xs">Grade </span>{kanji.grade}</span>
              )}
              {kanji.jlpt_level && (
                <span><span className="text-text-muted text-xs">JLPT </span>N{kanji.jlpt_level}</span>
              )}
              {kanji.stroke_count && (
                <span><span className="text-text-muted text-xs">Strokes </span>{kanji.stroke_count}</span>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-1">
            <button
              onClick={() => learnMutation.mutate()}
              disabled={learnMutation.isPending}
              className="px-4 py-2 rounded-lg bg-wk-kanji text-white font-bold text-sm hover:bg-accent-hover transition-colors disabled:opacity-50"
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
