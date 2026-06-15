import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type ReviewItem } from '../lib/api';
import { QuizCard, acceptableReadings, type CardType } from '../components/QuizCard';
import { finalizeRomaji } from '../lib/romaji';
import { isKana, matchesMeaning, matchesReading } from '../lib/quiz';

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
  const [showInfo, setShowInfo] = useState(false);
  const [inputError, setInputError] = useState('');
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

  // Global keys when answered
  useEffect(() => {
    if (!answered) return;
    answeredAt.current = Date.now();
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && Date.now() - answeredAt.current > 150) {
        commitAndAdvance();
      }
      if (e.key === 'Backspace') {
        // Undo the answer — retype (works even when correct, to deliberately fail it).
        e.preventDefault();
        undoAnswer();
      }
      if (e.key === 'f' || e.key === 'F') {
        setShowInfo((v) => !v);
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
  const meanings = item.item_details.meanings || [];

  const checkAnswer = () => {
    let value = input.trim();
    if (!value) return;
    setInputError('');

    let isCorrect: boolean;
    if (cardType === 'reading') {
      // Convert a trailing lone "n" to ん before checking (WaniKani-style).
      value = finalizeRomaji(value);
      setInput(value);
      const trimmed = value.toLowerCase();
      if (!isKana(trimmed)) {
        setInputError('Please enter your answer in kana');
        return;
      }
      isCorrect = matchesReading(trimmed, acceptableReadings(item.item_type, item.item_details));
    } else {
      isCorrect = matchesMeaning(value.toLowerCase(), meanings);
    }

    setCorrect(isCorrect);
    setAnswered(true);
    // Don't commit yet — wait for Enter (accept) or Backspace (redo)
  };

  // Undo: backspace when showing wrong answer → retype
  const undoAnswer = () => {
    setInput('');
    setAnswered(false);
    setCorrect(null);
    setInputError('');
  };

  // Commit: lock in the answer and move on
  const commitAndAdvance = () => {
    const key = itemKey(item);
    const updated = { ...results };
    if (!updated[key]) updated[key] = {};

    if (correct) {
      if (cardType === 'reading') updated[key].reading_correct = true;
      else updated[key].meaning_correct = true;
    } else {
      if (cardType === 'reading') updated[key].reading_wrong = true;
      else updated[key].meaning_wrong = true;
    }
    setResults(updated);
    maybeSubmit(key, updated, item);

    // Advance or retry
    if (correct) {
      setCurrentIndex((i) => i + 1);
    } else {
      if (mode === 'scrambled') {
        setCards((prev) => {
          const remaining = prev.slice(currentIndex + 1);
          const insertAt = Math.floor(Math.random() * (remaining.length + 1));
          const newCard = { ...card, key: card.key + '-retry' };
          remaining.splice(insertAt, 0, newCard);
          return [...prev.slice(0, currentIndex + 1), ...remaining];
        });
        setCurrentIndex((i) => i + 1);
      }
      // Paired: stays on same index, just resets below
    }

    setInput('');
    setAnswered(false);
    setCorrect(null);
    setShowInfo(false);
    setInputError('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      if (answered) commitAndAdvance();
      else checkAnswer();
    }
  };

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

      <QuizCard
        itemType={item.item_type}
        details={item.item_details}
        cardType={cardType}
        input={input}
        onInput={setInput}
        onKeyDown={handleKeyDown}
        inputRef={inputRef}
        inputError={inputError}
        answered={answered}
        correct={correct}
        showInfo={showInfo}
        onToggleInfo={() => setShowInfo((v) => !v)}
        continueLabel="continue"
        wrongLabel="accept"
      />

      {/* Stats */}
      <div className="flex justify-between text-xs text-text-muted mt-3 px-4">
        <span>{completedCorrect + completedIncorrect} / {totalItems} items</span>
        <span className="text-success">{completedCorrect} correct</span>
        {completedIncorrect > 0 && <span className="text-error">{completedIncorrect} incorrect</span>}
      </div>
    </div>
  );
}
