import { useEffect, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { RadicalList } from './RadicalList';
import { GlyphCell } from './GlyphCell';
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
  continueLabel = '次へ',
  wrongLabel = '正解にする',
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
  // Type accent: kanji = pink ink, vocab = purple. Bright var for dark surfaces,
  // the -dark variant where it must read on a light/washed surface.
  const typeColor = isKanji ? 'var(--color-wk-kanji)' : 'var(--color-wk-vocab)';
  const typeColorDark = isKanji ? 'var(--color-wk-kanji-dark)' : 'var(--color-wk-vocab-dark)';
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

  // The answer field flips to a solid correct/incorrect color once answered.
  const inputStateClass = !answered
    ? ''
    : correct
      ? 'border-success/75 bg-success/75 text-white placeholder:text-white/70'
      : 'border-destructive/75 bg-destructive/75 text-white placeholder:text-white/70';

  return (
    <>
      {/* Character — big mincho glyph on a very faint type-tinted block. Type
          (kanji/vocab) is signalled by the background tint + the glyph ink hue. */}
      <div
        className="flex items-center justify-center py-14"
        style={{ backgroundColor: `color-mix(in srgb, var(--card) 93%, ${typeColor})` }}
      >
        <span
          lang="ja"
          className="font-[family-name:var(--font-mincho)] text-8xl leading-none md:text-9xl"
          style={{ color: `color-mix(in srgb, var(--foreground) 75%, ${typeColorDark})` }}
        >
          {display}
        </span>
      </div>

      {/* Reading/Meaning bar — two-tone so you can tell at a glance which to
          answer: reading is a dark bar, meaning a light one (WaniKani-style). */}
      <div
        className="border-y border-border py-2.5 text-center"
        style={{
          backgroundColor:
            cardType === 'reading'
              ? 'color-mix(in srgb, var(--foreground) 84%, var(--background))'
              : 'var(--card)',
        }}
      >
        <span
          className={cn(
            'font-mono text-xs tracking-[0.2em]',
            cardType === 'reading' ? 'text-background/60' : 'text-muted-foreground',
          )}
        >
          {isKanji ? '漢字' : '語彙'} ・{' '}
          <span className={cardType === 'reading' ? 'text-background' : 'text-foreground'}>
            {cardType === 'reading' ? '読み' : '意味'}
          </span>
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
            placeholder={cardType === 'reading' ? '答え' : '意味を入力'}
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
              <span className={cn('text-lg font-bold', correct ? 'text-success' : 'text-destructive/75')}>
                {correct ? '正解！' : '不正解'}
              </span>
              <Button variant="outline" size="sm" onClick={onToggleInfo} className="text-muted-foreground">
                {showInfo ? '情報を隠す' : '項目情報'}{' '}
                <kbd className="ml-1 rounded bg-muted px-1 py-0.5 font-mono text-[10px]">F</kbd>
              </Button>
            </div>

            {showInfo && (
              <div className="text-left">
                {/* Meaning — auto-open only when this is a meaning card */}
                <InfoSection title="意味" open={cardType === 'meaning'}>
                  <p className="text-xl">{meanings[0]}</p>
                  {meanings.length > 1 && (
                    <p className="mt-0.5 text-sm text-muted-foreground">{meanings.slice(1).join(', ')}</p>
                  )}
                </InfoSection>

                {/* Reading — auto-open only when this is a reading card */}
                <InfoSection title="読み" open={cardType === 'reading'}>
                  {isKanji ? (
                    <div className="flex gap-8">
                      {readingsOn.length > 0 && (
                        <div>
                          <span className="block text-xs text-muted-foreground">音読み</span>
                          <span lang="ja" className="text-xl">{readingsOn.map(katakanaToHiragana).join('、')}</span>
                        </div>
                      )}
                      {readingsKun.length > 0 && (
                        <div>
                          <span className="block text-xs text-muted-foreground">訓読み</span>
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
                  <InfoSection title="部首">
                    <RadicalList components={components} size="sm" />
                  </InfoSection>
                )}
                {!isKanji && kanjiComposition.length > 0 && (
                  <InfoSection title="漢字構成">
                    <div className="flex flex-wrap gap-4">
                      {kanjiComposition.map((k) => (
                        <Link
                          key={k.character}
                          to={`/kanji/${encodeURIComponent(k.character)}`}
                          className="-mx-1 flex items-center gap-2 px-1 transition-colors hover:bg-accent"
                          title={`${k.character} を見る`}
                        >
                          <GlyphCell type="kanji" character={k.character} size="sm" />
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
                  <Badge key={tag} variant="secondary">
                    {tag}
                  </Badge>
                ))}
                {vocabComment && <span className="italic">"{vocabComment}"</span>}
                {vocabCreator && <span>作成者：{vocabCreator}</span>}
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
                {correct ? '取り消す' : '再入力'}
              </span>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
