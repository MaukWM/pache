import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type ReviewItem } from '../lib/api';
import { romajiToHiraganaLive } from '../lib/romaji';

type CardType = 'reading' | 'meaning';
type ReviewMode = 'scrambled' | 'paired';

interface ReviewCard {
  item: ReviewItem;
  type: CardType;
  key: string; // unique key for tracking
}

interface ItemResult {
  reading_correct?: boolean;
  meaning_correct?: boolean;
  reading_wrong?: boolean;
  meaning_wrong?: boolean;
}

function buildQueue(items: ReviewItem[], mode: ReviewMode): ReviewCard[] {
  let id = 0;
  if (mode === 'scrambled') {
    const cards: ReviewCard[] = [];
    for (const item of items) {
      cards.push({ item, type: 'reading', key: `r-${item.item_type}-${item.item_id}-${id++}` });
      cards.push({ item, type: 'meaning', key: `m-${item.item_type}-${item.item_id}-${id++}` });
    }
    for (let i = cards.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [cards[i], cards[j]] = [cards[j], cards[i]];
    }
    return cards;
  } else {
    const shuffled = [...items].sort(() => Math.random() - 0.5);
    const cards: ReviewCard[] = [];
    for (const item of shuffled) {
      cards.push({ item, type: 'reading', key: `r-${item.item_type}-${item.item_id}-${id++}` });
      cards.push({ item, type: 'meaning', key: `m-${item.item_type}-${item.item_id}-${id++}` });
    }
    return cards;
  }
}

function itemKey(item: ReviewItem): string {
  return `${item.item_type}-${item.item_id}`;
}

