export const SRS_STAGE_NAMES: Record<number, string> = {
  0: 'Locked',
  1: 'Apprentice I',
  2: 'Apprentice II',
  3: 'Apprentice III',
  4: 'Apprentice IV',
  5: 'Guru I',
  6: 'Guru II',
  7: 'Master',
  8: 'Enlightened',
  9: 'Burned',
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

export const SRS_GROUP_NAMES = ['Apprentice', 'Guru', 'Master', 'Enlightened', 'Burned'] as const;

export function getSrsGroup(stage: number): string {
  if (stage <= 0) return 'Locked';
  if (stage <= 4) return 'Apprentice';
  if (stage <= 6) return 'Guru';
  if (stage === 7) return 'Master';
  if (stage === 8) return 'Enlightened';
  return 'Burned';
}

export function getSrsGroupColor(group: string): string {
  switch (group) {
    case 'Apprentice': return '#dd0093';
    case 'Guru': return '#882d9e';
    case 'Master': return '#294ddb';
    case 'Enlightened': return '#0093dd';
    case 'Burned': return '#c8a000';
    default: return '#999999';
  }
}
