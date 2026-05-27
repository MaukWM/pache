import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { SRS_STAGE_NAMES, SRS_STAGE_COLORS, getSrsGroup } from '../lib/srs';
import { SrsStageBar } from '../components/SrsStageBar';

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
      <div className="flex gap-2 flex-wrap">
        {STAGE_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setStageFilter(f.value)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
              stageFilter === f.value
                ? 'bg-wk-kanji text-white'
                : 'bg-surface text-text-muted hover:bg-border'
            }`}
          >
            {f.label}
          </button>
        ))}
        <div className="w-px bg-border mx-1" />
        <button
          onClick={() => setTypeFilter(typeFilter === 'kanji' ? '' : 'kanji')}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            typeFilter === 'kanji'
              ? 'bg-wk-kanji text-white'
              : 'bg-surface text-text-muted hover:bg-border'
          }`}
        >
          Kanji
        </button>
        <button
          onClick={() => setTypeFilter(typeFilter === 'vocab' ? '' : 'vocab')}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            typeFilter === 'vocab'
              ? 'bg-wk-vocab text-white'
              : 'bg-surface text-text-muted hover:bg-border'
          }`}
        >
          Vocab
        </button>
      </div>

      {/* Items */}
      {progress.isLoading ? (
        <div className="text-text-muted animate-pulse">Loading...</div>
      ) : items.length === 0 ? (
        <div className="bg-surface rounded-xl p-8 text-center text-text-muted">
          No items match the current filter.
        </div>
      ) : (
        <div className="grid gap-2">
          {items.map((item) => {
            const isKanji = item.item_type === 'kanji';
            const display = item.item_details.character || item.item_details.word || '?';
            const bgColor = isKanji ? 'bg-wk-kanji' : 'bg-wk-vocab';
            const stageColor = SRS_STAGE_COLORS[item.srs_stage];

            return (
              <div
                key={`${item.item_type}-${item.item_id}`}
                className="bg-surface rounded-lg p-3 shadow-sm flex items-center gap-3"
              >
                <div
                  className={`${bgColor} w-10 h-10 rounded-lg flex items-center justify-center text-white font-bold shrink-0`}
                >
                  {display}
                </div>
                <div className="flex-1 min-w-0">
                  <span className="font-bold">{display}</span>
                  <span className="text-text-muted text-sm ml-2">
                    {item.item_details.meanings?.join(', ')}
                  </span>
                </div>
                <div
                  className="text-xs font-bold px-2.5 py-1 rounded-full text-white shrink-0"
                  style={{ backgroundColor: stageColor }}
                >
                  {SRS_STAGE_NAMES[item.srs_stage]}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
