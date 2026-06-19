import { useEffect, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { RadicalList } from './RadicalList';
import { romajiToHiraganaLive, katakanaToHiragana } from '../lib/romaji';
import type { KanjiComposition } from '../lib/api';
import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';

// A collapsible info section in the F-key inspection panel (WaniKani-style).
// The relevant section auto-opens; the other (e.g. meaning while quizzing the
// reading) stays collapsed so it isn't spoiled before its own card comes up.
function InfoSection({
  title,
  open,
  children,
}: {
  title: string;
  open?: boolean;
  children: ReactNode;
}) {
  return (
    <details open={open} className="group border-b border-border">
      <summary className="flex cursor-pointer list-none items-center justify-between py-2 text-sm font-bold tracking-wide text-muted-foreground uppercase select-none hover:text-foreground">
        <span>{title}</span>
        <ChevronRight className="size-3.5 transition-transform group-open:rotate-90" />
      </summary>
      <div className="pb-3">{children}</div>
    </details>
  );
}

export type CardType = 'reading' | 'meaning';

// Fields shared by review (ReviewItem) and lesson (QueueItem) item_details.
export interface QuizItemDetails {
  character?: string;
  word?: string;
  reading?: string;
  readings?: string[];
  meanings?: string[];
  readings_on?: string[];
  readings_kun?: string[];
  components?: string[];
  kanji?: KanjiComposition[];
  tags?: string[];
  creator_comment?: string | null;
  creator_username?: string | null;
}

// The readings accepted as correct for a reading card.
export function acceptableReadings(itemType: string, d: QuizItemDetails): string[] {
  if (itemType === 'kanji') return [...(d.readings_on || []), ...(d.readings_kun || [])];
  return d.readings || [];
}

/**
 * The shared quiz/review card face: hero character, reading/meaning prompt bar,
 * answer input, and (once answered) the verdict, the F-toggle item-info panel,
 * and vocab metadata. Purely presentational — the owning page drives all state
 * (input value, answered/correct, showInfo) and the answer-checking logic.
 */
export function QuizCard({
  itemType,
  details,
  cardType,
  input,
  onInput,
  onKeyDown,
  inputRef,
  inputError,
  warning,
  shakeSignal = 0,
  answered,
  correct,
  showInfo,
  onToggleInfo,
  continueLabel = 'continue',
  wrongLabel = 'accept',
}: {
  itemType: string;
  details: QuizItemDetails;
  cardType: CardType;
  input: string;
  onInput: (value: string) => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  inputRef: React.RefObject<HTMLInputElement | null>;
  inputError: string;
  warning?: string;
  shakeSignal?: number;
  answered: boolean;
  correct: boolean | null;
  showInfo: boolean;
  onToggleInfo: () => void;
  continueLabel?: string;
  wrongLabel?: string;
}) {
  // Re-trigger the shake animation each time shakeSignal increments.
  const [shaking, setShaking] = useState(false);
  useEffect(() => {
    if (shakeSignal > 0) setShaking(true);
  }, [shakeSignal]);
  const isKanji = itemType === 'kanji';
  const display = details.character || details.word || '?';
  const meanings = details.meanings || [];
  const readingsOn = details.readings_on || [];
  const readingsKun = details.readings_kun || [];
  const components = details.components || [];
  const kanjiComposition = details.kanji || [];
  const vocabReadings = details.readings || [];
  const vocabTags = details.tags || [];
  const vocabComment = details.creator_comment;
  const vocabCreator = details.creator_username;

  const headerBg = isKanji ? 'bg-wk-kanji' : 'bg-wk-vocab';
  const labelBg =
    cardType === 'reading' ? 'bg-[#303030] text-white' : 'bg-card text-foreground';
  // The answer field flips to a solid correct/incorrect color once answered.
  const inputStateClass = !answered
    ? ''
    : correct
      ? 'border-success bg-success text-white placeholder:text-white/70'
      : 'border-destructive bg-destructive text-white placeholder:text-white/70';

  return (
    <>
      {/* Character */}
      <div className={cn(headerBg, 'p-12 text-center text-white')}>
        <div lang="ja" className="text-9xl font-bold">
          {display}
        </div>
      </div>

      {/* Reading/Meaning bar */}
      <div className={cn(labelBg, 'py-2 text-center transition-colors duration-200')}>
        <span className="text-sm tracking-wide capitalize">
          {itemType}{' '}
          <span className="font-black">{cardType === 'reading' ? 'Reading' : 'Meaning'}</span>
        </span>
      </div>

      {/* Input */}
      <div className="bg-card">
        <div className="mx-auto max-w-2xl p-4">
          <Input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) =>
              onInput(cardType === 'reading' ? romajiToHiraganaLive(e.target.value) : e.target.value)
            }
            onKeyDown={onKeyDown}
            onAnimationEnd={() => setShaking(false)}
            placeholder={cardType === 'reading' ? '答え' : 'Your Response'}
            disabled={answered}
            lang={cardType === 'reading' ? 'ja' : 'en'}
            className={cn(
              'h-auto rounded-lg border-2 py-3 text-center !text-2xl transition-colors disabled:opacity-100',
              inputStateClass,
              shaking && 'animate-shake',
            )}
            autoComplete="off"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
          />
          {inputError && <p className="mt-2 text-center text-sm text-destructive">{inputError}</p>}
          {warning && !inputError && (
            <p className="mt-2 text-center text-sm font-medium text-[#c08400]">{warning}</p>
          )}
        </div>

        {answered && (
          <div className="mx-auto max-w-2xl space-y-3 px-4 pb-5">
            <div className="flex items-center justify-center gap-4">
              <span className={cn('text-lg font-bold', correct ? 'text-success' : 'text-destructive')}>
                {correct ? 'Correct!' : 'Incorrect'}
              </span>
              <Button variant="outline" size="sm" onClick={onToggleInfo} className="text-muted-foreground">
                {showInfo ? 'Hide Info' : 'Item Info'}{' '}
                <kbd className="ml-1 rounded bg-muted px-1 py-0.5 font-mono text-[10px]">F</kbd>
              </Button>
            </div>

            {showInfo && (
              <div className="text-left">
                {/* Meaning — auto-open only when this is a meaning card */}
                <InfoSection title="Meaning" open={cardType === 'meaning'}>
                  <p className="text-xl">{meanings[0]}</p>
                  {meanings.length > 1 && (
                    <p className="mt-0.5 text-sm text-muted-foreground">{meanings.slice(1).join(', ')}</p>
                  )}
                </InfoSection>

                {/* Reading — auto-open only when this is a reading card */}
                <InfoSection title="Reading" open={cardType === 'reading'}>
                  {isKanji ? (
                    <div className="flex gap-8">
                      {readingsOn.length > 0 && (
                        <div>
                          <span className="block text-xs text-muted-foreground">On'yomi</span>
                          <span lang="ja" className="text-xl">{readingsOn.map(katakanaToHiragana).join('、')}</span>
                        </div>
                      )}
                      {readingsKun.length > 0 && (
                        <div>
                          <span className="block text-xs text-muted-foreground">Kun'yomi</span>
                          <span lang="ja" className="text-xl">{readingsKun.join('、')}</span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p lang="ja" className="text-xl">{vocabReadings.join('、')}</p>
                  )}
                </InfoSection>

                {/* Radicals (kanji) / Kanji Composition (vocab) — collapsed by default */}
                {isKanji && components.length > 0 && (
                  <InfoSection title="Radicals">
                    <RadicalList components={components} size="sm" />
                  </InfoSection>
                )}
                {!isKanji && kanjiComposition.length > 0 && (
                  <InfoSection title="Kanji Composition">
                    <div className="flex flex-wrap gap-4">
                      {kanjiComposition.map((k) => (
                        <Link
                          key={k.character}
                          to={`/kanji/${encodeURIComponent(k.character)}`}
                          className="-mx-1 flex items-center gap-2 rounded px-1 transition-colors hover:bg-accent"
                          title={`View ${k.character}`}
                        >
                          <div className="flex size-9 items-center justify-center rounded-lg border-2 border-wk-kanji-dark bg-wk-kanji font-bold text-white" lang="ja">
                            {k.character}
                          </div>
                          <span className="text-sm">{k.meanings[0]}</span>
                        </Link>
                      ))}
                    </div>
                  </InfoSection>
                )}
              </div>
            )}

            {/* Tags & comment — always shown for vocab */}
            {!isKanji && (vocabTags.length > 0 || vocabComment || vocabCreator) && (
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                {vocabTags.map((tag) => (
                  <Badge
                    key={tag}
                    variant="secondary"
                    className="rounded-full bg-wk-vocab/10 text-wk-vocab"
                  >
                    {tag}
                  </Badge>
                ))}
                {vocabComment && <span className="italic">"{vocabComment}"</span>}
                {vocabCreator && <span>by {vocabCreator}</span>}
              </div>
            )}

            <div className="flex items-center justify-center gap-4 text-center text-xs text-muted-foreground">
              <span>
                <kbd className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-foreground">Enter</kbd>{' '}
                {correct ? continueLabel : wrongLabel}
              </span>
              <Separator orientation="vertical" className="!h-3.5" />
              <span>
                <kbd className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-foreground">Backspace</kbd>{' '}
                {correct ? 'undo' : 'retype'}
              </span>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