export function ReviewPage() {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<ReviewMode>('paired');
  const [cards, setCards] = useState<ReviewCard[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [input, setInput] = useState('');
  const [answered, setAnswered] = useState(false);
  const [correct, setCorrect] = useState<boolean | null>(null);
  const [results, setResults] = useState<Record<string, ItemResult>>({});
  const [completedCorrect, setCompletedCorrect] = useState(0);
  const [completedIncorrect, setCompletedIncorrect] = useState(0);
  const [started, setStarted] = useState(false);
  const [totalItems, setTotalItems] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const answeredAt = useRef(0);

  const reviewsQuery = useQuery({
    queryKey: ['reviews'],
    queryFn: api.getReviews,
  });

  const submitMutation = useMutation({
    mutationFn: api.submitReview,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['progressMap'] });
    },
  });

  const maybeSubmit = (key: string, updatedResults: Record<string, ItemResult>, item: ReviewItem) => {
    const r = updatedResults[key];
    if (r && r.reading_correct != null && r.meaning_correct != null) {
      const hadWrong = r.reading_wrong || r.meaning_wrong;
      submitMutation.mutate({
        item_type: item.item_type,
        item_id: item.item_id,
        reading_correct: !r.reading_wrong,
        meaning_correct: !r.meaning_wrong,
      });
      // Item fully complete — update progress bar
      if (hadWrong) {
        setCompletedIncorrect((c) => c + 1);
      } else {
        setCompletedCorrect((c) => c + 1);
      }
    }
  };

  useEffect(() => {
    if (!answered && started && currentIndex < cards.length) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [currentIndex, answered, started, cards.length]);

  // Global Enter when answered
  useEffect(() => {
    if (!answered) return;
    answeredAt.current = Date.now();
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && Date.now() - answeredAt.current > 150) {
        advance();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  });

  if (reviewsQuery.isLoading) {
    return (
      <div className="flex items-center justify-center h-96 text-text-muted animate-pulse text-lg">
        Loading reviews...
      </div>
    );
  }

  const reviewItems = reviewsQuery.data || [];

  if (!started) {
    if (reviewItems.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center py-20 space-y-4 text-center">
          <div className="text-5xl">&#128516;</div>
          <h2 className="text-2xl font-bold">No reviews due</h2>
          <p className="text-text-muted">Come back later when items are ready for review.</p>
        </div>
      );
    }

    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-6">
        <h2 className="text-2xl font-bold">{reviewItems.length} items to review</h2>
        <div className="flex gap-3">
          <button
            onClick={() => setMode('paired')}
            className={`px-4 py-2 rounded-lg text-sm font-bold transition-colors ${
              mode === 'paired' ? 'bg-wk-kanji text-white' : 'bg-surface border border-border'
            }`}
          >
            Paired
          </button>
          <button
            onClick={() => setMode('scrambled')}
            className={`px-4 py-2 rounded-lg text-sm font-bold transition-colors ${
              mode === 'scrambled' ? 'bg-wk-kanji text-white' : 'bg-surface border border-border'
            }`}
          >
            Scrambled
          </button>
        </div>
        <button
          onClick={() => {
            const q = buildQueue(reviewItems, mode);
            setCards(q);
            setTotalItems(reviewItems.length);
            setStarted(true);
          }}
          className="px-8 py-3 rounded-lg bg-wk-kanji text-white font-bold text-lg hover:bg-accent-hover transition-colors"
        >
          Start Reviews
        </button>
      </div>
    );
  }

  // Session complete
  if (currentIndex >= cards.length) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-6">
        <div className="text-6xl">&#10003;</div>
        <h2 className="text-2xl font-bold">All done!</h2>
        <p className="text-text-muted">{completedCorrect} correct, {completedIncorrect} incorrect</p>
        <button
          onClick={() => {
            setCards([]);
            setStarted(false);
            setCurrentIndex(0);
            setCompletedCorrect(0);
            setCompletedIncorrect(0);
            setResults({});
            setTotalItems(0);
            queryClient.invalidateQueries({ queryKey: ['reviews'] });
          }}
          className="px-6 py-3 rounded-lg bg-wk-kanji text-white font-bold text-lg hover:bg-accent-hover transition-colors"
        >
          Done
        </button>
      </div>
    );
  }

  const card = cards[currentIndex];
  const { item, type: cardType } = card;
  const isKanji = item.item_type === 'kanji';
  const display = item.item_details.character || item.item_details.word || '?';
  const meanings = item.item_details.meanings || [];
  const readingsOn = item.item_details.readings_on || [];
  const readingsKun = item.item_details.readings_kun || [];
  const vocabReadings = (item.item_details as { readings?: string[] }).readings || [];

  const headerBg = isKanji ? 'bg-wk-kanji' : 'bg-wk-vocab';
  const labelBg = cardType === 'reading' ? 'bg-[#303030] text-white' : 'bg-white text-text';

  const katakanaToHiragana = (str: string): string =>
    str.replace(/[\u30A0-\u30FF]/g, (ch) =>
      String.fromCharCode(ch.charCodeAt(0) - 0x60)
    );

  const getAcceptableReadings = (): string[] => {
    if (isKanji) {
      return [...readingsOn, ...readingsKun]
        .map((r) => katakanaToHiragana(r.replace(/[.\-]/g, '')));
    }
    return vocabReadings.map((r) => katakanaToHiragana(r.replace(/[.\-]/g, '')));
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setInput(cardType === 'reading' ? romajiToHiraganaLive(val) : val);
  };

  const checkAnswer = () => {
    const trimmed = input.trim().toLowerCase();
    if (!trimmed) return;

    let isCorrect: boolean;
    if (cardType === 'reading') {
      const acceptable = getAcceptableReadings();
      isCorrect = acceptable.some((r) => r === katakanaToHiragana(trimmed));
    } else {
      isCorrect = meanings.some((m) => {
        const lower = m.toLowerCase();
        return lower === trimmed || (trimmed.length >= 3 && lower.startsWith(trimmed));
      });
    }

    setCorrect(isCorrect);
    setAnswered(true);

    // Track per-item results
    const key = itemKey(item);
    const updated = { ...results };
    if (!updated[key]) updated[key] = {};
    if (isCorrect) {
      if (cardType === 'reading') updated[key].reading_correct = true;
      else updated[key].meaning_correct = true;
    } else {
      // Mark that this card type had a wrong answer (affects final submission)
      if (cardType === 'reading') updated[key].reading_wrong = true;
      else updated[key].meaning_wrong = true;
    }
    setResults(updated);

    // Only submit when both are answered correctly (card passed)
    if (isCorrect) {
      maybeSubmit(key, updated, item);
    }
  };

  const advance = () => {
    if (correct) {
      // Correct — move forward
      setCurrentIndex((i) => i + 1);
    } else {
      // Incorrect — put card back
      if (mode === 'scrambled') {
        // Shuffle back into remaining cards
        setCards((prev) => {
          const remaining = prev.slice(currentIndex + 1);
          const insertAt = Math.floor(Math.random() * (remaining.length + 1));
          const newCard = { ...card, key: card.key + '-retry' };
          remaining.splice(insertAt, 0, newCard);
          return [...prev.slice(0, currentIndex + 1), ...remaining];
        });
        setCurrentIndex((i) => i + 1);
      } else {
        // Paired — retry same card (don't advance index, just reset input)
      }
    }
    setInput('');
    setAnswered(false);
    setCorrect(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      if (answered) advance();
      else checkAnswer();
    }
  };

  const inputStyle = !answered
    ? 'border-transparent bg-white text-text'
    : correct
      ? 'border-transparent bg-[#88cc00] text-white'
      : 'border-transparent bg-[#ff4444] text-white';

  // Progress bar: per item (not per card)
  const correctPct = totalItems > 0 ? (completedCorrect / totalItems) * 100 : 0;
  const incorrectPct = totalItems > 0 ? (completedIncorrect / totalItems) * 100 : 0;

  return (
    <div className="-mx-4 -mt-6 min-h-[calc(100vh-3.5rem)]">
      {/* Progress bar — WK style with counts */}
      <div className="h-6 bg-border overflow-hidden flex text-xs font-bold">
        {completedCorrect > 0 && (
          <div
            className="h-full bg-success flex items-center justify-center text-white transition-all"
            style={{ width: `${correctPct}%` }}
          >
            {correctPct > 5 ? completedCorrect : ''}
          </div>
        )}
        {completedIncorrect > 0 && (
          <div
            className="h-full bg-error flex items-center justify-center text-white transition-all"
            style={{ width: `${incorrectPct}%` }}
          >
            {incorrectPct > 5 ? completedIncorrect : ''}
          </div>
        )}
      </div>

      {/* Character */}
      <div className={`${headerBg} p-12 text-white text-center`}>
        <div className="text-9xl font-bold">{display}</div>
      </div>

      {/* Reading/Meaning bar */}
      <div className={`${labelBg} py-2 text-center transition-colors duration-200`}>
        <span className="text-sm tracking-wide capitalize">
          {item.item_type} <span className="font-black">{cardType === 'reading' ? 'Reading' : 'Meaning'}</span>
        </span>
      </div>

      {/* Input */}
      <div className="bg-surface">
        <div className="max-w-2xl mx-auto p-4">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder={cardType === 'reading' ? '答え' : 'Your Response'}
            disabled={answered}
            lang={cardType === 'reading' ? 'ja' : 'en'}
            className={`w-full px-4 py-3 text-center text-2xl rounded-lg border-2 transition-colors focus:outline-none ${inputStyle}`}
            autoComplete="off"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
          />
        </div>

        {answered && (
          <div className="max-w-2xl mx-auto px-4 pb-5 space-y-3">
            <div className="text-center">
              <span className={`font-bold text-lg ${correct ? 'text-success' : 'text-error'}`}>
                {correct ? 'Correct!' : 'Incorrect'}
              </span>
            </div>

            <div className="bg-surface-alt rounded-lg p-4 space-y-3 text-sm">
              <div>
                <div className="text-text-muted text-xs uppercase tracking-wide mb-1">Meanings</div>
                <div>{meanings.join(', ')}</div>
              </div>
              {isKanji ? (
                <div className="grid grid-cols-2 gap-3">
                  {readingsOn.length > 0 && (
                    <div>
                      <div className="text-text-muted text-xs uppercase tracking-wide mb-1">On'yomi</div>
                      <div>{readingsOn.join('、')}</div>
                    </div>
                  )}
                  {readingsKun.length > 0 && (
                    <div>
                      <div className="text-text-muted text-xs uppercase tracking-wide mb-1">Kun'yomi</div>
                      <div>{readingsKun.join('、')}</div>
                    </div>
                  )}
                </div>
              ) : vocabReadings.length > 0 && (
                <div>
                  <div className="text-text-muted text-xs uppercase tracking-wide mb-1">Readings</div>
                  <div>{vocabReadings.join('、')}</div>
                </div>
              )}
            </div>

            <div className="text-center text-xs text-text-muted">
              Press <kbd className="px-1.5 py-0.5 rounded bg-border text-text text-[10px] font-mono">Enter</kbd> to {correct ? 'continue' : 'try again'}
            </div>
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="flex justify-between text-xs text-text-muted mt-3 px-4">
        <span>{completedCorrect + completedIncorrect} / {totalItems} items</span>
        <span className="text-success">{completedCorrect} correct</span>
        {completedIncorrect > 0 && <span className="text-error">{completedIncorrect} incorrect</span>}
      </div>
    </div>
  );
}
