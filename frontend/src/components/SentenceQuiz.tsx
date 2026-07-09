import { forwardRef } from 'react';
import { PolitenessBadge } from '@/pages/SentencesPage';
import type { Politeness } from '@/lib/api';
import { cn } from '@/lib/utils';

// Shared presentational bits for the sentence lesson-quiz and review screens.
// The two flows differ (review commits SRS + override + practice requeue; the lesson
// is a stateless judge gate), so only the shared UI + helpers live here — not the state.

// Faint green study-block tint, matching the kanji/vocab lesson hero pattern.
export const GREEN_TINT = 'color-mix(in srgb, var(--card) 93%, #00c46a)';

// Backend exact-match normalization: ignore spaces + trailing period.
export const normalize = (s: string) =>
  s.trim().replace(/[\s　]/g, '').replace(/[。.]+$/, '');

// English prompt + politeness target on a faint green block.
export function SentencePromptHero({
  label,
  english,
  politeness,
}: {
  label?: string;
  english: string;
  politeness: Politeness;
}) {
  return (
    <div
      className="flex shrink-0 flex-col items-center gap-3 py-12 text-center"
      style={{ backgroundColor: GREEN_TINT }}
    >
      {label && (
        <span className="font-mono text-[10px] tracking-[0.2em] text-muted-foreground uppercase">
          {label}
        </span>
      )}
      <span className="max-w-2xl px-4 text-2xl">{english}</span>
      <PolitenessBadge value={politeness} />
    </div>
  );
}

// IME answer box (no romaji conversion). Enter fires onEnter, Shift+Enter = newline,
// and an in-progress IME composition Enter is ignored (it confirms a candidate).
export const SentenceInput = forwardRef<
  HTMLTextAreaElement,
  {
    value: string;
    onChange: (v: string) => void;
    onEnter: () => void;
    disabled?: boolean;
    shake?: boolean;
    onAnimationEnd?: () => void;
    placeholder?: string;
  }
>(function SentenceInput(
  { value, onChange, onEnter, disabled, shake, onAnimationEnd, placeholder = '日本語で入力（IME）' },
  ref,
) {
  return (
    <textarea
      ref={ref}
      lang="ja"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onAnimationEnd={onAnimationEnd}
      onKeyDown={(e) => {
        if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
          e.preventDefault();
          onEnter();
        }
      }}
      placeholder={placeholder}
      disabled={disabled}
      rows={2}
      className={cn(
        'w-full resize-y border-2 border-input bg-card px-4 py-3 text-center font-[family-name:var(--font-mincho)] text-2xl',
        'focus:border-ring focus:ring-[3px] focus:ring-ring/40 focus:outline-none disabled:opacity-100',
        shake && 'animate-shake',
      )}
      autoComplete="off"
      spellCheck={false}
    />
  );
});

// The reference answer, revealed after judging.
export function ReferenceBlock({
  reference,
  tone = 'correct',
}: {
  reference: string;
  tone?: 'correct' | 'wrong';
}) {
  return (
    <div className={cn('border-l-4 bg-card p-4', tone === 'correct' ? 'border-wk-sentence' : 'border-destructive/70')}>
      <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">参照解答</div>
      <div lang="ja" className="font-[family-name:var(--font-mincho)] text-2xl">{reference}</div>
    </div>
  );
}

export function FeedbackBlock({ feedback }: { feedback: string | null | undefined }) {
  if (!feedback) return null;
  return <div className="bg-muted p-4 text-sm leading-relaxed">{feedback}</div>;
}
