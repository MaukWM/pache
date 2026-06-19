// Review-forecast bucketing.
//
// Two sources stack on each bar: "ours" (local items, from /me/progress
// next_review_at) and "wk" (live from WaniKani). Counts are per-bucket — how many
// reviews unlock in that specific hour/day, not a running total. All bucketing is
// done in the browser's local timezone.

export interface ForecastBucket {
  label: string;
  addOurs: number; // local reviews unlocking in this bucket
  addWk: number; // WaniKani reviews unlocking in this bucket
}

const HOUR_MS = 3_600_000;
const DAY_MS = 86_400_000;
const WEEKDAYS_JA = ['日', '月', '火', '水', '木', '金', '土'];

function parseTimes(iso: string[]): Date[] {
  return iso.map((s) => new Date(s)).filter((d) => !isNaN(d.getTime()));
}

function accumulate(
  starts: Date[],
  stepMs: number,
  labels: string[],
  now: Date,
  ours: Date[],
  wkUpcoming: Date[],
  wkNow: number,
): ForecastBucket[] {
  const n = starts.length;
  const addOurs = new Array<number>(n).fill(0);
  const addWk = new Array<number>(n).fill(0);

  // Items already due fold into the first (current) bucket.
  addWk[0] += wkNow;

  const base = starts[0].getTime();
  const endMs = base + n * stepMs; // exclusive end of the window
  const bucketOf = (t: Date): number => {
    const ms = t.getTime();
    if (ms < base) return 0;
    if (ms >= endMs) return -1; // beyond the window — not shown
    return Math.floor((ms - base) / stepMs);
  };

  for (const t of ours) {
    if (t.getTime() <= now.getTime()) {
      addOurs[0]++; // already due
      continue;
    }
    const i = bucketOf(t);
    if (i >= 0) addOurs[i]++;
  }
  for (const t of wkUpcoming) {
    const i = bucketOf(t);
    if (i >= 0) addWk[i]++;
  }

  return starts.map((_, i) => ({ label: labels[i], addOurs: addOurs[i], addWk: addWk[i] }));
}

// Next 24 hours, one bucket per clock hour starting from the current hour.
export function buildHourlyForecast(
  now: Date,
  oursIso: string[],
  wkUpcomingIso: string[],
  wkNow: number,
): ForecastBucket[] {
  const start = new Date(now);
  start.setMinutes(0, 0, 0);
  const starts = Array.from({ length: 24 }, (_, i) => new Date(start.getTime() + i * HOUR_MS));
  const labels = starts.map((d) => `${d.getHours()}時`);
  return accumulate(starts, HOUR_MS, labels, now, parseTimes(oursIso), parseTimes(wkUpcomingIso), wkNow);
}

// Next 7 days, one bucket per calendar day starting today (local).
export function buildDailyForecast(
  now: Date,
  oursIso: string[],
  wkUpcomingIso: string[],
  wkNow: number,
): ForecastBucket[] {
  const start = new Date(now);
  start.setHours(0, 0, 0, 0);
  const starts = Array.from({ length: 7 }, (_, i) => new Date(start.getTime() + i * DAY_MS));
  const labels = starts.map((d, i) =>
    i === 0 ? '今日' : i === 1 ? '明日' : WEEKDAYS_JA[d.getDay()],
  );
  return accumulate(starts, DAY_MS, labels, now, parseTimes(oursIso), parseTimes(wkUpcomingIso), wkNow);
}
