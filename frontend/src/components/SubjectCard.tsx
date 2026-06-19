// Genkō-yōshi (原稿用紙) practice cell: each subject character sits in a square
// manuscript-grid cell with a faint center crosshair — the guide marks you'd
// find on real Japanese writing paper. Pink ink = kanji, purple = vocab.
// States mirror SRS: dashed faint = not started, solid ink = learning, grey = burned.

import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { katakanaToHiragana } from '../lib/romaji';
import { SRS_STAGE_COLORS } from '../lib/srs';

export interface SubjectCardProps {
  type: 'kanji' | 'vocab';
  character: string;
  reading?: string;
  meaning?: string;
  /** SRS stage 1–9, or undefined when the user hasn't started the item. */
  srsStage?: number;
  selected?: boolean;
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
  const displayReading = isKanji && reading ? katakanaToHiragana(reading) : reading;
  const learned = srsStage != null;
  const burned = learned && srsStage! >= 9;

  // Char ink drives currentColor (and the crosshair): kanji renders in plain ink
  // (foreground), vocab keeps its purple. Literal class strings so Tailwind keeps them.
  const inkText = isKanji ? 'text-foreground' : 'text-wk-vocab';
  const inkHoverBorder = isKanji ? 'group-hover:border-foreground/40' : 'group-hover:border-wk-vocab';

  // Border = SRS stage color. Three distinct backgrounds:
  //   not started → bare (the manuscript grid shows through the dashed cell)
  //   learning    → solid card fill
  //   burned      → gold stage tint, so finished items stand clearly apart
  const stageColor = learned ? SRS_STAGE_COLORS[srsStage!] : undefined;
  const cellStyle = stageColor
    ? burned
      ? { borderColor: stageColor, backgroundColor: `${stageColor}29` }
      : { borderColor: stageColor }
    : undefined;

  return (
    <Link
      to={to}
      title={`${character}${meaning ? ` — ${meaning}` : ''}`}
      className="group inline-flex flex-col items-stretch gap-1.5"
    >
      <span
        lang="ja"
        style={cellStyle}
        className={cn(
          'relative grid h-16 min-w-16 place-items-center border-2 px-3 transition-colors',
          inkText,
          !learned && cn('border-border border-dashed', inkHoverBorder),
          learned && 'border-solid',
          learned && !burned && 'bg-card group-hover:bg-accent',
          selected && 'ring-2 ring-current ring-offset-2 ring-offset-background',
        )}
      >
        {/* genkō-yōshi center crosshair — inherits the cell ink via currentColor */}
        <span className="pointer-events-none absolute inset-x-2 top-1/2 h-px -translate-y-1/2 bg-current opacity-15 transition-opacity group-hover:opacity-30" />
        <span className="pointer-events-none absolute inset-y-2 left-1/2 w-px -translate-x-1/2 bg-current opacity-15 transition-opacity group-hover:opacity-30" />
        <span
          className={cn(
            'relative font-[family-name:var(--font-mincho)] text-3xl leading-none font-medium whitespace-nowrap',
            !learned && 'opacity-80',
          )}
        >
          {character}
        </span>
      </span>

      <span className="flex flex-col items-center text-center leading-tight">
        {displayReading && (
          <span lang="ja" className="text-sm whitespace-nowrap text-muted-foreground">
            {displayReading}
          </span>
        )}
        {meaning && (
          <span className="max-w-[12rem] truncate text-xs text-foreground/80">{meaning}</span>
        )}
      </span>
    </Link>
  );
}
