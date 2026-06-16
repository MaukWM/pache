import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type QueueItem } from '../lib/api';
import { RadicalList } from '../components/RadicalList';
import { LessonQuiz } from '../components/LessonQuiz';
import { QuizShell } from '../components/QuizShell';

type Tab = 'composition' | 'meaning' | 'reading' | 'info';

// The ordered tabs a card steps through. Vocab with constituent kanji gets a
// leading "Kanji Composition" panel (WaniKani-style); kanji and kana-only vocab
// skip it.
function tabOrderFor(item: QueueItem | undefined): Tab[] {
  const hasComposition = (item?.item_details?.kanji?.length ?? 0) > 0;
  return hasComposition
    ? ['composition', 'meaning', 'reading', 'info']
    : ['meaning', 'reading', 'info'];
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

  // Step back through tabs, then to the previous card's last tab ('info') so the
  // flow is reversible.
  const goBack = () => {
    if (!sessionActive || currentIndex >= sessionItems.length) return;
    const order = tabOrderFor(sessionItems[currentIndex]);
    const tabIdx = order.indexOf(activeTab);
    if (tabIdx > 0) {
      setActiveTab(order[tabIdx - 1]);
    } else if (currentIndex > 0) {
      setCurrentIndex((i) => i - 1);
      setActiveTab('info');
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

  // Queue overview
  if (!sessionActive) {
    const selectedCount = selectedIds.size || unlocked.length;

    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Lessons</h1>
          {unlocked.length > 0 && (
            <div className="flex items-center gap-2">
              <button
                onClick={selectAll}
                className="px-3 py-2 rounded-lg bg-surface border border-border text-sm font-medium hover:bg-border transition-colors"
              >
                {selectedIds.size === unlocked.length ? 'Deselect All' : 'Select All'}
              </button>
              <button
                onClick={startSession}
                className="px-5 py-2 rounded-lg bg-wk-radical text-white font-bold hover:opacity-90 transition-opacity"
              >
                Start Lessons ({selectedCount})
              </button>
            </div>
          )}
        </div>

        {/* Hint */}
        {unlocked.length > 0 && selectedIds.size === 0 && (
          <p className="text-sm text-text-muted">
            Tap items to select a subset, or start all {unlocked.length} at once.
          </p>
        )}
        {selectedIds.size > 0 && (
          <p className="text-sm text-text-muted">
            {selectedIds.size} of {unlocked.length} selected
          </p>
        )}

        {queue.isLoading ? (
          <div className="text-text-muted animate-pulse">Loading queue...</div>
        ) : items.length === 0 ? (
          <div className="bg-surface rounded-xl p-10 text-center text-text-muted">
            <p className="text-lg font-bold mb-2">No lessons queued</p>
            <p>Add items from the Kanji or Vocab pages to your queue, then come back here to study them.</p>
          </div>
        ) : (
          <>
            {unlocked.length > 0 && (
              <div className="flex flex-wrap gap-2.5">
                {unlocked.map((item) => {
                  const isKanji = item.item_type === 'kanji';
                  const display = item.item_details?.character || item.item_details?.word || '?';
                  const key = itemKey(item);
                  const isSelected = selectedIds.has(key);
                  const baseBg = isKanji ? 'bg-wk-kanji' : 'bg-wk-vocab';

                  return (
                    <div key={key} className="relative group">
                      <button
                        onClick={() => toggleSelect(item)}
                        className={`${baseBg} rounded-lg px-4 py-2.5 text-white font-bold text-xl transition-all hover:brightness-110 ${
                          isSelected
                            ? 'scale-95 opacity-100 shadow-lg outline outline-3 outline-offset-2 outline-white'
                            : selectedIds.size > 0 ? 'opacity-50' : ''
                        }`}
                        title={item.item_details?.meanings?.join(', ')}
                      >
                        {display}
                        {isSelected && (
                          <span className="absolute -top-1 -left-1 w-5 h-5 rounded-full bg-wk-radical text-white text-[10px] flex items-center justify-center font-bold shadow">
                            &#10003;
                          </span>
                        )}
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          removeMutation.mutate({ item_type: item.item_type, item_id: item.item_id });
                          setSelectedIds((prev) => { const next = new Set(prev); next.delete(key); return next; });
                        }}
                        className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-error text-white text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow z-10"
                        title="Remove from queue"
                      >
                        &times;
                      </button>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Locked: vocab waiting on its kanji to reach Guru — shown for look-ahead. */}
            {lockedItems.length > 0 && (
              <div className="space-y-2 pt-2">
                <p className="text-xs font-bold uppercase tracking-wide text-text-muted">
                  Locked — waiting on kanji ({lockedItems.length})
                </p>
                <div className="flex flex-wrap gap-2.5">
                  {lockedItems.map((item) => {
                    const display = item.item_details?.word || item.item_details?.character || '?';
                    const key = itemKey(item);
                    const blockedBy = item.locked_by ?? [];
                    const tip = blockedBy.length
                      ? `Locked until these kanji reach Guru: ${blockedBy.join('、')}`
                      : 'Locked until its kanji reach Guru';

                    return (
                      <div key={key} className="relative group">
                        <div
                          className="bg-wk-vocab/30 text-white/70 rounded-lg px-4 py-2.5 font-bold text-xl cursor-not-allowed select-none"
                          title={tip}
                        >
                          {display}
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            removeMutation.mutate({ item_type: item.item_type, item_id: item.item_id });
                          }}
                          className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-error text-white text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow z-10"
                          title="Remove from queue"
                        >
                          &times;
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
  const bgColor = isKanji ? 'bg-wk-kanji' : 'bg-wk-vocab';

  const tabOrder = tabOrderFor(item);
  const isLastStep = currentIndex === sessionItems.length - 1 && activeTab === 'info';
  const atStart = currentIndex === 0 && tabOrder.indexOf(activeTab) === 0;

  const tabLabels: Record<Tab, string> = {
    composition: 'Kanji Composition',
    meaning: 'Meaning',
    reading: isKanji ? 'Readings' : 'Reading',
    info: 'Info',
  };
  const tabs: { id: Tab; label: string }[] = tabOrder.map((id) => ({
    id,
    label: tabLabels[id],
  }));

  return (
    <QuizShell
      onExit={() => setSessionActive(false)}
      right={<span>{currentIndex + 1} / {sessionItems.length}</span>}
    >
      {/* Hero band — full width, WaniKani-style */}
      <div className={`${bgColor} p-10 text-white text-center shrink-0`}>
        <div className="text-7xl font-bold mb-3" lang="ja">{display}</div>
        <div className="text-xl opacity-90">{meanings[0]}</div>
      </div>

      {/* Tabs — full width */}
      <div className="bg-surface-alt flex border-b border-border shrink-0">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 py-3 text-sm font-medium transition-colors relative ${
              activeTab === tab.id ? 'text-text' : 'text-text-muted hover:text-text'
            }`}
          >
            {tab.label}
            {activeTab === tab.id && (
              <div className={`absolute bottom-0 left-0 right-0 h-0.5 ${bgColor}`} />
            )}
          </button>
        ))}
      </div>

      {/* Tab content + navigation in a centered column */}
      <div className="flex-1 w-full max-w-2xl mx-auto px-4 py-6">
        <div className="min-h-[200px]">
        {activeTab === 'composition' && (
          <div className="space-y-4">
            <h3 className="text-text-muted text-xs uppercase tracking-wide mb-2">
              Kanji Composition
            </h3>
            <p className="text-sm text-text-muted">
              This vocabulary is composed of{' '}
              {kanjiComposition.length === 1
                ? 'one kanji'
                : `${kanjiComposition.length} kanji`}
              :
            </p>
            <div className="flex gap-4 flex-wrap">
              {kanjiComposition.map((k) => (
                <Link
                  key={k.character}
                  to={`/kanji/${encodeURIComponent(k.character)}`}
                  className="flex items-center gap-2 rounded-lg hover:bg-surface-alt px-1 py-0.5 -mx-1 transition-colors"
                  title={`View ${k.character}`}
                >
                  <div className="bg-wk-kanji border-2 border-wk-kanji-dark w-11 h-11 rounded-lg flex items-center justify-center text-white text-xl font-bold" lang="ja">
                    {k.character}
                  </div>
                  <span className="text-sm">{k.meanings[0]}</span>
                </Link>
              ))}
            </div>
            <p className="text-sm text-text-muted pt-2">
              Does the combination of the kanji meanings relate to the vocabulary meaning?
              Can you guess the reading from the kanji?
            </p>
          </div>
        )}

        {activeTab === 'meaning' && (
          <div className="space-y-4">
            <div>
              <h3 className="text-text-muted text-xs uppercase tracking-wide mb-2">Meanings</h3>
              <p className="text-lg">{meanings.join(', ')}</p>
            </div>
            {isKanji && components.length > 0 && (
              <div>
                <h3 className="text-text-muted text-xs uppercase tracking-wide mb-2">Radicals</h3>
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
                    <h3 className="text-text-muted text-xs uppercase tracking-wide mb-2">On'yomi</h3>
                    <p className="text-lg">{readingsOn.join('、')}</p>
                  </div>
                )}
                {readingsKun && readingsKun.length > 0 && (
                  <div>
                    <h3 className="text-text-muted text-xs uppercase tracking-wide mb-2">Kun'yomi</h3>
                    <p className="text-lg">{readingsKun.join('、')}</p>
                  </div>
                )}
              </>
            ) : (
              <div>
                <h3 className="text-text-muted text-xs uppercase tracking-wide mb-2">Reading</h3>
                <p className="text-lg">{readings?.join('、') || 'None'}</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'info' && (
          <div className="space-y-2 text-sm">
            <div className="flex gap-2">
              <span className="text-text-muted">Type:</span>
              <span className="capitalize">{item.item_type}</span>
            </div>
            <div className="flex gap-2">
              <span className="text-text-muted">Added:</span>
              <span>{new Date(item.added_at).toLocaleDateString()}</span>
            </div>
          </div>
        )}
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between pt-6">
          <button
            onClick={goBack}
            disabled={atStart}
            className="px-5 py-2.5 rounded-lg bg-surface border border-border font-bold text-sm disabled:opacity-30 hover:bg-border transition-colors"
          >
            <kbd className="mr-1.5 px-1.5 py-0.5 rounded bg-border text-text text-[10px] font-mono">&larr;</kbd>
            Back
          </button>
          <button
            onClick={goForward}
            className="px-5 py-2.5 rounded-lg bg-wk-radical text-white font-bold text-sm hover:opacity-90 transition-opacity"
          >
            {isLastStep ? 'Finish' : 'Next'}
            <kbd className="ml-1.5 px-1.5 py-0.5 rounded bg-white/25 text-white text-[10px] font-mono">&rarr;</kbd>
          </button>
        </div>
      </div>
    </QuizShell>
  );
}
