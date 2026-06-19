import { useState, useMemo, useRef, useCallback, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, type KanjiItem } from '../lib/api';
import { SubjectCard } from '../components/SubjectCard';
import { romajiToKana } from '../lib/romaji';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

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
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState<SortMode>('frequency');
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
        <span className="text-sm text-muted-foreground">
          {hideKnown
            ? `${(sortedAll.length - Object.keys(progressMap.data || {}).length).toLocaleString()} unknown / ${sortedAll.length.toLocaleString()}`
            : `${sortedAll.length.toLocaleString()} kanji`}
        </span>
      </div>

      {/* Search + Sort + Filter */}
      <div className="flex gap-3">
        <Input
          type="text"
          placeholder="Search by character, meaning, or reading..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setVisibleCount(INITIAL_LOAD); }}
          className="flex-1"
        />
        <Button
          type="button"
          variant={hideKnown ? 'default' : 'outline'}
          onClick={() => { setHideKnown(!hideKnown); setVisibleCount(INITIAL_LOAD); }}
          className="whitespace-nowrap"
        >
          Hide Known
        </Button>
        <Select
          value={sort}
          onValueChange={(v) => { setSort(v as SortMode); setVisibleCount(INITIAL_LOAD); }}
        >
          <SelectTrigger className="w-auto">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SORT_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {kanji.isLoading ? (
        <div className="flex flex-wrap gap-2 pt-4">
          {Array.from({ length: 24 }).map((_, i) => (
            <Skeleton key={i} className="h-[88px] w-[78px] rounded-lg" />
          ))}
        </div>
      ) : (
        <div className="space-y-1">
          {chunks.map((chunk) => (
            <div key={chunk.label}>
              {/* Section divider */}
              <div className="flex items-center gap-3 py-2">
                <Separator className="flex-1" />
                <span className="text-xs text-muted-foreground font-medium whitespace-nowrap">
                  {chunk.label}
                  {hideKnown && chunk.items.length === 0 && ' ✓'}
                </span>
                <Separator className="flex-1" />
              </div>

              {/* Grid */}
              <div className="flex flex-wrap gap-2">
                {chunk.items.map((k) => (
                  <SubjectCard
                    key={k.id}
                    type="kanji"
                    character={k.character}
                    reading={k.readings_on[0] || k.readings_kun[0]}
                    meaning={k.meanings[0]}
                    srsStage={progressMap.data?.[`kanji-${k.id}`]}
                    to={`/kanji/${encodeURIComponent(k.character)}`}
                  />
                ))}
              </div>
            </div>
          ))}

          {/* Infinite scroll sentinel */}
          {hasMore && (
            <div ref={sentinelRef} className="text-center py-4 text-muted-foreground text-sm">
              Loading more...
            </div>
          )}

          {!hasMore && filtered.length > CHUNK_SIZE && (
            <div className="text-center py-4 text-muted-foreground text-xs">
              All {sortedAll.length.toLocaleString()} kanji loaded
            </div>
          )}
        </div>
      )}

    </div>
  );
}
