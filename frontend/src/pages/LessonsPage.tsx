import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { X } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type QueueItem } from '../lib/api';
import { RadicalList } from '../components/RadicalList';
import { GlyphCell } from '../components/GlyphCell';
import { LessonQuiz } from '../components/LessonQuiz';
import { QuizShell } from '../components/QuizShell';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';

// Remove-from-queue badge: a quiet paper square (sharp corners, ink border) that
// surfaces on cell hover and inks in (bg-foreground) when you hover the badge
// itself — mirroring the ✓ check badge. Stays in the sumi-ink palette; the X
// icon + tooltip carry the "remove" meaning, so no red is needed.
const removeBadgeClass =
  'absolute -top-2 -right-2 z-10 grid size-5 place-items-center border border-border ' +
  'bg-background text-muted-foreground opacity-0 transition-colors transition-opacity ' +
  'group-hover:opacity-100 hover:border-foreground hover:bg-foreground hover:text-background';

type Tab = 'composition' | 'meaning' | 'reading';

// The ordered tabs a card steps through. Vocab with constituent kanji gets a
// leading "Kanji Composition" panel (WaniKani-style); kanji and kana-only vocab
// skip it.
function tabOrderFor(item: QueueItem | undefined): Tab[] {
  const hasComposition = (item?.item_details?.kanji?.length ?? 0) > 0;
  return hasComposition
    ? ['composition', 'meaning', 'reading']
    : ['meaning', 'reading'];
}

