import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type DueSentence, type SentenceJudgeResult } from '../lib/api';
import { QuizShell } from '../components/QuizShell';
import { SentencePromptHero, SentenceInput, ReferenceBlock, FeedbackBlock } from '../components/SentenceQuiz';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

// A queued card. The first attempt at an item commits SRS (submitSentenceReview). A miss
// requeues the SAME item back-to-back as a `retry` card that re-grades for real (fast-path
// → LLM via judgeSentence) but WITHOUT touching SRS — the miss is already committed (+4h),
// so the redo can't game the stage. Mirrors the kanji/vocab in-session retry-till-pass.
interface Card {
  sentence: DueSentence;
  retry: boolean;
}

export function SentenceReviewPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [cards, setCards] = useState<Card[]>([]);
  const [index, setIndex] = useState(0);
  const [input, setInput] = useState('');
  const [result, setResult] = useState<SentenceJudgeResult | null>(null);
  const [overridden, setOverridden] = useState(false);
  const [showReason, setShowReason] = useState(false);
  const [reason, setReason] = useState('');
  const [shake, setShake] = useState(false);
  const [correctCount, setCorrectCount] = useState(0);
  const [wrongCount, setWrongCount] = useState(0);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const judgedAt = useRef(0); // guards the submit-Enter from also advancing
  const abortRef = useRef<AbortController | null>(null);

  const dueQuery = useQuery({ queryKey: ['sentenceReviews'], queryFn: api.getDueSentences });

  const card = cards[index];

  // First attempt → submitSentenceReview (commits SRS). Retry → judgeSentence (grade only,
  // no SRS): the miss is already committed, the redo just gates advancing to the next item.
  const submitMutation = useMutation({
    mutationFn: (submitted: string) => {
      abortRef.current = new AbortController();
      if (card.retry) {
        return api.judgeSentence(card.sentence.sentence_id, submitted, abortRef.current.signal);
      }
      return api.submitSentenceReview(card.sentence.sentence_id, submitted, abortRef.current.signal);
    },
    onSuccess: (res) => {
      setResult(res);
      judgedAt.current = Date.now();
      if (!card.retry) {
        queryClient.invalidateQueries({ queryKey: ['progressMap'] });
        queryClient.invalidateQueries({ queryKey: ['sentences'] });
      }
    },
  });

  // Cancel an in-flight judge (accidental submit) — abort the request (server rolls back
  // before commit) and return to editing with the text intact.
  const cancelSubmit = () => {
    abortRef.current?.abort();
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  const overrideMutation = useMutation({
    mutationFn: () => api.overrideSentenceReview(card.sentence.sentence_id, reason.trim() || undefined),
    onSuccess: () => {
      setOverridden(true);
      setShowReason(false);
      queryClient.invalidateQueries({ queryKey: ['progressMap'] });
    },
  });

  // Build the queue once loaded (a populated queue is itself the "started" flag).
  useEffect(() => {
    if (cards.length === 0 && dueQuery.data && dueQuery.data.length > 0) {
      setCards(dueQuery.data.map((s) => ({ sentence: s, retry: false })));
    }
  }, [cards.length, dueQuery.data]);

  const judged = result !== null;
  const judging = submitMutation.isPending;

  // Focus the answer box on each fresh (unjudged) card.
  useEffect(() => {
    if (!judged) setTimeout(() => inputRef.current?.focus(), 50);
  }, [index, judged]);

  const reset = () => {
    setResult(null);
    setOverridden(false);
    setShowReason(false);
    setReason('');
    setInput('');
  };

  // Requeue the current item as a back-to-back retry (real re-grade, no SRS).
  const requeueRetry = () => {
    setCards((prev) => {
      const next = [...prev];
      next.splice(index + 1, 0, { sentence: card.sentence, retry: true });
      return next;
    });
  };

  // Advance after a judged card. First attempt: tally + (on miss) requeue a retry. Retry:
  // no tally (already counted on the first miss) — pass moves on, another miss requeues again.
  const advance = () => {
    if (!result) return;
    if (card.retry) {
      if (!result.correct) requeueRetry();
    } else if (result.correct || overridden) {
      setCorrectCount((c) => c + 1);
    } else {
      setWrongCount((c) => c + 1);
      requeueRetry();
    }
    reset();
    setIndex((i) => i + 1);
  };

  // When a card is judged, Enter advances (outside the textarea).
  useEffect(() => {
    if (!judged) return;
    const handler = (e: KeyboardEvent) => {
      // Ignore the same Enter that submitted (fast exact-match) — require a fresh press.
      if (
        e.key === 'Enter' &&
        !showReason &&
        !(e.target instanceof HTMLTextAreaElement) &&
        Date.now() - judgedAt.current > 250
      ) {
        advance();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  });

  const loading = dueQuery.isLoading;
  const dueItems = dueQuery.data ?? [];
  const gradedTotal = dueItems.length;
  const done = correctCount + wrongCount;

  if (!loading && dueItems.length === 0) {
    return (
      <QuizShell exitTo="/">
        <div className="flex flex-1 flex-col items-center justify-center space-y-4 text-center">
          <h2 className="text-2xl font-bold">作文の復習はありません</h2>
          <p className="text-muted-foreground">文が復習可能になったら、また来てください。</p>
        </div>
      </QuizShell>
    );
  }

  if (loading || cards.length === 0) {
    return (
      <QuizShell exitTo="/">
        <div className="flex flex-1 animate-pulse items-center justify-center text-lg text-muted-foreground">
          復習を読み込み中...
        </div>
      </QuizShell>
    );
  }

  if (index >= cards.length) {
    return (
      <QuizShell exitTo="/">
        <div className="flex flex-1 flex-col items-center justify-center space-y-6">
          <div className="text-6xl">&#10003;</div>
          <h2 className="text-2xl font-bold">完了しました！</h2>
          <p className="text-muted-foreground">正解 {correctCount}件、不正解 {wrongCount}件</p>
          <Button
            size="lg"
            onClick={() => {
              queryClient.invalidateQueries({ queryKey: ['sentenceReviews'] });
              navigate('/');
            }}
          >
            ダッシュボードへ
          </Button>
        </div>
      </QuizShell>
    );
  }

  const finalCorrect = result?.correct || overridden;

  return (
    <QuizShell
      exitTo="/"
      right={
        <span className="flex items-center gap-3">
          <span>{done} / {gradedTotal}</span>
          <span className="text-success">{correctCount}✓</span>
          {wrongCount > 0 && <span className="text-destructive">{wrongCount}✗</span>}
        </span>
      }
    >
      {/* Progress bar (first attempts only) */}
      <div className="flex h-2 shrink-0 overflow-hidden bg-secondary">
        {correctCount > 0 && (
          <div className="h-full bg-success/75 transition-all" style={{ width: `${(correctCount / gradedTotal) * 100}%` }} />
        )}
        {wrongCount > 0 && (
          <div className="h-full bg-destructive/75 transition-all" style={{ width: `${(wrongCount / gradedTotal) * 100}%` }} />
        )}
      </div>

      <SentencePromptHero
        label={card.retry ? 'もう一度 — 英語 → 日本語' : '英語 → 日本語'}
        english={card.sentence.english}
        politeness={card.sentence.politeness}
      />

      <div className="mx-auto w-full max-w-2xl flex-1 p-4">
        <SentenceInput
          ref={inputRef}
          value={input}
          onChange={setInput}
          onEnter={() => !judged && submit()}
          disabled={judged || judging}
          shake={shake}
          onAnimationEnd={() => setShake(false)}
        />

        {/* Submit → judge. Cancellable while judging (accidental submit). */}
        {!judged && (
          <div className="flex justify-center gap-2 pt-4">
            {judging ? (
              <>
                <Button size="lg" disabled>判定中…</Button>
                <Button size="lg" variant="outline" onClick={cancelSubmit}>キャンセル</Button>
              </>
            ) : (
              <Button size="lg" onClick={submit} disabled={!input.trim()}>
                提出
                <kbd className="ml-2 bg-primary-foreground/20 px-1.5 py-0.5 font-mono text-[10px]">Enter</kbd>
              </Button>
            )}
          </div>
        )}

        {judged && result && (
          <div className="space-y-4 pt-5">
            <div className="text-center">
              <span className={cn('text-xl font-bold', finalCorrect ? 'text-success' : 'text-destructive/80')}>
                {overridden ? '正解にしました' : result.correct ? '正解！' : '不正解'}
              </span>
            </div>

            {/* Reference shown on the first attempt (learn it); hidden on a retry redo (recall it). */}
            {!card.retry && (
              <ReferenceBlock reference={result.reference} tone={finalCorrect ? 'correct' : 'wrong'} />
            )}
            <FeedbackBlock feedback={result.feedback} />

            {/* Override — first-attempt miss only (retries don't touch SRS, nothing to override). */}
            {!card.retry && !result.correct && !overridden && (
              showReason ? (
                <div className="space-y-2">
                  <textarea
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="なぜ正解にするか（任意）— 今後この文の判定に渡されます"
                    rows={2}
                    className="w-full resize-y border border-input bg-card px-3 py-2 text-sm focus:border-ring focus:ring-[3px] focus:ring-ring/40 focus:outline-none"
                  />
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => overrideMutation.mutate()} disabled={overrideMutation.isPending}>
                      {overrideMutation.isPending ? '送信中…' : '正解にする'}
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setShowReason(false)}>取消</Button>
                  </div>
                  {overrideMutation.isError && (
                    <p className="text-sm text-destructive">{(overrideMutation.error as Error).message}</p>
                  )}
                </div>
              ) : (
                <div className="flex justify-center">
                  <Button variant="outline" size="sm" onClick={() => setShowReason(true)}>
                    判定に納得できない — 上書き
                  </Button>
                </div>
              )
            )}

            {!showReason && (
              <div className="flex justify-center pt-1">
                <Button size="lg" onClick={advance}>
                  {result.correct || overridden ? '続ける' : '続ける（もう一度）'}
                  <kbd className="ml-2 bg-primary-foreground/20 px-1.5 py-0.5 font-mono text-[10px]">Enter</kbd>
                </Button>
              </div>
            )}
          </div>
        )}

        {submitMutation.isError && !judged && (submitMutation.error as Error).name !== 'AbortError' && (
          <p className="pt-3 text-center text-sm text-destructive">
            {(submitMutation.error as Error).message}
          </p>
        )}
      </div>
    </QuizShell>
  );

  function submit() {
    if (!input.trim() || judging || judged) return;
    submitMutation.mutate(input.trim());
  }
}
