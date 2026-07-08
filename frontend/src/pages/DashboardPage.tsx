import { useMemo, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ExternalLink } from 'lucide-react';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import { cn } from '@/lib/utils';
import { buildHourlyForecast, buildDailyForecast } from '../lib/forecast';
import { buildStageCounts, type SpreadMode } from '../lib/spread';
import { ReviewForecast } from '../components/ReviewForecast';
import { ActiveItemSpread } from '../components/ActiveItemSpread';
import { SrsSpread } from '../components/SrsSpread';

// A labelled pair of tiles bound into one bordered box (shared divider, no gap),
// with a section header + colored rule above (漢字・語彙 = pink→purple, 作文 = green).
function StatGroup({
  label,
  accent,
  children,
}: {
  label: string;
  accent: string;
  children: ReactNode;
}) {
  return (
    <section className="space-y-2">
      <div className="flex items-center gap-3">
        <span className="font-mono text-[11px] tracking-[0.2em] text-muted-foreground uppercase">
          {label}
        </span>
        <span className={cn('h-0.5 flex-1', accent)} />
      </div>
      <div className="grid grid-cols-2 divide-x-2 divide-border border-2 border-border">
        {children}
      </div>
    </section>
  );
}

// A genkō-style stat cell: big mincho numeral, mono label. Lives inside a StatGroup.
// "Ready" marker (not a loud color fill) signals there's something to do.
function StatTile({ to, count, label }: { to: string; count: number; label: string }) {
  const active = count > 0;
  return (
    <Link
      to={to}
      className="group relative flex flex-col items-center justify-center bg-card p-10 transition-colors hover:bg-accent"
    >
      {active && (
        <span className="absolute top-3 right-3 font-mono text-[10px] tracking-wider text-muted-foreground uppercase">
          準備完了
        </span>
      )}
      <span
        className={cn(
          'font-[family-name:var(--font-mincho)] text-6xl leading-none tabular-nums',
          active ? 'text-foreground' : 'text-muted-foreground/60',
        )}
      >
        {count}
      </span>
      <span className="mt-3 font-mono text-xs tracking-[0.2em] text-muted-foreground uppercase">
        {label}
      </span>
    </Link>
  );
}

const SPREAD_MODES: { key: SpreadMode; label: string }[] = [
  { key: 'combined', label: '合計' },
  { key: 'site', label: 'このサイト' },
  { key: 'wanikani', label: '鰐蟹' },
];

// Global source toggle for every data widget; 合計/鰐蟹 disabled without a WK key.
function SourceToggle({
  mode,
  onChange,
  wkConfigured,
}: {
  mode: SpreadMode;
  onChange: (m: SpreadMode) => void;
  wkConfigured: boolean;
}) {
  return (
    <div className="flex gap-0.5">
      {SPREAD_MODES.map((m) => {
        const disabled = !wkConfigured && m.key !== 'site';
        return (
          <button
            key={m.key}
            type="button"
            disabled={disabled}
            onClick={() => onChange(m.key)}
            className={cn(
              'border px-2 py-0.5 font-mono text-[10px] tracking-wider uppercase transition-colors',
              mode === m.key
                ? 'border-foreground bg-foreground text-background'
                : 'border-border text-muted-foreground hover:text-foreground',
              disabled && 'cursor-not-allowed opacity-40 hover:text-muted-foreground',
            )}
          >
            {m.label}
          </button>
        );
      })}
    </div>
  );
}

