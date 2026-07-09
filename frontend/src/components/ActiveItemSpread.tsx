import { SRS_STAGE_NAMES, getSrsGroup, getSrsGroupColor } from '../lib/srs';
import { type StageCounts, stageTotal, hasRadicals, hasSentences } from '../lib/spread';
import { cn } from '@/lib/utils';
import { Card } from '@/components/ui/card';

// WaniKani's "Active Item Spread" — a histogram, one bar per active SRS stage
// (1–8; burned is excluded, it's not "active"), each stacked by type
// (radical / kanji / vocab). The number table (SrsSpread) is the companion view.
const ACTIVE_STAGES = [1, 2, 3, 4, 5, 6, 7, 8];

function niceCeil(n: number): number {
  if (n <= 0) return 1;
  const pow = Math.pow(10, Math.floor(Math.log10(n)));
  const f = n / pow;
  const nice = f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10;
  return nice * pow;
}

export function ActiveItemSpread({
  stages,
  loading = false,
  className,
}: {
  stages: StageCounts;
  loading?: boolean;
  className?: string;
}) {
  const showRadical = hasRadicals(stages);
  const showSentence = hasSentences(stages);
  const total = ACTIVE_STAGES.reduce((s, st) => s + stageTotal(stages[st]), 0);
  const max = Math.max(...ACTIVE_STAGES.map((st) => stageTotal(stages[st])));
  const top = niceCeil(max);

  return (
    <Card className={cn('gap-3 p-5', className)}>
      <p className="font-mono text-xs font-semibold tracking-wider text-muted-foreground uppercase">
        アクティブ項目分布
      </p>

      {/* Type legend */}
      <div className="flex items-center gap-3 font-mono text-[10px] tracking-wider text-muted-foreground uppercase">
        {showRadical && (
          <span className="flex items-center gap-1.5">
            <span className="size-2.5 bg-wk-radical" /> 部首
          </span>
        )}
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 bg-wk-kanji" /> 漢字
        </span>
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 bg-wk-vocab" /> 語彙
        </span>
        {showSentence && (
          <span className="flex items-center gap-1.5">
            <span className="size-2.5 bg-wk-sentence" /> 作文
          </span>
        )}
      </div>

      {loading ? (
        <div className="py-6 text-center text-sm text-muted-foreground animate-pulse">読み込み中...</div>
      ) : total === 0 ? (
        <div className="py-6 text-center text-sm text-muted-foreground">アクティブな項目がありません。</div>
      ) : (
        <div className="flex gap-2">
          {/* y-axis ticks */}
          <div className="flex h-40 w-8 shrink-0 flex-col justify-between text-right font-mono text-[10px] text-muted-foreground tabular-nums">
            <span>{top}</span>
            <span>{top / 2}</span>
            <span>0</span>
          </div>

          <div className="flex-1">
            <div className="relative h-40">
              {/* gridlines */}
              <div className="absolute inset-0 flex flex-col justify-between">
                <div className="border-t border-border/60" />
                <div className="border-t border-border/40" />
                <div className="border-t border-border/60" />
              </div>
              {/* bars — columns stretch to full chart height so the % heights resolve */}
              <div className="absolute inset-0 flex items-stretch gap-1.5">
                {ACTIVE_STAGES.map((st) => {
                  const { radical, kanji, vocab, sentence } = stages[st];
                  const stTotal = radical + kanji + vocab + sentence;
                  return (
                    <div
                      key={st}
                      className="group/bar relative flex h-full flex-1 flex-col justify-end"
                      title={`${SRS_STAGE_NAMES[st]} — 部首 ${radical} · 漢字 ${kanji} · 語彙 ${vocab} · 作文 ${sentence}`}
                    >
                      {/* WaniKani-style count, just above the bar on hover */}
                      {stTotal > 0 && (
                        <span
                          className="pointer-events-none absolute left-1/2 -translate-x-1/2 -translate-y-1 font-mono text-[10px] font-semibold tabular-nums opacity-0 transition-opacity group-hover/bar:opacity-100"
                          style={{ bottom: `${(stTotal / top) * 100}%` }}
                        >
                          {stTotal}
                        </span>
                      )}
                      <div className="shrink-0 bg-wk-sentence transition-all" style={{ height: `${(sentence / top) * 100}%` }} />
                      <div className="shrink-0 bg-wk-vocab transition-all" style={{ height: `${(vocab / top) * 100}%` }} />
                      <div className="shrink-0 bg-wk-kanji transition-all" style={{ height: `${(kanji / top) * 100}%` }} />
                      <div className="shrink-0 bg-wk-radical transition-all" style={{ height: `${(radical / top) * 100}%` }} />
                    </div>
                  );
                })}
              </div>
            </div>
            {/* x labels: stage number, colored by SRS group */}
            <div className="mt-1 flex gap-1.5">
              {ACTIVE_STAGES.map((st) => (
                <span
                  key={st}
                  className="flex-1 text-center font-mono text-[10px] tabular-nums"
                  style={{ color: getSrsGroupColor(getSrsGroup(st)) }}
                >
                  {st}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
