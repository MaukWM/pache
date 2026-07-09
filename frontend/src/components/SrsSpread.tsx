import { getSrsGroup, getSrsGroupColor } from '../lib/srs';
import { type StageCounts, type TypeCounts, stageTotal, hasRadicals, hasSentences } from '../lib/spread';
import { Card } from '@/components/ui/card';

// Item spread across SRS stage groups, split by type — our take on WaniKani's
// "Item Spread" number table. Companion to the ActiveItemSpread histogram; this
// one includes burned. The 部首 column only appears when radicals are present.
const GROUPS = ['アプレンティス', 'グル', 'マスター', 'エンライテンド', 'バーンド'] as const;

export function SrsSpread({
  stages,
  loading = false,
}: {
  stages: StageCounts;
  loading?: boolean;
}) {
  const showRadical = hasRadicals(stages);
  const showSentence = hasSentences(stages);

  // Fold the 9 stages into their groups.
  const byGroup: Record<string, TypeCounts> = {};
  for (const g of GROUPS) byGroup[g] = { radical: 0, kanji: 0, vocab: 0, sentence: 0 };
  for (let stage = 1; stage <= 9; stage++) {
    const group = getSrsGroup(stage);
    const g = byGroup[group];
    const c = stages[stage];
    if (!g || !c) continue;
    g.radical += c.radical;
    g.kanji += c.kanji;
    g.vocab += c.vocab;
    g.sentence += c.sentence;
  }

  const total = GROUPS.reduce((s, g) => s + stageTotal(byGroup[g]), 0);
  const cell = (n: number) => (n ? n : '·');

  return (
    <Card className="gap-3 p-5">
      <div className="flex items-center justify-between gap-3">
        <p className="font-mono text-xs font-semibold tracking-wider text-muted-foreground uppercase">
          SRS分布
        </p>
        <span className="font-mono text-xs tracking-wider text-muted-foreground uppercase tabular-nums">
          計 {total}
        </span>
      </div>

      {loading ? (
        <div className="py-6 text-center text-sm text-muted-foreground animate-pulse">読み込み中...</div>
      ) : total === 0 ? (
        <div className="py-6 text-center text-sm text-muted-foreground">
          まだSRSに項目がありません。レッスンを始めましょう。
        </div>
      ) : (
        <div className="space-y-1">
          {/* Column header */}
          <div className="flex items-center gap-2 font-mono text-[10px] tracking-wider text-muted-foreground uppercase">
            <span className="flex-1" />
            {showRadical && <span className="w-12 text-right">部首</span>}
            <span className="w-12 text-right">漢字</span>
            <span className="w-12 text-right">語彙</span>
            {showSentence && <span className="w-12 text-right">作文</span>}
            <span className="w-12 text-right">計</span>
          </div>
          {GROUPS.map((group) => {
            const { radical, kanji, vocab, sentence } = byGroup[group];
            const rowTotal = radical + kanji + vocab + sentence;
            return (
              <div key={group} className="flex items-center gap-2 text-sm">
                <span className="h-4 w-1 shrink-0" style={{ backgroundColor: getSrsGroupColor(group) }} />
                <span className="flex-1 truncate" style={{ color: getSrsGroupColor(group) }}>
                  {group}
                </span>
                {showRadical && (
                  <span className="w-12 text-right font-mono tabular-nums">{cell(radical)}</span>
                )}
                <span className="w-12 text-right font-mono tabular-nums">{cell(kanji)}</span>
                <span className="w-12 text-right font-mono tabular-nums">{cell(vocab)}</span>
                {showSentence && (
                  <span className="w-12 text-right font-mono tabular-nums">{cell(sentence)}</span>
                )}
                <span className="w-12 text-right font-mono font-semibold tabular-nums">{cell(rowTotal)}</span>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
