/**
 * Simple romaji to hiragana/katakana converter for search.
 * Not exhaustive — covers common syllables for search matching.
 */

const ROMAJI_TO_HIRAGANA: [string, string][] = [
  // Double consonants (must come before single)
  ['kya', 'きゃ'], ['kyu', 'きゅ'], ['kyo', 'きょ'],
  ['sha', 'しゃ'], ['shi', 'し'], ['shu', 'しゅ'], ['sho', 'しょ'],
  ['cha', 'ちゃ'], ['chi', 'ち'], ['chu', 'ちゅ'], ['cho', 'ちょ'],
  ['tsu', 'つ'],
  ['nya', 'にゃ'], ['nyu', 'にゅ'], ['nyo', 'にょ'],
  ['hya', 'ひゃ'], ['hyu', 'ひゅ'], ['hyo', 'ひょ'],
  ['mya', 'みゃ'], ['myu', 'みゅ'], ['myo', 'みょ'],
  ['rya', 'りゃ'], ['ryu', 'りゅ'], ['ryo', 'りょ'],
  ['gya', 'ぎゃ'], ['gyu', 'ぎゅ'], ['gyo', 'ぎょ'],
  ['bya', 'びゃ'], ['byu', 'びゅ'], ['byo', 'びょ'],
  ['pya', 'ぴゃ'], ['pyu', 'ぴゅ'], ['pyo', 'ぴょ'],
  ['ja', 'じゃ'], ['ju', 'じゅ'], ['jo', 'じょ'],
  // Basic syllables
  ['ka', 'か'], ['ki', 'き'], ['ku', 'く'], ['ke', 'け'], ['ko', 'こ'],
  ['sa', 'さ'], ['si', 'し'], ['su', 'す'], ['se', 'せ'], ['so', 'そ'],
  ['ta', 'た'], ['ti', 'ち'], ['tu', 'つ'], ['te', 'て'], ['to', 'と'],
  ['na', 'な'], ['ni', 'に'], ['nu', 'ぬ'], ['ne', 'ね'], ['no', 'の'],
  ['ha', 'は'], ['hi', 'ひ'], ['hu', 'ふ'], ['fu', 'ふ'], ['he', 'へ'], ['ho', 'ほ'],
  ['ma', 'ま'], ['mi', 'み'], ['mu', 'む'], ['me', 'め'], ['mo', 'も'],
  ['ya', 'や'], ['yu', 'ゆ'], ['yo', 'よ'],
  ['ra', 'ら'], ['ri', 'り'], ['ru', 'る'], ['re', 'れ'], ['ro', 'ろ'],
  ['wa', 'わ'], ['wi', 'ゐ'], ['wo', 'を'],
  ['ga', 'が'], ['gi', 'ぎ'], ['gu', 'ぐ'], ['ge', 'げ'], ['go', 'ご'],
  ['za', 'ざ'], ['ji', 'じ'], ['zu', 'ず'], ['ze', 'ぜ'], ['zo', 'ぞ'],
  ['da', 'だ'], ['di', 'ぢ'], ['du', 'づ'], ['de', 'で'], ['do', 'ど'],
  ['ba', 'ば'], ['bi', 'び'], ['bu', 'ぶ'], ['be', 'べ'], ['bo', 'ぼ'],
  ['pa', 'ぱ'], ['pi', 'ぴ'], ['pu', 'ぷ'], ['pe', 'ぺ'], ['po', 'ぽ'],
  // Vowels
  ['a', 'あ'], ['i', 'い'], ['u', 'う'], ['e', 'え'], ['o', 'お'],
  ['n', 'ん'],
];

const HIRAGANA_TO_KATAKANA_OFFSET = 0x30A0 - 0x3040;

function hiraganaToKatakana(str: string): string {
  return str.replace(/[\u3040-\u309F]/g, (ch) =>
    String.fromCharCode(ch.charCodeAt(0) + HIRAGANA_TO_KATAKANA_OFFSET)
  );
}

export function romajiToKana(input: string): { hiragana: string; katakana: string } | null {
  const lower = input.toLowerCase();
  // Only convert if it looks like romaji (all ascii letters)
  if (!/^[a-z]+$/.test(lower)) return null;

  let result = lower;
  // nn → ん (before double consonant handler)
  result = result.replaceAll('nn', 'ん');
  // Handle double consonants (っ)
  result = result.replace(/([kstpgbdmr])\1/g, 'っ$1');

  for (const [romaji, kana] of ROMAJI_TO_HIRAGANA) {
    result = result.replaceAll(romaji, kana);
  }

  const hiragana = result;
  const katakana = hiraganaToKatakana(hiragana);
  return { hiragana, katakana };
}

/**
 * Live romaji-to-hiragana for typing. Keeps trailing consonants
 * as romaji so "n" doesn't become "ん" until we know it's not "na", "ni", etc.
 */
export function romajiToHiraganaLive(input: string): string {
  const lower = input.toLowerCase();

  // Split into already-converted kana and trailing ascii
  let i = 0;
  let kanaPrefix = '';
  while (i < lower.length && lower.charCodeAt(i) > 0x7f) {
    kanaPrefix += lower[i];
    i++;
  }
  const asciiTail = lower.slice(i);
  if (!asciiTail) return lower;

  // Only convert the ascii portion
  let result = asciiTail;

  // nn → ん
  result = result.replaceAll('nn', 'ん');
  // Handle double consonants
  result = result.replace(/([kstpgbdmr])\1/g, 'っ$1');

  // Check if the tail ends with a consonant that could start a new syllable
  const trailingConsonant = result.match(/[bcdfghjklmnpqrstvwxyz]+$/);
  const toConvert = trailingConsonant
    ? result.slice(0, result.length - trailingConsonant[0].length)
    : result;
  const trailing = trailingConsonant ? trailingConsonant[0] : '';

  // Convert the safe portion
  let converted = toConvert;
  for (const [romaji, kana] of ROMAJI_TO_HIRAGANA) {
    converted = converted.replaceAll(romaji, kana);
  }

  return kanaPrefix + converted + trailing;
}
