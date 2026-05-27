import { useState, useMemo, useRef, useCallback, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type KanjiItem } from '../lib/api';
import { romajiToKana } from '../lib/romaji';
import { SRS_STAGE_COLORS, SRS_STAGE_NAMES, getSrsGroup } from '../lib/srs';

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
  const [hideKnown, setHideKnown] = useState(false);

  const kanji = useQuery({
    queryKey: ['kanji', 'all'],
    queryFn: () => api.getKanji({ include_inactive: 'true' }),
  });

  // Fetch user progress to color-code tiles by SRS stage
  const progressMap = useQuery({
    queryKey: ['progressMap'],
    queryFn: api.getProgressMap,
  });

  // Full sorted list (before hide-known filtering) — used for stable chunk positions
  const sortedAll = useMemo(() => {
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

  const filtered = sortedAll;

  // Reset visible count when sort/search changes
  const prevSortedLen = useRef(sortedAll.length);
  if (sortedAll.length !== prevSortedLen.current) {
    prevSortedLen.current = sortedAll.length;
    if (visibleCount > INITIAL_LOAD) setVisibleCount(INITIAL_LOAD);
  }

  const hasMore = visibleCount < sortedAll.length;

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

  // Build chunks — either by sort-mode groups or fixed-size blocks
  const chunks = useMemo(() => {
    const visible = sortedAll.slice(0, visibleCount);
    const filterKnown = (items: KanjiItem[]) =>
      hideKnown && progressMap.data
        ? items.filter((k) => progressMap.data![`kanji-${k.id}`] == null)
        : items;

    // Group-based chunking for grade/jlpt/strokes
    if (sort === 'grade') {
      const groups = new Map<string, KanjiItem[]>();
      for (const k of visible) {
        const label = k.grade ? `Grade ${k.grade}` : 'No Grade';
        if (!groups.has(label)) groups.set(label, []);
        groups.get(label)!.push(k);
      }
      return [...groups.entries()].map(([label, items]) => ({
        label,
        items: filterKnown(items),
      }));
    }

    if (sort === 'jlpt') {
      const groups = new Map<string, KanjiItem[]>();
      // Old JLPT had 4 levels: 4≈N5+N4, 3≈N3, 2≈N2, 1≈N1
      const labelMap: Record<number, string> = {
        4: 'JLPT N4 + N5',
        3: 'JLPT N3',
        2: 'JLPT N2',
        1: 'JLPT N1',
      };
      for (const k of visible) {
        const label = k.jlpt_level ? (labelMap[k.jlpt_level] || `JLPT ${k.jlpt_level}`) : 'Not in JLPT';
        if (!groups.has(label)) groups.set(label, []);
        groups.get(label)!.push(k);
      }
      return [...groups.entries()].map(([label, items]) => ({
        label,
        items: filterKnown(items),
      }));
    }

    if (sort === 'strokes') {
      const groups = new Map<string, KanjiItem[]>();
      for (const k of visible) {
        const label = `${k.stroke_count} Stroke${k.stroke_count !== 1 ? 's' : ''}`;
        if (!groups.has(label)) groups.set(label, []);
        groups.get(label)!.push(k);
      }
      return [...groups.entries()].map(([label, items]) => ({
        label,
        items: filterKnown(items),
      }));
    }

    // Frequency / default: fixed-size blocks
    const result: { label: string; items: KanjiItem[] }[] = [];
    for (let i = 0; i < visible.length; i += CHUNK_SIZE) {
      const chunkItems = visible.slice(i, i + CHUNK_SIZE);
      result.push({
        label: `${i + 1}–${Math.min(i + CHUNK_SIZE, sortedAll.length)}`,
        items: filterKnown(chunkItems),
      });
    }
    return result;
  }, [sortedAll, visibleCount, hideKnown, progressMap.data, sort]);

  // Load everything when hiding known or using grouped sort modes
  const isGroupedSort = sort === 'grade' || sort === 'jlpt' || sort === 'strokes';
  useEffect(() => {
    if ((hideKnown || isGroupedSort) && hasMore) {
      setVisibleCount(sortedAll.length);
    }
  }, [hideKnown, isGroupedSort, sortedAll.length]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">Kanji</h1>
        <span className="text-sm text-text-muted">
          {hideKnown
            ? `${(sortedAll.length - Object.keys(progressMap.data || {}).length).toLocaleString()} unknown / ${sortedAll.length.toLocaleString()}`
            : `${sortedAll.length.toLocaleString()} kanji`}
        </span>
      </div>

      {/* Search + Sort + Filter */}
      <div className="flex gap-3">
        <input
          type="text"
          placeholder="Search by character, meaning, or reading..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setVisibleCount(INITIAL_LOAD); }}
          className="flex-1 px-4 py-2.5 rounded-lg border border-border bg-surface focus:outline-none focus:ring-2 focus:ring-wk-kanji"
        />
        <button
          onClick={() => { setHideKnown(!hideKnown); setVisibleCount(INITIAL_LOAD); }}
          className={`px-3 py-2.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
            hideKnown ? 'bg-wk-kanji text-white' : 'border border-border bg-surface hover:bg-border'
          }`}
        >
          Hide Known
        </button>
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
            <div key={chunk.label}>
              {/* Section divider */}
              <div className="flex items-center gap-3 py-2">
                <div className="flex-1 h-px bg-border" />
                <span className="text-xs text-text-muted font-medium">
                  {chunk.label}
                  {hideKnown && chunk.items.length === 0 && ' ✓'}
                </span>
                <div className="flex-1 h-px bg-border" />
              </div>

              {/* Grid */}
              <div className="grid grid-cols-[repeat(auto-fill,minmax(3.2rem,1fr))] gap-1.5">
                {chunk.items.map((k) => {
                  const srsStage = progressMap.data?.[`kanji-${k.id}`];
                  const stageColor = srsStage != null ? SRS_STAGE_COLORS[srsStage] : undefined;
                  const group = srsStage != null ? getSrsGroup(srsStage) : undefined;
                  return (
                    <button
                      key={k.id}
                      onClick={() => setSelected(k)}
                      className={`aspect-square rounded-lg flex items-center justify-center text-white text-2xl hover:scale-105 transition-all cursor-pointer ${
                        selected?.id === k.id ? 'ring-2 ring-offset-2' : ''
                      } ${!stageColor ? 'bg-border hover:bg-text-muted/30 text-text-muted' : ''}`}
                      style={stageColor ? { backgroundColor: stageColor } : undefined}
                      title={`${k.character} — ${k.meanings.join(', ')}${group ? ` (${group})` : ''}`}
                    >
                      {k.character}
                    </button>
                  );
                })}
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
              All {sortedAll.length.toLocaleString()} kanji loaded
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

  // Check if already in progress
  const progressMap = useQuery({
    queryKey: ['progressMap'],
    queryFn: api.getProgressMap,
  });
  const currentStage = progressMap.data?.[`kanji-${kanji.id}`];
  const alreadyLearned = currentStage != null;

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
        <div className="bg-wk-kanji w-20 h-20 rounded-xl flex items-center justify-center text-white text-4xl shadow-md shrink-0">
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
