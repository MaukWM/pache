// WaniKani-style subject card: a bordered white tile with the character/word in
// a colored box on top, then its primary reading and meaning. Color follows WK:
// kanji = pink, vocab = purple; a dashed outline when not yet learned, and a
// charcoal fill once burned.
//
// The card sizes itself to its content (placed in a flex-wrap grid) and never
// wraps the character text — long words like 殖産興業 stretch the card onto one
// line instead of wrapping inside it, mirroring WaniKani.

export interface SubjectCardProps {
  type: 'kanji' | 'vocab';
  character: string;
  reading?: string;
  meaning?: string;
  /** SRS stage 1–9, or undefined when the user hasn't started the item. */
  srsStage?: number;
  selected?: boolean;
  onClick?: () => void;
}

export function SubjectCard({
  type,
  character,
  reading,
  meaning,
  srsStage,
  selected,
  onClick,
}: SubjectCardProps) {
  const isKanji = type === 'kanji';
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
    <button
      type="button"
      onClick={onClick}
      title={`${character}${meaning ? ` — ${meaning}` : ''}`}
      className={`inline-flex flex-col items-center gap-1 px-2.5 py-2 rounded-lg border bg-surface transition-all hover:shadow-sm hover:-translate-y-0.5 cursor-pointer ${
        selected
          ? 'border-2 ' + (isKanji ? 'border-wk-kanji' : 'border-wk-vocab')
          : 'border-border'
      }`}
    >
      <span
        lang="ja"
        className={`px-2 py-1 rounded-md border-2 text-xl font-bold leading-tight whitespace-nowrap ${boxClass}`}
      >
        {character}
      </span>
      <span className="flex flex-col items-center leading-tight text-center">
        {reading && (
          <span lang="ja" className="text-xs text-text-muted whitespace-nowrap">
            {reading}
          </span>
        )}
        {meaning && <span className="text-xs text-text max-w-[11rem] truncate">{meaning}</span>}
      </span>
    </button>
  );
}
