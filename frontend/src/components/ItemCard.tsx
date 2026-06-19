import { cn } from '@/lib/utils';

interface ItemCardProps {
  type: 'kanji' | 'vocab' | 'radical';
  character?: string;
  word?: string;
  reading?: string;
  meanings: string[];
  onClick?: () => void;
  size?: 'sm' | 'md' | 'lg';
}

const TYPE_COLORS = {
  radical: 'bg-wk-radical',
  kanji: 'bg-wk-kanji',
  vocab: 'bg-wk-vocab',
};

const SIZES = {
  sm: 'w-16 h-16 text-2xl',
  md: 'w-24 h-24 text-4xl',
  lg: 'w-32 h-32 text-5xl',
};

export function ItemCard({ type, character, word, meanings, reading, onClick, size = 'md' }: ItemCardProps) {
  const display = character || word || '?';

  return (
    <button
      onClick={onClick}
      lang="ja"
      className={cn(
        TYPE_COLORS[type],
        SIZES[size],
        'rounded-lg text-white font-bold flex flex-col items-center justify-center shadow-md transition-all cursor-pointer group relative',
        'hover:shadow-lg hover:scale-105 focus-visible:ring-[3px] focus-visible:ring-ring/40 outline-none',
      )}
    >
      <span className="leading-none">{display}</span>
      {size !== 'sm' && (
        <span className="text-xs mt-1 opacity-80 font-normal truncate max-w-full px-1">
          {reading || meanings[0] || ''}
        </span>
      )}
      <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 bg-foreground text-background text-xs rounded px-2 py-1 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
        {meanings.join(', ')}
      </div>
    </button>
  );
}
