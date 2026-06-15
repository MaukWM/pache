// Shared answer-checking logic for review sessions and the lesson quiz, so both
// accept exactly the same answers.

import { finalizeRomaji } from './romaji';

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

export interface AnswerDetails {
  meanings?: string[];
  readings?: string[];
  readings_on?: string[];
  readings_kun?: string[];
}

export type AnswerOutcome =
  | { kind: 'correct'; value: string }
  | { kind: 'incorrect'; value: string }
  | { kind: 'invalid'; value: string; message: string } // not kana — keep typing
  | { kind: 'wrong-type'; value: string; message: string }; // valid but wrong reading type — warn & shake

/**
 * Evaluate a quiz answer. `value` is the normalized input to show back to the user
 * (e.g. trailing "n" finalized to ん for readings).
 *
 * Kanji readings: on'yomi is the reading we teach (the "kanji reading"). A correct
 * on'yomi passes; a correct kun'yomi is the wrong type → 'wrong-type' (warn + shake,
 * don't pass or fail). Kanji with no on'yomi fall back to accepting kun'yomi.
 */
export function evaluateAnswer(
  itemType: string,
  details: AnswerDetails,
  cardType: 'reading' | 'meaning',
  rawInput: string,
): AnswerOutcome {
  if (cardType === 'meaning') {
    const value = rawInput.trim();
    return matchesMeaning(value.toLowerCase(), details.meanings || [])
      ? { kind: 'correct', value }
      : { kind: 'incorrect', value };
  }

  // Reading: convert a trailing lone "n" to ん before checking (WaniKani-style).
  const value = finalizeRomaji(rawInput.trim());
  const trimmed = value.toLowerCase();
  if (!isKana(trimmed)) {
    return { kind: 'invalid', value, message: 'Please enter your answer in kana' };
  }

  if (itemType === 'kanji') {
    const on = details.readings_on || [];
    const kun = details.readings_kun || [];
    const expected = on.length ? on : kun;
    if (matchesReading(trimmed, expected)) return { kind: 'correct', value };
    if (on.length && matchesReading(trimmed, kun)) {
      return { kind: 'wrong-type', value, message: "We're looking for the on'yomi reading" };
    }
    return { kind: 'incorrect', value };
  }

  return matchesReading(trimmed, details.readings || [])
    ? { kind: 'correct', value }
    : { kind: 'incorrect', value };
}
