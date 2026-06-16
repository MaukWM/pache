// Shared building blocks for the kanji/vocab detail pages: a titled section
// card (always open) and the "Your Progression" block, which surfaces the
// user's SRS stage and key dates for an item.

import type { ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { SRS_STAGE_COLORS, SRS_STAGE_NAMES } from '../lib/srs';

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
    <section className="bg-surface rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xs font-bold uppercase tracking-wide text-text-muted">{title}</h2>
        {action}
      </div>
      {children}
    </section>
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
    <Section title="Your Progression">
      {!item ? (
        <p className="text-sm text-text-muted">Not started yet — add it to your lesson queue.</p>
      ) : (
        <div className="space-y-2 text-sm">
          <span
            className="inline-block text-xs font-bold px-3 py-1.5 rounded-full text-white"
            style={{ backgroundColor: SRS_STAGE_COLORS[item.srs_stage] }}
          >
            {SRS_STAGE_NAMES[item.srs_stage]}
          </span>
          <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-text-muted">
            <span>Unlocked</span>
            <span className="text-text">{fmtDate(item.unlocked_at)}</span>
            <span>Next review</span>
            <span className="text-text">{item.burned_at ? 'Burned' : fmtDate(item.next_review_at)}</span>
            {item.burned_at && (
              <>
                <span>Burned</span>
                <span className="text-text">{fmtDate(item.burned_at)}</span>
              </>
            )}
          </div>
        </div>
      )}
    </Section>
  );
}
