// A grid tile: the genkō-yōshi GlyphCell plus the item's reading and meaning.

import { Link } from 'react-router-dom';
import { katakanaToHiragana } from '../lib/romaji';
import { GlyphCell } from './GlyphCell';

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
  // Kanji on'yomi is stored as katakana; show it as hiragana like WaniKani.
  const displayReading = isKanji && reading ? katakanaToHiragana(reading) : reading;

  return (
    <Link
      to={to}
      title={`${character}${meaning ? ` — ${meaning}` : ''}`}
      className="group inline-flex flex-col items-stretch gap-1.5"
    >
      <GlyphCell type={type} character={character} srsStage={srsStage} selected={selected} />
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
