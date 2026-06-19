// WaniKani's own SRS terms — rendered in katakana (they're proper-noun jargon).
export const SRS_STAGE_NAMES: Record<number, string> = {
  0: 'ロック',
  1: 'アプレンティスI',
  2: 'アプレンティスII',
  3: 'アプレンティスIII',
  4: 'アプレンティスIV',
  5: 'グルI',
  6: 'グルII',
  7: 'マスター',
  8: 'エンライテンド',
  9: 'バーンド',
};

// Colors resolve to the --srs-* CSS vars (defined in index.css), so they
// automatically soften in dark mode. Safe in inline styles and color-mix().
export const SRS_STAGE_COLORS: Record<number, string> = {
  0: '#999999',
  1: 'var(--srs-apprentice)',
  2: 'var(--srs-apprentice)',
  3: 'var(--srs-apprentice)',
  4: 'var(--srs-apprentice)',
  5: 'var(--srs-guru)',
  6: 'var(--srs-guru)',
  7: 'var(--srs-master)',
  8: 'var(--srs-enlightened)',
  9: 'var(--srs-burned)',
};

export const SRS_GROUP_NAMES = ['アプレンティス', 'グル', 'マスター', 'エンライテンド', 'バーンド'] as const;

export function getSrsGroup(stage: number): string {
  if (stage <= 0) return 'ロック';
  if (stage <= 4) return 'アプレンティス';
  if (stage <= 6) return 'グル';
  if (stage === 7) return 'マスター';
  if (stage === 8) return 'エンライテンド';
  return 'バーンド';
}

export function getSrsGroupColor(group: string): string {
  switch (group) {
    case 'アプレンティス': return 'var(--srs-apprentice)';
    case 'グル': return 'var(--srs-guru)';
    case 'マスター': return 'var(--srs-master)';
    case 'エンライテンド': return 'var(--srs-enlightened)';
    case 'バーンド': return 'var(--srs-burned)';
    default: return '#999999';
  }
}
