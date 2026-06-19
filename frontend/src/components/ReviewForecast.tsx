import type { ForecastBucket } from '../lib/forecast';
import type { SpreadMode } from '../lib/spread';
import { cn } from '@/lib/utils';
import { Card } from '@/components/ui/card';

// Review forecast: one row per time bucket, a horizontal bar split into our-site
// ink + WaniKani amber. Each bar shows reviews unlocking *in that bucket only*
// (not a cumulative running total); the header shows the window's grand total.
// The shared source toggle (mode) decides which source(s) to show.
// Used twice on the dashboard (next 24h, next 7 days).
export function ReviewForecast({
  title,
  buckets,
  wkConfigured,
  mode,
  hideEmpty = false,
  loading = false,
}: {
  title: string;
  buckets: ForecastBucket[];
  wkConfigured: boolean;
  mode: SpreadMode;
  /** Drop buckets where nothing new arrives (keeps the hourly view compact). */
  hideEmpty?: boolean;
  loading?: boolean;
}) {
  const showOurs = mode !== 'wanikani';
  const showWk = wkConfigured && mode !== 'site';
  const valueOf = (b: ForecastBucket) => (showOurs ? b.addOurs : 0) + (showWk ? b.addWk : 0);

  const rows = hideEmpty ? buckets.filter((b) => valueOf(b) > 0) : buckets;
  const max = Math.max(1, ...buckets.map(valueOf));
  const grandTotal = buckets.reduce((s, b) => s + valueOf(b), 0);

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
            <span className="size-2.5 bg-foreground" /> このサイト
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
      ) : grandTotal === 0 ? (
        <div className="py-6 text-center text-sm text-muted-foreground">予定されている復習はありません。</div>
      ) : (
        <div className="space-y-1">
          {rows.map((b, i) => {
            const value = valueOf(b);
            return (
              <div key={`${b.label}-${i}`} className="flex items-center gap-2 text-xs">
                <span className="w-10 shrink-0 text-right font-mono text-muted-foreground tabular-nums">
                  {b.label}
                </span>
                <div className="flex h-4 flex-1 items-stretch overflow-hidden bg-secondary">
                  {showOurs && (
                    <div className="bg-foreground transition-all" style={{ width: `${(b.addOurs / max) * 100}%` }} />
                  )}
                  {showWk && (
                    <div className="transition-all" style={{ width: `${(b.addWk / max) * 100}%`, backgroundColor: 'var(--forecast-wk)' }} />
                  )}
                </div>
                <span className={cn('w-10 shrink-0 text-right font-mono tabular-nums', value > 0 ? 'text-foreground' : 'text-muted-foreground/40')}>
                  {value}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
