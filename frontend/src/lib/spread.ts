import type { ProgressItem, WanikaniSpreadStage } from './api';

// Item-spread data, shared by the histogram (ActiveItemSpread) and the number
// table (SrsSpread). Source modes:
//   'site'      — this site only: MANUAL-source progress, imported kanji excluded.
//   'wanikani'  — live WaniKani SRS distribution.
//   'combined'  — both summed (no double-count: imported locals are represented
//                 by the live WK data, not by their stale local copies).
export type SpreadMode = 'combined' | 'site' | 'wanikani';

export interface TypeCounts {
  radical: number;
  kanji: number;
  vocab: number;
}

export type StageCounts = Record<number, TypeCounts>;

function emptyStages(): StageCounts {
  const out: StageCounts = {};
  for (let stage = 1; stage <= 9; stage++) out[stage] = { radical: 0, kanji: 0, vocab: 0 };
  return out;
}

export function buildStageCounts(
  mode: SpreadMode,
  progress: ProgressItem[],
  wkStages: WanikaniSpreadStage[],
): StageCounts {
  const out = emptyStages();

  if (mode !== 'wanikani') {
    for (const item of progress) {
      // This site = manually-learned items only. Imported (source=wanikani)
      // items are WaniKani's data and would pollute the local picture.
      if (item.source !== 'manual') continue;
      const bucket = out[item.srs_stage];
      if (!bucket) continue; // skip locked (0)
      if (item.item_type === 'vocab') bucket.vocab++;
      else bucket.kanji++;
    }
  }

  if (mode !== 'site') {
    for (const st of wkStages) {
      const bucket = out[st.srs_stage];
      if (!bucket) continue;
      bucket.radical += st.radical;
      bucket.kanji += st.kanji;
      bucket.vocab += st.vocab;
    }
  }

  return out;
}

export function stageTotal(c: TypeCounts): number {
  return c.radical + c.kanji + c.vocab;
}

// Whether any stage carries radicals — drives whether the 部首 column/series shows.
export function hasRadicals(stages: StageCounts): boolean {
  return Object.values(stages).some((c) => c.radical > 0);
}
