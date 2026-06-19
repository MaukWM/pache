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

export const SRS_STAGE_COLORS: Record<number, string> = {
  0: '#999999',
  1: '#dd0093',
  2: '#dd0093',
  3: '#dd0093',
  4: '#dd0093',
  5: '#882d9e',
  6: '#882d9e',
  7: '#294ddb',
  8: '#0093dd',
  9: '#c8a000',
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
    case 'アプレンティス': return '#dd0093';
    case 'グル': return '#882d9e';
    case 'マスター': return '#294ddb';
    case 'エンライテンド': return '#0093dd';
    case 'バーンド': return '#c8a000';
    default: return '#999999';
  }
}
