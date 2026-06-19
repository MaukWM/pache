import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { SRS_STAGE_NAMES, SRS_STAGE_COLORS, getSrsGroup } from '../lib/srs';
import { SrsStageBar } from '../components/SrsStageBar';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';

const STAGE_FILTERS = [
  { label: 'All', value: '' },
  { label: 'Apprentice', value: '1,2,3,4' },
  { label: 'Guru', value: '5,6' },
  { label: 'Master', value: '7' },
  { label: 'Enlightened', value: '8' },
  { label: 'Burned', value: '9' },
];

export function ProgressPage() {
  const [stageFilter, setStageFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');

  const params: Record<string, string> = {};
  if (stageFilter) params.srs_stage = stageFilter;
  if (typeFilter) params.item_type = typeFilter;

  const progress = useQuery({
    queryKey: ['progress', params],
    queryFn: () => api.getProgress(Object.keys(params).length ? params : undefined),
  });

  // Compute SRS group counts from unfiltered data
  const allProgress = useQuery({
    queryKey: ['progress'],
    queryFn: () => api.getProgress(),
  });

  const srsCounts: Record<string, number> = {};
  if (allProgress.data) {
    for (const item of allProgress.data) {
      const group = getSrsGroup(item.srs_stage);
      srsCounts[group] = (srsCounts[group] || 0) + 1;
    }
  }

  const items = progress.data || [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Progress</h1>

      <SrsStageBar counts={srsCounts} />

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        {STAGE_FILTERS.map((f) => (
          <Button
            key={f.value}
            size="sm"
            variant={stageFilter === f.value ? 'default' : 'outline'}
            className="rounded-full"
            onClick={() => setStageFilter(f.value)}
          >
            {f.label}
          </Button>
        ))}
        <Separator orientation="vertical" className="mx-1 h-6" />
        <Button
          size="sm"
          variant={typeFilter === 'kanji' ? 'default' : 'outline'}
          className={cn('rounded-full', typeFilter === 'kanji' && 'bg-wk-kanji hover:bg-wk-kanji/90')}
          onClick={() => setTypeFilter(typeFilter === 'kanji' ? '' : 'kanji')}
        >
          Kanji
        </Button>
        <Button
          size="sm"
          variant={typeFilter === 'vocab' ? 'default' : 'outline'}
          className={cn('rounded-full', typeFilter === 'vocab' && 'bg-wk-vocab hover:bg-wk-vocab/90')}
          onClick={() => setTypeFilter(typeFilter === 'vocab' ? '' : 'vocab')}
        >
          Vocab
        </Button>
      </div>

      {/* Items */}
      {progress.isLoading ? (
        <div className="animate-pulse text-muted-foreground">Loading...</div>
      ) : items.length === 0 ? (
        <Card className="items-center p-8 text-center text-muted-foreground">
          No items match the current filter.
        </Card>
      ) : (
        <div className="grid gap-2">
          {items.map((item) => {
            const isKanji = item.item_type === 'kanji';
            const display = item.item_details.character || item.item_details.word || '?';
            const bgColor = isKanji ? 'bg-wk-kanji' : 'bg-wk-vocab';
            const stageColor = SRS_STAGE_COLORS[item.srs_stage];

            return (
              <Card
                key={`${item.item_type}-${item.item_id}`}
                className="flex-row items-center gap-3 p-3"
              >
                <div
                  className={cn(
                    'flex size-10 shrink-0 items-center justify-center rounded-lg font-bold text-white',
                    bgColor,
                  )}
                  lang="ja"
                >
                  {display}
                </div>
                <div className="min-w-0 flex-1">
                  <span className="font-bold" lang="ja">{display}</span>
                  <span className="ml-2 text-sm text-muted-foreground">
                    {item.item_details.meanings?.join(', ')}
                  </span>
                </div>
                <div
                  className="shrink-0 rounded-full px-2.5 py-1 text-xs font-bold text-white"
                  style={{ backgroundColor: stageColor }}
                >
                  {SRS_STAGE_NAMES[item.srs_stage]}
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
