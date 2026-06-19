import { useState, useRef, useEffect, useCallback } from 'react';
import { type QueueItem } from '../lib/api';
import { evaluateAnswer } from '../lib/quiz';
import { QuizCard, type CardType } from './QuizCard';
import { QuizShell } from './QuizShell';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';

interface Card {
  item: QueueItem;
  type: CardType;
  key: string;
}

function buildQueue(items: QueueItem[]): Card[] {
  let id = 0;
  const cards: Card[] = [];
  for (const item of items) {
    const base = `${item.item_type}-${item.item_id}`;
    cards.push({ item, type: 'meaning', key: `m-${base}-${id++}` });
    cards.push({ item, type: 'reading', key: `r-${base}-${id++}` });
  }
  // Fisher–Yates shuffle
  for (let i = cards.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [cards[i], cards[j]] = [cards[j], cards[i]];
  }
  return cards;
}

/**
 * WaniKani-style lesson quiz: the studied items must be answered correctly
 * (meaning + reading, scrambled, wrong answers re-queued without penalty)
 * before they are officially learned. Calls onPassed() once all cards clear.
 */
export function LessonQuiz({
  items,
  onPassed,
  onExit,
  submitting,
  error,
}: {
  items: QueueItem[];
  onPassed: () => void;
  onExit: () => void;
  submitting: boolean;
  error?: Error | null;
}) {
  const [cards, setCards] = useState<Card[]>(() => buildQueue(items));
  const [index, setIndex] = useState(0);
  const [input, setInput] = useState('');
  const [answered, setAnswered] = useState(false);
  const [correct, setCorrect] = useState<boolean | null>(null);
  const [showInfo, setShowInfo] = useState(false);
  const [inputError, setInputError] = useState('');
  const [warning, setWarning] = useState('');
  const [shakeSignal, setShakeSignal] = useState(0);
  // Card keys (item + type) cleared correctly. An item is "done" once both its
  // meaning and reading cards are cleared — progress counts items, not cards.
  const [clearedKeys, setClearedKeys] = useState<Set<string>>(() => new Set());
  const inputRef = useRef<HTMLInputElement>(null);
  const answeredAt = useRef(0);
  const passedFired = useRef(false);

  const totalItems = items.length;
  const itemsDone = items.filter(
    (it) =>
      clearedKeys.has(`${it.item_type}-${it.item_id}-meaning`) &&
      clearedKeys.has(`${it.item_type}-${it.item_id}-reading`),
  ).length;
  const done = index >= cards.length;

  // Lock in the lessons exactly once, when every card has been cleared.
  useEffect(() => {
    if (done && !passedFired.current) {
      passedFired.current = true;
      onPassed();
    }
  }, [done, onPassed]);

  useEffect(() => {
    if (!answered && !done) {
      const t = setTimeout(() => inputRef.current?.focus(), 50);
      return () => clearTimeout(t);
    }
  }, [index, answered, done]);

  const card = cards[index];

  const undoAnswer = useCallback(() => {
    setInput('');
    setAnswered(false);
    setCorrect(null);
    setInputError('');
    setWarning('');
  }, []);

  const commitAndAdvance = useCallback(() => {
    if (correct) {
      const c = cards[index];
      setClearedKeys((prev) => {
        const next = new Set(prev);
        next.add(`${c.item.item_type}-${c.item.item_id}-${c.type}`);
        return next;
      });
      setIndex((i) => i + 1);
    } else {
      // Re-queue the missed card later in the (remaining) deck.
      setCards((prev) => {
        const remaining = prev.slice(index + 1);
        const insertAt = Math.floor(Math.random() * (remaining.length + 1));
        const retry = { ...prev[index], key: `${prev[index].key}-retry` };
        remaining.splice(insertAt, 0, retry);
        return [...prev.slice(0, index + 1), ...remaining];
      });
      setIndex((i) => i + 1);
    }
    setInput('');
    setAnswered(false);
    setCorrect(null);
    setShowInfo(false);
    setInputError('');
    setWarning('');
  }, [correct, index, cards]);

  // Global keys once an answer is shown (Enter = continue, Backspace = retype, F = item info).
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
  }, [answered, correct, commitAndAdvance, undoAnswer]);

  if (done) {
    if (error) {
      return (
        <QuizShell onExit={onExit}>
          <div className="flex-1 flex flex-col items-center justify-center py-20 space-y-4 text-center">
            <div className="text-5xl">&#9888;&#65039;</div>
            <h2 className="text-2xl font-bold">Couldn't save your lessons</h2>
            <p className="max-w-md text-destructive">{error.message}</p>
            <div className="flex gap-3">
              <Button onClick={onPassed} disabled={submitting} size="lg">
                {submitting ? 'Retrying…' : 'Try again'}
              </Button>
              <Button onClick={onExit} variant="outline" size="lg">
                Back to lessons
              </Button>
            </div>
          </div>
        </QuizShell>
      );
    }
    return (
      <QuizShell onExit={onExit}>
        <div className="flex-1 flex flex-col items-center justify-center py-20 space-y-4">
          <div className="text-5xl">&#127881;</div>
          <h2 className="text-2xl font-bold">Quiz passed!</h2>
          <p className="text-muted-foreground">
            {submitting ? 'Locking in your lessons…' : 'Done!'}
          </p>
        </div>
      </QuizShell>
    );
  }

  const { item, type: cardType } = card;
  const details = item.item_details || {};

  const checkAnswer = () => {
    if (!input.trim()) return;
    const outcome = evaluateAnswer(item.item_type, details, cardType, input);
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
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      if (answered) commitAndAdvance();
      else checkAnswer();
    }
  };

  const progressPct = totalItems > 0 ? (itemsDone / totalItems) * 100 : 0;

  return (
    <QuizShell
      onExit={onExit}
      right={
        <span className="flex items-center gap-3">
          <span>{itemsDone} / {totalItems}</span>
          <span className="uppercase tracking-wide text-[11px]">Lesson Quiz</span>
        </span>
      }
    >
      {/* Progress bar */}
      <Progress
        value={progressPct}
        className="h-2 shrink-0 rounded-none bg-muted [&_[data-slot=progress-indicator]]:bg-success"
      />

      {/* Quiz fills the full width, band anchored to the top (WaniKani-style) */}
      <div className="flex-1">
        <QuizCard
          itemType={item.item_type}
          details={details}
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
          continueLabel="continue"
          wrongLabel="try again later"
        />
      </div>
    </QuizShell>
  );
}
