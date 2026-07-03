import { useState, useMemo, useRef, useCallback, useEffect } from 'react';
import { useQuery, useInfiniteQuery } from '@tanstack/react-query';
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

// Server page size; also the block size for the frequency/default dividers.
const PAGE_SIZE = 250;

type SortMode = 'frequency' | 'grade' | 'jlpt' | 'strokes' | 'default';

const SORT_OPTIONS: { value: SortMode; label: string }[] = [
  { value: 'frequency', label: '頻度' },
  { value: 'grade', label: '学年' },
  { value: 'jlpt', label: 'JLPTレベル' },
  { value: 'strokes', label: '画数' },
  { value: 'default', label: 'データベース順' },
];

// Debounce a value so search only hits the server after typing pauses.
function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(t);
  }, [value, delayMs]);
  return debounced;
}

export function KanjiPage() {
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState<SortMode>('frequency');
  const [hideKnown, setHideKnown] = useState(false);
  const debouncedSearch = useDebounced(search.trim(), 300);

  // Sorting, search, and the known-filter all run server-side; each page is
  // PAGE_SIZE rows. Changing any of them resets to the first page via the key.
  const kanji = useInfiniteQuery({
    queryKey: ['kanji', 'page', sort, debouncedSearch, hideKnown],
    queryFn: ({ pageParam }) => {
      const params: Record<string, string> = {
        include_inactive: 'true',
        limit: String(PAGE_SIZE),
        offset: String(pageParam),
        sort,
      };
      if (debouncedSearch) {
        params.q = debouncedSearch;
        const kana = romajiToKana(debouncedSearch);
        if (kana) params.q_kana = kana.hiragana;
      }
      if (hideKnown) params.hide_known = 'true';
      return api.getKanji(params);
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      const loaded = allPages.reduce((n, p) => n + p.items.length, 0);
      return loaded < lastPage.total ? loaded : undefined;
    },
  });

  const items = useMemo(
    () => kanji.data?.pages.flatMap((p) => p.items) ?? [],
    [kanji.data],
  );
  const total = kanji.data?.pages[0]?.total ?? 0;

  // Fetch user progress to color-code tiles by SRS stage
  const progressMap = useQuery({
    queryKey: ['progressMap'],
    queryFn: api.getProgressMap,
  });

  // Intersection observer sentinel triggers the next server page.
  const observerRef = useRef<IntersectionObserver | null>(null);
  const fetchNextRef = useRef(() => {});
  fetchNextRef.current = () => {
    if (kanji.hasNextPage && !kanji.isFetchingNextPage) kanji.fetchNextPage();
  };
  const sentinelRef = useCallback(
    (node: HTMLDivElement | null) => {
      if (observerRef.current) observerRef.current.disconnect();
      if (!node) return;
      observerRef.current = new IntersectionObserver(
        (entries) => {
          if (entries[0].isIntersecting) fetchNextRef.current();
        },
        { rootMargin: '400px' },
      );
      observerRef.current.observe(node);
    },
    [],
  );

  // Build display chunks — grouped by sort-mode label, or fixed-size blocks.
  // Items arrive server-sorted, so groups grow progressively as pages load.
  const chunks = useMemo(() => {
    if (sort === 'grade') {
      const groups = new Map<string, KanjiItem[]>();
      for (const k of items) {
        const label = k.grade ? `${k.grade}年生` : '学年なし';
        if (!groups.has(label)) groups.set(label, []);
        groups.get(label)!.push(k);
      }
      return [...groups.entries()].map(([label, items]) => ({ label, items }));
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
      for (const k of items) {
        const label = k.jlpt_level ? (labelMap[k.jlpt_level] || `JLPT ${k.jlpt_level}`) : 'JLPT対象外';
        if (!groups.has(label)) groups.set(label, []);
        groups.get(label)!.push(k);
      }
      return [...groups.entries()].map(([label, items]) => ({ label, items }));
    }

    if (sort === 'strokes') {
      const groups = new Map<string, KanjiItem[]>();
      for (const k of items) {
        const label = `${k.stroke_count}画`;
        if (!groups.has(label)) groups.set(label, []);
        groups.get(label)!.push(k);
      }
      return [...groups.entries()].map(([label, items]) => ({ label, items }));
    }

    // Frequency / default: banded blocks. The band label must keep its global
    // meaning ("1–250" = frequency ranks 1–250) even when hide-known drops
    // items, so derive the band from each kanji's own rank (frequency rank, or
    // DB id for database order) instead of its position in the filtered list.
    // Fully-known bands simply don't appear.
    if (hideKnown) {
      const groups = new Map<string, KanjiItem[]>();
      for (const k of items) {
        const rank = sort === 'frequency' ? k.frequency : k.id;
        const label = rank
          ? `${Math.floor((rank - 1) / PAGE_SIZE) * PAGE_SIZE + 1}–${(Math.floor((rank - 1) / PAGE_SIZE) + 1) * PAGE_SIZE}`
          : '頻度なし';
        if (!groups.has(label)) groups.set(label, []);
        groups.get(label)!.push(k);
      }
      return [...groups.entries()].map(([label, items]) => ({ label, items }));
    }

    // Unfiltered: list position equals global rank, so plain blocks are correct.
    const result: { label: string; items: KanjiItem[] }[] = [];
    for (let i = 0; i < items.length; i += PAGE_SIZE) {
      result.push({
        label: `${i + 1}–${Math.min(i + PAGE_SIZE, total)}`,
        items: items.slice(i, i + PAGE_SIZE),
      });
    }
    return result;
  }, [items, sort, total, hideKnown]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">漢字</h1>
        <span className="text-sm text-muted-foreground">
          {hideKnown
            ? `未習得 ${total.toLocaleString()}字`
            : `${total.toLocaleString()}字`}
        </span>
      </div>

      {/* Search + Sort + Filter */}
      <div className="flex gap-3">
        <Input
          type="text"
          placeholder="文字・意味・読みで検索..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1"
        />
        <Button
          type="button"
          variant={hideKnown ? 'default' : 'outline'}
          onClick={() => setHideKnown(!hideKnown)}
          className="whitespace-nowrap"
        >
          習得済みを隠す
        </Button>
        <Select value={sort} onValueChange={(v) => setSort(v as SortMode)}>
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

          {items.length === 0 && (
            <p className="text-center py-8 text-sm text-muted-foreground">
              該当する漢字がありません。
            </p>
          )}

          {/* Infinite scroll sentinel */}
          {kanji.hasNextPage && (
            <div ref={sentinelRef} className="text-center py-4 text-muted-foreground text-sm">
              読み込み中...
            </div>
          )}

          {!kanji.hasNextPage && items.length > PAGE_SIZE && (
            <div className="text-center py-4 text-muted-foreground text-xs">
              全{total.toLocaleString()}字を読み込みました
            </div>
          )}
        </div>
      )}

    </div>
  );
}
