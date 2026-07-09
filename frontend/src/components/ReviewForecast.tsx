import type { ForecastBucket } from '../lib/forecast';
import type { SpreadMode } from '../lib/spread';
import { cn } from '@/lib/utils';
import { Card } from '@/components/ui/card';

// Review forecast: one row per time bucket, a horizontal bar split into our-site
// ink + WaniKani amber. The bar shows reviews unlocking *in that bucket only*;
// each row also carries WaniKani-style numbers — the per-source increment
// (+ours/+wk) plus a cumulative running total (how many you'd have waiting at
// that time, seeded by what's already due). The header shows the window's grand
// total. The shared source toggle (mode) decides which source(s) to show.
// Used twice on the dashboard (next 24h, next 7 days).
export function ReviewForecast({
  title,
  buckets,
  wkConfigured,
  mode,
  includeSentence = true,
  hideEmpty = false,
  dropCurrent = false,
  loading = false,
}: {
  title: string;
  buckets: ForecastBucket[];
  wkConfigured: boolean;
  mode: SpreadMode;
  /** Whether to show the 作文 (sentence) series — off for accounts without access. */
  includeSentence?: boolean;
  /** Drop buckets where nothing new arrives (keeps the hourly view compact). */
  hideEmpty?: boolean;
  /**
   * Hide the current (first) block as a row — it's already on the review button.
   * Its count still seeds the cumulative baseline so totals match what's waiting.
   */
  dropCurrent?: boolean;
  loading?: boolean;
}) {
  const showOurs = mode !== 'wanikani';
  const showSentence = includeSentence && mode !== 'wanikani'; // 作文 = local, if user has access
  const showWk = wkConfigured && mode !== 'site';
  const valueOf = (b: ForecastBucket) =>
    (showOurs ? b.addOurs : 0) + (showSentence ? b.addSentence : 0) + (showWk ? b.addWk : 0);

  // Cumulative running total over the whole window (respects the source toggle).
  // The current block seeds the baseline even when its row is dropped, so the
  // last visible row's total equals the grand total in the header.
  let running = 0;
  const enriched = buckets.map((b) => {
    running += valueOf(b);
    return { bucket: b, increment: valueOf(b), cumulative: running };
  });
  const grandTotal = running;

  let rows = dropCurrent ? enriched.slice(1) : enriched;
  if (hideEmpty) rows = rows.filter((r) => r.increment > 0);
  const max = Math.max(1, ...rows.map((r) => r.increment));

  return (
    <Card className="gap-3 p-5">
      <div className="flex items-center justify-between">
        <p className="font-mono text-xs font-semibold tracking-wider text-muted-foreground uppercase">
          {title}
        </p>
        <span className="font-[family-name:var(--font-mincho)] text-lg leading-none tabular-nums">
          +{grandTotal}
        </span>
      </div>

      {/* Legend — reflects the active source(s). */}
      <div className="flex items-center gap-4 font-mono text-[10px] tracking-wider text-muted-foreground uppercase">
        {showOurs && (
          <span className="flex items-center gap-1.5">
            <span className="size-2.5 bg-foreground" /> 漢字・語彙
          </span>
        )}
        {showSentence && (
          <span className="flex items-center gap-1.5">
            <span className="size-2.5 bg-wk-sentence" /> 作文
          </span>
        )}
        {showWk && (
          <span className="flex items-center gap-1.5">
            <span className="size-2.5" style={{ backgroundColor: 'var(--forecast-wk)' }} /> 鰐蟹
          </span>
        )}
      </div>

      {loading ? (
        <div className="py-6 text-center text-sm text-muted-foreground animate-pulse">読み込み中...</div>
      ) : rows.length === 0 ? (
        <div className="py-6 text-center text-sm text-muted-foreground">予定されている復習はありません。</div>
      ) : (
        <div className="space-y-1">
          {rows.map(({ bucket: b, increment, cumulative }, i) => (
            <div key={`${b.label}-${i}`} className="flex items-center gap-2 text-xs">
              <span className="w-10 shrink-0 text-right font-mono text-muted-foreground tabular-nums">
                {b.label}
              </span>
              <div className="flex h-4 flex-1 items-stretch overflow-hidden bg-secondary">
                {showOurs && (
                  <div className="bg-foreground transition-all" style={{ width: `${(b.addOurs / max) * 100}%` }} />
                )}
                {showSentence && (
                  <div className="bg-wk-sentence transition-all" style={{ width: `${(b.addSentence / max) * 100}%` }} />
                )}
                {showWk && (
                  <div className="transition-all" style={{ width: `${(b.addWk / max) * 100}%`, backgroundColor: 'var(--forecast-wk)' }} />
                )}
              </div>
              {/* Per-source increments — kanji/vocab · 作文 (green) · 鰐蟹. */}
              <span
                className={cn(
                  'flex shrink-0 items-center justify-end gap-1 font-mono text-[11px] tabular-nums',
                  increment > 0 ? 'text-muted-foreground' : 'text-muted-foreground/40',
                )}
              >
                {showOurs && <span className="w-6 text-right">+{b.addOurs}</span>}
                {showSentence && <span className="w-6 text-right text-wk-sentence">+{b.addSentence}</span>}
                {showWk && <span className="w-6 text-right">+{b.addWk}</span>}
              </span>
              <span className="w-10 shrink-0 text-right font-mono tabular-nums text-foreground">
                {cumulative}
              </span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
