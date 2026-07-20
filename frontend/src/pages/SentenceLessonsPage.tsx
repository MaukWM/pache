import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type SentenceLesson, type SentenceJudgeResult } from '../lib/api';
import { QuizShell } from '../components/QuizShell';
import { PolitenessBadge } from './SentencesPage';
import { SentencePromptHero, SentenceInput, ReferenceBlock, FeedbackBlock } from '../components/SentenceQuiz';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

// Sentence lessons = light study step. You authored these, so the "lesson" just
// re-shows the pair (EN + JP + politeness) before it enters the review rotation.
export function SentenceLessonsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [sessionActive, setSessionActive] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [sessionItems, setSessionItems] = useState<SentenceLesson[]>([]);
  // Quiz gate: after studying, reproduce each sentence once (LLM-judged) before it elevates.
  const [quizzing, setQuizzing] = useState(false);
  const [quizItems, setQuizItems] = useState<SentenceLesson[]>([]);
  const [quizIndex, setQuizIndex] = useState(0);
  const [quizInput, setQuizInput] = useState('');
  const [quizResult, setQuizResult] = useState<SentenceJudgeResult | null>(null);
  const [quizPassed, setQuizPassed] = useState(0); // unique sentences cleared
  const [quizShake, setQuizShake] = useState(false);
  const quizRef = useRef<HTMLTextAreaElement>(null);
  const quizJudgedAt = useRef(0); // guards the 確認-Enter from also advancing

  const lessons = useQuery({ queryKey: ['sentenceLessons'], queryFn: api.getSentenceLessons });
  const items = lessons.data ?? [];

  const toggleSelect = (id: number) =>
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  const selectAll = () =>
    setSelectedIds((prev) => (prev.size === items.length ? new Set() : new Set(items.map((s) => s.sentence_id))));
  const startSession = () => {
    const toStudy = selectedIds.size > 0 ? items.filter((s) => selectedIds.has(s.sentence_id)) : items;
    setSessionItems(toStudy);
    setSessionActive(true);
    setCurrentIndex(0);
  };

  const completeMutation = useMutation({
    mutationFn: (ids: number[]) => api.completeSentenceLessons(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sentenceLessons'] });
      queryClient.invalidateQueries({ queryKey: ['sentenceReviews'] });
      queryClient.invalidateQueries({ queryKey: ['sentences'] });
    },
  });

  const item = sessionItems[currentIndex];
  const isLast = currentIndex === sessionItems.length - 1;
  const atStart = currentIndex === 0;

  const startQuiz = () => {
    setQuizItems([...sessionItems].sort(() => Math.random() - 0.5));
    setQuizIndex(0);
    setQuizInput('');
    setQuizResult(null);
    setQuizPassed(0);
    setQuizzing(true);
  };

  // Advance after a verdict. A miss requeues the sentence to the BACK of the line
  // (like the review); it reappears until cleared. All cleared → elevate.
  const advanceQuiz = () => {
    const wrong = quizResult != null && !quizResult.correct;
    const q = quizItems[quizIndex];
    setQuizInput('');
    setQuizResult(null);
    if (wrong && q) {
      setQuizItems((prev) => [...prev, q]);
      setQuizIndex((i) => i + 1);
      return;
    }
    // Correct → this sentence is done.
    const passed = quizPassed + 1;
    setQuizPassed(passed);
    if (passed >= sessionItems.length) {
      if (!completeMutation.isPending) completeMutation.mutate(sessionItems.map((s) => s.sentence_id));
    } else {
      setQuizIndex((i) => i + 1);
    }
  };

  // Quiz: LLM-judged (accepts natural variants; exact match is the free fast path).
  // Show the verdict + reference; correct waits for 続ける, a miss stays editable to retry.
  const judgeMutation = useMutation({
    mutationFn: ({ id, submitted }: { id: number; submitted: string }) =>
      api.judgeSentence(id, submitted),
    onSuccess: (res) => {
      setQuizResult(res);
      quizJudgedAt.current = Date.now();
      if (!res.correct) setQuizShake(true);
    },
  });

  const checkQuiz = () => {
    const q = quizItems[quizIndex];
    if (!q || !quizInput.trim() || judgeMutation.isPending) return;
    judgeMutation.mutate({ id: q.sentence_id, submitted: quizInput.trim() });
  };

  const goForward = () => {
    if (!sessionActive) return;
    if (!isLast) setCurrentIndex((i) => i + 1);
    else startQuiz();
  };
  const goBack = () => {
    if (sessionActive && !atStart) setCurrentIndex((i) => i - 1);
  };

  // Arrow keys drive study progression (not during the quiz gate).
  useEffect(() => {
    if (!sessionActive || quizzing) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') { e.preventDefault(); goForward(); }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); goBack(); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  });

  // Focus the quiz box on each fresh (unjudged) question.
  useEffect(() => {
    if (quizzing && !quizResult) setTimeout(() => quizRef.current?.focus(), 50);
  }, [quizzing, quizIndex, quizResult]);

  // Once judged (correct or miss), Enter advances (続ける) — guarded so the same Enter
  // that triggered 確認 (fast exact-match) doesn't immediately skip the verdict view.
  useEffect(() => {
    if (!quizResult) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && !(e.target instanceof HTMLTextAreaElement) && Date.now() - quizJudgedAt.current > 250) {
        advanceQuiz();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  });

  // Done screen — lessons learned.
  if (completeMutation.isSuccess) {
    return (
      <QuizShell exitTo="/">
        <div className="flex flex-1 flex-col items-center justify-center space-y-6">
          <div className="text-6xl">&#10003;</div>
          <h2 className="text-2xl font-bold">レッスン完了！</h2>
          <p className="text-muted-foreground">{sessionItems.length}件の文が復習に入りました。</p>
          <Button size="lg" onClick={() => navigate('/')}>ダッシュボードへ</Button>
        </div>
      </QuizShell>
    );
  }

  // Overview — pending lessons + start button.
  if (!sessionActive) {
    return (
      <QuizShell exitTo="/" right={items.length > 0 ? `${items.length}件` : undefined}>
        <div className="mx-auto w-full max-w-2xl space-y-6 px-4 py-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <h1 className="font-mono text-2xl font-bold tracking-wide uppercase">作文レッスン</h1>
            {items.length > 0 && (
              <div className="flex items-center gap-2">
                <Button variant="outline" onClick={selectAll}>
                  {selectedIds.size === items.length ? '選択を解除' : 'すべて選択'}
                </Button>
                <Button onClick={startSession}>
                  レッスン開始 ({selectedIds.size || items.length})
                </Button>
              </div>
            )}
          </div>

          {items.length > 0 && (
            <p className="text-sm text-muted-foreground">
              {selectedIds.size > 0
                ? `${items.length}件中${selectedIds.size}件を選択`
                : `文をタップして選択するか、${items.length}件すべてを開始します。`}
            </p>
          )}

          {lessons.isLoading ? (
            <div className="animate-pulse text-muted-foreground">読み込み中...</div>
          ) : items.length === 0 ? (
            <Card className="gap-2 p-10 text-center text-muted-foreground">
              <p className="mb-2 text-lg font-bold">レッスンはありません</p>
              <p>作文ページで新しい文を追加すると、ここに学習待ちとして表示されます。</p>
            </Card>
          ) : (
            <div className="divide-y divide-border border border-border">
              {items.map((s) => {
                const selected = selectedIds.has(s.sentence_id);
                const dim = selectedIds.size > 0 && !selected;
                return (
                  <button
                    key={s.sentence_id}
                    onClick={() => toggleSelect(s.sentence_id)}
                    className={cn(
                      'flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-accent',
                      dim && 'opacity-50',
                    )}
                  >
                    <span className={cn('grid size-5 shrink-0 place-items-center border font-mono text-[10px]',
                      selected ? 'border-foreground bg-foreground text-background' : 'border-border text-transparent')}>
                      ✓
                    </span>
                    <div className="min-w-0 flex-1">
                      <div lang="ja" className="truncate font-[family-name:var(--font-mincho)]">
                        {s.japanese}
                      </div>
                      <div className="truncate text-sm text-muted-foreground">{s.english}</div>
                    </div>
                    <PolitenessBadge value={s.politeness} />
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </QuizShell>
    );
  }

  // Quiz gate — reproduce each studied sentence once before it elevates.
  if (quizzing) {
    const q = quizItems[quizIndex];
    if (!q) return null;
    return (
      <QuizShell onExit={() => { setQuizzing(false); setSessionActive(false); }} right={`${quizPassed} / ${sessionItems.length}`}>
        <SentencePromptHero label="確認テスト — 英語 → 日本語" english={q.english} politeness={q.politeness} />

        <div className="mx-auto w-full max-w-2xl flex-1 p-4">
          <SentenceInput
            ref={quizRef}
            value={quizInput}
            onChange={setQuizInput}
            onEnter={() => !quizResult && checkQuiz()}
            disabled={quizResult != null || judgeMutation.isPending}
            shake={quizShake}
            onAnimationEnd={() => setQuizShake(false)}
          />

          {/* Verdict — shown after judging (both correct and miss). */}
          {quizResult && (
            <div className="mt-4 space-y-3">
              <div className="text-center">
                <span className={cn('text-lg font-bold', quizResult.correct ? 'text-success' : 'text-destructive/80')}>
                  {quizResult.correct ? '正解！' : '不正解'}
                </span>
              </div>
              <ReferenceBlock reference={q.japanese} tone={quizResult.correct ? 'correct' : 'wrong'} />
              <FeedbackBlock feedback={quizResult.feedback} />
            </div>
          )}

          <div className="flex justify-center gap-2 pt-4">
            {quizResult ? (
              <Button size="lg" onClick={advanceQuiz} disabled={completeMutation.isPending}>
                {completeMutation.isPending
                  ? '完了中…'
                  : quizResult.correct
                    ? '続ける'
                    : '続ける（後でもう一度）'}
                {!completeMutation.isPending && (
                  <kbd className="ml-2 bg-primary-foreground/20 px-1.5 py-0.5 font-mono text-[10px]">Enter</kbd>
                )}
              </Button>
            ) : (
              <Button size="lg" onClick={checkQuiz} disabled={!quizInput.trim() || judgeMutation.isPending}>
                {judgeMutation.isPending ? '判定中…' : '確認'}
                {!judgeMutation.isPending && (
                  <kbd className="ml-2 bg-primary-foreground/20 px-1.5 py-0.5 font-mono text-[10px]">Enter</kbd>
                )}
              </Button>
            )}
          </div>
          {judgeMutation.isError && (
            <p className="pt-3 text-center text-sm text-destructive">{(judgeMutation.error as Error).message}</p>
          )}
          {completeMutation.isError && (
            <p className="pt-3 text-center text-sm text-destructive">{(completeMutation.error as Error).message}</p>
          )}
        </div>
      </QuizShell>
    );
  }

  // Study session — one card at a time, both sides shown.
  if (!item) return null;

  return (
    <QuizShell onExit={() => setSessionActive(false)} right={`${currentIndex + 1} / ${sessionItems.length}`}>
      <SentencePromptHero english={item.english} politeness={item.politeness} />

      <div className="mx-auto w-full max-w-2xl flex-1 px-4 py-8">
        <div className="min-h-[160px] space-y-2">
          <h3 className="font-mono text-xs tracking-wide text-muted-foreground uppercase">日本語</h3>
          <p lang="ja" className="font-[family-name:var(--font-mincho)] text-3xl leading-relaxed">
            {item.japanese}
          </p>
          <p className="pt-4 text-sm text-muted-foreground">
            この文を覚えましょう。復習では英語だけが表示され、日本語を入力します。
          </p>
        </div>

        <div className="flex items-center justify-between pt-6">
          <Button variant="outline" onClick={goBack} disabled={atStart} className="disabled:opacity-30">
            <kbd className="mr-1.5 bg-muted px-1.5 py-0.5 font-mono text-[10px] text-foreground">&larr;</kbd>
            戻る
          </Button>
          <Button onClick={goForward}>
            {isLast ? '確認テストへ' : '次へ'}
            <kbd className="ml-1.5 bg-primary-foreground/20 px-1.5 py-0.5 font-mono text-[10px]">&rarr;</kbd>
          </Button>
        </div>
        {completeMutation.isError && (
          <p className="pt-3 text-center text-sm text-destructive">
            {(completeMutation.error as Error).message}
          </p>
        )}
      </div>
    </QuizShell>
  );
}
