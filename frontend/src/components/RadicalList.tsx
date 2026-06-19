import { cn } from '@/lib/utils';

interface RadicalListProps {
  components: string[];
  size?: 'sm' | 'md';
}

/**
 * Renders a kanji's visual radical components (from KRADFILE) as small chips.
 * Renders nothing when there are no components.
 */
export function RadicalList({ components, size = 'md' }: RadicalListProps) {
  if (!components || components.length === 0) return null;

  const chip =
    size === 'sm' ? 'w-8 h-8 text-lg' : 'w-10 h-10 text-2xl';

  return (
    <div className="flex flex-wrap gap-1.5">
      {components.map((c, i) => (
        <span
          key={`${c}-${i}`}
          lang="ja"
          className={cn(
            chip,
            'bg-wk-radical text-white rounded-md flex items-center justify-center font-bold leading-none shadow-sm',
          )}
        >
          {c}
        </span>
      ))}
    </div>
  );
}
