import { useEffect, useState } from 'react';
import { RadicalList } from './RadicalList';
import { romajiToHiraganaLive } from '../lib/romaji';
import type { KanjiComposition } from '../lib/api';

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
  const labelBg = cardType === 'reading' ? 'bg-[#303030] text-white' : 'bg-white text-text';
  const inputStyle = !answered
    ? 'border-transparent bg-white text-text'
    : correct
      ? 'border-transparent bg-[#88cc00] text-white'
      : 'border-transparent bg-[#ff4444] text-white';

  return (
    <>
      {/* Character */}
      <div className={`${headerBg} p-12 text-white text-center`}>
        <div className="text-9xl font-bold">{display}</div>
      </div>

      {/* Reading/Meaning bar */}
      <div className={`${labelBg} py-2 text-center transition-colors duration-200`}>
        <span className="text-sm tracking-wide capitalize">
          {itemType}{' '}
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
              onInput(cardType === 'reading' ? romajiToHiraganaLive(e.target.value) : e.target.value)
            }
            onKeyDown={onKeyDown}
            onAnimationEnd={() => setShaking(false)}
            placeholder={cardType === 'reading' ? '答え' : 'Your Response'}
            disabled={answered}
            lang={cardType === 'reading' ? 'ja' : 'en'}
            className={`w-full px-4 py-3 text-center text-2xl rounded-lg border-2 transition-colors focus:outline-none ${inputStyle} ${shaking ? 'animate-shake' : ''}`}
            autoComplete="off"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
          />
          {inputError && <p className="text-center text-sm text-error mt-2">{inputError}</p>}
          {warning && !inputError && (
            <p className="text-center text-sm text-[#c08400] mt-2 font-medium">{warning}</p>
          )}
        </div>

        {answered && (
          <div className="max-w-2xl mx-auto px-4 pb-5 space-y-3">
            <div className="flex items-center justify-center gap-4">
              <span className={`font-bold text-lg ${correct ? 'text-success' : 'text-error'}`}>
                {correct ? 'Correct!' : 'Incorrect'}
              </span>
              <button
                onClick={onToggleInfo}
                className="text-xs text-text-muted hover:text-text px-2 py-1 rounded bg-surface-alt border border-border transition-colors"
              >
                {showInfo ? 'Hide Info' : 'Item Info'}{' '}
                <kbd className="ml-1 px-1 py-0.5 rounded bg-border text-[10px] font-mono">F</kbd>
              </button>
            </div>

            {showInfo && (
              <div className="space-y-1">
                {/* Meaning — expanded when on a meaning card */}
                <details open={cardType === 'meaning'} className="bg-surface-alt rounded-lg overflow-hidden">
                  <summary className="px-4 py-2 text-xs font-bold uppercase tracking-wide text-text-muted cursor-pointer hover:bg-border/50">
                    Meaning
                  </summary>
                  <div className="px-4 pb-3 space-y-2 text-sm">
                    <div>{meanings.join(', ')}</div>
                  </div>
                </details>

                {/* Reading — expanded when on a reading card */}
                <details open={cardType === 'reading'} className="bg-surface-alt rounded-lg overflow-hidden">
                  <summary className="px-4 py-2 text-xs font-bold uppercase tracking-wide text-text-muted cursor-pointer hover:bg-border/50">
                    Reading
                  </summary>
                  <div className="px-4 pb-3 space-y-2 text-sm">
                    {isKanji ? (
                      <div className="grid grid-cols-2 gap-3">
                        {readingsOn.length > 0 && (
                          <div>
                            <span className="text-text-muted text-xs">On'yomi: </span>
                            {readingsOn.join('、')}
                          </div>
                        )}
                        {readingsKun.length > 0 && (
                          <div>
                            <span className="text-text-muted text-xs">Kun'yomi: </span>
                            {readingsKun.join('、')}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div>{vocabReadings.join('、')}</div>
                    )}
                  </div>
                </details>

                {/* Radicals — kanji composition for reference */}
                {isKanji && components.length > 0 && (
                  <details className="bg-surface-alt rounded-lg overflow-hidden">
                    <summary className="px-4 py-2 text-xs font-bold uppercase tracking-wide text-text-muted cursor-pointer hover:bg-border/50">
                      Radicals
                    </summary>
                    <div className="px-4 pb-3 pt-1">
                      <RadicalList components={components} size="sm" />
                    </div>
                  </details>
                )}

                {/* Kanji Composition — constituent kanji for vocab */}
                {!isKanji && kanjiComposition.length > 0 && (
                  <details className="bg-surface-alt rounded-lg overflow-hidden">
                    <summary className="px-4 py-2 text-xs font-bold uppercase tracking-wide text-text-muted cursor-pointer hover:bg-border/50">
                      Kanji Composition
                    </summary>
                    <div className="px-4 pb-3 pt-1 flex gap-4 flex-wrap">
                      {kanjiComposition.map((k) => (
                        <div key={k.character} className="flex items-center gap-2">
                          <div className="bg-wk-kanji w-9 h-9 rounded-lg flex items-center justify-center text-white font-bold">
                            {k.character}
                          </div>
                          <span className="text-sm">{k.meanings[0]}</span>
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            )}

            {/* Tags & comment — always shown for vocab */}
            {!isKanji && (vocabTags.length > 0 || vocabComment || vocabCreator) && (
              <div className="flex items-center gap-2 flex-wrap text-xs text-text-muted">
                {vocabTags.map((tag) => (
                  <span key={tag} className="bg-wk-vocab/10 text-wk-vocab px-2 py-0.5 rounded-full font-medium">
                    {tag}
                  </span>
                ))}
                {vocabComment && <span className="italic">"{vocabComment}"</span>}
                {vocabCreator && <span>by {vocabCreator}</span>}
              </div>
            )}

            <div className="text-center text-xs text-text-muted space-x-3">
              <span>
                <kbd className="px-1.5 py-0.5 rounded bg-border text-text text-[10px] font-mono">Enter</kbd>{' '}
                {correct ? continueLabel : wrongLabel}
              </span>
              <span>
                <kbd className="px-1.5 py-0.5 rounded bg-border text-text text-[10px] font-mono">Backspace</kbd>{' '}
                {correct ? 'undo' : 'retype'}
              </span>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
