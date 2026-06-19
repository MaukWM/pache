// Shared building blocks for the kanji/vocab detail pages: a titled section
// card (always open) and the "Your Progression" block, which surfaces the
// user's SRS stage and key dates for an item.

import type { ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { SRS_STAGE_COLORS, SRS_STAGE_NAMES } from '../lib/srs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export function Section({
  title,
  action,
  children,
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <Card className="gap-3 p-5">
      <CardHeader className="flex flex-row items-center justify-between p-0">
        <CardTitle className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
          {title}
        </CardTitle>
        {action}
      </CardHeader>
      <CardContent className="p-0">{children}</CardContent>
    </Card>
  );
}

function fmtDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

export function ProgressionSection({
  itemType,
  itemId,
}: {
  itemType: 'kanji' | 'vocab';
  itemId: number;
}) {
  const progress = useQuery({ queryKey: ['progress'], queryFn: () => api.getProgress() });
  const item = progress.data?.find((p) => p.item_type === itemType && p.item_id === itemId);

  return (
    <Section title="進捗">
      {!item ? (
        <p className="text-sm text-muted-foreground">まだ開始していません — 学習キューに追加してください。</p>
      ) : (
        <div className="space-y-2 text-sm">
          <span
            className="inline-block px-3 py-1 font-mono text-[11px] font-semibold uppercase tracking-wider text-white"
            style={{ backgroundColor: SRS_STAGE_COLORS[item.srs_stage] }}
          >
            {SRS_STAGE_NAMES[item.srs_stage]}
          </span>
          <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-muted-foreground">
            <span>解放日</span>
            <span className="text-foreground">{fmtDate(item.unlocked_at)}</span>
            <span>次の復習</span>
            <span className="text-foreground">{item.burned_at ? 'バーンド' : fmtDate(item.next_review_at)}</span>
            {item.burned_at && (
              <>
                <span>バーンド</span>
                <span className="text-foreground">{fmtDate(item.burned_at)}</span>
              </>
            )}
          </div>
        </div>
      )}
    </Section>
  );
}
