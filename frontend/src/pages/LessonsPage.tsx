import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type QueueItem } from '../lib/api';
import { RadicalList } from '../components/RadicalList';
import { LessonQuiz } from '../components/LessonQuiz';

type Tab = 'meaning' | 'reading' | 'info';

// Order the lesson session steps through: tabs of a card, then the next card.
const TAB_ORDER: Tab[] = ['meaning', 'reading', 'info'];

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

  // Step forward: meaning -> reading -> info -> next card.
  const goForward = () => {
    if (!sessionActive || currentIndex >= sessionItems.length) return;
    const tabIdx = TAB_ORDER.indexOf(activeTab);
    if (tabIdx < TAB_ORDER.length - 1) {
      setActiveTab(TAB_ORDER[tabIdx + 1]);
    } else {
      setCurrentIndex((i) => i + 1);
      setActiveTab('meaning');
    }
  };

  // Step back: info -> reading -> meaning -> previous card (landing on its info
  // tab so the flow is reversible).
  const goBack = () => {
    if (!sessionActive || currentIndex >= sessionItems.length) return;
    const tabIdx = TAB_ORDER.indexOf(activeTab);
    if (tabIdx > 0) {
      setActiveTab(TAB_ORDER[tabIdx - 1]);
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
    if (selectedIds.size === items.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(items.map(itemKey)));
    }
  };

  const startSession = () => {
    const toStudy = selectedIds.size > 0
      ? items.filter((i) => selectedIds.has(itemKey(i)))
      : items;
    setSessionItems(toStudy);
    setSessionActive(true);
    setCurrentIndex(0);
    setActiveTab('meaning');
  };

  // Queue overview
  if (!sessionActive) {
    const selectedCount = selectedIds.size || items.length;

    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Lessons</h1>
          {items.length > 0 && (
            <div className="flex items-center gap-2">
              <button
                onClick={selectAll}
                className="px-3 py-2 rounded-lg bg-surface border border-border text-sm font-medium hover:bg-border transition-colors"
              >
                {selectedIds.size === items.length ? 'Deselect All' : 'Select All'}
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
        {items.length > 0 && selectedIds.size === 0 && (
          <p className="text-sm text-text-muted">
            Tap items to select a subset, or start all {items.length} at once.
          </p>
        )}
        {selectedIds.size > 0 && (
          <p className="text-sm text-text-muted">
            {selectedIds.size} of {items.length} selected
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
          <div className="flex flex-wrap gap-2.5">
            {items.map((item) => {
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
  const bgColor = isKanji ? 'bg-wk-kanji' : 'bg-wk-vocab';

  const isLastStep = currentIndex === sessionItems.length - 1 && activeTab === 'info';
  const atStart = currentIndex === 0 && activeTab === 'meaning';

  const tabs: { id: Tab; label: string }[] = [
    { id: 'meaning', label: 'Meaning' },
    { id: 'reading', label: isKanji ? 'Readings' : 'Reading' },
    { id: 'info', label: 'Info' },
  ];

  return (
    <div className="max-w-2xl mx-auto space-y-0">
      {/* Progress */}
      <div className="flex items-center justify-between text-sm text-text-muted mb-4">
        <button
          onClick={() => setSessionActive(false)}
          className="hover:text-text transition-colors"
        >
          &larr; Back to queue
        </button>
        <span>{currentIndex + 1} / {sessionItems.length}</span>
      </div>

      {/* Hero card */}
      <div className={`${bgColor} rounded-t-2xl p-10 text-white text-center`}>
        <div className="text-7xl font-bold mb-3">{display}</div>
        <div className="text-xl opacity-90">{meanings[0]}</div>
      </div>

      {/* Tabs */}
      <div className="bg-surface-alt flex border-b border-border">
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

      {/* Tab content */}
      <div className="bg-surface rounded-b-2xl p-6 shadow-sm min-h-[200px]">
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
      <div className="flex items-center justify-between pt-4">
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
  );
}
