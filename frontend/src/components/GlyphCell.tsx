// The genkō-yōshi (原稿用紙) practice cell — the app's signature. A character in
// a manuscript-grid square with a faint center crosshair.
//   char ink : plain ink (foreground) for every type
//   border   : SRS stage color (apprentice→burned); dashed neutral if not started;
//              solid neutral for radicals (components, no SRS of their own)
//   fill     : not started = bare (grid shows through) · learning/radical = card · burned = gold tint
// Shared by grid tiles (SubjectCard, "md"), detail heroes ("lg"), and radicals ("sm").

import { cn } from '@/lib/utils';
import { SRS_STAGE_COLORS } from '../lib/srs';

const SIZE = {
  sm: { box: 'h-9 min-w-9 px-1.5 text-xl', hLine: 'inset-x-1', vLine: 'inset-y-1' },
  md: { box: 'h-16 min-w-16 px-3 text-3xl', hLine: 'inset-x-2', vLine: 'inset-y-2' },
  lg: { box: 'h-28 min-w-28 px-5 text-6xl', hLine: 'inset-x-3', vLine: 'inset-y-3' },
  xl: { box: 'h-44 min-w-44 px-6 text-8xl', hLine: 'inset-x-5', vLine: 'inset-y-5' },
} as const;

export function GlyphCell({
  type,
  character,
  srsStage,
  size = 'md',
  selected,
  className,
}: {
  type: 'kanji' | 'vocab' | 'radical';
  character: string;
  srsStage?: number;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  selected?: boolean;
  className?: string;
}) {
  const isRadical = type === 'radical';
  const learned = !isRadical && srsStage != null;
  const burned = learned && srsStage! >= 9;

  const stageColor = learned ? SRS_STAGE_COLORS[srsStage!] : undefined;
  const style = stageColor
    ? burned
      ? {
          borderColor: stageColor,
          // ~16% tint of the (theme-softened) burned color over the card.
          backgroundColor: `color-mix(in srgb, ${stageColor} 16%, transparent)`,
        }
      : { borderColor: stageColor }
    : undefined;

  const { box, hLine, vLine } = SIZE[size];

  return (
    <span
      lang="ja"
      style={style}
      className={cn(
        'relative grid shrink-0 place-items-center border-2 text-foreground transition-colors',
        box,
        // radical: neutral solid filled cell · unlearned: bare dashed · learning: card · burned: tint (inline)
        isRadical && 'border-border border-solid bg-card',
        !isRadical && !learned && 'border-border border-dashed group-hover:border-foreground/40',
        learned && 'border-solid',
        learned && !burned && 'bg-card group-hover:bg-accent',
        selected && 'ring-2 ring-current ring-offset-2 ring-offset-background',
        className,
      )}
    >
      {/* genkō crosshair — guides where to write the character; radicals are
          just components, so no practice grid for them. */}
      {!isRadical && (
        <>
          <span
            className={cn(
              'pointer-events-none absolute top-1/2 h-px -translate-y-1/2 bg-current opacity-15 transition-opacity group-hover:opacity-30',
              hLine,
            )}
          />
          <span
            className={cn(
              'pointer-events-none absolute left-1/2 w-px -translate-x-1/2 bg-current opacity-15 transition-opacity group-hover:opacity-30',
              vLine,
            )}
          />
        </>
      )}
      <span
        className={cn(
          'relative font-[family-name:var(--font-mincho)] leading-none font-medium whitespace-nowrap',
          !isRadical && !learned && 'opacity-80',
        )}
      >
        {character}
      </span>
    </span>
  );
}
