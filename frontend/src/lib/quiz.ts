// Shared answer-checking logic for review sessions and the lesson quiz, so both
// accept exactly the same answers.

export function levenshtein(a: string, b: string): number {
  const m = a.length, n = b.length;
  const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));
  for (let i = 0; i <= m; i++) dp[i][0] = i;
  for (let j = 0; j <= n; j++) dp[0][j] = j;
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      dp[i][j] = a[i - 1] === b[j - 1]
        ? dp[i - 1][j - 1]
        : 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]);
    }
  }
  return dp[m][n];
}

// Allowed typo tolerance for meaning answers, scaled by answer length.
export function allowedDistance(len: number): number {
  if (len <= 3) return 0;
  if (len <= 5) return 1;
  if (len <= 7) return 2;
  return Math.min(3, Math.floor(len * 0.3));
}

export function isKana(str: string): boolean {
  return /^[぀-ゟ゠-ヿ　-〿ー]+$/.test(str);
}

export function katakanaToHiragana(str: string): string {
  return str.replace(/[゠-ヿ]/g, (ch) =>
    String.fromCharCode(ch.charCodeAt(0) - 0x60),
  );
}

// Normalize dictionary readings (strip okurigana dots/hyphens, katakana -> hiragana).
export function normalizeReadings(readings: string[]): string[] {
  return readings.map((r) => katakanaToHiragana(r.replace(/[.\-]/g, '')));
}

export function matchesReading(input: string, readings: string[]): boolean {
  const trimmed = input.trim().toLowerCase();
  if (!trimmed) return false;
  return normalizeReadings(readings).some((r) => r === katakanaToHiragana(trimmed));
}

export function matchesMeaning(input: string, meanings: string[]): boolean {
  const trimmed = input.trim().toLowerCase();
  if (!trimmed) return false;
  return meanings.some((m) => {
    const lower = m.toLowerCase();
    if (lower === trimmed) return true;
    return levenshtein(lower, trimmed) <= allowedDistance(lower.length);
  });
}