export function DashboardPage() {
  const { user } = useAuth();
  const [rawMode, setRawMode] = useState<SpreadMode>('combined');

  const reviews = useQuery({ queryKey: ['reviews'], queryFn: api.getReviews });
  const queue = useQuery({ queryKey: ['queue'], queryFn: api.getQueue });
  const sentenceLessons = useQuery({
    queryKey: ['sentenceLessons'],
    queryFn: api.getSentenceLessons,
  });
  const sentenceReviews = useQuery({
    queryKey: ['sentenceReviews'],
    queryFn: api.getDueSentences,
  });
  const progress = useQuery({ queryKey: ['progress'], queryFn: () => api.getProgress() });
  const wanikani = useQuery({
    queryKey: ['wanikani-status'],
    queryFn: api.getWanikaniStatus,
    retry: false,
  });
  const forecast = useQuery({
    queryKey: ['wanikani-forecast'],
    queryFn: api.getWanikaniForecast,
    retry: false,
  });
  const spread = useQuery({
    queryKey: ['wanikani-spread'],
    queryFn: api.getWanikaniSpread,
    retry: false,
    staleTime: 5 * 60 * 1000, // heavy live call — cache for a few minutes
  });

  const reviewCount = reviews.data?.length ?? 0;
  const lessonCount = queue.data?.filter((i) => !i.locked).length ?? 0;
  const sentenceLessonCount = sentenceLessons.data?.length ?? 0;
  const sentenceReviewCount = sentenceReviews.data?.length ?? 0;
  const wkConfigured = wanikani.data?.configured ?? false;
  const wkDue = wanikani.data?.reviews_due ?? 0;
  // Without a WK key only "this site" is meaningful.
  const mode: SpreadMode = wkConfigured ? rawMode : 'site';

  // Local review times — must mirror /me/reviews exactly: only MANUAL-source,
  // non-burned items count as our reviews. WaniKani-source items review on WK
  // (any next_review_at they carry is stale) and belong to the 鰐蟹 forecast.
  const oursIso = useMemo(
    () =>
      (progress.data ?? [])
        .filter((p) => p.source === 'manual' && p.srs_stage < 9 && !!p.next_review_at)
        .map((p) => p.next_review_at as string),
    [progress.data],
  );
  const wkUpcoming = forecast.data?.upcoming ?? [];
  const wkNow = forecast.data?.available_now ?? 0;
  const wkForecastConfigured = forecast.data?.configured ?? false;

  const { hourly, daily } = useMemo(() => {
    const now = new Date();
    return {
      hourly: buildHourlyForecast(now, oursIso, wkUpcoming, wkNow),
      daily: buildDailyForecast(now, oursIso, wkUpcoming, wkNow),
    };
  }, [oursIso, wkUpcoming, wkNow]);

  const spreadStages = useMemo(
    () => buildStageCounts(mode, progress.data ?? [], spread.data?.stages ?? []),
    [mode, progress.data, spread.data],
  );

  const forecastLoading = progress.isLoading || forecast.isLoading;
  const spreadLoading = progress.isLoading || (mode !== 'site' && spread.isLoading);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">おかえりなさい、{user?.username}！</h1>

      {/* Two grouped pairs: 漢字・語彙 (pink→purple) over 作文 (green). */}
      <div className="space-y-5">
        <StatGroup label="漢字・語彙" accent="bg-gradient-to-r from-wk-kanji to-wk-vocab">
          <StatTile to="/lessons" count={lessonCount} label="レッスン" />
          <StatTile to="/reviews" count={reviewCount} label="復習" />
        </StatGroup>
        <StatGroup label="作文" accent="bg-wk-sentence">
          <StatTile to="/sentences/lessons" count={sentenceLessonCount} label="レッスン" />
          <StatTile to="/sentences/review" count={sentenceReviewCount} label="復習" />
        </StatGroup>
      </div>

      {wkConfigured && (
        <a
          href="https://www.wanikani.com/subjects/review"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-between border border-border bg-card p-5 transition-colors hover:bg-accent"
        >
          <div className="flex items-center gap-3">
            <span className="font-[family-name:var(--font-mincho)] text-3xl leading-none tabular-nums">{wkDue}</span>
            <span className="text-sm text-muted-foreground">鰐蟹の復習</span>
          </div>
          <span className="flex items-center gap-1.5 font-mono text-xs tracking-wider text-muted-foreground uppercase">
            鰐蟹を開く
            <ExternalLink className="size-3.5" />
          </span>
        </a>
      )}

      {/* One global toggle drives every widget below. */}
      <div className="flex items-center justify-between gap-3">
        <span className="font-mono text-xs tracking-wider text-muted-foreground uppercase">表示</span>
        <SourceToggle mode={mode} onChange={setRawMode} wkConfigured={wkConfigured} />
      </div>

      {/* 2-column: item-spread views on the left, the two forecasts on the right. */}
      <div className="grid items-start gap-4 md:grid-cols-2">
        <div className="space-y-4">
          <ActiveItemSpread stages={spreadStages} loading={spreadLoading} />
          <SrsSpread stages={spreadStages} loading={spreadLoading} />
        </div>
        <div className="space-y-4">
          <ReviewForecast
            title="次の24時間"
            buckets={hourly}
            wkConfigured={wkForecastConfigured}
            mode={mode}
            hideEmpty
            dropCurrent
            loading={forecastLoading}
          />
          <ReviewForecast
            title="次の7日間"
            buckets={daily}
            wkConfigured={wkForecastConfigured}
            mode={mode}
            loading={forecastLoading}
          />
        </div>
      </div>
    </div>
  );
}
