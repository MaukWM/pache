import { GlyphCell } from './GlyphCell';

interface RadicalListProps {
  components: string[];
  size?: 'sm' | 'md';
}

/**
 * Renders a kanji's visual radical components (from KRADFILE) as genkō-yōshi
 * cells. Renders nothing when there are no components.
 */
export function RadicalList({ components, size = 'md' }: RadicalListProps) {
  if (!components || components.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5">
      {components.map((c, i) => (
        <GlyphCell key={`${c}-${i}`} type="radical" character={c} size={size} />
      ))}
    </div>
  );
}
