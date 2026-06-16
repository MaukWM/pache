// WaniKani-style subject card: a bordered white tile with the character/word in
// a colored box on top, then its primary reading and meaning. Color follows WK:
// kanji = pink, vocab = purple; a dashed outline when not yet learned, and a
// charcoal fill once burned.
//
// The card sizes itself to its content (placed in a flex-wrap grid) and never
// wraps the character text — long words like 殖産興業 stretch the card onto one
// line instead of wrapping inside it, mirroring WaniKani.

import { Link } from 'react-router-dom';
import { katakanaToHiragana } from '../lib/romaji';

export interface SubjectCardProps {
  type: 'kanji' | 'vocab';
  character: string;
  reading?: string;
  meaning?: string;
  /** SRS stage 1–9, or undefined when the user hasn't started the item. */
  srsStage?: number;
  selected?: boolean;
  /** Route to the item's detail page. Rendered as a link so ctrl/cmd/middle
   *  click opens it in a new tab natively. */
  to: string;
}

export function SubjectCard({
  type,
  character,
  reading,
  meaning,
  srsStage,
  selected,
  to,
}: SubjectCardProps) {
  const isKanji = type === 'kanji';
  // Kanji on'yomi is stored as katakana; show it as hiragana like WaniKani.
  const displayReading = isKanji && reading ? katakanaToHiragana(reading) : reading;
  const learned = srsStage != null;
  const burned = srsStage != null && srsStage >= 9;

  // The colored character box, mirroring WaniKani's three visual states.
  let boxClass: string;
  if (burned) {
    boxClass = 'bg-wk-burned text-white border-solid border-wk-burned-dark';
  } else if (learned) {
    boxClass = isKanji
      ? 'bg-wk-kanji text-white border-solid border-wk-kanji-dark'
      : 'bg-wk-vocab text-white border-solid border-wk-vocab-dark';
  } else {
    boxClass = isKanji
      ? 'bg-transparent text-wk-kanji border-dashed border-wk-kanji'
      : 'bg-transparent text-wk-vocab border-dashed border-wk-vocab';
  }

  return (
    <Link
      to={to}
      title={`${character}${meaning ? ` — ${meaning}` : ''}`}
      className={`inline-flex flex-col items-center gap-1.5 px-3.5 py-3 rounded-lg border bg-surface transition-all hover:shadow-sm hover:-translate-y-0.5 cursor-pointer ${
        selected
          ? 'border-2 ' + (isKanji ? 'border-wk-kanji' : 'border-wk-vocab')
          : 'border-border'
      }`}
    >
      <span
        lang="ja"
        className={`px-3 py-1.5 rounded-md border-2 text-2xl font-bold leading-tight whitespace-nowrap ${boxClass}`}
      >
        {character}
      </span>
      <span className="flex flex-col items-center leading-tight text-center">
        {displayReading && (
          <span lang="ja" className="text-sm text-text-muted whitespace-nowrap">
            {displayReading}
          </span>
        )}
        {meaning && <span className="text-sm text-text max-w-[12rem] truncate">{meaning}</span>}
      </span>
    </Link>
  );
}
