import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { SRS_STAGE_NAMES, SRS_STAGE_COLORS } from '../lib/srs';

type Phase = 'meaning' | 'reading' | 'result';

export function ReviewPage() {
  const queryClient = useQueryClient();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [phase, setPhase] = useState<Phase>('meaning');
  const [input, setInput] = useState('');
  const [meaningCorrect, setMeaningCorrect] = useState<boolean | null>(null);
  const [readingCorrect, setReadingCorrect] = useState<boolean | null>(null);
  const [showAnswer, setShowAnswer] = useState(false);
  const [completed, setCompleted] = useState(0);

  const reviews = useQuery({
    queryKey: ['reviews'],
    queryFn: api.getReviews,
  });

  const submitMutation = useMutation({
    mutationFn: api.submitReview,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
      queryClient.invalidateQueries({ queryKey: ['progress'] });
    },
  });

  if (reviews.isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-text-muted animate-pulse text-lg">Loading reviews...</div>
      </div>
    );
  }

  const items = reviews.data || [];

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-center">
        <div className="w-24 h-24 bg-success/20 rounded-full flex items-center justify-center mb-4">
          <span className="text-4xl">&#10003;</span>
        </div>
        <h2 className="text-2xl font-bold">All caught up!</h2>
        <p className="text-text-muted mt-2">No reviews due right now. Come back later.</p>
        {completed > 0 && (
          <p className="text-sm text-text-muted mt-1">
            You completed {completed} review{completed !== 1 ? 's' : ''} this session.
          </p>
        )}
      </div>
    );
  }

  const item = items[currentIndex % items.length];
  const isKanji = item.item_type === 'kanji';
  const display = item.item_details.character || item.item_details.word || '?';
  const meanings = item.item_details.meanings || [];
  const reading = item.item_details.reading || item.item_details.readings_kun?.[0] || item.item_details.readings_on?.[0] || '';

  const handleCheck = () => {
    const trimmed = input.trim().toLowerCase();

    if (phase === 'meaning') {
      const correct = meanings.some(
        (m) => m.toLowerCase() === trimmed
      );
      setMeaningCorrect(correct);
      setShowAnswer(true);
    } else if (phase === 'reading') {
      const correct = trimmed === reading;
      setReadingCorrect(correct);
      setShowAnswer(true);
    }
  };

  const handleNext = () => {
    if (phase === 'meaning') {
      if (isKanji) {
        // Kanji gets reading phase too
        setPhase('reading');
        setInput('');
        setShowAnswer(false);
      } else {
        // Vocab: submit combined result
        const correct = meaningCorrect === true;
        submitMutation.mutate({
          item_type: item.item_type,
          item_id: item.item_id,
          correct,
        });
        goToNext();
      }
    } else if (phase === 'reading') {
      // Submit combined result: both must be correct
      const correct = meaningCorrect === true && readingCorrect === true;
      submitMutation.mutate({
        item_type: item.item_type,
        item_id: item.item_id,
        correct,
      });
      goToNext();
    }
  };

  const goToNext = () => {
    setCompleted((c) => c + 1);
    setCurrentIndex((i) => i + 1);
    setPhase('meaning');
    setInput('');
    setMeaningCorrect(null);
    setReadingCorrect(null);
    setShowAnswer(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      if (showAnswer) {
        handleNext();
      } else if (input.trim()) {
        handleCheck();
      }
    }
  };

  const bgColor = isKanji ? 'bg-wk-kanji' : 'bg-wk-vocab';
  const stageColor = SRS_STAGE_COLORS[item.srs_stage];

  return (
    <div className="max-w-xl mx-auto space-y-6">
      {/* Progress bar */}
      <div className="flex items-center justify-between text-sm text-text-muted">
        <span>{completed} completed</span>
        <span>{items.length} remaining</span>
      </div>

      {/* Main review card */}
      <div className={`${bgColor} rounded-2xl p-10 text-white text-center shadow-lg`}>
        <div className="text-7xl font-bold mb-4">{display}</div>
        <div
          className="inline-block text-xs font-bold px-3 py-1 rounded-full"
          style={{ backgroundColor: stageColor }}
        >
          {SRS_STAGE_NAMES[item.srs_stage]}
        </div>
      </div>

      {/* Question */}
      <div className="text-center">
        <div className="text-sm font-bold uppercase tracking-wider text-text-muted mb-2">
          {phase === 'meaning' ? 'Meaning' : 'Reading'}
        </div>

        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={showAnswer}
          placeholder={phase === 'meaning' ? 'Type the meaning...' : 'Type the reading...'}
          autoFocus
          className={`w-full text-center text-xl px-4 py-3 rounded-lg border-2 focus:outline-none transition-colors ${
            showAnswer
              ? (phase === 'meaning' ? meaningCorrect : readingCorrect)
                ? 'border-success bg-success/10'
                : 'border-error bg-error/10'
              : 'border-border bg-surface focus:border-wk-kanji'
          }`}
        />

        {showAnswer && (
          <div className="mt-3 space-y-1">
            <p className="text-sm">
              {phase === 'meaning'
                ? `Accepted meanings: ${meanings.join(', ')}`
                : `Reading: ${reading}`}
            </p>
            <button
              onClick={handleNext}
              className="mt-2 px-6 py-2 rounded-lg bg-wk-kanji text-white font-bold hover:bg-accent-hover transition-colors"
            >
              {phase === 'meaning' && isKanji ? 'Next: Reading' : 'Next'}
            </button>
          </div>
        )}

        {!showAnswer && (
          <button
            onClick={handleCheck}
            disabled={!input.trim()}
            className="mt-3 px-6 py-2 rounded-lg bg-text text-white font-bold hover:bg-text/80 transition-colors disabled:opacity-30"
          >
            Check
          </button>
        )}
      </div>
    </div>
  );
}
