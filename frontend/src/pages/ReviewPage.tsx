import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type ReviewItem } from '../lib/api';
import { QuizCard, type CardType } from '../components/QuizCard';
import { QuizShell } from '../components/QuizShell';
import { evaluateAnswer } from '../lib/quiz';
import { Button } from '@/components/ui/button';

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
  const [warning, setWarning] = useState('');
  const [shakeSignal, setShakeSignal] = useState(0);
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
      <QuizShell exitTo="/">
        <div className="flex-1 flex items-center justify-center text-muted-foreground animate-pulse text-lg">
          復習を読み込み中...
        </div>
      </QuizShell>
    );
  }

  const reviewItems = reviewsQuery.data || [];

  if (!started) {
    if (reviewItems.length === 0) {
      return (
        <QuizShell exitTo="/">
          <div className="flex-1 flex flex-col items-center justify-center space-y-4 text-center">
            <h2 className="text-2xl font-bold">復習はありません</h2>
            <p className="text-muted-foreground">項目が復習可能になったら、また来てください。</p>
          </div>
        </QuizShell>
      );
    }

    return (
      <QuizShell exitTo="/">
      <div className="flex-1 flex flex-col items-center justify-center space-y-6">
        <h2 className="text-2xl font-bold">復習する項目: {reviewItems.length}件</h2>
        <div className="flex gap-3">
          <Button
            variant={mode === 'paired' ? 'default' : 'outline'}
            onClick={() => setMode('paired')}
          >
            ペア
          </Button>
          <Button
            variant={mode === 'scrambled' ? 'default' : 'outline'}
            onClick={() => setMode('scrambled')}
          >
            シャッフル
          </Button>
        </div>
        <Button
          size="lg"
          onClick={() => {
            const q = buildQueue(reviewItems, mode);
            setCards(q);
            setTotalItems(reviewItems.length);
            setStarted(true);
          }}
        >
          復習を開始
        </Button>
      </div>
      </QuizShell>
    );
  }

  // Session complete
  if (currentIndex >= cards.length) {
    return (
      <QuizShell exitTo="/">
      <div className="flex-1 flex flex-col items-center justify-center space-y-6">
        <div className="text-6xl">&#10003;</div>
        <h2 className="text-2xl font-bold">完了しました！</h2>
        <p className="text-muted-foreground">正解 {completedCorrect}件、不正解 {completedIncorrect}件</p>
        <Button
          size="lg"
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
        >
          終了
        </Button>
      </div>
      </QuizShell>
    );
  }

  const card = cards[currentIndex];
  const { item, type: cardType } = card;

  const checkAnswer = () => {
    if (!input.trim()) return;
    const outcome = evaluateAnswer(item.item_type, item.item_details, cardType, input);
    setInput(outcome.value);

    if (outcome.kind === 'invalid') {
      setWarning('');
      setInputError(outcome.message);
      return;
    }
    if (outcome.kind === 'wrong-type') {
      // Valid reading, but not the one we teach — warn, shake, let them retype.
      setInputError('');
      setWarning(outcome.message);
      setShakeSignal((s) => s + 1);
      return;
    }

    setInputError('');
    setWarning('');
    setCorrect(outcome.kind === 'correct');
    setAnswered(true);
    // Don't commit yet — wait for Enter (accept) or Backspace (redo)
  };

  // Undo: backspace when showing an answer → retype
  const undoAnswer = () => {
    setInput('');
    setAnswered(false);
    setCorrect(null);
    setInputError('');
    setWarning('');
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
    setWarning('');
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
    <QuizShell
      exitTo="/"
      right={
        <span className="flex items-center gap-3">
          <span>{completedCorrect + completedIncorrect} / {totalItems}</span>
          <span className="text-success">{completedCorrect}✓</span>
          {completedIncorrect > 0 && <span className="text-destructive">{completedIncorrect}✗</span>}
        </span>
      }
    >
      {/* Progress bar — WK style with counts */}
      <div className="h-2 bg-secondary overflow-hidden flex shrink-0">
        {completedCorrect > 0 && (
          <div className="h-full bg-success transition-all" style={{ width: `${correctPct}%` }} />
        )}
        {completedIncorrect > 0 && (
          <div className="h-full bg-destructive transition-all" style={{ width: `${incorrectPct}%` }} />
        )}
      </div>

      {/* Quiz fills the full width, band anchored to the top (WaniKani-style) */}
      <div className="flex-1">
        <QuizCard
          itemType={item.item_type}
          details={item.item_details}
          cardType={cardType}
          input={input}
          onInput={setInput}
          onKeyDown={handleKeyDown}
          inputRef={inputRef}
          inputError={inputError}
          warning={warning}
          shakeSignal={shakeSignal}
          answered={answered}
          correct={correct}
          showInfo={showInfo}
          onToggleInfo={() => setShowInfo((v) => !v)}
          continueLabel="続ける"
          wrongLabel="確定"
        />
      </div>
    </QuizShell>
  );
}