export function LessonsPage() {
  const queryClient = useQueryClient();
  const [sessionActive, setSessionActive] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [activeTab, setActiveTab] = useState<Tab>('meaning');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [sessionItems, setSessionItems] = useState<QueueItem[]>([]);

  const queue = useQuery({
    queryKey: ['queue'],
    queryFn: api.getQueue,
  });

  const removeMutation = useMutation({
    mutationFn: ({ item_type, item_id }: { item_type: string; item_id: number }) =>
      api.removeFromQueue(item_type, item_id),
    onMutate: async ({ item_type, item_id }) => {
      await queryClient.cancelQueries({ queryKey: ['queue'] });
      queryClient.setQueryData<QueueItem[]>(['queue'], (old) =>
        old?.filter((i) => !(i.item_type === item_type && i.item_id === item_id))
      );
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['queue'] });
    },
  });

  const completeMutation = useMutation({
    mutationFn: api.completeLessons,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queue'] });
      queryClient.invalidateQueries({ queryKey: ['progress'] });
      queryClient.invalidateQueries({ queryKey: ['progressMap'] });
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
      setSessionActive(false);
      setCurrentIndex(0);
      setSelectedIds(new Set());
    },
  });

  // Step forward through the current card's tabs, then on to the next card
  // (landing on its first tab).
  const goForward = () => {
    if (!sessionActive || currentIndex >= sessionItems.length) return;
    const order = tabOrderFor(sessionItems[currentIndex]);
    const tabIdx = order.indexOf(activeTab);
    if (tabIdx < order.length - 1) {
      setActiveTab(order[tabIdx + 1]);
    } else {
      const next = currentIndex + 1;
      setCurrentIndex(next);
      setActiveTab(tabOrderFor(sessionItems[next])[0]);
    }
  };

  // Step back through tabs, then to the previous card's last tab so the flow is
  // reversible.
  const goBack = () => {
    if (!sessionActive || currentIndex >= sessionItems.length) return;
    const order = tabOrderFor(sessionItems[currentIndex]);
    const tabIdx = order.indexOf(activeTab);
    if (tabIdx > 0) {
      setActiveTab(order[tabIdx - 1]);
    } else if (currentIndex > 0) {
      const prev = currentIndex - 1;
      const prevOrder = tabOrderFor(sessionItems[prev]);
      setCurrentIndex(prev);
      setActiveTab(prevOrder[prevOrder.length - 1]);
    }
  };

  // Arrow keys drive the same progression as the on-screen buttons.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) return;
      if (e.key === 'ArrowRight') { e.preventDefault(); goForward(); }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); goBack(); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  });

  const items = queue.data ?? [];
  // Locked vocab (constituent kanji not yet Guru) is shown for look-ahead but can't be studied.
  const unlocked = items.filter((i) => !i.locked);
  const lockedItems = items.filter((i) => i.locked);

  const itemKey = (item: QueueItem) => `${item.item_type}-${item.item_id}`;

  const toggleSelect = (item: QueueItem) => {
    const key = itemKey(item);
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const selectAll = () => {
    if (selectedIds.size === unlocked.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(unlocked.map(itemKey)));
    }
  };

  const startSession = () => {
    const toStudy = selectedIds.size > 0
      ? unlocked.filter((i) => selectedIds.has(itemKey(i)))
      : unlocked;
    setSessionItems(toStudy);
    setSessionActive(true);
    setCurrentIndex(0);
    setActiveTab(tabOrderFor(toStudy[0])[0]);
  };

  // Queue overview — immersive (no navbar), home button via QuizShell.
  if (!sessionActive) {
    const selectedCount = selectedIds.size || unlocked.length;
    const unlockedKanji = unlocked.filter((i) => i.item_type === 'kanji');
    const unlockedVocab = unlocked.filter((i) => i.item_type === 'vocab');

    const renderCell = (item: QueueItem) => {
      const display = item.item_details?.character || item.item_details?.word || '?';
      const key = itemKey(item);
      const isSelected = selectedIds.has(key);
      return (
        <div key={key} className="group relative">
          <button
            onClick={() => toggleSelect(item)}
            className={cn('block transition-opacity', !isSelected && selectedIds.size > 0 && 'opacity-50')}
            title={item.item_details?.meanings?.join(', ')}
          >
            <GlyphCell
              type={item.item_type as 'kanji' | 'vocab'}
              character={display}
              selected={isSelected}
              size="md"
            />
          </button>
          {isSelected && (
            <span className="absolute -top-2 -left-2 z-10 grid size-5 place-items-center bg-foreground font-mono text-[10px] text-background">
              &#10003;
            </span>
          )}
          <button
            onClick={(e) => {
              e.stopPropagation();
              removeMutation.mutate({ item_type: item.item_type, item_id: item.item_id });
              setSelectedIds((prev) => { const next = new Set(prev); next.delete(key); return next; });
            }}
            className={removeBadgeClass}
            title="キューから削除"
            aria-label="キューから削除"
          >
            <X className="size-3" strokeWidth={2.5} />
          </button>
        </div>
      );
    };

    return (
      <QuizShell exitTo="/" right={items.length > 0 ? `${unlocked.length}件 準備完了` : undefined}>
        <div className="mx-auto w-full max-w-4xl space-y-6 px-4 py-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <h1 className="font-mono text-2xl font-bold tracking-wide uppercase">レッスン</h1>
            {unlocked.length > 0 && (
              <div className="flex items-center gap-2">
                <Button variant="outline" onClick={selectAll}>
                  {selectedIds.size === unlocked.length ? '選択を解除' : 'すべて選択'}
                </Button>
                <Button onClick={startSession}>レッスン開始 ({selectedCount})</Button>
              </div>
            )}
          </div>

          {/* Hint */}
          {unlocked.length > 0 && selectedIds.size === 0 && (
            <p className="text-sm text-muted-foreground">
              項目をタップして選択するか、{unlocked.length}件すべてを開始します。
            </p>
          )}
          {selectedIds.size > 0 && (
            <p className="text-sm text-muted-foreground">
              {unlocked.length}件中{selectedIds.size}件を選択
            </p>
          )}

          {queue.isLoading ? (
            <div className="animate-pulse text-muted-foreground">読み込み中...</div>
          ) : items.length === 0 ? (
            <Card className="gap-2 p-10 text-center text-muted-foreground">
              <p className="mb-2 text-lg font-bold">レッスンキューは空です</p>
              <p>漢字ページまたは語彙ページから項目をキューに追加し、ここに戻って学習しましょう。</p>
            </Card>
          ) : (
            <>
              {/* Grouped by type with a divider so kanji vs vocab read clearly. */}
              {unlockedKanji.length > 0 && (
                <div className="space-y-2">
                  <p className="font-mono text-xs font-semibold tracking-wider text-muted-foreground uppercase">
                    漢字 ({unlockedKanji.length})
                  </p>
                  <div className="flex flex-wrap gap-3">{unlockedKanji.map(renderCell)}</div>
                </div>
              )}

              {unlockedKanji.length > 0 && unlockedVocab.length > 0 && <Separator />}

              {unlockedVocab.length > 0 && (
                <div className="space-y-2">
                  <p className="font-mono text-xs font-semibold tracking-wider text-muted-foreground uppercase">
                    語彙 ({unlockedVocab.length})
                  </p>
                  <div className="flex flex-wrap gap-3">{unlockedVocab.map(renderCell)}</div>
                </div>
              )}

              {/* Locked: vocab waiting on its kanji to reach Guru — shown for look-ahead. */}
              {lockedItems.length > 0 && (
                <div className="space-y-2 pt-2">
                  <p className="font-mono text-xs font-semibold tracking-wider text-muted-foreground uppercase">
                    ロック中 — 漢字待ち ({lockedItems.length})
                  </p>
                  <div className="flex flex-wrap gap-3">
                    {lockedItems.map((item) => {
                      const display = item.item_details?.word || item.item_details?.character || '?';
                      const key = itemKey(item);
                      const blockedBy = item.locked_by ?? [];
                      const tip = blockedBy.length
                        ? `次の漢字が「Guru」に達するまでロックされています: ${blockedBy.join('、')}`
                        : '漢字が「Guru」に達するまでロックされています';

                      return (
                        <div key={key} className="group relative cursor-not-allowed opacity-40" title={tip}>
                          <GlyphCell type={item.item_type as 'kanji' | 'vocab'} character={display} size="md" />
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              removeMutation.mutate({ item_type: item.item_type, item_id: item.item_id });
                            }}
                            className={removeBadgeClass}
                            title="キューから削除"
                            aria-label="キューから削除"
                          >
                            <X className="size-3" strokeWidth={2.5} />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </QuizShell>
    );
  }

  // Lesson session
  const item = sessionItems[currentIndex];
  if (!item) {
    // All cards viewed — gate official learning behind a scrambled quiz.
    return (
      <LessonQuiz
        items={sessionItems}
        submitting={completeMutation.isPending}
        error={completeMutation.error}
        onPassed={() =>
          completeMutation.mutate({
            item_ids: sessionItems.map((c) => ({
              item_type: c.item_type,
              item_id: c.item_id,
            })),
          })
        }
        onExit={() => setSessionActive(false)}
      />
    );
  }

  const isKanji = item.item_type === 'kanji';
  const display = item.item_details?.character || item.item_details?.word || '?';
  const meanings = item.item_details?.meanings || [];
  const readingsOn = (item.item_details as Record<string, unknown>)?.readings_on as string[] | undefined;
  const readingsKun = (item.item_details as Record<string, unknown>)?.readings_kun as string[] | undefined;
  const readings = (item.item_details as Record<string, unknown>)?.readings as string[] | undefined;
  const components = item.item_details?.components ?? [];
  const kanjiComposition = item.item_details?.kanji ?? [];

  const tabOrder = tabOrderFor(item);
  const isLastStep =
    currentIndex === sessionItems.length - 1 && activeTab === tabOrder[tabOrder.length - 1];
  const atStart = currentIndex === 0 && tabOrder.indexOf(activeTab) === 0;

  const tabLabels: Record<Tab, string> = {
    composition: '漢字構成',
    meaning: '意味',
    reading: isKanji ? '読み' : '読み方',
  };
  const tabs: { id: Tab; label: string }[] = tabOrder.map((id) => ({
    id,
    label: tabLabels[id],
  }));

  return (
    <QuizShell
      onExit={() => setSessionActive(false)}
      right={`${currentIndex + 1} / ${sessionItems.length}`}
    >
      {/* Hero — character floats in a very faint type-tinted block (pink=kanji, purple=vocab) */}
      <div
        className="flex shrink-0 flex-col items-center gap-3 py-14"
        style={{ backgroundColor: `color-mix(in srgb, var(--card) 93%, ${isKanji ? '#ff00aa' : '#aa00ff'})` }}
      >
        <span lang="ja" className="font-[family-name:var(--font-mincho)] text-8xl leading-none">
          {display}
        </span>
        <span className="text-lg text-muted-foreground">{meanings[0]}</span>
      </div>

      {/* Tabs — full width, mono */}
      <div className="flex shrink-0 border-y border-border bg-muted">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'relative flex-1 py-3 font-mono text-xs tracking-wider uppercase transition-colors',
              activeTab === tab.id ? 'text-foreground' : 'text-muted-foreground hover:text-foreground',
            )}
          >
            {tab.label}
            {activeTab === tab.id && (
              <div className="absolute right-0 bottom-0 left-0 h-0.5 bg-foreground" />
            )}
          </button>
        ))}
      </div>

      {/* Tab content + navigation in a centered column */}
      <div className="flex-1 w-full max-w-2xl mx-auto px-4 py-6">
        <div className="min-h-[200px]">
        {activeTab === 'composition' && (
          <div className="space-y-4">
            <h3 className="text-muted-foreground text-xs uppercase tracking-wide mb-2">
              漢字構成
            </h3>
            <p className="text-sm text-muted-foreground">
              この語彙は{kanjiComposition.length === 1
                ? '1つの漢字'
                : `${kanjiComposition.length}つの漢字`}で構成されています:
            </p>
            <div className="flex gap-4 flex-wrap">
              {kanjiComposition.map((k) => (
                <Link
                  key={k.character}
                  to={`/kanji/${encodeURIComponent(k.character)}`}
                  className="-mx-1 flex items-center gap-2 px-1 py-0.5 transition-colors hover:bg-accent"
                  title={`${k.character} を表示`}
                >
                  <GlyphCell type="kanji" character={k.character} size="sm" />
                  <span className="text-sm">{k.meanings[0]}</span>
                </Link>
              ))}
            </div>
            <p className="text-sm text-muted-foreground pt-2">
              これらの漢字の意味の組み合わせは、語彙の意味と関係していますか。
              漢字から読み方を推測できますか。
            </p>
          </div>
        )}

        {activeTab === 'meaning' && (
          <div className="space-y-4">
            <div>
              <h3 className="text-muted-foreground text-xs uppercase tracking-wide mb-2">意味</h3>
              <p className="text-lg">{meanings.join('、')}</p>
            </div>
            {isKanji && components.length > 0 && (
              <div>
                <h3 className="text-muted-foreground text-xs uppercase tracking-wide mb-2">部首</h3>
                <RadicalList components={components} />
              </div>
            )}
          </div>
        )}

        {activeTab === 'reading' && (
          <div className="space-y-4">
            {isKanji ? (
              <>
                {readingsOn && readingsOn.length > 0 && (
                  <div>
                    <h3 className="text-muted-foreground text-xs uppercase tracking-wide mb-2">音読み</h3>
                    <p className="text-lg">{readingsOn.join('、')}</p>
                  </div>
                )}
                {readingsKun && readingsKun.length > 0 && (
                  <div>
                    <h3 className="text-muted-foreground text-xs uppercase tracking-wide mb-2">訓読み</h3>
                    <p className="text-lg">{readingsKun.join('、')}</p>
                  </div>
                )}
              </>
            ) : (
              <div>
                <h3 className="text-muted-foreground text-xs uppercase tracking-wide mb-2">読み方</h3>
                <p className="text-lg">{readings?.join('、') || 'なし'}</p>
              </div>
            )}
          </div>
        )}
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between pt-6">
          <Button variant="outline" onClick={goBack} disabled={atStart} className="disabled:opacity-30">
            <kbd className="mr-1.5 bg-muted px-1.5 py-0.5 font-mono text-[10px] text-foreground">&larr;</kbd>
            戻る
          </Button>
          <Button onClick={goForward}>
            {isLastStep ? '完了' : '次へ'}
            <kbd className="ml-1.5 bg-primary-foreground/20 px-1.5 py-0.5 font-mono text-[10px]">&rarr;</kbd>
          </Button>
        </div>
      </div>
    </QuizShell>
  );
}
