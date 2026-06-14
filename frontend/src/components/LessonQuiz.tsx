import { useState, useRef, useEffect, useCallback } from 'react';
import { type QueueItem } from '../lib/api';
import { romajiToHiraganaLive, finalizeRomaji } from '../lib/romaji';
import { isKana, matchesMeaning, matchesReading } from '../lib/quiz';

type CardType = 'reading' | 'meaning';

interface QuizCard {
  item: QueueItem;
  type: CardType;
  key: string;
}

function buildQueue(items: QueueItem[]): QuizCard[] {
  let id = 0;
  const cards: QuizCard[] = [];
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

function acceptableReadings(item: QueueItem): string[] {
  if (item.item_type === 'kanji') {
    return [
      ...(item.item_details?.readings_on || []),
      ...(item.item_details?.readings_kun || []),
    ];
  }
  return item.item_details?.readings || [];
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
}: {
  items: QueueItem[];
  onPassed: () => void;
  onExit: () => void;
  submitting: boolean;
}) {
  const [cards, setCards] = useState<QuizCard[]>(() => buildQueue(items));
  const [index, setIndex] = useState(0);
  const [input, setInput] = useState('');
  const [answered, setAnswered] = useState(false);
  const [correct, setCorrect] = useState<boolean | null>(null);
  const [inputError, setInputError] = useState('');
  const [cleared, setCleared] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const answeredAt = useRef(0);
  const passedFired = useRef(false);

  const total = cards.length; // grows as wrong cards are re-queued
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
  }, []);

  const commitAndAdvance = useCallback(() => {
    if (correct) {
      setCleared((c) => c + 1);
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
    setInputError('');
  }, [correct, index]);

  // Global keys once an answer is shown (Enter = continue, Backspace = retype).
  useEffect(() => {
    if (!answered) return;
    answeredAt.current = Date.now();
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && Date.now() - answeredAt.current > 150) {
        commitAndAdvance();
      }
      if (e.key === 'Backspace' && !correct) {
        e.preventDefault();
        undoAnswer();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [answered, correct, commitAndAdvance, undoAnswer]);

  if (done) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-4">
        <div className="text-5xl">&#127881;</div>
        <h2 className="text-2xl font-bold">Quiz passed!</h2>
        <p className="text-text-muted">
          {submitting ? 'Locking in your lessons…' : 'Done!'}
        </p>
      </div>
    );
  }

  const { item, type: cardType } = card;
  const isKanji = item.item_type === 'kanji';
  const display = item.item_details?.character || item.item_details?.word || '?';
  const meanings = item.item_details?.meanings || [];

  const headerBg = isKanji ? 'bg-wk-kanji' : 'bg-wk-vocab';
  const labelBg = cardType === 'reading' ? 'bg-[#303030] text-white' : 'bg-white text-text';

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
      isCorrect = matchesReading(trimmed, acceptableReadings(item));
    } else {
      isCorrect = matchesMeaning(value.toLowerCase(), meanings);
    }
    setCorrect(isCorrect);
    setAnswered(true);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      if (answered) commitAndAdvance();
      else checkAnswer();
    }
  };

  const inputStyle = !answered
    ? 'border-transparent bg-white text-text'
    : correct
      ? 'border-transparent bg-[#88cc00] text-white'
      : 'border-transparent bg-[#ff4444] text-white';

  const progressPct = total > 0 ? (cleared / total) * 100 : 0;

  return (
    <div className="-mx-4 -mt-6 min-h-[calc(100vh-3.5rem)]">
      {/* Quiz banner + progress */}
      <div className="bg-wk-radical text-white text-center py-1.5 text-xs font-bold tracking-wide uppercase">
        Lesson Quiz
      </div>
      <div className="h-2 bg-border overflow-hidden">
        <div className="h-full bg-success transition-all" style={{ width: `${progressPct}%` }} />
      </div>

      {/* Character */}
      <div className={`${headerBg} p-12 text-white text-center`}>
        <div className="text-9xl font-bold">{display}</div>
      </div>

      {/* Reading/Meaning bar */}
      <div className={`${labelBg} py-2 text-center transition-colors duration-200`}>
        <span className="text-sm tracking-wide capitalize">
          {item.item_type}{' '}
          <span className="font-black">{cardType === 'reading' ? 'Reading' : 'Meaning'}</span>
        </span>
      </div>

      {/* Input */}
      <div className="bg-surface">
        <div className="max-w-2xl mx-auto p-4">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) =>
              setInput(cardType === 'reading' ? romajiToHiraganaLive(e.target.value) : e.target.value)
            }
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
          {inputError && <p className="text-center text-sm text-error mt-2">{inputError}</p>}
        </div>

        {answered && (
          <div className="max-w-2xl mx-auto px-4 pb-5 space-y-3">
            <div className="text-center">
              <span className={`font-bold text-lg ${correct ? 'text-success' : 'text-error'}`}>
                {correct ? 'Correct!' : 'Not quite'}
              </span>
            </div>
            {!correct && (
              <div className="text-center text-sm">
                <span className="text-text-muted">Answer: </span>
                {cardType === 'reading'
                  ? acceptableReadings(item).join('、')
                  : meanings.join(', ')}
              </div>
            )}
            <div className="text-center text-xs text-text-muted space-x-3">
              <span>
                <kbd className="px-1.5 py-0.5 rounded bg-border text-text text-[10px] font-mono">Enter</kbd>{' '}
                {correct ? 'continue' : 'try again later'}
              </span>
              {!correct && (
                <span>
                  <kbd className="px-1.5 py-0.5 rounded bg-border text-text text-[10px] font-mono">Backspace</kbd>{' '}
                  retype
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="max-w-2xl mx-auto px-4 pt-3 flex justify-between text-xs text-text-muted">
        <button onClick={onExit} className="hover:text-text transition-colors">
          &larr; Back to lessons
        </button>
        <span>{items.length} item{items.length !== 1 ? 's' : ''} to clear</span>
      </div>
    </div>
  );
}
